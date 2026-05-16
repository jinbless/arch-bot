#!/usr/bin/env python3
"""Evaluate Stage 2~5 quality on synthetic_observations_v1..v10.

Stage 1 Vision/Text LLM is intentionally skipped.  The synthetic observations
are treated as the Stage 1 substitute and replayed through the current OHS
pipeline so that RiskFeature normalization, SHE matching, SR mapping, Guide/WP
recommendation, and CI immediate-action quality can be reviewed together.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import csv
import io
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.db.models import (  # noqa: E402
    PgChecklistItem,
    PgCiSrMapping,
    PgGuideEntityFeatureCandidate,
    PgGuideSrLinkCandidate,
)
from app.services.analysis_pipeline import AnalysisRunInput, analysis_pipeline  # noqa: E402
from app.services.broad_sr_policy import get_broad_sr_ids  # noqa: E402
from app.services.guide_recommendation_service import BROAD_FEATURE_CODES  # noqa: E402
from app.services.guide_photo_matchability import (  # noqa: E402
    PHOTO_ACTIONABLE,
    PHOTO_CONDITIONAL_FOLLOWUP,
    PHOTO_UNMATCHABLE,
    get_photo_matchability,
)
from evaluate_synthetic_guide_recommendations import (  # noqa: E402
    GENERIC_FEATURE_CODES,
    OBVIOUS_MISMATCH_CATEGORIES,
    OK_CATEGORIES,
    classify_top_procedure,
    compact_procedure,
    load_profiles,
    load_synthetic_rows,
    synthetic_to_llm_result,
)
from evaluate_synthetic_observations import (  # noqa: E402
    _normalized_expected_behavior,
    normalize_features,
)
from she_shadow_candidates import install_shadow_she_candidates  # noqa: E402

DEFAULT_INPUT_GLOB = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "synthetic_observations_v*.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_PREFIX = "pipeline_quality_v1_v10_usage_profile11"
DEFAULT_PHOTO_BASELINE_REPORT = DEFAULT_OUTPUT_DIR / "pipeline_quality_v1_v10_situation_frame_support7.json"
DEFAULT_SHADOW_SHE_CANDIDATES = (
    PROJECT_ROOT / "koshaontology" / "data" / "she" / "she-stage3-new-pattern-candidates-reference-guard1.jsonl"
)
ACTIONABLE_SHE_STATUSES = {"confirmed", "candidate", "review_candidate"}
SERVING_REVIEW_STATUSES = {"candidate", "asserted"}

FIELD_TO_AXIS = {
    "accident_types": "accident_type",
    "hazardous_agents": "hazardous_agent",
    "work_contexts": "work_context",
}
AXIS_TO_FIELD = {axis: field for field, axis in FIELD_TO_AXIS.items()}


class DatabaseUnavailableError(RuntimeError):
    pass

SR_FAMILY_BY_FEATURE = {
    "FALL": "FALL",
    "SLIP": "SLIP",
    "COLLISION": "COLLISION",
    "FALLING_OBJECT": "FALLING_OBJECT",
    "CRUSH": "CRUSH",
    "CUT": "CUT",
    "COLLAPSE": "COLLAPSE",
    "ERGONOMIC": "ERGONOMIC",
    "BURN": "BURN",
    "ELECTRIC_SHOCK": "ELECTRIC",
    "EXPLOSION": "FIRE_EXPLOSION",
    "FIRE": "FIRE_EXPLOSION",
    "CHEMICAL": "CHEMICAL",
    "CHEMICAL_EXPOSURE": "CHEMICAL",
    "CHEMICAL_WORK": "CHEMICAL",
    "TOXIC": "CHEMICAL",
    "CORROSION": "CHEMICAL",
    "DUST": "DUST",
    "RADIATION": "RADIATION",
    "NOISE": "NOISE",
    "HEAT_COLD": "HEAT",
    "BIOLOGICAL": "BIOLOGICAL",
    "CONFINED_SPACE": "CONFINED",
    "EXCAVATION": "EXCAVATION",
    "MACHINE": "MACHINE",
    "VEHICLE": "VEHICLE",
    "CRANE": "CRANE",
    "CONVEYOR": "MACHINE",
    "CONSTRUCTION_EQUIP": "CONSTRUCTION_EQUIP",
    "MATERIAL_HANDLING": "CARGO",
    "BOX_HANDLING": "CARGO",
    "FORKLIFT_OPERATION": "VEHICLE",
    "LADDER": "FALL",
    "SCAFFOLD": "FALL",
    "ELECTRICAL_WORK": "ELECTRIC",
    "ELECTRICITY": "ELECTRIC",
    "WELDING": "FIRE_EXPLOSION",
    "PAINTING": "CHEMICAL",
    "GRINDING": "MACHINE",
}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(v for v in values if v))


def case_key_from_values(version: Any, line_no: Any, case_id: Any) -> str:
    return f"{version}::{line_no}::{case_id}"


def case_key(row: dict[str, Any]) -> str:
    return case_key_from_values(row.get("version"), row.get("line_no"), row.get("case_id"))


def load_photo_baseline_top_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for record in data.get("records") or []:
        key = case_key_from_values(record.get("version"), record.get("line_no"), record.get("case_id"))
        top = ((record.get("stage5_guide_ci") or {}).get("top_procedure") or {})
        if top:
            result[key] = {
                "guide_code": top.get("guide_code"),
                "title": top.get("title"),
                "evidence_summary": top.get("evidence_summary"),
            }
    return result


def expected_feature_sets(row: dict[str, Any]) -> dict[str, set[str]]:
    expected = row.get("expected_features") or {}
    return {
        field: {str(code) for code in expected.get(field, []) or [] if code}
        for field in FIELD_TO_AXIS
    }


def actual_feature_sets(response: Any) -> dict[str, set[str]]:
    features: dict[str, set[str]] = {field: set() for field in FIELD_TO_AXIS}
    for feature in response.risk_features:
        field = AXIS_TO_FIELD.get(str(feature.axis))
        if field:
            features[field].add(str(feature.code))
    return features


def row_with_runtime_features(row: dict[str, Any], response: Any) -> dict[str, Any]:
    scoped = dict(row)
    scoped["expected_features"] = {
        field: sorted(values)
        for field, values in actual_feature_sets(response).items()
    }
    return scoped


def flat_feature_codes(feature_sets: dict[str, set[str]]) -> set[str]:
    out: set[str] = set()
    for codes in feature_sets.values():
        out.update(codes)
    return out


def classify_stage2(row: dict[str, Any], response: Any) -> dict[str, Any]:
    expected_sets = expected_feature_sets(row)
    actual_sets = actual_feature_sets(response)
    expected_codes = flat_feature_codes(expected_sets)
    actual_codes = flat_feature_codes(actual_sets)
    _, normalization_notes = normalize_features(row.get("expected_features") or {})

    queues: list[str] = []
    unsupported = [note for note in normalization_notes if note.get("error") == "unsupported"]
    risk_axis_unsupported = [note for note in unsupported if note.get("field") in FIELD_TO_AXIS]
    context_unsupported = [note for note in unsupported if note.get("field") not in FIELD_TO_AXIS]
    if risk_axis_unsupported:
        queues.append("non_catalog_feature")

    for field, expected in expected_sets.items():
        actual = actual_sets.get(field, set())
        for code in expected:
            if code not in actual and any(code in actual_sets[other] for other in actual_sets if other != field):
                queues.append("wrong_axis")
                break

    if expected_sets["work_contexts"] and not actual_sets["work_contexts"]:
        queues.append("missing_work_context")

    if actual_codes:
        if actual_codes <= GENERIC_FEATURE_CODES:
            queues.append("generic_only")
        elif actual_codes <= BROAD_FEATURE_CODES:
            queues.append("broad_feature_only")

    expected_behavior = _normalized_expected_behavior(row)
    if (
        row.get("case_type") == "negative"
        and not expected_behavior.get("should_match_she")
        and len(actual_codes - expected_codes) >= 2
    ):
        queues.append("over_normalized")

    return {
        "status": "attention" if queues else "ok",
        "queues": _unique(queues),
        "expected_features": {field: sorted(values) for field, values in expected_sets.items()},
        "actual_features": {field: sorted(values) for field, values in actual_sets.items()},
        "normalization_notes": normalization_notes,
        "risk_axis_unsupported_notes": risk_axis_unsupported,
        "context_unsupported_notes": context_unsupported,
    }


def classify_stage3(row: dict[str, Any], response: Any) -> dict[str, Any]:
    expected = _normalized_expected_behavior(row)
    matches = response.situation_matches
    statuses = [match.status for match in matches]
    has_any = bool(matches)
    has_actionable = any(status in ACTIONABLE_SHE_STATUSES for status in statuses)
    has_confirmed = any(status == "confirmed" for status in statuses)

    queues: list[str] = []
    if expected["should_match_she"] and not has_actionable:
        queues.append("she_missed")
    if not expected["should_match_she"] and has_actionable:
        queues.append("she_false_positive")
    if row.get("case_type") == "ambiguous" and has_confirmed:
        queues.append("ambiguous_over_promoted")
    if row.get("case_type") == "negative" and has_any:
        queues.append("negative_not_suppressed")
    if row.get("case_type") == "positive" and expected["should_match_she"] and has_actionable and not has_confirmed:
        queues.append("confirmed_downgraded_to_candidate")

    return {
        "status": "attention" if queues else "ok",
        "queues": _unique(queues),
        "expected_should_match_she": bool(expected["should_match_she"]),
        "has_she": has_any,
        "has_actionable_she": has_actionable,
        "has_confirmed_she": has_confirmed,
        "match_status_counts": dict(Counter(statuses)),
        "top_she": [
            {
                "pattern_id": match.pattern_id,
                "status": match.status,
                "score": match.score,
                "matched_features": list(match.matched_features or []),
                "applies_sr_ids": list(match.applies_sr_ids or [])[:5],
                "applies_ci_ids": list(match.applies_ci_ids or [])[:5],
            }
            for match in matches[:5]
        ],
    }


def expected_sr_families(row: dict[str, Any]) -> set[str]:
    families: set[str] = set()
    for code in flat_feature_codes(expected_feature_sets(row)):
        family = SR_FAMILY_BY_FEATURE.get(code)
        if family:
            families.add(family)
    return families


def sr_id_family(sr_id: str) -> str:
    parts = sr_id.split("-")
    return parts[1] if len(parts) >= 3 else sr_id


def classify_stage4(row: dict[str, Any], response: Any, broad_sr_ids: set[str]) -> dict[str, Any]:
    expected = _normalized_expected_behavior(row)
    sr_ids = list(response.reasoning_trace.safety_requirements or [])
    sr_set = set(sr_ids)
    broad = sr_set & broad_sr_ids
    non_broad = sr_set - broad_sr_ids
    expected_families = expected_sr_families(row)
    actual_families = {sr_id_family(sr_id) for sr_id in sr_ids}

    queues: list[str] = []
    if expected["should_recommend_sr"] and not sr_ids:
        queues.append("sr_missed")
    if not expected["should_recommend_sr"] and sr_ids:
        queues.append("sr_false_positive")
    if sr_ids and not non_broad:
        queues.append("broad_sr_only")
    if expected_families and sr_ids and expected_families.isdisjoint(actual_families):
        queues.append("sr_family_mismatch")
    if classify_stage3(row, response)["has_actionable_she"] and not sr_ids:
        queues.append("she_sr_link_missing")

    return {
        "status": "attention" if queues else "ok",
        "queues": _unique(queues),
        "expected_should_recommend_sr": bool(expected["should_recommend_sr"]),
        "sr_ids": sr_ids,
        "broad_sr_ids": sorted(broad),
        "non_broad_sr_ids": sorted(non_broad),
        "expected_sr_families": sorted(expected_families),
        "actual_sr_families": sorted(actual_families),
    }


def compact_action(action: Any | None) -> dict[str, Any] | None:
    if not action:
        return None
    return {
        "action_id": action.action_id,
        "title": action.title,
        "description": action.description,
        "source_type": action.source_type,
        "source_id": action.source_id,
        "urgency": action.urgency,
        "confidence": action.confidence,
    }


def ci_metadata(db: Any, ci_id: str | None) -> dict[str, Any]:
    if not ci_id:
        return {}
    ci = db.query(PgChecklistItem).filter(PgChecklistItem.identifier == ci_id).one_or_none()
    if not ci:
        return {"ci_id": ci_id, "found": False}
    sr_ids = [
        row.sr_id
        for row in db.query(PgCiSrMapping).filter(PgCiSrMapping.ci_id == ci.identifier).all()
    ]
    sr_candidate_statuses = dict(
        Counter(
            status
            for (status,) in db.query(PgGuideSrLinkCandidate.review_status)
            .filter(PgGuideSrLinkCandidate.entity_type == "CI")
            .filter(PgGuideSrLinkCandidate.entity_id == ci.identifier)
            .all()
        )
    )
    feature_candidate_statuses = dict(
        Counter(
            status
            for (status,) in db.query(PgGuideEntityFeatureCandidate.review_status)
            .filter(PgGuideEntityFeatureCandidate.entity_type == "CI")
            .filter(PgGuideEntityFeatureCandidate.entity_id == ci.identifier)
            .all()
        )
    )
    return {
        "ci_id": ci.identifier,
        "found": True,
        "source_guide": ci.source_guide,
        "source_section": ci.source_section,
        "binding_force": ci.binding_force,
        "requirement_type": ci.requirement_type,
        "sr_ids": sorted(sr_ids),
        "sr_candidate_review_status_counts": sr_candidate_statuses,
        "feature_candidate_review_status_counts": feature_candidate_statuses,
    }


def classify_ci(
    row: dict[str, Any],
    response: Any,
    db: Any,
    profiles: dict[str, Any],
    broad_sr_ids: set[str],
) -> dict[str, Any]:
    expected = _normalized_expected_behavior(row)
    top_action = response.immediate_actions[0] if response.immediate_actions else None
    action = compact_action(top_action)
    meta = ci_metadata(db, action.get("source_id") if action else None)
    ci_sr_ids = set(meta.get("sr_ids") or [])
    response_sr_ids = set(response.reasoning_trace.safety_requirements or [])
    sr_candidate_counts = meta.get("sr_candidate_review_status_counts", {})
    feature_candidate_counts = meta.get("feature_candidate_review_status_counts", {})
    has_serving_candidate = any(sr_candidate_counts.get(status) for status in SERVING_REVIEW_STATUSES) or any(
        feature_candidate_counts.get(status) for status in SERVING_REVIEW_STATUSES
    )
    has_needs_review_candidate = bool(sr_candidate_counts.get("needs_review") or feature_candidate_counts.get("needs_review"))
    has_asserted_runtime_sr = bool(ci_sr_ids & response_sr_ids)
    queues: list[str] = []

    if expected["should_match_she"] and row.get("case_type") == "positive" and not action:
        queues.append("ci_no_action")
    if row.get("case_type") == "negative" and action:
        queues.append("ci_context_mismatch")
    action_evidence = str((action or {}).get("description") or "")
    has_contextual_ci_evidence = any(
        marker in action_evidence
        for marker in (
            "SHE related checklist cue",
            "CI context term:",
            "CI support term:",
            "guide-local contextual CI fallback",
            "domain-safe top Guide CI-SR fallback",
        )
    )
    if ci_sr_ids and ci_sr_ids <= broad_sr_ids and not has_contextual_ci_evidence:
        queues.append("ci_broad_sr_only")
    if has_needs_review_candidate and not has_serving_candidate and not has_asserted_runtime_sr:
        queues.append("ci_needs_review_used")

    top_procedure = response.standard_procedures[0] if response.standard_procedures else None
    same_as_top_procedure = bool(
        action
        and top_procedure
        and meta.get("source_guide")
        and top_procedure.guide_code
        and meta["source_guide"] == top_procedure.guide_code
    )
    ci_profile_category = "not_evaluated"
    ci_profile_reason = ""
    ci_profile_detail: dict[str, Any] = {}
    if action and meta.get("source_guide"):
        has_direct_she_ci_evidence = "SHE related checklist cue" in str(action.get("description") or "")
        top_procedure_category = "not_evaluated"
        if same_as_top_procedure and top_procedure:
            top_procedure_category, _, _ = classify_top_procedure(
                row=row_with_runtime_features(row, response),
                procedure=compact_procedure(top_procedure),
                profiles=profiles,
                broad_sr_ids=broad_sr_ids,
            )
        ci_profile_category, ci_profile_reason, ci_profile_detail = classify_top_procedure(
            row=row_with_runtime_features(row, response),
            procedure={
                "guide_code": meta["source_guide"],
                "source_sr_ids": sorted(ci_sr_ids),
                "evidence_summary": action.get("description") or "",
                "top_steps": [],
            },
            profiles=profiles,
            broad_sr_ids=broad_sr_ids,
        )
        if (
            ci_profile_category in OBVIOUS_MISMATCH_CATEGORIES
            and not has_direct_she_ci_evidence
            and top_procedure_category not in OK_CATEGORIES
        ):
            queues.append("ci_guide_boundary_mismatch")

    return {
        "status": "attention" if queues else "ok",
        "queues": _unique(queues),
        "action_count": len(response.immediate_actions),
        "top_action": action,
        "top_action_ci_metadata": meta,
        "top_action_same_as_top_procedure": same_as_top_procedure,
        "top_action_source_guide_category": ci_profile_category,
        "top_action_source_guide_reason": ci_profile_reason,
        "top_action_source_guide_detail": ci_profile_detail,
    }


def procedure_photo_matchability(
    procedure: dict[str, Any] | None,
    profiles: dict[str, Any],
) -> dict[str, Any]:
    if not procedure:
        return {
            "guide_code": None,
            "photo_matchability": "NO_TOP",
            "top_procedure_policy": None,
            "followup_policy": None,
        }
    guide_code = procedure.get("guide_code")
    profile = profiles.get(guide_code or "")
    policy = get_photo_matchability(guide_code, profile)
    return {
        "guide_code": guide_code,
        "photo_matchability": policy.get("photo_matchability") or PHOTO_ACTIONABLE,
        "top_procedure_policy": policy.get("top_procedure_policy"),
        "followup_policy": policy.get("followup_policy"),
        "procedure_role": (profile or {}).get("procedure_role"),
    }


def classify_photo_policy(
    procedures: list[dict[str, Any]],
    profiles: dict[str, Any],
    baseline_top: dict[str, Any] | None,
) -> dict[str, Any]:
    top = procedures[0] if procedures else None
    top_policy = procedure_photo_matchability(top, profiles)
    retained_followups = [
        procedure_photo_matchability(procedure, profiles)
        for procedure in procedures[1:]
        if procedure_photo_matchability(procedure, profiles).get("photo_matchability")
        in {PHOTO_CONDITIONAL_FOLLOWUP, PHOTO_UNMATCHABLE}
    ]
    baseline_policy = procedure_photo_matchability(baseline_top, profiles) if baseline_top else None
    baseline_matchability = (baseline_policy or {}).get("photo_matchability")
    baseline_guide = (baseline_top or {}).get("guide_code")
    top_guide = (top or {}).get("guide_code")
    top_matchability = top_policy.get("photo_matchability")
    baseline_non_actionable = baseline_matchability in {PHOTO_CONDITIONAL_FOLLOWUP, PHOTO_UNMATCHABLE}
    return {
        "top": top_policy,
        "baseline_top": baseline_policy,
        "photo_unmatchable_top": top_matchability == PHOTO_UNMATCHABLE,
        "photo_unmatchable_suppressed": (
            baseline_matchability == PHOTO_UNMATCHABLE
            and bool(baseline_guide)
            and baseline_guide != top_guide
        ),
        "top_replaced_by_photo_actionable": (
            baseline_non_actionable
            and top_matchability == PHOTO_ACTIONABLE
            and bool(baseline_guide)
            and baseline_guide != top_guide
        ),
        "followup_only_retained_count": len(retained_followups),
        "followup_only_retained": retained_followups[:3],
    }


def classify_stage5(
    row: dict[str, Any],
    response: Any,
    db: Any,
    profiles: dict[str, Any],
    broad_sr_ids: set[str],
    baseline_top: dict[str, Any] | None = None,
) -> dict[str, Any]:
    procedures = [
        compact_procedure(procedure)
        for procedure in response.standard_procedures
    ]
    top_procedure = procedures[0] if procedures else None
    scoring_row = row_with_runtime_features(row, response)
    category, reason, detail = classify_top_procedure(
        row=scoring_row,
        procedure=top_procedure,
        profiles=profiles,
        broad_sr_ids=broad_sr_ids,
    )
    ci = classify_ci(row, response, db, profiles, broad_sr_ids)
    photo_policy = classify_photo_policy(procedures, profiles, baseline_top)
    queues = []
    if category not in OK_CATEGORIES:
        queues.append(category)
    queues.extend(ci["queues"])
    return {
        "status": "attention" if queues else "ok",
        "queues": _unique(queues),
        "guide_category": category,
        "guide_reason": reason,
        "guide_detail": detail,
        "procedure_count": len(response.standard_procedures),
        "top_procedure": top_procedure,
        "photo_policy": photo_policy,
        "ci": ci,
    }


async def replay_row(db: Any, row: dict[str, Any]) -> Any:
    llm_result = synthetic_to_llm_result(row)
    description = row.get("photo_description") or row.get("scene_description") or row.get("case_id") or "synthetic observation"
    return await analysis_pipeline.run(
        db=db,
        run_input=AnalysisRunInput(
            result=llm_result,
            analysis_type="synthetic_stage2_5_quality",
            input_preview=description[:120],
            full_description=" ".join(
                filter(
                    None,
                    [
                        row.get("industry_context"),
                        row.get("work_context"),
                        description,
                        row.get("expected_primary_risk"),
                    ],
                )
            ),
            declared_industry_text=row.get("industry_context"),
        ),
    )


async def build_case_record(
    db: Any,
    row: dict[str, Any],
    profiles: dict[str, Any],
    broad_sr_ids: set[str],
    baseline_top_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    response = await replay_row(db, row)
    stage2 = classify_stage2(row, response)
    stage3 = classify_stage3(row, response)
    stage4 = classify_stage4(row, response, broad_sr_ids)
    stage5 = classify_stage5(
        row,
        response,
        db,
        profiles,
        broad_sr_ids,
        baseline_top=(baseline_top_map or {}).get(case_key(row)),
    )

    stage_statuses = {
        "stage2": stage2["status"],
        "stage3": stage3["status"],
        "stage4": stage4["status"],
        "stage5": stage5["status"],
    }
    failure_stages = [stage for stage, status in stage_statuses.items() if status == "attention"]
    return {
        "version": row.get("version"),
        "line_no": row.get("line_no"),
        "case_id": row.get("case_id"),
        "case_type": row.get("case_type"),
        "industry_context": row.get("industry_context"),
        "work_context": row.get("work_context"),
        "photo_description": row.get("photo_description") or row.get("scene_description"),
        "expected_primary_risk": row.get("expected_primary_risk"),
        "expected_corrective_direction": row.get("expected_corrective_direction"),
        "false_positive_risk": row.get("false_positive_risk"),
        "finding_status": response.finding_status,
        "penalty_exposure_status": response.penalty_exposure_status,
        "failure_stages": failure_stages,
        "primary_failure_stage": failure_stages[0] if failure_stages else "ok",
        "stage2_risk_feature": stage2,
        "stage3_she": stage3,
        "stage4_sr": stage4,
        "stage5_guide_ci": stage5,
    }


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{numerator / denominator:.1%}"


def top_items(counter: Counter[Any], limit: int = 30) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key, count in counter.most_common(limit):
        if isinstance(key, tuple):
            label = " / ".join(str(part) for part in key)
        else:
            label = str(key)
        items.append({"key": label, "count": count})
    return items


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    stage_counts = Counter(stage for record in records for stage in record["failure_stages"])
    primary_counts = Counter(record["primary_failure_stage"] for record in records)
    stage2_queues = Counter(queue for record in records for queue in record["stage2_risk_feature"]["queues"])
    stage3_queues = Counter(queue for record in records for queue in record["stage3_she"]["queues"])
    stage4_queues = Counter(queue for record in records for queue in record["stage4_sr"]["queues"])
    stage5_queues = Counter(queue for record in records for queue in record["stage5_guide_ci"]["queues"])
    guide_categories = Counter(record["stage5_guide_ci"]["guide_category"] for record in records)
    ci_queues = Counter(queue for record in records for queue in record["stage5_guide_ci"]["ci"]["queues"])
    she_missed_records = [record for record in records if "she_missed" in record["stage3_she"]["queues"]]
    pure_she_missed_records = [
        record for record in she_missed_records
        if not record["stage2_risk_feature"]["queues"]
    ]
    no_top_records = [
        record for record in records
        if record["stage5_guide_ci"]["guide_category"] == "missing_usage_profile"
    ]
    industry_boundary_records = [
        record for record in records
        if record["stage5_guide_ci"]["guide_category"] == "industry_boundary_gap"
    ]
    workprocess_mismatch_records = [
        record for record in records
        if record["stage5_guide_ci"]["guide_category"] == "workprocess_mismatch"
    ]
    ci_mismatch_records = [
        record for record in records
        if "ci_guide_boundary_mismatch" in record["stage5_guide_ci"]["ci"]["queues"]
    ]
    ci_no_action_records = [
        record for record in records
        if "ci_no_action" in record["stage5_guide_ci"]["ci"]["queues"]
    ]
    photo_policies = [record["stage5_guide_ci"].get("photo_policy") or {} for record in records]
    photo_top_counts = Counter(
        ((policy.get("top") or {}).get("photo_matchability") or "unknown")
        for policy in photo_policies
    )

    expected_she = sum(1 for record in records if record["stage3_she"]["expected_should_match_she"])
    she_tp = sum(
        1 for record in records
        if record["stage3_she"]["expected_should_match_she"] and record["stage3_she"]["has_actionable_she"]
    )
    she_fn = sum(
        1 for record in records
        if record["stage3_she"]["expected_should_match_she"] and not record["stage3_she"]["has_actionable_she"]
    )
    she_fp = sum(
        1 for record in records
        if not record["stage3_she"]["expected_should_match_she"] and record["stage3_she"]["has_actionable_she"]
    )

    expected_sr = sum(1 for record in records if record["stage4_sr"]["expected_should_recommend_sr"])
    sr_tp = sum(
        1 for record in records
        if record["stage4_sr"]["expected_should_recommend_sr"] and record["stage4_sr"]["sr_ids"]
    )
    sr_fn = sum(
        1 for record in records
        if record["stage4_sr"]["expected_should_recommend_sr"] and not record["stage4_sr"]["sr_ids"]
    )
    sr_fp = sum(
        1 for record in records
        if not record["stage4_sr"]["expected_should_recommend_sr"] and record["stage4_sr"]["sr_ids"]
    )

    obvious_mismatch = sum(
        1 for record in records
        if record["stage5_guide_ci"]["guide_category"] in OBVIOUS_MISMATCH_CATEGORIES
    )
    no_top = guide_categories.get("missing_usage_profile", 0)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_samples": total,
        "version_counts": dict(sorted(Counter(record["version"] for record in records).items())),
        "case_type_counts": dict(sorted(Counter(record["case_type"] for record in records).items())),
        "failure_stage_counts": dict(sorted(stage_counts.items())),
        "primary_failure_stage_counts": dict(sorted(primary_counts.items())),
        "stage2_queue_counts": dict(sorted(stage2_queues.items())),
        "stage3_queue_counts": dict(sorted(stage3_queues.items())),
        "stage4_queue_counts": dict(sorted(stage4_queues.items())),
        "stage5_queue_counts": dict(sorted(stage5_queues.items())),
        "guide_category_counts": dict(sorted(guide_categories.items())),
        "ci_queue_counts": dict(sorted(ci_queues.items())),
        "she_metrics": {
            "expected_positive": expected_she,
            "true_positive": she_tp,
            "false_negative": she_fn,
            "false_positive": she_fp,
            "recall": pct(she_tp, expected_she),
        },
        "sr_metrics": {
            "expected_positive": expected_sr,
            "true_positive": sr_tp,
            "false_negative": sr_fn,
            "false_positive": sr_fp,
            "recall": pct(sr_tp, expected_sr),
        },
        "guide_metrics": {
            "current_obvious_top_guide_mismatch": obvious_mismatch,
            "no_top": no_top,
            "industry_boundary_gap": guide_categories.get("industry_boundary_gap", 0),
            "workprocess_mismatch": guide_categories.get("workprocess_mismatch", 0),
            "broad_sr_overreach": guide_categories.get("broad_sr_overreach", 0),
            "photo_unmatchable_top_count": sum(1 for policy in photo_policies if policy.get("photo_unmatchable_top")),
            "photo_unmatchable_suppressed_count": sum(
                1 for policy in photo_policies if policy.get("photo_unmatchable_suppressed")
            ),
            "followup_only_retained_count": sum(
                int(policy.get("followup_only_retained_count") or 0) for policy in photo_policies
            ),
            "top_replaced_by_photo_actionable_count": sum(
                1 for policy in photo_policies if policy.get("top_replaced_by_photo_actionable")
            ),
            "top_photo_matchability_counts": dict(sorted(photo_top_counts.items())),
        },
        "ci_metrics": {
            "ci_no_action": ci_queues.get("ci_no_action", 0),
            "ci_context_mismatch": ci_queues.get("ci_context_mismatch", 0),
            "ci_broad_sr_only": ci_queues.get("ci_broad_sr_only", 0),
            "ci_needs_review_used": ci_queues.get("ci_needs_review_used", 0),
            "ci_guide_boundary_mismatch": ci_queues.get("ci_guide_boundary_mismatch", 0),
        },
        "diagnostic_hotspots": {
            "stage2_risk_axis_unsupported": top_items(Counter(
                (note.get("field"), note.get("from"))
                for record in records
                for note in record["stage2_risk_feature"].get("risk_axis_unsupported_notes", [])
            )),
            "stage2_context_unsupported": top_items(Counter(
                (note.get("field"), note.get("from"))
                for record in records
                for note in record["stage2_risk_feature"].get("context_unsupported_notes", [])
            ), limit=20),
            "she_missed_by_version": top_items(Counter(record["version"] for record in she_missed_records)),
            "she_missed_by_industry": top_items(Counter(record.get("industry_context") for record in she_missed_records), limit=20),
            "pure_stage3_missed_by_version": top_items(Counter(record["version"] for record in pure_she_missed_records)),
            "pure_stage3_missed_by_industry": top_items(Counter(record.get("industry_context") for record in pure_she_missed_records), limit=20),
            "no_top_by_industry": top_items(Counter(record.get("industry_context") for record in no_top_records), limit=20),
            "industry_boundary_top_guides": top_items(Counter(
                (record["stage5_guide_ci"].get("top_procedure") or {}).get("guide_code")
                for record in industry_boundary_records
            ), limit=20),
            "workprocess_mismatch_top_guides": top_items(Counter(
                (record["stage5_guide_ci"].get("top_procedure") or {}).get("guide_code")
                for record in workprocess_mismatch_records
            ), limit=20),
            "ci_mismatch_source_guides": top_items(Counter(
                (record["stage5_guide_ci"]["ci"].get("top_action_ci_metadata") or {}).get("source_guide")
                for record in ci_mismatch_records
            ), limit=20),
            "ci_no_action_by_industry": top_items(Counter(record.get("industry_context") for record in ci_no_action_records), limit=20),
            "photo_unmatchable_baseline_suppressed_guides": top_items(Counter(
                ((record["stage5_guide_ci"].get("photo_policy") or {}).get("baseline_top") or {}).get("guide_code")
                for record in records
                if (record["stage5_guide_ci"].get("photo_policy") or {}).get("photo_unmatchable_suppressed")
            ), limit=20),
            "photo_actionable_replacement_guides": top_items(Counter(
                ((record["stage5_guide_ci"].get("photo_policy") or {}).get("top") or {}).get("guide_code")
                for record in records
                if (record["stage5_guide_ci"].get("photo_policy") or {}).get("top_replaced_by_photo_actionable")
            ), limit=20),
        },
        "attention_count": sum(1 for record in records if record["failure_stages"]),
        "attention_cases": [
            {
                "case_id": record["case_id"],
                "version": record["version"],
                "case_type": record["case_type"],
                "industry_context": record["industry_context"],
                "work_context": record["work_context"],
                "primary_failure_stage": record["primary_failure_stage"],
                "stage2": record["stage2_risk_feature"]["queues"],
                "stage3": record["stage3_she"]["queues"],
                "stage4": record["stage4_sr"]["queues"],
                "stage5": record["stage5_guide_ci"]["queues"],
                "top_guide": (record["stage5_guide_ci"].get("top_procedure") or {}).get("guide_code"),
                "top_ci": (record["stage5_guide_ci"]["ci"].get("top_action") or {}).get("source_id"),
            }
            for record in records
            if record["failure_stages"]
        ][:150],
    }


def write_markdown(path: Path, summary: dict[str, Any], records: list[dict[str, Any]]) -> None:
    lines = [
        "# Stage 2~5 Pipeline Quality Report",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- total_samples: `{summary['total_samples']}`",
        f"- version_counts: `{summary['version_counts']}`",
        f"- case_type_counts: `{summary['case_type_counts']}`",
        "",
        "## Stage Failure Counts",
        "",
        "```json",
        json.dumps({
            "failure_stage_counts": summary["failure_stage_counts"],
            "primary_failure_stage_counts": summary["primary_failure_stage_counts"],
        }, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Stage 2 RiskFeature",
        "",
        "```json",
        json.dumps(summary["stage2_queue_counts"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Stage 3 SHE",
        "",
        "```json",
        json.dumps({
            "metrics": summary["she_metrics"],
            "queues": summary["stage3_queue_counts"],
        }, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Stage 4 SR",
        "",
        "```json",
        json.dumps({
            "metrics": summary["sr_metrics"],
            "queues": summary["stage4_queue_counts"],
        }, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Stage 5 Guide / CI",
        "",
        "```json",
        json.dumps({
            "guide_metrics": summary["guide_metrics"],
            "guide_categories": summary["guide_category_counts"],
            "ci_metrics": summary["ci_metrics"],
            "ci_queues": summary["ci_queue_counts"],
        }, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Diagnostic Hotspots",
        "",
        "```json",
        json.dumps(summary["diagnostic_hotspots"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Attention Samples",
        "",
    ]
    for item in summary["attention_cases"][:50]:
        lines.append(
            f"- `{item['case_id']}` {item['primary_failure_stage']} "
            f"stage2={item['stage2']} stage3={item['stage3']} "
            f"stage4={item['stage4']} stage5={item['stage5']} "
            f"guide={item['top_guide']} ci={item['top_ci']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "version",
                "case_id",
                "case_type",
                "industry_context",
                "work_context",
                "primary_failure_stage",
                "failure_stages",
                "stage2_queues",
                "stage3_queues",
                "stage4_queues",
                "stage5_queues",
                "she_expected",
                "she_actionable",
                "she_confirmed",
                "sr_expected",
                "sr_count",
                "broad_sr_count",
                "top_guide",
                "top_guide_photo_matchability",
                "photo_unmatchable_suppressed",
                "top_replaced_by_photo_actionable",
                "guide_category",
                "top_ci",
                "ci_queues",
                "finding_status",
                "penalty_exposure_status",
            ],
        )
        writer.writeheader()
        for record in records:
            stage5 = record["stage5_guide_ci"]
            ci = stage5["ci"]
            photo_policy = stage5.get("photo_policy") or {}
            top_photo = photo_policy.get("top") or {}
            writer.writerow({
                "version": record["version"],
                "case_id": record["case_id"],
                "case_type": record["case_type"],
                "industry_context": record["industry_context"],
                "work_context": record["work_context"],
                "primary_failure_stage": record["primary_failure_stage"],
                "failure_stages": ",".join(record["failure_stages"]),
                "stage2_queues": ",".join(record["stage2_risk_feature"]["queues"]),
                "stage3_queues": ",".join(record["stage3_she"]["queues"]),
                "stage4_queues": ",".join(record["stage4_sr"]["queues"]),
                "stage5_queues": ",".join(stage5["queues"]),
                "she_expected": record["stage3_she"]["expected_should_match_she"],
                "she_actionable": record["stage3_she"]["has_actionable_she"],
                "she_confirmed": record["stage3_she"]["has_confirmed_she"],
                "sr_expected": record["stage4_sr"]["expected_should_recommend_sr"],
                "sr_count": len(record["stage4_sr"]["sr_ids"]),
                "broad_sr_count": len(record["stage4_sr"]["broad_sr_ids"]),
                "top_guide": (stage5.get("top_procedure") or {}).get("guide_code"),
                "top_guide_photo_matchability": top_photo.get("photo_matchability"),
                "photo_unmatchable_suppressed": bool(photo_policy.get("photo_unmatchable_suppressed")),
                "top_replaced_by_photo_actionable": bool(photo_policy.get("top_replaced_by_photo_actionable")),
                "guide_category": stage5["guide_category"],
                "top_ci": (ci.get("top_action") or {}).get("source_id"),
                "ci_queues": ",".join(ci["queues"]),
                "finding_status": record["finding_status"],
                "penalty_exposure_status": record["penalty_exposure_status"],
            })


async def run(args: argparse.Namespace) -> dict[str, Path]:
    if args.enable_stage2_normalization_v2:
        os.environ["OHS_ENABLE_STAGE2_NORMALIZATION_V2"] = "1"
    rows = load_synthetic_rows(args.input_glob)
    if args.limit:
        rows = rows[: args.limit]
    profiles = load_profiles()
    broad_sr_ids = get_broad_sr_ids()
    photo_baseline_top_map = load_photo_baseline_top_map(args.photo_baseline_report)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    original_persist = analysis_pipeline._persist_response
    analysis_pipeline._persist_response = lambda *_, **__: None  # type: ignore[method-assign]
    db = SessionLocal()
    records: list[dict[str, Any]] = []
    shadow_stats: dict[str, Any] | None = None
    try:
        try:
            db.execute(text("SELECT 1"))
        except OperationalError as exc:
            raise DatabaseUnavailableError(
                "PostgreSQL is not reachable. Start the OHS database before running Stage 2~5 replay."
            ) from exc
        if args.shadow_she_candidates:
            shadow_stats = install_shadow_she_candidates(
                db,
                args.shadow_she_candidates,
                priorities=args.shadow_she_priorities,
                limit=args.shadow_she_limit,
                use_runtime_match_features=args.shadow_she_use_runtime_match_features,
                require_visual_trigger=args.shadow_she_require_visual_trigger,
                min_visual_score=args.shadow_she_min_visual_score,
            )
            print(f"[INFO] installed shadow SHE candidates: {shadow_stats}")
        for index, row in enumerate(rows, start=1):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                records.append(await build_case_record(db, row, profiles, broad_sr_ids, photo_baseline_top_map))
            if args.progress_every and index % args.progress_every == 0:
                print(f"[INFO] processed {index}/{len(rows)}")
    finally:
        if shadow_stats:
            db.rollback()
        db.close()
        analysis_pipeline._persist_response = original_persist  # type: ignore[method-assign]

    summary = build_summary(records)
    report = {
        "input_pattern": str(args.input_glob),
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settings": {
            "limit": args.limit,
            "enable_stage2_normalization_v2": bool(args.enable_stage2_normalization_v2),
            "shadow_she": shadow_stats,
            "photo_baseline_report": str(args.photo_baseline_report) if args.photo_baseline_report else None,
        },
        "summary": summary,
        "records": records,
    }

    json_path = args.output_dir / f"{args.report_prefix}.json"
    md_path = args.output_dir / f"{args.report_prefix}.md"
    csv_path = args.output_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, summary, records)
    write_csv(csv_path, records)
    return {"json": json_path, "md": md_path, "csv": csv_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-glob", type=Path, default=DEFAULT_INPUT_GLOB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--limit", type=int, default=0, help="Optional first-N sample limit for smoke runs.")
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument(
        "--photo-baseline-report",
        type=Path,
        default=DEFAULT_PHOTO_BASELINE_REPORT,
        help="Baseline Stage 2~5 report used to count photo-unmatchable suppressions/replacements.",
    )
    parser.add_argument(
        "--enable-stage2-normalization-v2",
        action="store_true",
        help="Opt into experimental Stage 2 exact-code folding without changing default runtime behavior.",
    )
    parser.add_argument(
        "--shadow-she-candidates",
        type=Path,
        default=None,
        const=DEFAULT_SHADOW_SHE_CANDIDATES,
        nargs="?",
        help="Temporarily insert review-only SHE candidates into this DB session and rollback after replay.",
    )
    parser.add_argument(
        "--shadow-she-priorities",
        default="high",
        help="Comma-separated review priorities to include, or 'all'. Default: high.",
    )
    parser.add_argument(
        "--shadow-she-limit",
        type=int,
        default=0,
        help="Optional first-N shadow candidate limit after priority filtering.",
    )
    parser.add_argument(
        "--shadow-she-use-runtime-match-features",
        action="store_true",
        help="Insert candidate runtime_match_features instead of exact ontology features for shadow matching.",
    )
    parser.add_argument(
        "--shadow-she-require-visual-trigger",
        action="store_true",
        help="Require candidate visual_triggers to match the observation before a shadow SHE can match.",
    )
    parser.add_argument(
        "--shadow-she-min-visual-score",
        type=float,
        default=0.2,
        help="Minimum visual trigger score when --shadow-she-require-visual-trigger is enabled.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        paths = asyncio.run(run(args))
    except DatabaseUnavailableError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    report = json.loads(paths["json"].read_text(encoding="utf-8"))
    summary = report["summary"]
    print("=== Stage 2~5 Pipeline Quality ===")
    print(f"total: {summary['total_samples']}")
    print(f"stage failures: {summary['failure_stage_counts']}")
    print(f"SHE: {summary['she_metrics']}")
    print(f"SR: {summary['sr_metrics']}")
    print(f"Guide: {summary['guide_metrics']}")
    print(f"CI: {summary['ci_metrics']}")
    print(f"wrote: {paths['json']}")
    print(f"wrote: {paths['md']}")
    print(f"wrote: {paths['csv']}")


if __name__ == "__main__":
    main()
