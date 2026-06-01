"""효과(실효) eval — fine-first가 맥락-특화 guide를 끌어올리는 정도 정량화 (3축).

전 synthetic_observations 버전(v1~v10)의 expected_features(accident_type/hazardous_agent/
work_context 3축)를 관찰로 주입, query_guide_for_facets ON/OFF 비교. K=6(실 추천 크기).
지표(라벨/사진 없으니 correctness 아닌 specificity/관련성 proxy):
  · fine_precision@K : top-K guide 중 그 관찰의 fine 코드(어느 축이든)로 GF 태깅된 guide 비율
      (canonical-only OFF가 묻어버린 맥락-특화 guide를 ON이 끌어올린 정도 = Δ)
  · activation       : top-1 guide가 OFF→ON에서 바뀐 비율
  · coverage         : fine 코드에 태깅 guide ≥1 존재하는 관찰 비율
실행: backend에서 `python scripts/eval_fine_effectiveness.py`
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.database import SessionLocal
from app.services import hazard_rule_engine as hre

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import glob
import json
from collections import Counter

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "shared" / "reference"))
import canonical_vocab as cv  # noqa: E402

K = 6
AXES = [("accident_type", "accident_types"), ("hazardous_agent", "hazardous_agents"), ("work_context", "work_contexts")]


def tagged_guides(db, pairs):
    from app.db.models import PgGuideEntityFeatureCandidate as GF
    from sqlalchemy import and_, or_
    if not pairs:
        return set()
    conds = [and_(GF.canonical_axis == a, GF.feature_code == c) for a, c in pairs]
    return {r[0] for r in db.query(GF.guide_code).filter(or_(*conds)).distinct()}


def main() -> int:
    counts: Counter = Counter()
    for f in sorted(glob.glob(str(ROOT / "data-team/05-enrichment/eval-data/synthetic_observations_v*.jsonl"))):
        for l in open(f, encoding="utf-8"):
            ef = json.loads(l).get("expected_features", {})
            key = tuple(tuple(sorted(ef.get(col) or [])) for _, col in AXES)
            if any(key):
                counts[key] += 1

    db = SessionLocal()
    agg = dict(obs=0, uniq=0, fp_off=0.0, fp_on=0.0, act=0, cov=0)
    try:
        for key, n in counts.items():
            acc, agt, wc = (list(k) for k in key)
            pairs = [(ax, c) for (ax, _), codes in zip(AXES, (acc, agt, wc))
                     for c in codes if c and cv.to_canonical(ax, c)[1] != c]
            if not pairs:
                continue
            agg["uniq"] += 1
            agg["obs"] += n
            tg = tagged_guides(db, pairs)
            if tg:
                agg["cov"] += n
            os.environ["FINE_GRADED_MATCH"] = ""
            off = [g["guide_code"] for g in hre.query_guide_for_facets(db, acc, agt, wc, limit=K)]
            os.environ["FINE_GRADED_MATCH"] = "1"
            on = [g["guide_code"] for g in hre.query_guide_for_facets(db, acc, agt, wc, limit=K)]
            agg["fp_off"] += (len(set(off) & tg) / K) * n
            agg["fp_on"] += (len(set(on) & tg) / K) * n
            if off and on and off[0] != on[0]:
                agg["act"] += n
    finally:
        db.close()

    o = agg["obs"] or 1
    print("=== fine-first 효과 eval (synthetic v1~v10, 3축) ===")
    print(f"fine 코드 보유 관찰: {agg['obs']} (고유 입력 {agg['uniq']})")
    print(f"coverage(태깅 guide≥1): {agg['cov']}/{agg['obs']} = {agg['cov']/o:.1%}")
    print(f"fine_precision@{K}:  OFF {agg['fp_off']/o:.3f}  →  ON {agg['fp_on']/o:.3f}  (Δ +{(agg['fp_on']-agg['fp_off'])/o:.3f})")
    print(f"activation(top-1 변경): {agg['act']}/{agg['obs']} = {agg['act']/o:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
