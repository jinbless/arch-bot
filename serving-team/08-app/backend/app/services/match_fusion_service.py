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


# ═══ analysis_pipeline 계약 어댑터 — fusion 결과 → checklist_rows / guide_rows ═══
# 기존 get_immediate_checklist_items / get_standard_guides 출력 계약을 그대로 산출해
# 다운스트림 응답 조립(_build_immediate_actions / _build_standard_procedures) 무변경.

def build_recommendation_rows(
    db: Session,
    accident_types: list[str],
    hazardous_agents: list[str],
    work_contexts: list[str],
    *,
    ci_limit: int = 12,
    guide_limit: int = 6,
    industry_contexts: Optional[list[str]] = None,
) -> dict:
    """O facets → 독립 매칭+fusion → 파이프라인 계약형 {checklist_rows, guide_rows} (단일 호출)."""
    from app.db.models import PgChecklistItem, PgCiSrMapping, PgWorkProcess

    fused = fuse_matches(
        db, accident_types, hazardous_agents, work_contexts,
        ci_limit=ci_limit, guide_limit=guide_limit, industry_contexts=industry_contexts,
    )
    ci = fused["checklist_items"]
    guides = fused["guides"]

    # CI: canonical → 대표 instance(identifier/source_guide/section/binding) + sr_ids
    checklist_rows: list[dict] = []
    if ci:
        cids = [c["canonical_ci_id"] for c in ci]
        reps: dict = {}
        for cid, ident, sg, sec, bf in (
            db.query(PgChecklistItem.canonical_ci_id, PgChecklistItem.identifier,
                     PgChecklistItem.source_guide, PgChecklistItem.source_section,
                     PgChecklistItem.binding_force)
            .filter(PgChecklistItem.canonical_ci_id.in_(cids)).all()
        ):
            reps.setdefault(cid, (ident, sg, sec, bf))
        sr_by_canon: dict = {}
        for cid, sr_id in (
            db.query(PgChecklistItem.canonical_ci_id, PgCiSrMapping.sr_id)
            .join(PgCiSrMapping, PgCiSrMapping.ci_id == PgChecklistItem.identifier)
            .filter(PgChecklistItem.canonical_ci_id.in_(cids)).all()
        ):
            sr_by_canon.setdefault(cid, set()).add(sr_id)
        for c in ci:
            cid = c["canonical_ci_id"]
            ident, sg, sec, bf = reps.get(cid, (cid, None, None, None))
            checklist_rows.append({
                "identifier": ident,
                "text": c["text"],
                "binding_force": bf,
                "source_guide": sg,
                "source_section": sec or "",
                "source_sr_ids": sorted(sr_by_canon.get(cid, set())),
                "relevance_score": round(min(0.99, c["score"]), 4),
                "evidence_summary": f"facet 매칭 {c['matched_axes']}축 · 특이도 deg={c['guide_degree']}",
            })

    # Guide: work_process_steps 보강 + corroboration 근거
    guide_rows: list[dict] = []
    if guides:
        gcodes = [g["guide_code"] for g in guides]
        wp_by_guide: dict = {}
        for wp in (
            db.query(PgWorkProcess)
            .filter(PgWorkProcess.source_guide.in_(gcodes))
            .order_by(PgWorkProcess.source_guide, PgWorkProcess.process_order).all()
        ):
            steps = wp_by_guide.setdefault(wp.source_guide, [])
            if len(steps) < 8:
                steps.append({
                    "step_id": wp.identifier,
                    "order": wp.process_order,
                    "title": wp.process_name or "작업 절차 검토",
                    "safety_measures": wp.safety_measures,
                    "source_section": wp.source_section or "",
                    "source_sr_ids": [],
                })
        for g in guides:
            steps = wp_by_guide.get(g["guide_code"], [])
            guide_rows.append({
                "guide_code": g["guide_code"],
                "title": g["title"],
                "classification": g.get("domain") or "general",
                "industry_alignment": "general",
                "relevant_sections": [],
                "relevance_score": round(min(0.99, g["fused_score"]), 4),
                "mapping_type": "facet_fusion",
                "ci_hit_count": g.get("corroborating_ci_count", 0),
                "work_process_steps": steps,
                "source_sr_ids": [],
                "source_ci_ids": [],
                "evidence_summary": f"독립 facet {g['matched_axes']}축 · corroboration {g.get('corroborating_ci_count', 0)} CI",
            })

    return {"checklist_rows": checklist_rows, "guide_rows": guide_rows}
