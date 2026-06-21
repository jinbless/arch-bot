#!/usr/bin/env python3
"""USE 2 — 텍스트 semi-gold + 매처 대규모 검증 (라벨 병목 우회).

KOSHA 텍스트 사례(SIF/구조화)는 기인물 + 조치가 라벨됨. 이를 매칭절반(기인물→조문) 대규모
검증에 사용. 각 사례:
  후보 = 기인물 → alias → 절/관 group → 관찰조문 ∪ 횡단.
  GOLD = '감소대책/예방조치' → 후보 중 대응 조문(LLM). [입력=처방된 조치]
  PRED = '재해개요/발생상황' → 후보 RANK(LLM). [입력=상황] = 매처 시뮬레이션.
  채점 = PRED vs GOLD (P@1/Hit@k). 입력이 달라(조치 vs 상황) 완전 순환 아님.

신뢰원칙: GOLD는 LLM 후보. **사람 spot-check 표본만 신뢰.** 시트 출력.

파일럿(--sample N, 기본 120)으로 설계 검증 후 전수.

사용: .venv/bin/python scripts/build_text_semigold.py --sample 120
"""
from __future__ import annotations

import argparse
import csv
import json
import re
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
from gimulmul_match import CROSS  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
REF = REPO / "data-team" / "05-enrichment" / "reference-data" / "기인물참고자료"
INDEX = ART / "gimulmul_index.json"
ALIAS = ART / "gimulmul_alias.json"
SIGS = ART / "article_signatures.jsonl"
SIF = REF / "parsed" / "sif_archive.jsonl"
CASES = REF / "parsed" / "accident_cases.jsonl"
CASE_CSV = REF / "기인물_사례별.csv"


def norm_code(s):
    """LLM 반환('제192조 비상정지장치')에서 조 코드만 추출."""
    m = re.search(r"제\d+조(?:의\d+)?", s or "")
    return m.group(0) if m else (s or "").strip()
OUT_JSONL = ART / "text_semigold.jsonl"
OUT_CSV = ART / "text_semigold_spotcheck.csv"
MODEL = "gpt-5.4"

GOLD_SYS = ("너는 산업안전보건 전문가다. 한 사고사례의 '필요했던 안전조치'와 후보 산업안전보건규칙 조"
            "(제목+요구조치)를 받는다. 그 조치가 직접 대응하는(그 조의 요구사항을 충족시키는) 조를 고르라. "
            "조치별로 가장 정확한 조. 후보에 없으면 고르지 말 것.")
GOLD_SCHEMA = {"name": "g", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"articles": {"type": "array", "items": {"type": "string"}}}, "required": ["articles"]}}

PRED_SYS = ("너는 산업안전보건 전문가다. 사고 '상황 서술'과 후보 산업안전보건규칙 조(제목+요구조치)를 받는다. "
            "그 상황에서 위반으로 성립하는 조를 확신 높은 순으로 정렬하라(yes/maybe만).")
