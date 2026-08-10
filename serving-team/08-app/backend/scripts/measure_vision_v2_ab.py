#!/usr/bin/env python3
"""Vision 서술 v2(관찰 체크리스트) A/B — 앵커 잔여 오인식 5장 조준.

배경: 판별 단서 보강 후 잔여 오인식의 원인이 **Vision 서술 누락**으로 좁혀졌다
(소화기·분전반이 안 찍힌 게 아니라 서술이 안 담음 — anchor-a0-metrics 문서).
카탈로그를 Vision에 주입하는 것(3회 실패)이 아니라, **관찰 범위를 넓히는** 체크리스트를
시스템 프롬프트에 붙인다. 판단(그룹 선택)은 여전히 RESOLVE+카탈로그 몫.

A/B 설계:
  A(현행) = intake_vision_gold.json의 기존 서술 + 현행 RESOLVE 캐시(재계측 불필요 — anchor_accuracy)
  B(v2)   = VIS_SYS + 체크리스트로 51장 재판독 → 같은 카탈로그로 RESOLVE → 같은 채점
  비교    = exact·flow_valid의 사진 단위 flip (회복/악화 명시)

부재 추정 금지를 명문화한다 — '소화기 없음' 같은 부재 주장을 시키면 환각·오탐(FP 67장 자산)
리스크가 생긴다. 보이는 것만 서술.

사용: .venv/bin/python scripts/measure_vision_v2_ab.py [--workers 4]
출력: runtime-artifacts/vision_v2_ab_report.json (+ 자체 캐시 vision_v2_ab_cache.json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))

import intake_photos as IP          # noqa: E402 — VIS_SCHEMA·scene_text·data_url 재사용
import rank_ab_gold as R            # noqa: E402 — RESOLVE 프롬프트·카탈로그·chat 재사용

ART = R.ART
PHOTO_DIR = R.REPO / "real-test-photo" / "label_photo"
ACC = ART / "anchor_accuracy.json"
CACHE = ART / "vision_v2_ab_cache.json"
OUT = ART / "vision_v2_ab_report.json"
VISION_MODEL = "gpt-4.1"

# ── v2 프롬프트 = 현행 + 관찰 체크리스트 (선택 지시 아님 — 서술 범위 확장) ──
V2_CHECKLIST = (
    " ★관찰 체크리스트 — 다음 계통은 위험 판정의 결정적 단서인데 서술에서 자주 누락된다. "
    "사진에 **보이면 반드시** visual_observations와 visual_cues에 포함하라 "
    "(보이지 않으면 적지 말 것 — 부재 추정 금지): "
    "①소방·화기: 소화기·소화전·흡연 표지·재떨이·용접 불꽃 흔적 "
    "②전기 계통: 분전반·배전반과 그 덮개 상태, 접지선·접지 단자, 누전차단기, 콘센트·멀티탭 "
    "③밀폐·차단: 출입구를 덮은 비닐·시트 밀폐, 경고표지·출입금지 표지, 임시 차단막 "
    "④환기·배기: 후드·덕트·국소배기장치 "
    "⑤대형 설비의 부위: 크레인 마스트·지브·훅, 곤돌라, 리프트 — 일부만 보여도 부위를 명시 "
    "⑥기계 회전부의 방호덮개 상태(명확히 보이는 경우만).")
# 정본(intake_photos.VIS_SYS)에 체크리스트가 승격된 뒤에는 이중 부착을 막는다
VIS_SYS_V2 = IP.VIS_SYS if "관찰 체크리스트" in IP.VIS_SYS else IP.VIS_SYS + V2_CHECKLIST


def _coord(section: str) -> tuple:
    p = j = jeol = gwan = None
    for tok in re.split(r"[>\s]+", section or ""):
        m = re.match(r"(편|장|절|관)(\d+)", tok.strip())
        if not m:
            continue
        lvl, n = m.group(1), int(m.group(2))
        p, j, jeol, gwan = (n, j, jeol, gwan) if lvl == "편" else (p, n, jeol, gwan) if lvl == "장" \
            else (p, j, n, gwan) if lvl == "절" else (p, j, jeol, n)
    return (p, j, jeol, gwan)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    acc = json.loads(ACC.read_text(encoding="utf-8"))
    per_a = {r["photo"]: r for r in acc["per_photo"]}
    photos = sorted(per_a)
    truth = {p: {tuple(t) for t in per_a[p]["truth"]} for p in photos}

    sigs = {json.loads(l)["article_code"]: json.loads(l)
            for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    gim = json.loads((ART / "gimulmul_index.json").read_text(encoding="utf-8"))["groups"]
    gkey_coord = {k: {_coord(sigs[a["code"]]["section"]) for a in g.get("articles", []) if a["code"] in sigs}
                  for k, g in gim.items()}
    flow_refs_by_key: dict[str, set] = {}
    for fr in json.loads((ART / "flow_slice_all.json").read_text(encoding="utf-8"))["rows"]:
        refs = {m.group(0) for its in (fr.get("items") or {}).values() for it in its
                if (m := re.match(r"제\d+조(의\d+)?", (it.get("ref") or "").strip()))}
        for kk in {fr.get("src_key"), fr.get("no")}:
            if kk:
                flow_refs_by_key.setdefault(kk, set()).update(refs)
    import csv as _csv
    gold_arts: dict[str, set] = {}
    with (R.REPO / "real-test-photo" / "label_photo" / "label_curation_gold_v2.csv").open(encoding="utf-8-sig") as f:
        for row in _csv.DictReader(f):
            if (row.get("match") or "").strip().lower() == "y":
                c = row["article_code"].strip()
                m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
                if m and not m.group(2):
                    c = f"제{m.group(1)}조"
                gold_arts.setdefault(row["photo_file"], set()).add(c)

    manifest = {"vis_sys_sha": hashlib.sha256(VIS_SYS_V2.encode()).hexdigest()[:12],
                "vision_model": VISION_MODEL, "resolve_model": R.MODEL,
                "catalog_sha": hashlib.sha256("\n".join(sorted(R.catalog_text.splitlines())).encode()).hexdigest()[:12]}
    cache = {}
    if CACHE.exists():
        old = json.loads(CACHE.read_text(encoding="utf-8"))
        if old.get("_manifest") == manifest:
            cache = old.get("runs", {})
            print(f"자체 캐시 {len(cache)}장 재사용")
        else:
            print("⚠ 매니페스트 변경 — v2 캐시 재실행")

    # 사진 파일 매핑 — gold 키는 파일명 그대로(intake는 '(' 앞까지 자르지만 label_photo엔 괄호명 존재)
    def photo_path(name: str) -> Path | None:
        p = PHOTO_DIR / name
        return p if p.exists() else None

    from openai import OpenAI
    client = OpenAI()

    def run_one(name: str) -> dict:
        p = photo_path(name)
        if p is None:
            return {"error": "file_not_found"}
        r = client.chat.completions.create(model=VISION_MODEL, messages=[
            {"role": "system", "content": VIS_SYS_V2},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": IP.data_url(p)}}]}],
            response_format={"type": "json_schema", "json_schema": IP.VIS_SCHEMA})
        vis = json.loads(r.choices[0].message.content)
        st = IP.scene_text(vis)
        rv = R.chat(R.RESOLVE_SYS, f"[장면]\n{st}\n\n[기인물 그룹 카탈로그]\n{R.catalog_text}\n\n"
                                   "주요 기인물의 group_key 선택.", R.RESOLVE_SCHEMA)
        return {"vision": vis, "resolve": rv}

    todo = [p for p in photos if p not in cache]
    print(f"사진 {len(photos)}장 (신규 {len(todo)}) · vision={VISION_MODEL} · resolve={R.MODEL}")
    fails = []
    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(run_one, p): p for p in todo}
            for i, fu in enumerate(as_completed(futs), 1):
                name = futs[fu]
                try:
                    cache[name] = fu.result()
                except Exception as e:  # noqa: BLE001
                    fails.append({"photo": name, "err": str(e)[:160]})
                if i % 10 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
                    CACHE.write_text(json.dumps({"_manifest": manifest, "runs": cache},
                                                ensure_ascii=False), encoding="utf-8")
    CACHE.write_text(json.dumps({"_manifest": manifest, "runs": cache}, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    # ── 채점 (measure_anchor_accuracy와 동일 규칙) ──
    rows = []
    for p in photos:
        run = cache.get(p)
        if not run or "resolve" not in run:
            continue
        picked = [g.split(" ::")[0].strip() for g in run["resolve"].get("group_keys", [])]
        pred = set().union(*(gkey_coord.get(k, set()) for k in picked)) if picked else set()
        exact_b = bool(truth[p] & pred)
        frefs = set().union(*(flow_refs_by_key.get(k, set()) for k in picked)) if picked else set()
        flow_b = exact_b or bool(gold_arts.get(p, set()) & frefs)
        rows.append({"photo": p, "exact_b": exact_b, "flow_b": flow_b,
                     "exact_a": per_a[p]["exact"], "flow_a": per_a[p].get("flow_valid", per_a[p]["exact"]),
                     "picked_b": picked})
    n = len(rows)
    ea = sum(1 for r in rows if r["exact_a"]) / n
    eb = sum(1 for r in rows if r["exact_b"]) / n
    fa = sum(1 for r in rows if r["flow_a"]) / n
    fb = sum(1 for r in rows if r["flow_b"]) / n
    fixed = [r["photo"] for r in rows if r["exact_b"] and not r["exact_a"]]
    broke = [r["photo"] for r in rows if not r["exact_b"] and r["exact_a"]]
    ffixed = [r["photo"] for r in rows if r["flow_b"] and not r["flow_a"]]
    fbroke = [r["photo"] for r in rows if not r["flow_b"] and r["flow_a"]]

    OUT.write_text(json.dumps({"_manifest": manifest, "n": n, "fails": fails,
                               "exact": {"A": round(ea, 3), "B": round(eb, 3)},
                               "flow_valid": {"A": round(fa, 3), "B": round(fb, 3)},
                               "exact_fixed": fixed, "exact_broke": broke,
                               "flow_fixed": ffixed, "flow_broke": fbroke,
                               "per_photo": rows}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== Vision v2 A/B (채점 {n}장, 실패 {len(fails)}) ===")
    print(f"  exact      A {ea:.3f} → B {eb:.3f}")
    print(f"  flow_valid A {fa:.3f} → B {fb:.3f}")
    print(f"  exact 회복 {len(fixed)}: {[p[:34] for p in fixed]}")
    print(f"  exact 악화 {len(broke)}: {[p[:34] for p in broke]}")
    print(f"  flow 회복 {len(ffixed)} / 악화 {len(fbroke)}: {[p[:34] for p in fbroke]}")
    print(f"→ {OUT.name}")


if __name__ == "__main__":
    main()
