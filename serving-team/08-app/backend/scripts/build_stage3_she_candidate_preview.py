#!/usr/bin/env python3
"""Build review-only SHE candidate JSONL from Stage 3 gap diagnostics.

The generated candidates are deliberately not serving artifacts:

- status=draft
- review_status=needs_review
- no DB import path in this script
- source SRs are candidate evidence, not asserted legal mappings

Use this after `analyze_stage3_she_gap_candidates.py` to turn structural SHE
gaps into a compact review queue.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
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
from app.services import hazard_rule_engine  # noqa: E402
from app.services.industry_context import industry_hints_for_features  # noqa: E402
from analyze_stage3_she_gap_candidates import CONTEXT_FAMILY_HINTS  # noqa: E402
from bootstrap_she_from_synthetic import broadness, build_features, build_she_id  # noqa: E402
from evaluate_synthetic_guide_recommendations import load_synthetic_rows  # noqa: E402
from evaluate_synthetic_observations import (  # noqa: E402
    apply_case_work_context_hint,
    infer_features_from_row,
    normalize_features,
)


DEFAULT_GAP_REPORT = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "stage3_she_gap_candidates_reference_guard1.json"
DEFAULT_SYNTHETIC_GLOB = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "synthetic_observations_v*.jsonl"
DEFAULT_CANDIDATE_OUTPUT = (
    PROJECT_ROOT / "koshaontology" / "data" / "she" / "she-stage3-new-pattern-candidates-reference-guard1.jsonl"
)
DEFAULT_REPORT_PREFIX = "stage3_she_new_pattern_candidate_preview_reference_guard1"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_CLASSES = ("new_she_pattern_needed",)

ADDITIONAL_CONTEXT_FAMILY_HINTS = {
    "ASSEMBLY_PRESS": ["MACHINE"],
    "BAND_SAW": ["MACHINE", "SAWING"],
    "BINDING_MACHINE": ["MACHINE"],
    "BLASTING_OPERATION": ["EXCAVATION", "CHEMICAL_WORK"],
    "BRAKE_EXHAUST_WORK": ["VEHICLE", "MACHINE", "CHEMICAL_WORK"],
    "CHEMICAL_DISINFECTANT": ["CHEMICAL_WORK", "CLEANING_WET"],
    "CLEANING_SANITATION": ["CHEMICAL_WORK", "CLEANING_WET"],
    "CLEANROOM_OPERATION": ["CHEMICAL_WORK", "GENERAL_WORKPLACE"],
    "COLD_CHAIN_HANDLING": ["COLD_STORAGE", "MATERIAL_HANDLING"],
    "COLD_STORAGE_WORK": ["COLD_STORAGE"],
    "CONCRETE_FINISHING": ["CONSTRUCTION_EQUIP", "EXCAVATION"],
    "CONCRETE_POURING": ["CONSTRUCTION_EQUIP"],
    "CONVEYOR_HOOK": ["CONVEYOR", "CRANE"],
    "CONVEYOR_OPERATION": ["CONVEYOR", "MACHINE"],
    "CUTTING_BONING": ["MACHINE"],
    "CUTTING_FABRIC": ["MACHINE"],
    "DECKING_INSTALLATION": ["SCAFFOLD", "STEELWORK"],
    "DUST_COLLECTION": ["CHEMICAL_WORK", "VENTILATION_POOR"],
    "DYEING_FINISHING": ["CHEMICAL_WORK"],
    "EARTH_RETAINING": ["EXCAVATION"],
    "ENGINE_OVERHAUL": ["VEHICLE", "MACHINE", "CHEMICAL_WORK"],
    "EQUIPMENT_MAINTENANCE": ["MACHINE"],
    "EXTRUSION_OPERATION": ["MACHINE"],
    "FOOD_PROCESSING_LINE": ["MACHINE", "CONVEYOR"],
    "FORMWORK_STRIPPING": ["SCAFFOLD", "CONSTRUCTION_EQUIP"],
    "MACHINE_MAINTENANCE": ["MACHINE"],
    "MAINTENANCE_HEIGHT": ["SCAFFOLD", "LADDER", "ROPE_ACCESS"],
    "MINE_GAS_DETECTION": ["CONFINED_SPACE", "EXCAVATION"],
    "NEEDLE_BROKEN": ["BIOLOGICAL", "GENERAL_WORKPLACE"],
    "PACKAGING_OPERATION": ["MACHINE", "CONVEYOR", "MATERIAL_HANDLING"],
    "PATIENT_TRANSFER": ["MATERIAL_HANDLING", "GENERAL_WORKPLACE"],
    "PLANER_JOINTER": ["MACHINE"],
    "PLATE_MAKING": ["CHEMICAL_WORK"],
    "PUMP_OPERATION": ["CONSTRUCTION_EQUIP", "PRESSURE_VESSEL", "MACHINE"],
    "REBAR_WORK": ["STEELWORK", "CONSTRUCTION_EQUIP"],
    "SLAUGHTER_LINE": ["MACHINE"],
    "SORTING_LINE": ["CONVEYOR", "MATERIAL_HANDLING"],
    "STEEL_ERECTION": ["STEELWORK", "SCAFFOLD", "CRANE"],
    "TUNNEL_SUPPORT": ["EXCAVATION", "CONFINED_SPACE"],
    "UNDERGROUND_UTILITY": ["EXCAVATION", "CONFINED_SPACE", "ELECTRICAL_WORK"],
}

CONTEXT_KEYWORD_FAMILY_HINTS = (
    (("SAW", "CUTTING", "PLANER", "JOINTER", "LATHE", "MILLING"), ["MACHINE"]),
    (("PRESS", "MOLDING", "INJECTION", "EXTRUSION", "SHREDDER", "COMPACTOR"), ["MACHINE"]),
    (("CONVEYOR", "SORTING_LINE", "PACKAGING"), ["CONVEYOR", "MATERIAL_HANDLING"]),
    (("CRANE", "HOIST", "LIFT"), ["CRANE", "LIFT_WORK"]),
    (("EXCAVATION", "TUNNEL", "UNDERGROUND", "SOIL", "EARTH"), ["EXCAVATION"]),
    (("TANK",), ["CONFINED_SPACE", "PRESSURE_VESSEL"]),
    (("PUMP",), ["CONSTRUCTION_EQUIP", "PRESSURE_VESSEL", "MACHINE"]),
    (("FORMWORK", "ROOF", "HEIGHT", "DECKING", "SCAFFOLD"), ["SCAFFOLD"]),
    (("CHEMICAL", "SOLVENT", "DISINFECTANT", "DYEING", "PLATE"), ["CHEMICAL_WORK"]),
    (("DEEP_FRYER", "STEAM", "DISHWASHING", "KETTLE"), ["KITCHEN_COOKING"]),
    (("COLD",), ["COLD_STORAGE"]),
    (("WAFER", "CLEANROOM"), ["CHEMICAL_WORK", "ELECTRICAL_WORK"]),
    (("TRUCK", "VEHICLE", "ENGINE"), ["VEHICLE"]),
    (("MEDICAL", "NEEDLE", "PATIENT"), ["BIOLOGICAL", "GENERAL_WORKPLACE"]),
)


class DatabaseUnavailableError(RuntimeError):
    pass


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _feature_hash(features: dict[str, str]) -> str:
    raw = json.dumps(features, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]


def _load_gap_rows(path: Path, classes: set[str]) -> list[dict[str, Any]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    return [
        row
        for row in (report.get("records") or [])
        if row.get("remediation_class") in classes
    ]


def _load_synthetic_by_case(pattern: Path) -> dict[str, dict[str, Any]]:
    rows = load_synthetic_rows(pattern)
    return {str(row.get("case_id")): row for row in rows if row.get("case_id")}


def _canonical_features(db: Any, row: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, list[str]], list[dict[str, str]]]:
    normalized, notes = normalize_features(row.get("expected_features") or {})
    apply_case_work_context_hint(normalized, row.get("work_context"))
    infer_features_from_row(row, normalized, notes)
    canonical = hazard_rule_engine.apply_rules(
        {
            "accident_types": normalized["accident_types"],
            "hazardous_agents": normalized["hazardous_agents"],
            "work_contexts": normalized["work_contexts"],
            "unknown_codes": [note["from"] for note in notes if note.get("error")],
            "forced_fit_notes": [],
        },
        db,
        allow_context_only_inference=False,
    )
    return normalized, canonical, notes


def _family_contexts_for(work_contexts: list[str]) -> list[str]:
    out: list[str] = []
    for context in work_contexts:
        out.extend(CONTEXT_FAMILY_HINTS.get(context, []))
        out.extend(ADDITIONAL_CONTEXT_FAMILY_HINTS.get(context, []))
        for needles, hints in CONTEXT_KEYWORD_FAMILY_HINTS:
            if any(needle in context for needle in needles):
                out.extend(hints)
    return _unique([context for context in out if context not in work_contexts])


def _query_sr_candidates(
    db: Any,
    *,
    accident_types: list[str],
    hazardous_agents: list[str],
    work_contexts: list[str],
    industry_context: str | None,
    sr_limit: int,
) -> tuple[list[dict[str, Any]], str]:
    industry_contexts = [industry_context] if industry_context else []
    sr_rows = hazard_rule_engine.query_sr_for_facets(
        db,
        accident_types,
        hazardous_agents,
        work_contexts,
        limit=sr_limit,
        industry_contexts=industry_contexts,
    )
    strong = [row for row in sr_rows if row.get("matched_axes", 0) >= 2]
    if strong:
        return strong[:5], "direct_multi_axis"

    fallback_contexts = _family_contexts_for(work_contexts)
    if not fallback_contexts:
        if sr_rows:
            return sr_rows[:3], "direct_single_axis"
        return [], "none"

    fallback_rows = hazard_rule_engine.query_sr_for_facets(
        db,
        accident_types,
        hazardous_agents,
        fallback_contexts,
        limit=sr_limit,
        industry_contexts=industry_contexts,
    )
    strong_fallback = [row for row in fallback_rows if row.get("matched_axes", 0) >= 2]
    if strong_fallback:
        return strong_fallback[:5], "family_context_multi_axis"
    if sr_rows:
        return sr_rows[:3], "direct_single_axis"
    if fallback_rows:
        return fallback_rows[:3], "family_context_single_axis"
    return [], "none"


def _visual_triggers(row: dict[str, Any]) -> list[str]:
    triggers = _unique([str(value) for value in (row.get("visual_cues") or [])])
    for key in ("photo_description", "expected_primary_risk", "expected_corrective_direction"):
        value = str(row.get(key) or "").strip()
        if value:
            triggers.append(value)
    return _unique(triggers)[:8]


def _source_sr_evidence_strength(method: str) -> str:
    if method.endswith("multi_axis"):
        return "medium"
    if method.endswith("single_axis"):
        return "weak"
    return "missing"


def _promotion_blockers(
    *,
    source_sr_ids: list[str],
    sr_method: str,
    feature_specificity: float,
) -> list[str]:
    blockers: list[str] = []
    if not source_sr_ids:
        blockers.append("missing_source_sr")
    if sr_method.endswith("single_axis"):
        blockers.append("single_axis_sr_evidence")
    if feature_specificity < 0.5:
        blockers.append("low_feature_specificity")
    return blockers


def _make_candidate(
    db: Any,
    gap_row: dict[str, Any],
    synthetic_row: dict[str, Any],
    *,
    source_report: Path,
    sr_limit: int,
) -> dict[str, Any]:
    normalized, canonical, notes = _canonical_features(db, synthetic_row)
    runtime_match_features = build_features(normalized, canonical)
    features = dict(runtime_match_features)
    observed_work_context = str(gap_row.get("work_context") or synthetic_row.get("work_context") or "").strip()
    if observed_work_context and observed_work_context != "None":
        # Preserve the actual missing context found by the Stage 3 diagnostic.
        # Otherwise the candidate collapses back to broad contexts such as
        # MACHINE/CRANE and no longer represents the ontology gap.
        features["work_context"] = observed_work_context
    family_contexts = _family_contexts_for([features["work_context"]])
    feature_specificity = broadness(features)
    sr_rows, sr_method = _query_sr_candidates(
        db,
        accident_types=canonical.get("accident_types") or [],
        hazardous_agents=canonical.get("hazardous_agents") or [],
        work_contexts=[features["work_context"]],
        industry_context=synthetic_row.get("industry_context"),
        sr_limit=sr_limit,
    )
    source_sr_ids = _unique([row.get("identifier") for row in sr_rows])
    blockers = _promotion_blockers(
        source_sr_ids=source_sr_ids,
        sr_method=sr_method,
        feature_specificity=feature_specificity,
    )
    if not blockers:
        review_priority = "high"
    elif blockers == ["single_axis_sr_evidence"]:
        review_priority = "medium"
    else:
        review_priority = "blocked"
    evidence_cases = [
        {
            "case_id": synthetic_row.get("case_id"),
            "version": gap_row.get("version"),
            "case_type": synthetic_row.get("case_type"),
            "industry_context": synthetic_row.get("industry_context"),
            "work_context": synthetic_row.get("work_context"),
            "photo_description": synthetic_row.get("photo_description") or synthetic_row.get("scene_description"),
            "expected_primary_risk": synthetic_row.get("expected_primary_risk"),
        }
    ]
    source_model = "synthetic/stage3-gap-preview"
    she_id = build_she_id(features)
    if not source_sr_ids:
        she_id = f"{she_id}-NOSR"[:60]

    return {
        "she_id": she_id,
        "name": f"{features.get('work_context', 'OTHER')} {features.get('accident_type', 'OTHER')} pattern"[:120],
        "name_pattern": f"stage3_gap_{str(synthetic_row.get('case_id', '')).lower()}",
        "features": features,
        "runtime_match_features": runtime_match_features,
        "industry_hints": industry_hints_for_features(features),
        "visual_triggers": _visual_triggers(synthetic_row),
        "rationale": (
            f"Review candidate from Stage 3 gap {synthetic_row.get('case_id')}; "
            "current catalog has no exact SHE pattern for the observed context."
        ),
        "source_sr_ids": source_sr_ids,
        "source_sr_candidates": sr_rows,
        "source_sr_selection_method": sr_method,
        "source_sr_evidence_strength": _source_sr_evidence_strength(sr_method),
        "promotion_blockers": blockers,
        "review_priority": review_priority,
        "source_model": source_model,
        "source_prompt_hash": hashlib.md5(source_model.encode("utf-8")).hexdigest(),
        "broadness_score": feature_specificity,
        "status": "draft",
        "review_status": "needs_review",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notes": {
            "source_report": str(source_report),
            "remediation_class": gap_row.get("remediation_class"),
            "observed_work_context": observed_work_context,
            "source_sr_family_contexts": family_contexts,
            "runtime_expansion_risk": gap_row.get("runtime_expansion_risk"),
            "normalization_notes": notes,
            "canonical": canonical,
            "evidence_cases": evidence_cases,
            "candidate_policy": "preview_only_no_asserted_mapping",
        },
    }


def _merge_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        key = _feature_hash(candidate["features"])
        if key not in merged:
            merged[key] = candidate
            continue
        current = merged[key]
        current["source_sr_ids"] = _unique(current.get("source_sr_ids", []) + candidate.get("source_sr_ids", []))[:8]
        current["source_sr_candidates"] = (current.get("source_sr_candidates", []) + candidate.get("source_sr_candidates", []))[:12]
        current["visual_triggers"] = _unique(current.get("visual_triggers", []) + candidate.get("visual_triggers", []))[:12]
        current["notes"]["evidence_cases"].extend(candidate["notes"].get("evidence_cases") or [])
        current["notes"]["evidence_cases"] = current["notes"]["evidence_cases"][:12]
        methods = _unique([
            current.get("source_sr_selection_method"),
            candidate.get("source_sr_selection_method"),
        ])
        current["source_sr_selection_method"] = "+".join(methods)
        current["source_sr_evidence_strength"] = (
            "medium"
            if any(str(method).endswith("multi_axis") for method in methods)
            else _source_sr_evidence_strength(current["source_sr_selection_method"])
        )
        current["promotion_blockers"] = _unique(
            current.get("promotion_blockers", []) + candidate.get("promotion_blockers", [])
        )
        if not current["promotion_blockers"]:
            current["review_priority"] = "high"
        elif current["promotion_blockers"] == ["single_axis_sr_evidence"]:
            current["review_priority"] = "medium"
        else:
            current["review_priority"] = "blocked"
        if "Also supported by" not in current["rationale"]:
            current["rationale"] += " Also supported by additional synthetic Stage 3 gap cases."
    return sorted(
        merged.values(),
        key=lambda row: (
            0 if row.get("source_sr_ids") else 1,
            row["features"].get("work_context", ""),
            row["features"].get("accident_type", ""),
            row["she_id"],
        ),
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _summary(candidates: list[dict[str, Any]], source_rows: int, missing_source_rows: int) -> dict[str, Any]:
    with_sr = [row for row in candidates if row.get("source_sr_ids")]
    no_sr = [row for row in candidates if not row.get("source_sr_ids")]
    no_blockers = [row for row in candidates if not row.get("promotion_blockers")]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_gap_rows": source_rows,
        "missing_synthetic_rows": missing_source_rows,
        "candidate_count": len(candidates),
        "candidate_with_source_sr": len(with_sr),
        "candidate_without_source_sr": len(no_sr),
        "candidate_without_promotion_blockers": len(no_blockers),
        "status_counts": dict(Counter(row.get("status") for row in candidates)),
        "review_status_counts": dict(Counter(row.get("review_status") for row in candidates)),
        "review_priority_counts": dict(Counter(row.get("review_priority") for row in candidates)),
        "source_sr_evidence_strength_counts": dict(Counter(row.get("source_sr_evidence_strength") for row in candidates)),
        "promotion_blocker_counts": dict(Counter(blocker for row in candidates for blocker in row.get("promotion_blockers", []))),
        "source_sr_selection_method_counts": dict(Counter(row.get("source_sr_selection_method") for row in candidates)),
        "top_work_contexts": [
            {"key": key, "count": count}
            for key, count in Counter(row["features"].get("work_context") for row in candidates).most_common(30)
        ],
        "top_no_sr_work_contexts": [
            {"key": key, "count": count}
            for key, count in Counter(row["features"].get("work_context") for row in no_sr).most_common(30)
        ],
        "notes": [
            "Candidates are review-only drafts and are not loaded by the runtime matcher.",
            "source_sr_ids are candidate evidence for reviewer triage, not asserted legal mappings.",
            "Rows without source_sr_ids need SR taxonomy/mapping review before they can be promoted.",
        ],
    }


def _write_markdown(path: Path, summary: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
    lines = [
        "# Stage 3 SHE New Pattern Candidate Preview",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- source_gap_rows: `{summary['source_gap_rows']}`",
        f"- candidate_count: `{summary['candidate_count']}`",
        f"- candidate_with_source_sr: `{summary['candidate_with_source_sr']}`",
        f"- candidate_without_source_sr: `{summary['candidate_without_source_sr']}`",
        f"- candidate_without_promotion_blockers: `{summary['candidate_without_promotion_blockers']}`",
        "",
        "## Review Priority",
        "",
        "```json",
        json.dumps({
            "review_priority": summary["review_priority_counts"],
            "source_sr_evidence_strength": summary["source_sr_evidence_strength_counts"],
            "promotion_blockers": summary["promotion_blocker_counts"],
        }, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Source SR Selection",
        "",
        "```json",
        json.dumps(summary["source_sr_selection_method_counts"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Top Work Contexts",
        "",
        "| context | count |",
        "|---|---:|",
    ]
    for item in summary["top_work_contexts"][:25]:
        lines.append(f"| `{item['key']}` | {item['count']} |")

    lines.extend([
        "",
        "## No-SR Work Contexts",
        "",
        "| context | count |",
        "|---|---:|",
    ])
    for item in summary["top_no_sr_work_contexts"][:25]:
        lines.append(f"| `{item['key']}` | {item['count']} |")

    lines.extend([
        "",
        "## Candidate Samples",
        "",
    ])
    for row in candidates[:60]:
        evidence = row["notes"]["evidence_cases"][0]
        lines.append(
            f"- `{row['she_id']}` context=`{row['features'].get('work_context')}` "
            f"accident=`{row['features'].get('accident_type')}` agent=`{row['features'].get('hazardous_agent')}` "
            f"sr={row.get('source_sr_ids') or []} method=`{row.get('source_sr_selection_method')}` "
            f"priority=`{row.get('review_priority')}` blockers={row.get('promotion_blockers') or []} "
            f"case=`{evidence.get('case_id')}`"
        )

    lines.extend(["", "## Notes", ""])
    for note in summary["notes"]:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path: Path, candidates: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "she_id",
                "status",
                "review_status",
                "work_context",
                "accident_type",
                "hazardous_agent",
                "broadness_score",
                "source_sr_ids",
                "source_sr_selection_method",
                "source_sr_evidence_strength",
                "promotion_blockers",
                "review_priority",
                "evidence_case_count",
                "first_case_id",
                "first_industry_context",
                "first_description",
            ],
        )
        writer.writeheader()
        for row in candidates:
            first_case = (row["notes"].get("evidence_cases") or [{}])[0]
            writer.writerow({
                "she_id": row["she_id"],
                "status": row["status"],
                "review_status": row["review_status"],
                "work_context": row["features"].get("work_context"),
                "accident_type": row["features"].get("accident_type"),
                "hazardous_agent": row["features"].get("hazardous_agent"),
                "broadness_score": row["broadness_score"],
                "source_sr_ids": ",".join(row.get("source_sr_ids") or []),
                "source_sr_selection_method": row.get("source_sr_selection_method"),
                "source_sr_evidence_strength": row.get("source_sr_evidence_strength"),
                "promotion_blockers": ",".join(row.get("promotion_blockers") or []),
                "review_priority": row.get("review_priority"),
                "evidence_case_count": len(row["notes"].get("evidence_cases") or []),
                "first_case_id": first_case.get("case_id"),
                "first_industry_context": first_case.get("industry_context"),
                "first_description": first_case.get("photo_description"),
            })


def run(args: argparse.Namespace) -> dict[str, Path]:
    classes = {item.strip() for item in args.classes.split(",") if item.strip()}
    gap_rows = _load_gap_rows(args.gap_report, classes)
    synthetic_by_case = _load_synthetic_by_case(args.synthetic_glob)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)

    candidates: list[dict[str, Any]] = []
    missing_source_rows = 0
    db = SessionLocal()
    try:
        try:
            db.execute(text("SELECT 1"))
        except OperationalError as exc:
            raise DatabaseUnavailableError(
                "PostgreSQL is not reachable. Start the OHS database before building SHE candidates."
            ) from exc

        for gap_row in gap_rows:
            case_id = str(gap_row.get("case_id") or "")
            synthetic_row = synthetic_by_case.get(case_id)
            if not synthetic_row:
                missing_source_rows += 1
                continue
            candidates.append(
                _make_candidate(
                    db,
                    gap_row,
                    synthetic_row,
                    source_report=args.gap_report,
                    sr_limit=args.sr_limit,
                )
            )
    finally:
        db.close()

    candidates = _merge_candidates(candidates)
    _write_jsonl(args.output, candidates)

    summary = _summary(candidates, len(gap_rows), missing_source_rows)
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gap_report": str(args.gap_report),
        "synthetic_glob": str(args.synthetic_glob),
        "candidate_output": str(args.output),
        "classes": sorted(classes),
        "summary": summary,
        "candidates": candidates,
    }

    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(md_path, summary, candidates)
    _write_csv(csv_path, candidates)
    return {"candidate_jsonl": args.output, "json": json_path, "md": md_path, "csv": csv_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gap-report", type=Path, default=DEFAULT_GAP_REPORT)
    parser.add_argument("--synthetic-glob", type=Path, default=DEFAULT_SYNTHETIC_GLOB)
    parser.add_argument("--output", type=Path, default=DEFAULT_CANDIDATE_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    parser.add_argument("--classes", default=",".join(DEFAULT_CLASSES))
    parser.add_argument("--sr-limit", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        paths = run(args)
    except DatabaseUnavailableError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(2) from None

    report = json.loads(paths["json"].read_text(encoding="utf-8"))
    summary = report["summary"]
    print("=== Stage 3 SHE Candidate Preview ===")
    print(f"source_gap_rows: {summary['source_gap_rows']}")
    print(f"candidate_count: {summary['candidate_count']}")
    print(f"candidate_with_source_sr: {summary['candidate_with_source_sr']}")
    print(f"candidate_without_source_sr: {summary['candidate_without_source_sr']}")
    print(f"candidate_without_promotion_blockers: {summary['candidate_without_promotion_blockers']}")
    print(f"review_priority: {summary['review_priority_counts']}")
    print(f"source_sr_selection: {summary['source_sr_selection_method_counts']}")
    print(f"wrote: {paths['candidate_jsonl']}")
    print(f"wrote: {paths['json']}")
    print(f"wrote: {paths['md']}")
    print(f"wrote: {paths['csv']}")


if __name__ == "__main__":
    main()
