#!/usr/bin/env python3
"""Phase 3 검증 — match_hazards_to_guides의 SEMANTIC_ATTACH off/on 비교.

- off: 기존 facet @> 경로 (무회귀 기준선)
- on : GPT 원문 rich text hybrid recall + 온톨로지 검증 → SR 부착 → SR→CI→Guide

실행: ./.venv/bin/python scripts/test_semantic_attach.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.database import SessionLocal  # noqa: E402
from app.services.hazard_normalizer import normalize_hazards_array  # noqa: E402
from app.services.hazard_to_guide_service import match_hazards_to_guides  # noqa: E402

# 라이브 지게차 GPT 위험요소(rich text) — 사용자 제공 출력 스타일(높음/물리적위험/충돌)
HAZARDS = [
    {
        "name": "지게차 충돌",
        "risk_level": "high",
        "location": "물류 창고 통로",
        "description": "지게차가 운행 중이며 주변에 작업자가 도보로 이동하고 있습니다. 지게차와 작업자 간 충돌 및 협착 위험이 높음. 보행로와 차량 경로가 분리되어 있지 않음.",
        "preventive_measures": ["보행자·차량 동선 분리", "후진경보기·경광등 설치", "운전자 안전벨트 착용"],
    },
    {
        "name": "프레스 끼임",
        "risk_level": "high",
        "location": "프레스 작업장",
        "description": "대형 동력 프레스기 금형 사이에 신체가 진입하여 협착·절단될 위험. 광전자식 방호장치·양수조작장치 식별 불가.",
        "preventive_measures": ["광전자식 방호장치 설치", "양수조작식 안전장치"],
    },
]


def run(mode: str):
    os.environ["SEMANTIC_ATTACH"] = mode
    with SessionLocal() as db:
        canonical = normalize_hazards_array(HAZARDS, context_text=" ".join(h["description"] for h in HAZARDS))
        relations, sr_global = match_hazards_to_guides(
            db=db, hazards=HAZARDS, canonical=canonical, industry_contexts=[],
        )
    print(f"\n{'='*70}\n[SEMANTIC_ATTACH={mode}]  unique SR={len(sr_global)}")
    for r in relations:
        print(f"\n  ▶ {r['hazard_name']}  | attach={r.get('attach_method')} | matched_sr={r['matched_sr_count']}")
        sem = r.get("semantic_sr_ids") or []
        if sem:
            print(f"    semantic SR(top): {sem[:6]}")
        for g in r["guides"]:
            print(f"      [{g.get('mapping_type','')[:20]:20s}] {g['guide_code']:10s} {(g.get('title') or '')[:46]}")


if __name__ == "__main__":
    run("off")
    run("on")
