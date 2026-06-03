"""「즉시 조치」 v5화 — GPT hazards(조치+설명) → raw CI 벡터매칭 → Guide+섹션 인용.

GPT의 자유 preventive_measures/description을 우리 권위 checklist_item(CI)에 grounding →
source_guide+source_section 인용(근거·추적성). ohs_ci_raw(raw checklist_items, guide+section 메타) 매칭
+ 온톨로지 SSOT 존재검증. 결과는 analysis_pipeline._build_immediate_actions 호환 checklist_rows.

flag: _semantic_attach_enabled()와 동일(SEMANTIC_ATTACH / OHS_ENABLE_HYBRID_SEARCH). off면 [] → legacy 유지.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.services.hazard_to_guide_service import _semantic_attach_enabled

logger = logging.getLogger(__name__)


def match_hazards_to_ci(
    db: Session,
    hazards: list[dict],
    n_per_hazard: int = 4,
    total_limit: int = 12,
    industry_contexts: Optional[list[str]] = None,
) -> list[dict]:
    """GPT hazards → raw CI hybrid 매칭 → 즉시조치 rows(guide+section 인용). flag off면 []."""
    if not _semantic_attach_enabled() or not hazards:
        return []
    try:
        from app.services.hybrid_search import hybrid_search
    except Exception as e:  # noqa: BLE001
        logger.warning("[HazardToCI] hybrid_search import 실패: %s", e)
        return []
    from app.db.models import PgKoshaGuide

    picked: list[dict] = []
    seen: set[str] = set()
    for h in hazards:
        name = (h.get("name") or "").strip()
        measures = [m for m in (h.get("preventive_measures") or []) if isinstance(m, str) and m.strip()]
        # 즉시조치 grounding: 조치(measures) + 위험 설명을 질의로 (조치 우선).
        query = " ".join(filter(None, [name, (h.get("description") or "").strip(), *measures]))
        if not query.strip():
            continue
        try:
            cands = hybrid_search("ci_raw", query, n_results=n_per_hazard * 2)
        except Exception as e:  # noqa: BLE001
            logger.warning("[HazardToCI] '%s' 매칭 실패: %s", name, e)
            continue
        cnt = 0
        for c in cands:
            cid = c["id"]
            if cid in seen:
                continue
            meta = c.get("meta") or {}
            picked.append({
                "identifier": cid,
                "text": c.get("doc") or "",
                "source_guide": meta.get("guide") or "",
                "source_section": meta.get("section") or "",
                "binding_force": meta.get("binding") or "",
                "hazard_name": name,
            })
            seen.add(cid)
            cnt += 1
            if cnt >= n_per_hazard:
                break

    if not picked:
        return []

    # 온톨로지 SSOT 존재검증 + guide 제목 부여
    gcodes = {r["source_guide"] for r in picked if r["source_guide"]}
    gtitle: dict[str, str] = {}
    if gcodes:
        for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(list(gcodes))).all():
            gtitle[g.guide_code] = g.title

    rows: list[dict] = []
    for rank, r in enumerate(picked[:total_limit]):
        gc = r["source_guide"]
        if not gc or gc not in gtitle:
            continue  # 인용 불가(guide 없음) 또는 SSOT 존재검증 실패(stale) → 제외
        sec = r["source_section"]
        cite = "근거: " + (gc or "?")
        if gc in gtitle:
            cite += f"({(gtitle[gc] or '')[:18]})"
        if sec:
            cite += f" {sec}절"
        rows.append({
            "identifier": r["identifier"],
            "text": r["text"],
            "evidence_summary": cite,           # guide+section 인용 → 즉시조치 description에 노출
            "source_section": sec,
            "source_guide": gc,
            "binding_force": r["binding_force"],
            "relevance_score": round(max(0.5, 0.95 - 0.03 * rank), 3),
            "mapping_type": "hybrid_ci",
            "hazard_name": r["hazard_name"],
        })
    logger.info("[HazardToCI] %d CI grounded (guide+section 인용)", len(rows))
    return rows
