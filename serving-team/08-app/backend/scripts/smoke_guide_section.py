#!/usr/bin/env python3
"""빠른 smoke — §섹션 근거 사후 부착(_attach_section_evidence)이 full match_hazards_to_guides
경로에서 동작하는지 + 랭킹은 검증된 1벡터 경로 유지(mapping_type != _section)인지 확인.

rerank off로 LLM 호출 최소(섹션 근거용 임베딩만). 실행:
  ./scripts/_runpy.sh scripts/smoke_guide_section.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
os.environ["SEMANTIC_ATTACH_RERANK"] = "0"   # rerank off (LLM 최소)
os.environ.pop("GUIDE_SECTION_RECALL", None)  # 랭킹 = 검증된 1벡터 경로(기본 off)

from app.db.database import SessionLocal  # noqa: E402
from app.services import hazard_to_guide_service as H  # noqa: E402
from app.services.hybrid_search import get_index  # noqa: E402

print(f"ohs_guide_section count = {get_index('ohs_guide_section').count()}", flush=True)
print(f"_guide_section_enabled (랭킹 flag, 기본) = {H._guide_section_enabled()}  (False=검증된 1벡터 랭킹)", flush=True)

HAZARDS = [
    {"name": "지게차 충돌", "risk_level": "high", "location": "물류창고",
     "description": "작업장 내 지게차와 보행자 동선이 분리되지 않음",
     "preventive_measures": ["보행자 통로 분리", "출입통제", "유도자 배치"]},
    {"name": "고소 추락", "risk_level": "high", "location": "비계",
     "description": "비계 위 작업자가 안전대를 착용하지 않음",
     "preventive_measures": ["안전난간 설치", "안전대 착용", "추락방지망"]},
    {"name": "프레스 끼임", "risk_level": "high", "location": "프레스기",
     "description": "동력 프레스에 방호장치가 없음",
     "preventive_measures": ["광전자식 방호장치", "양수조작식 안전장치 설치"]},
]
canonical = {"hazard_name_to_codes": {}}  # 0-코드 → semantic 경로 단독(_attach_section_evidence 검증)

with SessionLocal() as db:
    relations, sr_ids = H.match_hazards_to_guides(
        db, HAZARDS, canonical, industry_contexts=[], guides_per_hazard=3
    )

for r in relations:
    print(f"\n■ {r['hazard_name']}  (attach={r.get('attach_method')}, SR={r['matched_sr_count']})")
    for g in r["guides"]:
        secs = ", ".join(s["section_title"] for s in (g.get("relevant_sections") or [])) or "(없음)"
        flag = "⚠️_section랭킹" if g["mapping_type"].endswith("_section") else "✓1벡터"
        print(f"    {g['guide_code']:12s} {g['relevance_score']:.2f} {flag} {g['mapping_type']:20s} §{secs}  | {g['title'][:30]}")

# 표준개선절차 패널 노출 검증 — analysis_pipeline v5 dedup → evidence_summary (프론트 GuideProcedurePanel이 렌더)
print("\n── 표준개선절차 패널 evidence_summary (dedup 후, 프론트 노출 문자열) ──")
_seen = {}
for _rel in relations:
    for _g in _rel.get("guides") or []:
        _gc = _g.get("guide_code")
        if not _gc:
            continue
        _sc = float(_g.get("relevance_score") or 0.0)
        if _gc not in _seen or _sc > _seen[_gc]["relevance_score"]:
            _secs = [s.get("section_title") for s in (_g.get("relevant_sections") or []) if s.get("section_title")]
            _ev = f"근거 섹션 — {_gc} §{'·'.join(_secs[:3])}" if _secs else None
            _seen[_gc] = {"guide_code": _gc, "relevance_score": _sc, "evidence_summary": _ev}
for row in sorted(_seen.values(), key=lambda x: x["relevance_score"], reverse=True):
    print(f"    {row['guide_code']:12s} → description/근거: {row['evidence_summary']}")
print("\nsmoke OK — 랭킹 mapping_type에 _section 없어야 정상(검증된 1벡터 경로). §섹션 evidence_summary 모두 채워져야 함.")
