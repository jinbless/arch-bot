"""Three-Worlds Phase 4 검증 — 독립 facet 매칭 + corroboration fusion 동작 확인.

O facets(시나리오) → match_fusion_service.fuse_matches → CI/Guide 랭킹 출력.
corroboration이 구체 CI를 bundle한 Guide를 광범위 facet-only Guide 위로 올리는지 확인.

실행(WSL venv):
  cd /mnt/c/project/arch-bot && DATABASE_URL='postgresql://kosha:1229@localhost:5432/kosha' \
    PYTHONIOENCODING=utf-8 ./serving-team/08-app/backend/.venv/bin/python \
    serving-team/08-app/backend/scripts/verify_fusion_matching.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.models  # noqa: F401  register tables on Base
from app.services import match_fusion_service

SCENARIOS = [
    ("지게차", ["CAUGHT_IN", "COLLISION", "CRUSHED_OVERTURNED"], [], ["VEHICLE"]),
    ("화학물질 취급", ["CHEMICAL_EXPOSURE"], ["CHEMICAL"], ["CHEMICAL_WORK"]),
]


def main() -> int:
    url = os.environ.get("DATABASE_URL", "postgresql://kosha:1229@localhost:5432/kosha")
    db = sessionmaker(bind=create_engine(url))()
    for name, acc, agt, ctx in SCENARIOS:
        print(f"\n=== {name}: accident={acc} agent={agt} context={ctx} ===")
        out = match_fusion_service.fuse_matches(db, acc, agt, ctx, ci_limit=5, guide_limit=6)
        print("  -- O↔CI 독립 매칭 top 5 --")
        for c in out["checklist_items"]:
            print(f"    score={c['score']:.3f} deg={c['guide_degree']:>3}  {c['text'][:50]}")
        print("  -- Guide fusion (facet + corroboration) top 6 --")
        for g in out["guides"]:
            print(f"    fused={g['fused_score']:.3f} (facet={g['score']:.3f} +corro={g['corroboration']:.3f} "
                  f"ciN={g['corroborating_ci_count']})  {g['guide_code']:<12} {g['title'][:30]}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
