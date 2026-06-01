"""효과(실효) eval — fine-first가 맥락-특화 guide를 끌어올리는 정도 정량화.

전 synthetic_observations 버전(v1~v10, 다양 업종)의 work_contexts를 관찰로 주입,
query_guide_for_facets ON/OFF 비교. K=6(실 추천 크기).
지표(라벨/사진 없으니 correctness 아닌 specificity/관련성 proxy):
  · fine_precision@K : top-K guide 중 그 관찰의 fine wc 코드로 GF 태깅된 guide 비율
      (canonical-only OFF가 묻어버린 맥락-특화 guide를 ON이 끌어올린 정도 = Δ)
  · activation       : top-1 guide가 OFF→ON에서 바뀐 비율(가시 보정)
  · coverage         : fine 코드에 태깅 guide ≥1 존재하는 관찰 비율(태깅 도달률)
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

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "shared" / "reference"))
import canonical_vocab as cv  # noqa: E402

K = 6


def tagged_guides(db, fine_codes):
    from app.db.models import PgGuideEntityFeatureCandidate as GF
    if not fine_codes:
        return set()
    return {r[0] for r in db.query(GF.guide_code).filter(
        GF.canonical_axis == "work_context", GF.feature_code.in_(list(fine_codes))).distinct()}


def main() -> int:
    # 전 버전 관찰 → work_contexts tuple로 dedup(빈도 가중)
    from collections import Counter
    counts: Counter = Counter()
    for f in sorted(glob.glob(str(ROOT / "data-team/05-enrichment/eval-data/synthetic_observations_v*.jsonl"))):
        for l in open(f, encoding="utf-8"):
            wc = tuple(sorted((json.loads(l).get("expected_features", {}).get("work_contexts") or [])))
            if wc:
                counts[wc] += 1

    db = SessionLocal()
    agg = dict(obs=0, uniq=0, fp_off=0.0, fp_on=0.0, act=0, cov=0, fine_obs=0)
    try:
        for wc_t, n in counts.items():
            wc = list(wc_t)
            fine = {c for c in wc if cv.to_canonical("work_context", c)[1] != c}
            if not fine:
                continue
            agg["uniq"] += 1
            agg["obs"] += n
            tg = tagged_guides(db, fine)
            if tg:
                agg["cov"] += n
            os.environ["FINE_GRADED_MATCH"] = ""
            off = [g["guide_code"] for g in hre.query_guide_for_facets(db, [], [], wc, limit=K)]
            os.environ["FINE_GRADED_MATCH"] = "1"
            on = [g["guide_code"] for g in hre.query_guide_for_facets(db, [], [], wc, limit=K)]
            fp_off = len(set(off) & tg) / K
            fp_on = len(set(on) & tg) / K
            agg["fp_off"] += fp_off * n
            agg["fp_on"] += fp_on * n
            if off and on and off[0] != on[0]:
                agg["act"] += n
    finally:
        db.close()

    o = agg["obs"] or 1
    print("=== fine-first 효과 eval (synthetic v1~v10, work_context) ===")
    print(f"fine wc 보유 관찰: {agg['obs']} (고유 wc입력 {agg['uniq']})")
    print(f"coverage(태깅 guide≥1 존재): {agg['cov']}/{agg['obs']} = {agg['cov']/o:.1%}")
    print(f"fine_precision@{K}:  OFF {agg['fp_off']/o:.3f}  →  ON {agg['fp_on']/o:.3f}  (Δ +{(agg['fp_on']-agg['fp_off'])/o:.3f})")
    print(f"activation(top-1 변경): {agg['act']}/{agg['obs']} = {agg['act']/o:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
