"""Hazard-Direct Pivot Phase 3 Day 1-2 — hazard_to_guide_service.

각 GPT hazard.name별로 catalog code 매핑 → SR → Guide 추출 + grouping.
hazard_rule_engine.query_sr_for_facets() + get_guides_from_srs() 재사용
(Phase G.2 domain profile + Phase G.3 penalty 차별점 유지).

핵심 차이점 (vs 기존 SHE-based path):
- SHE matcher 우회 (broadness 회귀 risk 제거)
- hazard별 grouping (frontend UX 친화적, moellab 스타일)
- canonical 3축 → SR → Guide는 동일 (penalty 3-경로 차별점 보존)
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.services.hazard_rule_engine import (
    get_guides_from_srs,
    query_sr_for_facets,
)

logger = logging.getLogger(__name__)


def _axis_field(axis: str) -> str:
    return {
        "accident_type": "accident_types",
        "hazardous_agent": "hazardous_agents",
        "work_context": "work_contexts",
    }.get(axis, "")


def match_hazards_to_guides(
    db: Session,
    hazards: list[dict],
    canonical: dict,
    industry_contexts: Optional[list[str]] = None,
    guides_per_hazard: int = 3,
    sr_limit_per_hazard: int = 20,
) -> tuple[list[dict], list[str]]:
    """⭐ Hazard-Direct Pivot 핵심 — hazard별 Guide 매핑.

    Args:
        hazards: GPT hazards[] (name, risk_level, location, description, preventive_measures)
        canonical: normalize_hazards_array 결과 (hazard_name_to_codes 포함)
        industry_contexts: Phase G.2 domain profile gating용
        guides_per_hazard: hazard 1건당 최대 Guide 수 (default 3)
        sr_limit_per_hazard: hazard별 SR 쿼리 limit

    Returns:
        (hazard_guide_relations, sr_ids_global)
        hazard_guide_relations: [
            {
                "hazard_name": "추락",
                "risk_level": "high",
                "location": "...",
                "description": "...",
                "preventive_measures": [...],
                "mapped_codes": ["accident_type.FALL_FROM_HEIGHT"],
                "guides": [{guide_code, title, classification, relevance_score, mapping_type, ci_hit_count, industry_alignment}],
                "matched_sr_count": int,
            },
            ...
        ]
        sr_ids_global: hazard들 union으로 매칭된 SR id 리스트 (penalty path 생성 시 재사용)
    """
    industry_contexts = industry_contexts or []
    hazard_name_to_codes: dict[str, list[str]] = canonical.get("hazard_name_to_codes", {}) or {}

    relations: list[dict] = []
    sr_id_set: set[str] = set()

    for h in hazards or []:
        name = (h.get("name") or "").strip()
        if not name:
            continue
        codes = hazard_name_to_codes.get(name) or []
        # codes 형식: "axis.code"
        accident_types: list[str] = []
        hazardous_agents: list[str] = []
        work_contexts: list[str] = []
        for compound in codes:
            if "." not in compound:
                continue
            axis, code = compound.split(".", 1)
            if axis == "accident_type":
                accident_types.append(code)
            elif axis == "hazardous_agent":
                hazardous_agents.append(code)
            elif axis == "work_context":
                work_contexts.append(code)

        if not (accident_types or hazardous_agents or work_contexts):
            # 매핑 실패 — guides 없이 hazard만 보여줌
            relations.append({
                "hazard_name": name,
                "risk_level": h.get("risk_level", ""),
                "location": h.get("location", ""),
                "description": h.get("description", ""),
                "preventive_measures": list(h.get("preventive_measures") or []),
                "mapped_codes": [],
                "guides": [],
                "matched_sr_count": 0,
            })
            continue

        sr_rows = query_sr_for_facets(
            db,
            accident_types=accident_types,
            hazardous_agents=hazardous_agents,
            work_contexts=work_contexts,
            limit=sr_limit_per_hazard,
            industry_contexts=industry_contexts,
        )
        sr_ids = [row["identifier"] for row in sr_rows]
        sr_id_set.update(sr_ids)

        guides = get_guides_from_srs(
            db,
            sr_ids=sr_ids,
            limit=guides_per_hazard,
            industry_contexts=industry_contexts,
        )

        relations.append({
            "hazard_name": name,
            "risk_level": h.get("risk_level", ""),
            "location": h.get("location", ""),
            "description": h.get("description", ""),
            "preventive_measures": list(h.get("preventive_measures") or []),
            "mapped_codes": codes,
            "guides": guides,
            "matched_sr_count": len(sr_ids),
        })

    sr_ids_global = sorted(sr_id_set)
    logger.info(
        f"[HazardToGuide] {len(relations)} hazards / {len(sr_ids_global)} unique SR / "
        f"{sum(len(r['guides']) for r in relations)} guide rows"
    )
    return relations, sr_ids_global