PRED_SCHEMA = {"name": "p", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"ranked": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"article_code": {"type": "string"}, "applies": {"type": "string", "enum": ["yes", "maybe", "no"]}},
        "required": ["article_code", "applies"]}}}, "required": ["ranked"]}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=120)
    args = ap.parse_args()

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    groups = idx["groups"]
    alias = json.loads(ALIAS.read_text(encoding="utf-8"))
    cross_set = sorted(set(CROSS) & set(idx["observable_codes"]))
    sig = {json.loads(l)["article_code"]: json.loads(l)
           for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()}

    # alias 정규화 lookup(괄호 제거 부분일치 허용)
    def resolve_gks(gim):
        if not gim:
            return []
        if gim in alias and alias[gim]["group_keys"]:
            return alias[gim]["group_keys"]
        base = gim.split("(")[0].strip()
        # 부분일치
        for k, v in alias.items():
            if v["group_keys"] and (k.split("(")[0].strip() == base or base and base in k):
                return v["group_keys"]
        return []

    # 사례 기인물 보강(accident_cases엔 기인물 없음 → 기인물_사례별.csv 조인: (업종,순번))
    case_gim = {}
    if CASE_CSV.exists():
        for r in csv.DictReader(CASE_CSV.open(encoding="utf-8-sig")):
            case_gim[(r.get("업종", ""), str(r.get("순번", "")).strip())] = (r.get("기인물_품목") or "").strip()

    # 사례 로드 + 표본(조치 있는 것만)
    rows = []
    for p, mk in ((SIF, "감소대책"), (CASES, "예방조치")):
        for l in p.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            measures = r.get(mk) or []
            gim = r.get("gimulmul") or ""
            if not gim and r.get("source") == "case":
                # 순번 zero-pad 차이 흡수
                num = str(r.get("순번", "")).lstrip("0")
                gim = case_gim.get((r["domain"], num)) or case_gim.get((r["domain"], str(r.get("순번", "")))) or ""
            situ = r.get("재해개요") or r.get("발생상황") or ""
            if measures and gim and situ:
                rows.append({"id": r["id"], "domain": r["domain"], "gim": gim,
                             "measures": measures, "situ": situ, "src": p.stem})
    # 층화 표본(domain별 균등) — 결정적(앞에서 stride)
    by = defaultdict(list)
    for r in rows:
        by[r["domain"]].append(r)
    per = max(1, args.sample // max(len(by), 1))
    sample = []
    for d, rs in by.items():
        step = max(1, len(rs) // per)
        sample += rs[::step][:per]
    sample = sample[:args.sample]
    print(f"사례 {len(rows)}건 중 표본 {len(sample)} (domain별 ~{per})")

    _ensure_key()
    from openai import OpenAI
    client = OpenAI()

    def cand_for(gim):
        gks = resolve_gks(gim)
        cand, seen = [], set()
        for gk in gks:
            for a in groups.get(gk, {}).get("articles", []):
                if a["observable"] in ("yes", "partial") and a["code"] not in seen:
                    seen.add(a["code"]); cand.append(a["code"])
        for c in cross_set:
            if c not in seen:
                seen.add(c); cand.append(c)
        return gks, cand

    def cand_block(cand):
        lines = []
        for c in cand:
            s = sig.get(c, {})
            rm = ", ".join(s.get("required_measures") or [])
            lines.append(f"- {c} {s.get('title','')} | 요구조치: {rm}")
        return "\n".join(lines)

    def chat(sysp, user, schema):
        r = client.chat.completions.create(model=MODEL, messages=[
            {"role": "system", "content": sysp}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": schema})
        return json.loads(r.choices[0].message.content)

    def process(r):
        gks, cand = cand_for(r["gim"])
        if not gks or not cand:
            return {**r, "gks": gks, "skip": "no_candidates"}
        cb = cand_block(cand)
        g = chat(GOLD_SYS, f"[필요했던 안전조치]\n- " + "\n- ".join(r["measures"]) + f"\n\n[후보 조]\n{cb}\n\n대응 조 선택.", GOLD_SCHEMA)
        gold = [nc for nc in (norm_code(c) for c in g["articles"]) if nc in cand]
        p = chat(PRED_SYS, f"[상황]\n{r['situ']}\n\n[후보 조]\n{cb}\n\n적용 조 확신순 정렬.", PRED_SCHEMA)
        pred = [nc for nc in (norm_code(x["article_code"]) for x in p["ranked"] if x["applies"] in ("yes", "maybe")) if nc in cand]
        return {**r, "gks": gks, "gold": gold, "pred": pred}

    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fu in as_completed([ex.submit(process, r) for r in sample]):
            results.append(fu.result())

    scored = [r for r in results if r.get("gold")]
    KS = [1, 3, 5]
    agg = defaultdict(list)
    for r in scored:
        g, pred = set(r["gold"]), r["pred"]
        agg["p1"].append(1.0 if pred and pred[0] in g else 0.0)
        for k in KS:
            agg[f"hit{k}"].append(1.0 if set(pred[:k]) & g else 0.0)
            agg[f"r{k}"].append(len(set(pred[:k]) & g) / len(g))

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # spot-check 시트(사람: GOLD 적절성 ok/정정)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "domain", "기인물", "감소대책", "gold_articles", "gold_titles", "pred_top3", "CONFIRM(ok/정정)"])
        for r in scored:
            w.writerow([r["id"], r["domain"], r["gim"], " / ".join(r["measures"])[:120],
                        " ".join(r["gold"]), " ".join((sig.get(c, {}).get("title", "")) for c in r["gold"]),
                        " ".join(r["pred"][:3]), ""])

    skipped = sum(1 for r in results if r.get("skip"))
    print(f"\n표본 {len(results)} | gold생성 {len(scored)} | skip(후보없음) {skipped}")
    print(f"매처(상황→조문) vs gold(조치→조문):")
    print(f"  P@1={mean(agg['p1']):.1%}  Hit@3={mean(agg['hit3']):.1%}  Hit@5={mean(agg['hit5']):.1%}  R@3={mean(agg['r3']):.1%}")
    print(f"→ {OUT_JSONL.name} / spot-check {OUT_CSV.name}")


if __name__ == "__main__":
    main()
