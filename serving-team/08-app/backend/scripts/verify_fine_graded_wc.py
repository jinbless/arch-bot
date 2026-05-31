"""WC-C 검증 — query_guide_for_facets fine-first work_context (무회귀 + forklift 승격).

전체 후보 풀(limit 큼)로 OFF/ON 비교:
  - 무회귀: OFF 결과 set == ON 결과 set (WHERE=canonical 불변 → recall 동일), OFF 순서=기존(fine 미고려).
  - 승격: ON에서 관찰 fine wc(FORKLIFT_OPERATION)를 GF에 보유한 guide가 상위로(fold-only 위).
실행: backend 디렉토리에서 `python scripts/verify_fine_graded_wc.py`
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ → 'app' 임포트 가능

from app.db.database import SessionLocal
from app.services import hazard_rule_engine as hre

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WC = ["FORKLIFT_OPERATION"]  # fine (→ canonical VEHICLE). GF에 48 guide 보유.
LIMIT = 300  # 후보 전체 확보(top-N 절단으로 인한 set 차이 제거)


def run(db):
    return hre.query_guide_for_facets(db, [], [], WC, limit=LIMIT)


def main() -> int:
    db = SessionLocal()
    try:
        os.environ["FINE_GRADED_MATCH"] = ""        # OFF
        off = run(db)
        os.environ["FINE_GRADED_MATCH"] = "1"        # ON
        on = run(db)
    finally:
        db.close()

    off_codes = [g["guide_code"] for g in off]
    on_codes = [g["guide_code"] for g in on]
    fine_on = [g["guide_code"] for g in on if g.get("fine_match")]

    print(f"후보: OFF {len(off)} / ON {len(on)}")
    print(f"[무회귀] 결과 set 동일(recall 불변): {set(off_codes) == set(on_codes)}")
    print(f"[무회귀] OFF 순서 == fine 미적용 순서: {all(not g.get('fine_match') for g in off)}")
    print(f"fine_match guide 수 (ON): {len(fine_on)}")
    print(f"OFF top10: {off_codes[:10]}")
    print(f"ON  top10: {on_codes[:10]}")

    if fine_on:
        roff = {c: i for i, c in enumerate(off_codes)}
        ron = {c: i for i, c in enumerate(on_codes)}
        # fine guide 전부 fold-only guide보다 위인가?
        last_fine_rank = max(ron[c] for c in fine_on)
        first_nonfine_rank = min((ron[c] for c in on_codes if c not in set(fine_on)), default=10**9)
        print(f"[fine-first] 마지막 fine rank {last_fine_rank} < 첫 non-fine rank {first_nonfine_rank}: "
              f"{last_fine_rank < first_nonfine_rank}")
        print("  promotion 샘플(fine guide rank OFF→ON):")
        for gc in sorted(fine_on, key=lambda c: ron[c])[:6]:
            print(f"    {gc}: {roff.get(gc)} -> {ron.get(gc)}")
    else:
        print("  [WARN] fine_match guide 0 — GF 매칭/입력 확인 필요")
    return 0


if __name__ == "__main__":
    sys.exit(main())
