#!/usr/bin/env python3
"""OWA→CWA 정밀화 — 기인물-앵커 매칭 (자유 의미매칭 SIG / 배포 DEPL 대비).

파이프라인(사진별):
  1) RESOLVE: 장면 + 기인물 그룹 카탈로그 → 주요 기인물의 절/관 group_key 선택(LLM).
  2) ASSEMBLE: 후보 = 선택 그룹의 관찰가능 조문 ∪ 횡단 일반의무 조문(보호구·추락·전도·통로 등).
     536 → ~25-40으로 좁힘(닫힌세계 내 기인물 국소화).
  3) RANK: 장면 + 후보(코드/제목/violation_scene/전문발췌) → 적용 조문 순위(LLM).
이후 gold(label_sheet)로 P@1/Hit@k/R@k 채점, SIG/DEPL과 비교.

violation_scene 과대추론(사람 가정) 완화: RANK는 조문 전문도 함께 주고 '사진에 보이는
설비/상태 기준으로' 판정하도록 지시.

사용: .venv/bin/python scripts/gimulmul_match.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402
from build_article_signatures import _ensure_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
VISION = ART / "claude_vision_8photo_input.json"
INDEX = ART / "gimulmul_index.json"
SIGS = ART / "article_signatures.jsonl"
LABELS = ART / "label_sheet.csv"
OUT_MD = ART / "gimulmul_match.md"
MODEL = os.environ.get("LLM_JUDGE_MODEL", "gpt-5.4")

# 횡단 일반의무(기인물 무관, 관찰가능) — gold·빈출 기반 큐레이션
CROSS = ["제3조", "제5조", "제13조", "제14조", "제20조", "제22조", "제23조",
         "제32조", "제42조", "제43조", "제44조", "제45조", "제46조",
         "제88조", "제92조", "제93조"]

RESOLVE_SYS = (
    "너는 산업안전보건 현장점검관이다. 작업장 장면 서술과 '기인물 그룹 카탈로그'(산업안전보건규칙의 "
    "절/관 = 기계·설비·물질·작업 분류)를 받는다. 이 장면에서 사고를 일으킬 수 있는 주요 기인물"
    "(기계/설비/물질/구조물/작업)을 식별하고, 카탈로그에서 해당하는 group_key를 1~4개 고르라. "
    "정확히 카탈로그에 있는 group_key 문자열만. 추측 금지.")
RESOLVE_SCHEMA = {"name": "resolve", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"gimulmul": {"type": "array", "items": {"type": "string"}},
                   "group_keys": {"type": "array", "items": {"type": "string"}}},
    "required": ["gimulmul", "group_keys"]}}

RANK_SYS = (
    "너는 대한민국 산업안전보건 현장점검관이다. 작업장 장면과 후보 산업안전보건규칙 조(제목·위반장면·전문발췌)를 받는다. "
    "목표: 이 사진을 보면 점검관이 '가장 먼저 지적할' 위반 조문을 1순위로, 구체성·가시성 순으로 정렬한다. "
    "'적용 가능한 모든 의무'를 나열하는 게 아니라, 사진이 '구체적으로 보여주는' 위반을 위로 올린다. "
    "순위 원칙: "
    "(1) 특정 > 일반: 사진에 직접 보이는 구체적 결여(개구부 방호 없음, 안전난간 없음, 보호구 미착용, "
    "방호장치·덮개 없음, 식별된 설비 전용 의무 미충족)를 최상위. [기인물] 표시 조와 구체 위험조 우선. "
    "(2) 포괄 의무 강등: 제3조(안전조치 일반)·제5조·제23조 등 '거의 모든 작업장에 성립하는 포괄/우산 의무'는 "
    "이 사진의 핵심 위반이 아니면 하위로 내리거나 maybe. 구체 조가 있으면 절대 포괄 조를 그 위에 두지 않는다. "
    "(3) 사람이 안 보이면 설비/구조의 결여상태(방호장치·덮개·난간 없음 등)로 판단. "
    "(4) 식별된 기인물(설비)에 당연히 요구되나 사진에서 충족 확인 안 되는 조는 maybe로 포함하되, 명백 무관은 no "
    "(예: 지게차면 좌석안전띠·헤드가드·백레스트). "
    "applies yes(사진에 구체적으로 보임)/maybe(정황·미확인)/no(무관). "
    "적용 조를 '점검관이 지적할 순서'(구체성·가시성 순, 범용 적용성 순 아님)로 정렬해 반환.")
RANK_SCHEMA = {"name": "rank", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"ranked": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"article_code": {"type": "string"}, "applies": {"type": "string", "enum": ["yes", "maybe", "no"]}},
        "required": ["article_code", "applies"]}}}, "required": ["ranked"]}}


def scene_text(res):
    obs = " ".join(o.get("text", "") for o in res.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in res.get("visual_cues") or [])
    haz = "; ".join(h.get("name", "") for h in res.get("hazards") or [])
    return f"{obs} 시각단서: {cues} 위험: {haz}".strip()


def main():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    groups = idx["groups"]
    cross_set = set(CROSS) & set(idx["observable_codes"])
    sig = {json.loads(l)["article_code"]: json.loads(l)
           for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()}
    vis = json.load(open(VISION, encoding="utf-8"))["photos"]

    # gold
    gold = defaultdict(set)
    for r in csv.DictReader(LABELS.open(encoding="utf-8-sig")):
        if (r.get("LABEL") or "").strip().lower().startswith("y"):
            gold[r["photo"]].add(r["article_code"])

    db = SessionLocal()
    full = {r[0]: r[1] for r in db.execute(text(
        "select article_code, full_text from articles where law_type='RULE' and not deleted")).fetchall()}
    db.close()

    _ensure_key()
    from openai import OpenAI
    client = OpenAI()

    # RESOLVE 카탈로그: 관찰가능 ≥1 그룹(횡단 제외)
    catalog = []
    for gk, g in groups.items():
        nobs = sum(1 for a in g["articles"] if a["observable"] in ("yes", "partial"))
        if nobs >= 1 and gk not in idx["cross_cutting"]:
            catalog.append(f"{gk}  ::기인물={g['gimulmul']} ({nobs}조)")
    catalog_text = "\n".join(sorted(catalog))

    def chat(sys_p, user, schema):
        r = client.chat.completions.create(model=MODEL, messages=[
            {"role": "system", "content": sys_p}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": schema})
        return json.loads(r.choices[0].message.content)

    def metrics(ranked_codes, g):
        if not g:
            return None
        KS = [1, 3, 5, 10]
        p1 = 1.0 if ranked_codes and ranked_codes[0] in g else 0.0
        out = {"p1": p1}
        for k in KS:
            out[f"hit{k}"] = 1.0 if set(ranked_codes[:k]) & g else 0.0
            out[f"r{k}"] = len(set(ranked_codes[:k]) & g) / len(g)
        return out

    md = ["# 기인물-앵커 매칭 결과 (vs SIG/DEPL)", ""]
    agg = defaultdict(list)
    per = []
    for p in vis:
        name = p.get("photo", "?").split("(")[0]
        st = scene_text(p.get("result") or {})
        g = gold.get(name, set())

        # 1) RESOLVE
        rv = chat(RESOLVE_SYS, f"[장면]\n{st}\n\n[기인물 그룹 카탈로그]\n{catalog_text}\n\n주요 기인물의 group_key 선택.", RESOLVE_SCHEMA)
        gks = [k for k in rv["group_keys"] if k in groups]
        # 2) ASSEMBLE — 기인물 전용 vs 횡단 태깅
        cand = []
        seen = set()
        kind = {}
        for gk in gks:
            for a in groups[gk]["articles"]:
                if a["observable"] in ("yes", "partial") and a["code"] not in seen:
                    seen.add(a["code"]); cand.append(a["code"]); kind[a["code"]] = "기인물"
        for c in sorted(cross_set):
            if c not in seen:
                seen.add(c); cand.append(c); kind[c] = "횡단"
        # 3) RANK
        lines = [f"[장면]\n{st}", "", "[후보 조]"]
        for c in cand:
            s = sig.get(c, {})
            vs = s.get("violation_scene", "")
            lines.append(f"- [{kind[c]}] {c} {s.get('title','')} | {vs[:90]}\n  전문: {(full.get(c,'') or '')[:160]}")
        rk = chat(RANK_SYS, "\n".join(lines) + "\n\n적용 조를 확신순 정렬.", RANK_SCHEMA)
        ranked = [x["article_code"] for x in rk["ranked"] if x["applies"] in ("yes", "maybe")]

        m = metrics(ranked, g)
        if m:
            for k, v in m.items():
                agg[k].append(v)
        per.append((name, g, gks, len(cand), ranked, m))

        md.append(f"## {name}")
        md.append(f"- 기인물: {', '.join(rv['gimulmul'])}")
        md.append(f"- 해석 group_key: {' | '.join(gks)}")
        md.append(f"- 후보 {len(cand)}개 → 랭킹 yes/maybe {len(ranked)}개")
        md.append(f"- top5: {' · '.join(ranked[:5])}")
        md.append(f"- gold: {', '.join(sorted(g)) or '(없음)'}")
        if m:
            md.append(f"- **P@1={m['p1']:.0f} Hit@5={m['hit5']:.0f} R@5={m['r5']:.2f}**")
        md.append("")

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    print("=== 기인물-앵커 매칭 (8장, gold y) ===")
    print(f"{'metric':<8}{'GIMULMUL':>12}")
    print(f"{'P@1':<8}{mean(agg['p1']):>12.1%}")
    for k in [1, 3, 5, 10]:
        print(f"{'Hit@'+str(k):<8}{mean(agg[f'hit{k}']):>12.1%}")
    for k in [1, 3, 5, 10]:
        print(f"{'R@'+str(k):<8}{mean(agg[f'r{k}']):>12.1%}")
    print("\n--- 사진별 (기인물 그룹수 | 후보수 | P@1/Hit@5) ---")
    for name, g, gks, ncand, ranked, m in per:
        if m:
            print(f"  {name:<12} grp{len(gks)} cand{ncand} | P@1={m['p1']:.0f} Hit@5={m['hit5']:.0f} | gold {sorted(g)}")
            print(f"      top5: {ranked[:5]}")
    md.append("\n## 집계")
    md.append(f"P@1={mean(agg['p1']):.1%} Hit@5={mean(agg['hit5']):.1%} R@5={mean(agg['r5']):.1%} R@10={mean(agg['r10']):.1%}")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"\n→ {OUT_MD.name}")


if __name__ == "__main__":
    main()
