"""WC-D eval — fine-first work_context graded matching 무회귀+보정 정량화.

synthetic_observations_v6(330 케이스)의 expected_features를 관찰로 주입(LLM 비용 0·결정적),
query_guide_for_facets를 FINE_GRADED_MATCH off/on으로 비교. 측정:
  · recall_identical    : 후보 set off==on (WHERE=canonical 불변) — recall 손실 0 입증
  · within_order_ok     : non-fine 상대순서·fine 상대순서 보존(fine-first가 블록만 들어올림, shuffle 아님)
  · fine_first_partition: on에서 fine guide 전부 non-fine보다 위 — 결정적 fine-first
  · canonical_control   : wc를 canonical로 fold한 입력은 off==on(=fine 신호 없으면 무변화) — flag ON 안전
  · 보정 coverage       : fine guide 존재 케이스 수 / top-1 변경 케이스 수(사용자 가시 보정)
실행: backend 디렉토리에서 `python scripts/eval_fine_graded_wc.py`
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from app.db.database import SessionLocal
from app.services import hazard_rule_engine as hre

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "shared" / "reference"))
import canonical_vocab as cv  # noqa: E402

SYN = ROOT / "data-team" / "05-enrichment" / "eval-data" / "synthetic_observations_v6.jsonl"
LIMIT = 300


def q(db, acc, agt, wc):
    return hre.query_guide_for_facets(db, acc, agt, wc, limit=LIMIT)


def fold_wc(wc):
    return sorted({cv.to_canonical("work_context", c)[1] for c in wc if c})


def subseq(codes, drop: set):
    return [c for c in codes if c not in drop]


def main() -> int:
    cases = [json.loads(l) for l in open(SYN, encoding="utf-8")]
    # 동일 facet 입력 dedup (관찰 단위 평가)
    uniq = {}
    for c in cases:
        ef = c.get("expected_features", {})
        key = (tuple(sorted(ef.get("accident_types", []))),
               tuple(sorted(ef.get("hazardous_agents", []))),
               tuple(sorted(ef.get("work_contexts", []))))
        uniq.setdefault(key, 0)
        uniq[key] += 1

    db = SessionLocal()
    m = dict(n_inputs=0, cases=len(cases), recall_ok=0, within_ok=0, partition_ok=0,
             has_fine=0, top1_changed=0, control_ok=0, control_total=0, empty=0)
    top1_examples = []
    try:
        for (acc, agt, wc), ncase in uniq.items():
            acc, agt, wc = list(acc), list(agt), list(wc)
            os.environ["FINE_GRADED_MATCH"] = ""
            off = q(db, acc, agt, wc)
            os.environ["FINE_GRADED_MATCH"] = "1"
            on = q(db, acc, agt, wc)
            if not off and not on:
                m["empty"] += 1
                continue
            m["n_inputs"] += 1
            offc = [g["guide_code"] for g in off]
            onc = [g["guide_code"] for g in on]
            fine = {g["guide_code"] for g in on if g.get("fine_match")}

            if set(offc) == set(onc):
                m["recall_ok"] += 1
            # within-group order 보존: fine 제거한 on == fine 제거한 off(같은 set) 상대순서
            if subseq(onc, fine) == subseq(offc, fine) and subseq(onc, set(onc) - fine) == subseq(offc, set(offc) - fine):
                m["within_ok"] += 1
            # fine-first partition
            ranks = {c: i for i, c in enumerate(onc)}
            if fine:
                m["has_fine"] += 1
                last_fine = max(ranks[c] for c in fine)
                first_non = min((ranks[c] for c in onc if c not in fine), default=10**9)
                if last_fine < first_non:
                    m["partition_ok"] += 1
                if offc and onc and offc[0] != onc[0]:
                    m["top1_changed"] += 1
                    if len(top1_examples) < 8:
                        top1_examples.append((wc, offc[0], onc[0]))
            else:
                m["partition_ok"] += 1  # fine 없으면 자명 통과

            # canonical control: fold한 입력 → off==on (fine 신호 없으면 무변화)
            fwc = fold_wc(wc)
            if fwc != sorted(set(wc)):  # 실제로 fine이 있던 입력만 control 의미
                m["control_total"] += 1
                os.environ["FINE_GRADED_MATCH"] = ""
                coff = [g["guide_code"] for g in q(db, acc, agt, fwc)]
                os.environ["FINE_GRADED_MATCH"] = "1"
                con = [g["guide_code"] for g in q(db, acc, agt, fwc)]
                if coff == con:
                    m["control_ok"] += 1
    finally:
        db.close()

    n = m["n_inputs"] or 1
    print(f"=== WC-D eval (synthetic_observations_v6) ===")
    print(f"케이스 {m['cases']} → 고유 facet 입력 {m['n_inputs']} (guide 매칭 0: {m['empty']})")
    print(f"[무회귀] recall_identical(off==on set)    : {m['recall_ok']}/{n}")
    print(f"[무회귀] within_group_order 보존          : {m['within_ok']}/{n}")
    print(f"[결정적] fine_first_partition            : {m['partition_ok']}/{n}")
    print(f"[안전]   canonical_control off==on        : {m['control_ok']}/{m['control_total']}  (fold 입력=fine 신호 제거)")
    print(f"[보정]   fine guide 보유 입력             : {m['has_fine']}/{n}")
    print(f"[보정]   top-1 guide 변경(가시 보정)      : {m['top1_changed']}/{m['has_fine'] or 1}")
    for wc, a, b in top1_examples:
        print(f"    wc={wc}: top1 {a} -> {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
