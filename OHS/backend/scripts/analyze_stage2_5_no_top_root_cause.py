#!/usr/bin/env python3
"""Classify Stage 2~5 NO_TOP cases into structural repair queues.

This audit consumes the integrated Stage 2~5 replay report.  It does not run
the product pipeline again and it does not change runtime data.  The goal is to
separate NO_TOP cases into taxonomy, SHE/SR, SituationFrame, Guide usage
profile, and WorkProcess/serving bridge queues so the next repair is structural
instead of keyword-by-keyword.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.guide_photo_matchability import PHOTO_ACTIONABLE, get_photo_matchability  # noqa: E402
from app.services.situation_frame_service import build_situation_frame, match_guide_support_candidates  # noqa: E402


DEFAULT_SOURCE_REPORT = PROJECT_ROOT / "pictures-json" / "reports" / "pipeline_quality_v1_v10_photo_matchability1.json"
DEFAULT_PREVIOUS_REPORT = PROJECT_ROOT / "pictures-json" / "reports" / "pipeline_quality_v1_v10_situation_frame_support7.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_PROFILE_PATH = BACKEND_DIR / "app" / "data" / "guide_domain_profiles.json"

GENERIC_FEATURE_CODES = {
    "GENERAL_WORKPLACE",
    "CHEMICAL",
    "CHEMICAL_EXPOSURE",
    "CHEMICAL_WORK",
    "FIRE",
    "EXPLOSION",
    "FIRE_EXPLOSION",
    "ELECTRICAL_WORK",
    "ELECTRICITY",
    "MACHINE",
    "ERGONOMIC",
    "VENTILATION_POOR",
}
BROAD_FEATURE_CODES = {
    "FALL",
    "SLIP",
    "COLLISION",
    "FALLING_OBJECT",
    "CRUSH",
    "CUT",
    "COLLAPSE",
    "ERGONOMIC",
    "BURN",
    "ELECTRIC_SHOCK",
    "EXPLOSION",
    "CHEMICAL_EXPOSURE",
    "MATERIAL_HANDLING",
    "MACHINE",
    "VEHICLE",
    "CHEMICAL",
    "FIRE",
    "ELECTRICITY",
    "ELECTRICAL_WORK",
}
DOMAIN_BUCKET_FEATURES = {
    "service_healthcare_people_gap": {
        "HAIR_WASH",
        "DOG_GROOMING",
        "CAT_HANDLING",
        "SKIN_DEVICE",
        "CASHIER_AREA",
        "NIGHT_SOLO",
        "GENERAL_WORKPLACE",
    },
    "chemical_profile_gap": {
        "CHEMICAL",
        "CHEMICAL_WORK",
        "CHEMICAL_EXPOSURE",
        "TOXIC",
        "CORROSION",
        "DRY_CLEANING_SOLVENT",
        "PAINTING",
    },
    "machine_profile_gap": {
        "MACHINE",
        "CRUSH",
        "CUT",
        "SAWING",
        "INJECTION_MOLDING",
        "TIRE_CHANGE",
        "CONVEYOR",
    },
    "construction_fall_profile_gap": {
        "FALL",
        "LADDER",
        "SCAFFOLD",
        "LIFT_WORK",
        "EXCAVATION",
        "COLLAPSE",
        "CONSTRUCTION_EQUIP",
        "CRANE",
    },
    "material_handling_profile_gap": {
        "MATERIAL_HANDLING",
        "BOX_HANDLING",
        "FALLING_OBJECT",
        "STEELWORK",
        "FORKLIFT_OPERATION",
    },
    "electrical_profile_gap": {
        "ELECTRICITY",
        "ELECTRICAL_WORK",
        "ELECTRIC_SHOCK",
        "ARC_FLASH",
    },
    "burn_heat_profile_gap": {
        "BURN",
        "HEAT_COLD",
        "HOT_BEVERAGE",
        "DEEP_FRYING",
    },
}
DOMAIN_BUCKET_TEXT = {
    "service_healthcare_people_gap": ("복지", "병원", "요양", "미용", "아동", "상담", "고객", "이용자", "환자"),
    "chemical_profile_gap": ("화학", "약품", "용제", "시약", "도장", "살포", "msds"),
    "machine_profile_gap": ("기계", "세탁기", "슬라이서", "프레스", "성형", "컨베이어", "회전"),
    "construction_fall_profile_gap": ("건설", "굴착", "비계", "거푸집", "고소", "크레인", "추락"),
    "material_handling_profile_gap": ("운반", "적재", "하역", "팔레트", "중량물", "상자"),
    "electrical_profile_gap": ("전기", "활선", "감전", "배전", "충전부"),
    "burn_heat_profile_gap": ("화상", "고온", "튀김", "뜨거운", "가열"),
}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _case_key(record: dict[str, Any]) -> str:
    return f"{record.get('version')}::{record.get('line_no')}::{record.get('case_id')}"


def _text(record: dict[str, Any]) -> str:
    values = [
        record.get("industry_context") or "",
        record.get("work_context") or "",
        record.get("photo_description") or "",
        record.get("expected_primary_risk") or "",
    ]
    return " ".join(str(value) for value in values if value).lower()


def _actual_features(record: dict[str, Any]) -> dict[str, list[str]]:
    return record["stage2_risk_feature"].get("actual_features") or {
        "accident_types": [],
        "hazardous_agents": [],
        "work_contexts": [],
    }


def _feature_codes(record: dict[str, Any]) -> list[str]:
    actual = _actual_features(record)
    codes: list[str] = []
    for field in ("accident_types", "hazardous_agents", "work_contexts"):
        codes.extend(str(code) for code in actual.get(field, []) if code)
    return _unique(codes)


def _canonical(record: dict[str, Any]) -> dict[str, list[str]]:
    actual = _actual_features(record)
    return {
        "accident_types": list(actual.get("accident_types") or []),
        "hazardous_agents": list(actual.get("hazardous_agents") or []),
        "work_contexts": list(actual.get("work_contexts") or []),
    }


def _profile_terms(profile: dict[str, Any]) -> list[str]:
    boundary = profile.get("recommendation_boundary") or {}
    terms: list[str] = []
    for key in (
        "required_context_terms",
        "visual_triggers",
        "industry_alignment",
        "intended_workplaces",
        "intended_tasks",
        "observable_required_cues",
    ):
        values = profile.get(key) or []
        if isinstance(values, list):
            terms.extend(str(value) for value in values if value)
    terms.extend(str(value) for value in (boundary.get("include_when") or []) if value)
    if profile.get("guide_code") == "P-55-2012":
        terms = [term for term in terms if term != "황"]
    return _unique(terms)


def _term_hits(text: str, terms: list[str], limit: int = 5) -> list[str]:
    hits: list[str] = []
    for term in terms:
        lowered = term.lower()
        if lowered and lowered in text and term not in hits:
            hits.append(term)
        if len(hits) >= limit:
            break
    return hits


def _load_profiles(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("profiles") or {}


def _previous_top_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for record in data.get("records") or []:
        top = ((record.get("stage5_guide_ci") or {}).get("top_procedure") or {})
        if top:
            out[_case_key(record)] = top
    return out


def domain_bucket(record: dict[str, Any], frame: dict[str, Any]) -> str:
    features = set(_feature_codes(record))
    text = _text(record)
    for bucket, bucket_features in DOMAIN_BUCKET_FEATURES.items():
        if features & bucket_features:
            return bucket
    for bucket, terms in DOMAIN_BUCKET_TEXT.items():
        if any(term in text for term in terms):
            return bucket
    parents = set(frame.get("parent_contexts") or [])
    if "MACHINE" in parents:
        return "machine_profile_gap"
    if "CHEMICAL_WORK" in parents:
        return "chemical_profile_gap"
    if parents & {"EXCAVATION", "SCAFFOLD", "CONSTRUCTION_EQUIP", "CRANE"}:
        return "construction_fall_profile_gap"
    if parents & {"MATERIAL_HANDLING", "BOX_HANDLING"}:
        return "material_handling_profile_gap"
    return "other_taxonomy_gap"


def profile_candidates(record: dict[str, Any], profiles: dict[str, Any]) -> dict[str, Any]:
    text = _text(record)
    features = set(_feature_codes(record))
    non_generic = features - GENERIC_FEATURE_CODES
    rows: list[dict[str, Any]] = []
    for guide_code, profile in profiles.items():
        policy = get_photo_matchability(guide_code, profile)
        if policy.get("photo_matchability") != PHOTO_ACTIONABLE:
            continue
        profile_features = set(profile.get("feature_codes") or [])
        feature_hits = sorted((features & profile_features) - GENERIC_FEATURE_CODES)
        if not feature_hits and non_generic:
            continue
        term_hits = _term_hits(text, _profile_terms(profile), limit=4)
        if not feature_hits and not term_hits:
            continue
        score = len(feature_hits) * 2 + len(term_hits)
        rows.append({
            "guide_code": guide_code,
            "title": profile.get("title"),
            "procedure_role": profile.get("procedure_role"),
            "profile_level": profile.get("profile_level"),
            "feature_hits": feature_hits[:5],
            "term_hits": term_hits[:5],
            "score": score,
        })
    rows.sort(key=lambda item: (-item["score"], item["guide_code"]))
    return {
        "candidate_count": len(rows),
        "term_candidate_count": sum(1 for row in rows if row["term_hits"]),
        "feature_candidate_count": sum(1 for row in rows if row["feature_hits"]),
        "top_candidates": rows[:5],
    }


def primary_root_cause(
    *,
    record: dict[str, Any],
    frame: dict[str, Any],
    support_hits: list[dict[str, Any]],
    candidates: dict[str, Any],
    previous_top: dict[str, Any] | None,
    previous_top_matchability: str | None,
) -> tuple[str, str, str]:
    stage2_queues = set(record["stage2_risk_feature"].get("queues") or [])
    stage3_queues = set(record["stage3_she"].get("queues") or [])
    stage4_queues = set(record["stage4_sr"].get("queues") or [])
    sr_ids = record["stage4_sr"].get("sr_ids") or []
    child_available = bool(frame.get("equipment_contexts"))
    broad_parent_without_child = bool(frame.get("parent_contexts")) and not child_available
    catalog_gap = bool(stage2_queues & {"non_catalog_feature", "wrong_axis", "missing_work_context"})

    if previous_top and previous_top_matchability != PHOTO_ACTIONABLE:
        return "photo_gate_removed_only_candidate", "stage5_profile", "Previous top was non-photo-actionable and no replacement top exists."
    if frame.get("match_policy") == "status_safe":
        return "synthetic_fixture_or_safe_controlled_positive", "fixture_review", "Positive fixture has safe/control cues, so no top procedure may be acceptable."
    if catalog_gap:
        return "stage2_taxonomy_or_normalization_gap", "stage2_taxonomy", "Runtime features miss a needed catalog/axis/work-context value."
    if "sr_missed" in stage4_queues and "she_missed" in stage3_queues:
        return "stage3_she_to_sr_gap", "stage3_she_sr", "No actionable SHE/SR path reaches Guide recommendation."
    if "sr_missed" in stage4_queues:
        return "stage4_sr_lookup_gap", "stage4_sr", "Risk features exist, but SR lookup produced no serving SR."
    if "she_missed" in stage3_queues and sr_ids:
        return "stage3_she_gap_but_sr_available", "stage3_she", "SRs exist, but no actionable SHE source Guide or support signal anchors ranking."
    if child_available and not support_hits:
        return "situation_frame_child_support_gap", "situation_frame_support", "Child context exists but has no accepted Guide support candidate."
    if broad_parent_without_child:
        return "situation_frame_child_context_gap", "situation_frame_taxonomy", "Only broad parent context is available; child context is needed for Guide support."
    if candidates["candidate_count"] == 0:
        return "guide_usage_profile_coverage_gap", "guide_usage_profile", "No photo-actionable Guide profile overlaps runtime feature/context."
    if candidates["term_candidate_count"] == 0:
        return "guide_usage_profile_context_gap", "guide_usage_profile", "Potential Guide profiles exist by feature but lack observable/context term hits."
    return "runtime_scoring_or_db_bridge_gap", "serving_bridge", "Profiles/SRs exist but did not materialize into a ranked standard procedure."


def build_rows(
    source_report: dict[str, Any],
    profiles: dict[str, Any],
    previous_top_by_case: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in source_report.get("records") or []:
        stage5 = record.get("stage5_guide_ci") or {}
        if stage5.get("guide_category") != "missing_usage_profile":
            continue
        if (stage5.get("top_procedure") or {}).get("guide_code"):
            continue
        text = _text(record)
        frame = build_situation_frame(
            canonical=_canonical(record),
            visual_cues=[],
            context_text=text,
            industry_contexts=[str(record.get("industry_context") or "")],
        ).to_dict()
        support_hits = match_guide_support_candidates(frame, visual_cues=[], context_text=text)
        candidates = profile_candidates(record, profiles)
        previous_top = previous_top_by_case.get(_case_key(record))
        previous_top_policy = None
        if previous_top:
            previous_profile = profiles.get(previous_top.get("guide_code") or "")
            previous_top_policy = get_photo_matchability(previous_top.get("guide_code"), previous_profile).get("photo_matchability")
        root_cause, repair_lane, root_reason = primary_root_cause(
            record=record,
            frame=frame,
            support_hits=support_hits,
            candidates=candidates,
            previous_top=previous_top,
            previous_top_matchability=previous_top_policy,
        )
        stage2_queues = record["stage2_risk_feature"].get("queues") or []
        stage3_queues = record["stage3_she"].get("queues") or []
        stage4_queues = record["stage4_sr"].get("queues") or []
        rows.append({
            "case_key": _case_key(record),
            "version": record.get("version"),
            "line_no": record.get("line_no"),
            "case_id": record.get("case_id"),
            "case_type": record.get("case_type"),
            "industry_context": record.get("industry_context"),
            "work_context": record.get("work_context"),
            "primary_root_cause": root_cause,
            "repair_lane": repair_lane,
            "root_reason": root_reason,
            "domain_bucket": domain_bucket(record, frame),
            "stage2_queues": stage2_queues,
            "stage3_queues": stage3_queues,
            "stage4_queues": stage4_queues,
            "sr_count": len(record["stage4_sr"].get("sr_ids") or []),
            "broad_sr_count": len(record["stage4_sr"].get("broad_sr_ids") or []),
            "top_she_count": len(record["stage3_she"].get("top_she") or []),
            "frame_match_policy": frame.get("match_policy"),
            "frame_child_contexts": frame.get("equipment_contexts") or [],
            "frame_parent_contexts": frame.get("parent_contexts") or [],
            "frame_task_contexts": frame.get("task_contexts") or [],
            "frame_observable_cues": frame.get("observable_cues") or [],
            "frame_safe_cues": frame.get("safe_cues") or [],
            "support_hit_count": len(support_hits),
            "support_hits": support_hits[:3],
            "profile_candidate_count": candidates["candidate_count"],
            "profile_term_candidate_count": candidates["term_candidate_count"],
            "profile_feature_candidate_count": candidates["feature_candidate_count"],
            "profile_top_candidates": candidates["top_candidates"],
            "previous_top_guide": (previous_top or {}).get("guide_code"),
            "previous_top_photo_matchability": previous_top_policy,
            "feature_codes": _feature_codes(record),
            "photo_description": record.get("photo_description"),
            "expected_primary_risk": record.get("expected_primary_risk"),
            "expected_corrective_direction": record.get("expected_corrective_direction"),
        })
    return rows


def top_items(counter: Counter[Any], limit: int = 30) -> list[dict[str, Any]]:
    out = []
    for key, count in counter.most_common(limit):
        if isinstance(key, tuple):
            label = " / ".join(str(part) for part in key)
        else:
            label = str(key)
        out.append({"key": label, "count": count})
    return out


def build_summary(rows: list[dict[str, Any]], source_report: Path, previous_report: Path | None) -> dict[str, Any]:
    root_counts = Counter(row["primary_root_cause"] for row in rows)
    lane_counts = Counter(row["repair_lane"] for row in rows)
    bucket_counts = Counter(row["domain_bucket"] for row in rows)
    stage2_counts = Counter(queue for row in rows for queue in row["stage2_queues"])
    stage3_counts = Counter(queue for row in rows for queue in row["stage3_queues"])
    stage4_counts = Counter(queue for row in rows for queue in row["stage4_queues"])
    candidate_counts = [int(row["profile_candidate_count"]) for row in rows]
    term_candidate_counts = [int(row["profile_term_candidate_count"]) for row in rows]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_report": str(source_report),
        "previous_report": str(previous_report) if previous_report else None,
        "total_no_top": len(rows),
        "primary_root_cause_counts": dict(root_counts.most_common()),
        "repair_lane_counts": dict(lane_counts.most_common()),
        "domain_bucket_counts": dict(bucket_counts.most_common()),
        "stage_queue_counts": {
            "stage2": dict(stage2_counts.most_common()),
            "stage3": dict(stage3_counts.most_common()),
            "stage4": dict(stage4_counts.most_common()),
        },
        "situation_frame": {
            "match_policy_counts": dict(Counter(row["frame_match_policy"] for row in rows).most_common()),
            "child_context_available": sum(1 for row in rows if row["frame_child_contexts"]),
            "broad_parent_without_child": sum(
                1 for row in rows if row["frame_parent_contexts"] and not row["frame_child_contexts"]
            ),
            "support_hit_cases": sum(1 for row in rows if row["support_hit_count"]),
            "top_parent_contexts": top_items(Counter(parent for row in rows for parent in row["frame_parent_contexts"]), 25),
            "top_child_contexts": top_items(Counter(child for row in rows for child in row["frame_child_contexts"]), 25),
        },
        "guide_profile_candidates": {
            "avg_candidate_count": round(mean(candidate_counts), 2) if candidate_counts else 0,
            "avg_term_candidate_count": round(mean(term_candidate_counts), 2) if term_candidate_counts else 0,
            "zero_profile_candidate_cases": sum(1 for count in candidate_counts if count == 0),
            "zero_term_candidate_cases": sum(1 for count in term_candidate_counts if count == 0),
        },
        "hotspots": {
            "top_industries": top_items(Counter(row["industry_context"] for row in rows), 25),
            "top_work_contexts": top_items(Counter(row["work_context"] for row in rows), 25),
            "top_feature_codes": top_items(Counter(feature for row in rows for feature in row["feature_codes"]), 30),
            "root_cause_by_domain": top_items(Counter(
                (row["primary_root_cause"], row["domain_bucket"]) for row in rows
            ), 30),
            "repair_lane_by_domain": top_items(Counter(
                (row["repair_lane"], row["domain_bucket"]) for row in rows
            ), 30),
        },
        "priority_repair_plan": priority_repair_plan(rows),
    }


def priority_repair_plan(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    combos = Counter((row["repair_lane"], row["domain_bucket"]) for row in rows)
    plan = []
    for (lane, bucket), count in combos.most_common(12):
        sample_rows = [row for row in rows if row["repair_lane"] == lane and row["domain_bucket"] == bucket][:5]
        plan.append({
            "repair_lane": lane,
            "domain_bucket": bucket,
            "count": count,
            "why_it_matters": repair_lane_reason(lane),
            "sample_case_ids": [row["case_id"] for row in sample_rows],
            "sample_feature_codes": _unique([feature for row in sample_rows for feature in row["feature_codes"]])[:12],
            "sample_child_contexts": _unique([child for row in sample_rows for child in row["frame_child_contexts"]])[:12],
            "sample_parent_contexts": _unique([parent for row in sample_rows for parent in row["frame_parent_contexts"]])[:12],
        })
    return plan


def repair_lane_reason(lane: str) -> str:
    return {
        "fixture_review": "Check whether the positive fixture actually shows a current unsafe condition.",
        "stage2_taxonomy": "Add or re-axis child context taxonomy without broadening status-level inference.",
        "stage3_she_sr": "Create review-only SHE/SR candidates or connect existing patterns conservatively.",
        "stage4_sr": "Repair SR lookup/family coverage before Guide scoring.",
        "stage3_she": "Attach Guide support without promoting SHE status when SRs already exist.",
        "situation_frame_support": "Convert child contexts into Guide support candidates with strict boundary evidence.",
        "situation_frame_taxonomy": "Split broad parent contexts into observable child contexts.",
        "guide_usage_profile": "Add usage profile terms, visual triggers, and primary WorkProcess ids.",
        "serving_bridge": "Inspect DB candidate/materialized links and scoring gates.",
        "stage5_profile": "Photo gate removed the only candidate; find a photo-actionable replacement profile.",
    }.get(lane, "Review manually.")


def write_outputs(rows: list[dict[str, Any]], summary: dict[str, Any], output_dir: Path, prefix: str) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{prefix}.json"
    csv_path = output_dir / f"{prefix}.csv"
    md_path = output_dir / f"{prefix}.md"
    json_path.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fieldnames = [
        "case_id",
        "version",
        "case_type",
        "industry_context",
        "work_context",
        "primary_root_cause",
        "repair_lane",
        "domain_bucket",
        "stage2_queues",
        "stage3_queues",
        "stage4_queues",
        "sr_count",
        "top_she_count",
        "frame_match_policy",
        "frame_child_contexts",
        "frame_parent_contexts",
        "support_hit_count",
        "profile_candidate_count",
        "profile_term_candidate_count",
        "previous_top_guide",
        "previous_top_photo_matchability",
        "feature_codes",
        "photo_description",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(row[key], ensure_ascii=False) if isinstance(row.get(key), (list, dict)) else row.get(key)
                for key in fieldnames
            })
    write_markdown(md_path, summary, rows)
    return {"json": json_path, "csv": csv_path, "md": md_path}


def write_markdown(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Stage 2~5 NO_TOP Root-Cause Audit",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- source_report: `{summary['source_report']}`",
        f"- total_no_top: `{summary['total_no_top']}`",
        "",
        "## Primary Root Causes",
        "",
        "| root cause | count |",
        "| --- | ---: |",
    ]
    for key, count in summary["primary_root_cause_counts"].items():
        lines.append(f"| `{key}` | {count} |")
    lines.extend(["", "## Repair Lanes", "", "| repair lane | count |", "| --- | ---: |"])
    for key, count in summary["repair_lane_counts"].items():
        lines.append(f"| `{key}` | {count} |")
    lines.extend(["", "## Domain Buckets", "", "| domain bucket | count |", "| --- | ---: |"])
    for key, count in summary["domain_bucket_counts"].items():
        lines.append(f"| `{key}` | {count} |")
    lines.extend([
        "",
        "## SituationFrame Snapshot",
        "",
        "```json",
        json.dumps(summary["situation_frame"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Guide Profile Candidate Snapshot",
        "",
        "```json",
        json.dumps(summary["guide_profile_candidates"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Priority Repair Plan",
        "",
    ])
    for item in summary["priority_repair_plan"]:
        lines.append(
            f"- `{item['repair_lane']}` / `{item['domain_bucket']}`: {item['count']} cases. "
            f"{item['why_it_matters']} samples={item['sample_case_ids']}"
        )
    lines.extend(["", "## Samples", ""])
    for row in rows[:40]:
        lines.append(
            f"- `{row['case_id']}` `{row['primary_root_cause']}` / `{row['domain_bucket']}` "
            f"{row.get('industry_context') or ''} {row.get('work_context') or ''}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument("--previous-report", type=Path, default=DEFAULT_PREVIOUS_REPORT)
    parser.add_argument("--profile-path", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-prefix", default="stage2_5_no_top_root_cause_photo_matchability1")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = json.loads(args.source_report.read_text(encoding="utf-8"))
    profiles = _load_profiles(args.profile_path)
    previous_top = _previous_top_map(args.previous_report)
    rows = build_rows(source, profiles, previous_top)
    summary = build_summary(rows, args.source_report, args.previous_report)
    paths = write_outputs(rows, summary, args.output_dir, args.report_prefix)
    print(json.dumps({
        "total_no_top": summary["total_no_top"],
        "primary_root_cause_counts": summary["primary_root_cause_counts"],
        "repair_lane_counts": summary["repair_lane_counts"],
        "outputs": {key: str(value) for key, value in paths.items()},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
