#!/usr/bin/env python3
"""Track A 인테이크(turnkey) — 사진 폴더 → rich Vision 추출 → baseline 후보 라벨시트.

사용자가 사진 30~100장을 폴더에 넣으면: 각 사진 rich Vision 추출 → 기인물 RESOLVE →
후보(절/관 관찰조문 ∪ 횡단, 시각가능) → RANK 정렬 → 사람 라벨시트 CSV.
사람이 LABEL(y/n/m) 기입 → score_label_sheet.py로 대규모 사진 정확도 측정.

매처는 검증된 baseline(gimulmul_match) 방식 — 8장서 P@1 62.5%/Hit@3 100%.

산출: intake_vision.json (추출 캐시) / intake_label_sheet.csv (사람 라벨용).

사용: .venv/bin/python scripts/intake_photos.py --photos-dir /path/to/photos [--vision-model gpt-4.1]
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from build_article_signatures import _ensure_key  # noqa: E402
from gimulmul_match import RESOLVE_SYS, RESOLVE_SCHEMA, RANK_SYS, RANK_SCHEMA, CROSS  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
REF = REPO / "data-team" / "05-enrichment" / "reference-data" / "기인물참고자료"
INDEX = ART / "gimulmul_index.json"
SIGS = ART / "article_signatures.jsonl"
ALIAS = ART / "gimulmul_alias.json"
CURATED = REF / "parsed" / "case_rule_mapping.json"
OUT_VISION = ART / "intake_vision.json"
OUT_CSV = ART / "intake_label_sheet.csv"
MATCH_MODEL = "gpt-5.4"

VIS_SYS = (
    "너는 산업안전보건 현장점검 비전 분석기다. 작업장 사진 1장을 받는다. 풍부하게 산출하라: "
    "visual_observations(보이는 사실, 설비·작업·상태 구체적), visual_cues(위험 시각단서), "
    "hazards(예상 위험: name·location·description), gimulmul(사고 직접원인 기인물명 — 규칙어휘로 정규화: "
    "지게차·고소작업대·사출성형기·프레스·굴착기·컨베이어·크레인 등), industry(업종 추정), "
    "immediate_actions(즉시조치 체크리스트). 사진에 실제 보이는 근거로만. 추측 금지. 한국어."
    # v2 관찰 체크리스트(2026-08-10, A/B 실측 exact 0.725→0.784·악화 0 — vision_v2_ab_report).
    # 카탈로그 주입(3회 실패)이 아니라 **관찰 범위 확장**이다 — 판단은 RESOLVE 몫.
    # v3(2026-08-10 2차): ①에 흡연 흔적 세목 추가 — miss11 분해에서 제니알테크 사진의
    # 그을린 깡통 재떨이·라이터·담뱃갑을 Vision이 전부 누락한 것이 확인됨(miss11-decompose).
    " ★관찰 체크리스트 — 다음 계통은 위험 판정의 결정적 단서인데 서술에서 자주 누락된다. "
    "사진에 **보이면 반드시** visual_observations와 visual_cues에 포함하라 "
    "(보이지 않으면 적지 말 것 — 부재 추정 금지): "
    "①소방·화기: 소화기·소화전·흡연 표지·용접 불꽃 흔적, 흡연 흔적(재떨이 또는 재떨이로 쓰인 "
    "그을린 깡통·담배꽁초·라이터·담뱃갑) "
    "②전기 계통: 분전반·배전반과 그 덮개 상태, 접지선·접지 단자, 누전차단기, 콘센트·멀티탭 "
    "③밀폐·차단: 출입구를 덮은 비닐·시트 밀폐, 경고표지·출입금지 표지, 임시 차단막 "
    "④환기·배기: 후드·덕트·국소배기장치 "
    "⑤대형 설비의 부위: 크레인 마스트·지브·훅, 곤돌라, 리프트 — 일부만 보여도 부위를 명시 "
    "⑥기계 회전부의 방호덮개 상태(명확히 보이는 경우만).")
VIS_SCHEMA = {"name": "vision", "strict": True, "schema": {"type": "object", "additionalProperties": False, "properties": {
    "visual_observations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    "visual_cues": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    "hazards": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"name": {"type": "string"}, "location": {"type": "string"}, "description": {"type": "string"}},
        "required": ["name", "location", "description"]}},
    "gimulmul": {"type": "array", "items": {"type": "string"}},
    "industry": {"type": "string"},
    "immediate_actions": {"type": "array", "items": {"type": "string"}}},
    "required": ["visual_observations", "visual_cues", "hazards", "gimulmul", "industry", "immediate_actions"]}}


def scene_text(res):
    obs = " ".join(o.get("text", "") for o in res.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in res.get("visual_cues") or [])
    haz = "; ".join(h.get("name", "") for h in res.get("hazards") or [])
    return f"{obs} 시각단서: {cues} 위험: {haz}".strip()


def data_url(p: Path):
    ext = p.suffix.lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos-dir", default=str(REPO / "real-test-photo"))
    ap.add_argument("--vision-model", default="gpt-4.1")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    pdir = Path(args.photos_dir)
    imgs = sorted([p for p in pdir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")])
    if args.limit:
        imgs = imgs[:args.limit]
    print(f"사진 {len(imgs)}장 @ {pdir}")

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    groups = idx["groups"]
    cross_set = sorted(set(CROSS) & set(idx["observable_codes"]))
    sig = {json.loads(l)["article_code"]: json.loads(l)
           for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()}
    alias = json.loads(ALIAS.read_text(encoding="utf-8")) if ALIAS.exists() else {}
    curated = json.loads(CURATED.read_text(encoding="utf-8"))["gimulmul_articles"] if CURATED.exists() else {}

    def curated_lookup(gim):
        base = gim.split("(")[0].strip()
        for k, v in curated.items():
            if k.split("(")[0].strip() == base or base in k or k in base:
                return [a["code"] for a in v["articles"]]
        return []

    _ensure_key()
    from openai import OpenAI
    client = OpenAI()
    from app.db.database import SessionLocal
    from sqlalchemy import text as sqltext
    db = SessionLocal()
    full = {r[0]: r[1] for r in db.execute(sqltext(
        "select article_code, full_text from articles where law_type='RULE' and not deleted")).fetchall()}
    db.close()

    catalog = []
    for gk, g in groups.items():
        nobs = sum(1 for a in g["articles"] if a["observable"] in ("yes", "partial"))
        if nobs >= 1 and gk not in idx["cross_cutting"]:
            catalog.append(f"{gk} ::기인물={g['gimulmul']} ({nobs}조)")
    catalog_text = "\n".join(sorted(catalog))

    def vision(p):
        r = client.chat.completions.create(model=args.vision_model, max_completion_tokens=3000, messages=[
            {"role": "system", "content": VIS_SYS},
            {"role": "user", "content": [{"type": "text", "text": "이 사진을 분석하라."},
                                         {"type": "image_url", "image_url": {"url": data_url(p)}}]}],
            response_format={"type": "json_schema", "json_schema": VIS_SCHEMA})
        return json.loads(r.choices[0].message.content)

    def chat(sysp, user, schema):
        r = client.chat.completions.create(model=MATCH_MODEL, messages=[
            {"role": "system", "content": sysp}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": schema})
        return json.loads(r.choices[0].message.content)

    def process(p):
        name = p.name.split("(")[0]
        try:
            res = vision(p)
        except Exception as e:  # noqa: BLE001
            return name, {"error": str(e)[:160]}, []
        st = scene_text(res)
        rv = chat(RESOLVE_SYS, f"[장면]\n{st}\n\n[기인물 그룹 카탈로그]\n{catalog_text}\n\n주요 기인물의 group_key 선택.", RESOLVE_SCHEMA)
        gks = [k for k in rv["group_keys"] if k in groups]
        gims = rv.get("gimulmul", [])
        cand, seen, kind = [], set(), {}

        def add(code, tag):
            if code not in seen and sig.get(code, {}).get("observable") in ("yes", "partial"):
                seen.add(code); cand.append(code); kind[code] = tag
        # recall 우선 넓은 net: Section B 큐레이션 ∪ alias 절/관 ∪ RESOLVE 그룹 ∪ 횡단 (관찰가능만)
        for gim in gims:
            for c in curated_lookup(gim):
                add(c, "큐레이션")
        for gim in gims:
            for gk in alias.get(gim, {}).get("group_keys", []):
                for a in groups.get(gk, {}).get("articles", []):
                    add(a["code"], "기인물")
        for gk in gks:
            for a in groups[gk]["articles"]:
                add(a["code"], "기인물")
        for c in cross_set:
            add(c, "횡단")
        lines = [f"[장면]\n{st}", "", "[후보 조]"]
        for c in cand:
            s = sig.get(c, {})
            lines.append(f"- [{kind[c]}] {c} {s.get('title','')} | {s.get('violation_scene','')[:80]}")
        rk = chat(RANK_SYS, "\n".join(lines) + "\n\n적용 조를 확신순 정렬.", RANK_SCHEMA)
        ranked = [x["article_code"] for x in rk["ranked"] if x["applies"] in ("yes", "maybe") and x["article_code"] in kind]
        # 라벨시트: ranked 상위 + 나머지 전체 후보(recall 우선 — 사람이 추가 안 하게)
        sheet = ranked + [c for c in cand if c not in ranked]
        return name, {"result": res, "photo": p.name}, [(name, c, kind[c], ("Y" if c in ranked else ""),
                      ranked.index(c) + 1 if c in ranked else "", sig, full) for c in sheet]

    vision_out = {"_note": "intake rich vision", "photos": []}
    rows = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for fu in as_completed([ex.submit(process, p) for p in imgs]):
            name, vrec, sheet = fu.result()
            if "error" in vrec:
                print(f"  ERR {name}: {vrec['error']}", flush=True); continue
            vision_out["photos"].append({"photo": vrec["photo"], "industry": vrec["result"].get("industry", ""),
                                         "result": vrec["result"]})
            for (nm, c, knd, ismatch, rank, sigd, fulld) in sheet:
                s = sigd.get(c, {})
                rows.append({"photo": nm, "article_code": c, "title": s.get("title", ""),
                             "kind": knd, "ranked": ismatch, "rank": rank,
                             "violation_scene": s.get("violation_scene", ""),
                             "full_excerpt": (fulld.get(c, "") or "")[:280].replace("\n", " "),
                             "LABEL(y/n/m)": "", "사유(선택)": ""})
            print(f"  OK {name}: 후보 {len(sheet)}", flush=True)

    OUT_VISION.write_text(json.dumps(vision_out, ensure_ascii=False, indent=1), encoding="utf-8")
    cols = ["photo", "article_code", "title", "kind", "ranked", "rank", "violation_scene", "full_excerpt", "LABEL(y/n/m)", "사유(선택)"]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)
    print(f"\n추출 {len(vision_out['photos'])}장 → {OUT_VISION.name}")
    print(f"라벨시트 {len(rows)}행 → {OUT_CSV.name} (사람: LABEL y/n/m)")


if __name__ == "__main__":
    main()
