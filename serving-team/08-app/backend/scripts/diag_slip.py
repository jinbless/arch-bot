#!/usr/bin/env python3
"""진단 — '전도/미끄럼' 위험에 왜 현수교/사장교 교량 가이드가 우선?
normalize 코드 + facet(GF-direct) vs semantic recall 각각 추적."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("SEMANTIC_ATTACH", "on")
os.environ.setdefault("SEMANTIC_ATTACH_RERANK", "on")

from app.db.database import SessionLocal  # noqa: E402
from app.services.hazard_normalizer import normalize_hazards_array  # noqa: E402
from app.services.hazard_to_guide_service import _semantic_guide_candidates, _hazard_rich_text, match_hazards_to_guides  # noqa: E402
from app.services.hazard_rule_engine import get_guides_by_hazard_features  # noqa: E402

HZ = {"name": "전도/미끄럼", "risk_level": "medium", "location": "작업장 바닥",
      "description": "작업장 바닥의 기름·물기로 미끄러져 넘어질 위험", "preventive_measures": ["바닥 정리정돈", "미끄럼 방지 처리"]}

canon = normalize_hazards_array([HZ])
codes = canon.get("hazard_name_to_codes", {}).get("전도/미끄럼", [])
print("normalize codes:", codes)
acc, agt, wc = [], [], []
for c in codes:
    if "." in c:
        a, cc = c.split(".", 1)
        (acc if a == "accident_type" else agt if a == "hazardous_agent" else wc).append(cc)
print("acc/agt/wc:", acc, agt, wc)

with SessionLocal() as db:
    print("\n--- ① facet GF-direct (get_guides_by_hazard_features) ---")
    for g in get_guides_by_hazard_features(db, acc, agt, wc, limit=6):
        print(f"   {g['guide_code']:10s} score={g.get('relevance_score'):<5} {(g.get('title') or '')[:34]}")
    print("\n--- ② semantic recall (_semantic_guide_candidates) ---")
    for g in _semantic_guide_candidates(db, _hazard_rich_text(HZ), n=6):
        print(f"   {g['guide_code']:10s} score={g.get('relevance_score'):<5} mt={g.get('mapping_type')} {(g.get('title') or '')[:30]}")
    print("\n--- ③ 최종 merge (match_hazards_to_guides) ---")
    rels, _ = match_hazards_to_guides(db, [HZ], canon, industry_contexts=[])
    for g in (rels[0].get("guides") or []):
        print(f"   {g['guide_code']:10s} score={g.get('relevance_score'):<5} mt={g.get('mapping_type')} {(g.get('title') or '')[:30]}")
