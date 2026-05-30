"""Three-Worlds rank fusion — O↔SR/CI/Guide 독립 매칭 + 구조 corroboration.

원리(사용자 합의): open-world 관찰 O는 SR/CI/Guide 각 표면과 *독립* facet 매칭(recall).
표면 간 구조(Guide-bundles-CI)는 매칭 경로가 아니라 *랭킹 corroboration*(precision):
  - 매칭된 CI를 매칭된 Guide가 bundle하면 → 두 채널 일치 → Guide 가산.
  - 가산량은 corroborating CI의 특이도(1/log2(2+guide_degree)) 합 (boilerplate는 query 단계에서 이미 제외).
→ 광범위 facet만 겹치는 Guide(예: VEHICLE만 맞는 '오토바이 배달')는 corroboration 없이 하위로,
  구체 CI(좌석안전띠·포크삽입)를 bundle하는 지게차 Guide는 상위로.

단순 가산식부터(plan). 8-photo eval로 가중 튜닝.
"""
from __future__ import annotations

import math
from typing import Optional

from sqlalchemy.orm import Session

from app.services import hazard_rule_engine

_CORRO_PER_CI = 0.15   # corroborating CI 특이도 합에 곱하는 가중
_CORRO_CAP = 0.40      # corroboration boost 상한


def fuse_matches(
    db: Session,
    accident_types: list[str],
    hazardous_agents: list[str],
    work_contexts: list[str],
    *,
    ci_limit: int = 12,
    guide_limit: int = 6,
    industry_contexts: Optional[list[str]] = None,
) -> dict:
    """O facets → 독립 매칭 3표면 + Guide corroboration 융합. 반환: {checklist_items, guides}."""
    ci = hazard_rule_engine.query_ci_for_facets(
        db, accident_types, hazardous_agents, work_contexts, limit=ci_limit * 3
    )
    guides = hazard_rule_engine.query_guide_for_facets(
        db, accident_types, hazardous_agents, work_contexts,
        limit=guide_limit * 4, industry_contexts=industry_contexts,
    )

    # Guide corroboration: 매칭 CI ∩ Guide bundle
    matched_ci = {c["canonical_ci_id"]: c for c in ci}
    if matched_ci and guides:
        from app.db.models import PgGuideControlBundle
        gcodes = [g["guide_code"] for g in guides]
        rows = (
            db.query(PgGuideControlBundle.guide_code, PgGuideControlBundle.canonical_ci_id)
            .filter(PgGuideControlBundle.guide_code.in_(gcodes))
            .filter(PgGuideControlBundle.canonical_ci_id.in_(list(matched_ci.keys())))
            .all()
        )
        boost: dict[str, float] = {}
        corro: dict[str, list] = {}
        for gc, cid in rows:
            c = matched_ci[cid]
            spec = 1.0 / math.log2(2 + (c["guide_degree"] or 1))
            boost[gc] = boost.get(gc, 0.0) + spec
            corro.setdefault(gc, []).append(cid)
        for g in guides:
            b = min(_CORRO_CAP, _CORRO_PER_CI * boost.get(g["guide_code"], 0.0))
            g["corroboration"] = round(b, 3)
            g["corroborating_ci_count"] = len(corro.get(g["guide_code"], []))
            g["fused_score"] = round(min(1.0, g["score"] + b), 3)
    else:
        for g in guides:
            g["corroboration"] = 0.0
            g["corroborating_ci_count"] = 0
            g["fused_score"] = g["score"]

    guides.sort(key=lambda g: (g["fused_score"], g["corroborating_ci_count"], g["matched_axes"]), reverse=True)
    return {
        "checklist_items": ci[:ci_limit],
        "guides": guides[:guide_limit],
    }
