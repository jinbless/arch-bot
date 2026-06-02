#!/usr/bin/env python3
"""Phase 4 검증 — 학습 promoted 캐시 읽기 경로 (HYBRID_ATTACH_CACHE).

같은 hazard(FALL|SCAFFOLD)를 3모드로:
- off          : 기존 facet 경로 (무회귀 기준)
- semantic     : recall(+rerank) — LLM 호출
- cache hit    : 학습 캐시 hit → recall/rerank LLM 미호출, 결정적

실행: ./.venv/bin/python scripts/test_attach_cache.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.database import SessionLocal  # noqa: E402
from app.services.hazard_to_guide_service import match_hazards_to_guides  # noqa: E402

HZ = [{
    "name": "비계 추락", "risk_level": "high", "location": "외벽 시스템비계",
    "description": "시스템비계 4단에서 안전난간 없이 작업, 안전대 후크 미체결",
    "preventive_measures": ["안전난간 설치", "안전대 체결"],
}]
# 학습 store에 promoted된 code_sig (accumulate_hybrid_attach 산출)
CANON = {"hazard_name_to_codes": {"비계 추락": ["accident_type.FALL", "work_context.SCAFFOLD"]},
         "work_contexts": ["SCAFFOLD"]}

MODES = [
    ("off            ", {"SEMANTIC_ATTACH": "off", "SEMANTIC_ATTACH_RERANK": "off", "HYBRID_ATTACH_CACHE": "off"}),
    ("semantic+rerank ", {"SEMANTIC_ATTACH": "on", "SEMANTIC_ATTACH_RERANK": "on", "HYBRID_ATTACH_CACHE": "off"}),
    ("cache hit       ", {"SEMANTIC_ATTACH": "on", "SEMANTIC_ATTACH_RERANK": "on", "HYBRID_ATTACH_CACHE": "on"}),
]

for label, env in MODES:
    for k, v in env.items():
        os.environ[k] = v
    with SessionLocal() as db:
        rels, _ = match_hazards_to_guides(db, HZ, CANON, industry_contexts=[])
    r = rels[0]
    guides = [(g["guide_code"], g.get("mapping_type")) for g in r["guides"]]
    print(f"[{label}] attach={r['attach_method']:14s} guides={guides}")
