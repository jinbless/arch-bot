#!/usr/bin/env python3
"""진단 — 정확한 semantic SR → get_guides_from_srs가 왜 엉뚱 guide를 주나.
top-K SR capping이 guide noise를 잡는지 실측."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.database import SessionLocal  # noqa: E402
from app.services.hybrid_search import hybrid_search  # noqa: E402
from app.services.hazard_rule_engine import get_guides_from_srs  # noqa: E402

RICH = ("지게차 충돌 지게차가 운행 중이며 주변에 작업자가 도보로 이동하고 있습니다. "
        "지게차와 작업자 간 충돌 및 협착 위험이 높음. 보행로와 차량 경로가 분리되어 있지 않음. "
        "보행자·차량 동선 분리 후진경보기·경광등 설치 운전자 안전벨트 착용")

rows = hybrid_search("sr", RICH, 20)
sr_ids = [r["id"] for r in rows]
print("SR recall rank(20):", sr_ids)

with SessionLocal() as db:
    for k in (1, 3, 5, 8, 20):
        gs = get_guides_from_srs(db, sr_ids[:k], limit=5)
        print(f"\n--- top-{k} SR → guides:")
        for g in gs:
            print(f"   {g['guide_code']:10s} w={g.get('weighted_ci'):<6} ci={g.get('ci_hit_count'):<4} {(g.get('title') or '')[:44]}")
