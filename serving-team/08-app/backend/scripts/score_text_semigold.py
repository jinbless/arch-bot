#!/usr/bin/env python3
"""USE 2 — 사람 검수된 텍스트 semi-gold 채점.

text_semigold_spotcheck.csv의 CONFIRM(ok/X/정정조문) 기입 후 실행.
  - ok-rate = LLM-gold 신뢰도(감소대책→조문 매핑 정확도).
  - 신뢰 gold = ok 행의 gold_조문 + 정정조문. 이걸로 매처(상황→조문) P@1/Hit@k 재계산.
= 사람 확정 기준의 '진짜' 매칭-반 수치.

사용: .venv/bin/python scripts/score_text_semigold.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
SHEET = ART / "text_semigold_spotcheck.csv"
SEMI = ART / "text_semigold.jsonl"


def main():
    pred = {r["id"]: r.get("pred", []) for r in
            (json.loads(l) for l in SEMI.read_text(encoding="utf-8").splitlines() if l.strip())}

    rows = list(csv.DictReader(SHEET.open(encoding="utf-8-sig")))
    confirm_col = next((c for c in rows[0] if c.startswith("CONFIRM")), "CONFIRM(ok/X/정정조문)") if rows else None

    n_ok = n_x = n_fix = n_blank = 0
    gold = defaultdict(set)  # id -> 신뢰 gold codes
    for r in rows:
        cid = r["id"]
        v = (r.get(confirm_col) or "").strip()
        gc = r["gold_조문"].strip()
        if not v:
            n_blank += 1
            continue
        vl = v.lower()
        fix = re.match(r"제\d+조(?:의\d+)?$", v)  # CONFIRM이 '순수 조문코드'일 때만 정정
        if vl in ("x", "무관", "no", "n", "아님", "틀림"):
            n_x += 1
        elif vl in ("ok", "o", "y", "yes", "맞음"):
            n_ok += 1
            gold[cid].add(gc)
        elif fix:
            n_fix += 1
            gold[cid].add(fix.group(0))
        else:  # 알 수 없는 값 → X로 보수 처리
            n_x += 1

    reviewed = n_ok + n_x + n_fix
    print(f"=== 검수 현황 ===")
    print(f"  검수 {reviewed} / 미검수(blank) {n_blank}")
    if reviewed == 0:
        print("  CONFIRM 미기입 — 검수 후 다시 실행."); return
    print(f"  ok {n_ok} · X(무관) {n_x} · 정정 {n_fix}")
    print(f"  **LLM-gold ok-rate = {n_ok/reviewed:.1%}** (정정포함 유효 {(n_ok+n_fix)/reviewed:.1%})")

    # 신뢰 gold로 매처 채점
    KS = [1, 3, 5]
    agg = defaultdict(list)
    cases = [cid for cid in gold if gold[cid]]
    for cid in cases:
        g, p = gold[cid], pred.get(cid, [])
        agg["p1"].append(1.0 if p and p[0] in g else 0.0)
        for k in KS:
            agg[f"hit{k}"].append(1.0 if set(p[:k]) & g else 0.0)
            agg[f"r{k}"].append(len(set(p[:k]) & g) / len(g))

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0
    print(f"\n=== 매처(상황→조문) vs 사람확정 gold (사례 {len(cases)}) ===")
    print(f"  P@1={mean(agg['p1']):.1%}  Hit@3={mean(agg['hit3']):.1%}  Hit@5={mean(agg['hit5']):.1%}  R@3={mean(agg['r3']):.1%}")


if __name__ == "__main__":
    main()
