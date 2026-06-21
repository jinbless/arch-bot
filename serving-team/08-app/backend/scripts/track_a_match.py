#!/usr/bin/env python3
"""Track A — 사진→조문 (엄격, 시각 가능만). 사람 큐레이션 + 관찰성 필터 + 편/장 컨텍스트.

후보 = 기인물 → [Section B 큐레이션 조문(사람검증)] ∪ [alias 절/관 관찰조문] ∪ [횡단 일반의무]
      → **관찰성 필터**(article_signatures observable yes/partial = 시각 판단가능만) 적용.
비가시 조문(제38 작업계획서·제98 속도 등)은 제외(→ Track B 자문으로).
RANK 우선순위: 큐레이션 > 절관 > 횡단. RESOLVE/RANK에 편/장 목적 컨텍스트 주입.

8장 사람 gold로 채점, 기존 gimulmul_match(62.5%) 대비.

사용: .venv/bin/python scripts/track_a_match.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from build_article_signatures import _ensure_key  # noqa: E402
from gimulmul_match import RESOLVE_SCHEMA, RANK_SCHEMA, CROSS  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
REF = REPO / "data-team" / "05-enrichment" / "reference-data" / "기인물참고자료"
VISION = ART / "claude_vision_8photo_input.json"
INDEX = ART / "gimulmul_index.json"
ALIAS = ART / "gimulmul_alias.json"
SIGS = ART / "article_signatures.jsonl"
CURATED = REF / "parsed" / "case_rule_mapping.json"
PYEONJANG = REF / "규칙_편장_목적과_적용상황.md"
LABELS = ART / "label_sheet.csv"
OUT_MD = ART / "track_a_match.md"
MODEL = "gpt-5.4"

RESOLVE_SYS = (
    "너는 산업안전보건 현장점검관이다. 작업장 장면과 '기인물 그룹 카탈로그', '규칙 편/장 안내'를 받는다. "
    "사고를 일으킬 주요 기인물(기계·설비·물질·구조물·작업)을 식별하고, 카탈로그에서 group_key를 1~4개 고르라. "
    "정확히 카탈로그의 group_key 문자열만. gimulmul에는 정규화된 기인물명(지게차·고소작업대·사출성형기·프레스·굴착기 등).")

RANK_SYS = (
    "너는 대한민국 산업안전보건 전문가다. 작업장 장면과 후보 조(출처태그·요구조치 포함)를 받는다. "
    "'사진에서 시각적으로 판단 가능한 위반'만 성립으로 본다(절차·기록·측정·속도 등 사진으로 확인 불가한 것은 no). "
    "사람이 안 보이면 설비/구조의 결여상태로 판단.\n"
    "랭킹 원칙: (1) [큐레이션](사람검증 기인물 전용 조)·[절관](기인물 절/관)을 [횡단](일반의무)보다 우선. "
    "(2) 사진 결여조치와 그 조 요구조치가 직접 일치하면 강한 신호. (3) 같은 절/관 형제조문은 결여조치로 변별. "
    "(4) 식별된 기인물의 시각가능 의무는 미확인이면 maybe. applies yes/maybe/no. 적용 조를 확신순 정렬.")


def scene_text(res):
    obs = " ".join(o.get("text", "") for o in res.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in res.get("visual_cues") or [])
    haz = "; ".join(h.get("name", "") for h in res.get("hazards") or [])
    return f"{obs} 시각단서: {cues} 위험: {haz}".strip()


def norm(s):
    return s.split("(")[0].strip()


def main():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    groups = idx["groups"]
    alias = json.loads(ALIAS.read_text(encoding="utf-8"))
    cross_set = sorted(set(CROSS) & set(idx["observable_codes"]))
    sig = {json.loads(l)["article_code"]: json.loads(l)
           for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()}
    curated = json.loads(CURATED.read_text(encoding="utf-8"))["gimulmul_articles"]
    # 편/장 컨텍스트(상위 요약만, 토큰 절약 위해 ## 헤더+첫 설명행)
    pj = PYEONJANG.read_text(encoding="utf-8")
    pj_ctx = "\n".join(l for l in pj.splitlines() if l.startswith("- **제") or l.startswith("| 제"))[:2200]

    gold = defaultdict(set)
    for r in csv.DictReader(LABELS.open(encoding="utf-8-sig")):
        if (r.get("LABEL") or "").strip().lower().startswith("y"):
            gold[r["photo"]].add(r["article_code"])

    vis = json.load(open(VISION, encoding="utf-8"))["photos"]

    _ensure_key()
    from openai import OpenAI
    client = OpenAI()

    catalog = []
    for gk, g in groups.items():
        nobs = sum(1 for a in g["articles"] if a["observable"] in ("yes", "partial"))
        if nobs >= 1 and gk not in idx["cross_cutting"]:
            catalog.append(f"{gk} ::기인물={g['gimulmul']} ({nobs}조)")
    catalog_text = "\n".join(sorted(catalog))

    def observable_ok(code):
        return sig.get(code, {}).get("observable") in ("yes", "partial")

    def curated_lookup(gim):
        base = norm(gim)
        for k, v in curated.items():
            if norm(k) == base or base in k or k in base:
                return [a["code"] for a in v["articles"]]
        return []

    def chat(sysp, user, schema):
        r = client.chat.completions.create(model=MODEL, messages=[
            {"role": "system", "content": sysp}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": schema})
        return json.loads(r.choices[0].message.content)

    def process(p):
        name = p.get("photo", "?").split("(")[0]
        st = scene_text(p.get("result") or {})
        rv = chat(RESOLVE_SYS, f"[장면]\n{st}\n\n[기인물 그룹 카탈로그]\n{catalog_text}\n\n[규칙 편/장 안내]\n{pj_ctx}\n\n주요 기인물의 group_key 선택.", RESOLVE_SCHEMA)
        gks = [k for k in rv["group_keys"] if k in groups]
        gims = rv.get("gimulmul", [])

        cand, kind = [], {}

        def add(code, tag):
            if code not in kind and observable_ok(code):
                kind[code] = tag; cand.append(code)
        # 1) Section B 큐레이션(사람검증) — 관찰성 필터
        for gim in gims:
            for code in curated_lookup(gim):
                add(code, "큐레이션")
        # 2) alias 절/관 그룹 관찰조문
        for gim in gims:
            for gk in alias.get(gim, {}).get("group_keys", []):
                for a in groups.get(gk, {}).get("articles", []):
                    add(a["code"], "절관")
        # 3) RESOLVE group_keys 그룹
        for gk in gks:
            for a in groups.get(gk, {}).get("articles", []):
                add(a["code"], "절관")
        # 4) 횡단
        for c in cross_set:
            add(c, "횡단")

        lines = [f"[장면]\n{st}", "", "[후보 조]"]
        for c in cand:
            s = sig.get(c, {})
            rm = ", ".join(s.get("required_measures") or [])
            lines.append(f"- [{kind[c]}] {c} {s.get('title','')} | 요구조치: {rm} | {s.get('violation_scene','')[:70]}")
        rk = chat(RANK_SYS, "\n".join(lines) + "\n\n적용 조를 확신순 정렬.", RANK_SCHEMA)
        ranked = [x["article_code"] for x in rk["ranked"] if x["applies"] in ("yes", "maybe") and x["article_code"] in kind]
        return name, gims, len(cand), ranked

    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fu in as_completed([ex.submit(process, p) for p in vis]):
            name, gims, ncand, ranked = fu.result()
            results[name] = (gims, ncand, ranked)

    KS = [1, 3, 5, 10]
    agg = defaultdict(list)
    md = ["# Track A 매칭 (Section B 큐레이션 + 관찰성 필터 + 편장 컨텍스트)", ""]
    for name in sorted(results):
        gims, ncand, ranked = results[name]
        g = gold.get(name, set())
        if not g:
            continue
        p1 = 1.0 if ranked and ranked[0] in g else 0.0
        agg["p1"].append(p1)
        for k in KS:
            agg[f"hit{k}"].append(1.0 if set(ranked[:k]) & g else 0.0)
            agg[f"r{k}"].append(len(set(ranked[:k]) & g) / len(g))
        md.append(f"## {name}  기인물={gims} 후보{ncand}")
        md.append(f"- top5: {ranked[:5]} | gold: {sorted(g)} | P@1={p1:.0f}")

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0
    print("=== Track A (8장, gold y) ===")
    print(f"P@1={mean(agg['p1']):.1%}  Hit@3={mean(agg['hit3']):.1%}  Hit@5={mean(agg['hit5']):.1%}  R@5={mean(agg['r5']):.1%}  R@10={mean(agg['r10']):.1%}")
    print("(기준 gimulmul_match: P@1 62.5% Hit@3 100% R@5 72.9%)")
    for name in sorted(results):
        gims, ncand, ranked = results[name]
        g = gold.get(name, set())
        print(f"  {name:<12} cand{ncand:<3} P@1={'1' if ranked and ranked[0] in g else '0'} | top5 {ranked[:5]} | gold {sorted(g)}")
    md.append(f"\n## 집계\nP@1={mean(agg['p1']):.1%} Hit@3={mean(agg['hit3']):.1%} Hit@5={mean(agg['hit5']):.1%} R@5={mean(agg['r5']):.1%}")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"→ {OUT_MD.name}")


if __name__ == "__main__":
    main()
