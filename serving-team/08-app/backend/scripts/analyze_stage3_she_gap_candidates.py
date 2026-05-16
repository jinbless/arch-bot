#!/usr/bin/env python3
"""Analyze Stage 3 SHE gaps from a Stage 2~5 pipeline quality report.

This script is intentionally diagnostic. It does not change runtime matching,
candidate tables, or asserted ontology mappings. Its job is to separate SHE
failures into structural queues:

- upstream Stage 2 feature gaps
- missing SHE patterns for an observed work context
- existing SHE patterns that need visual trigger / confirmation tuning
- negative or ambiguous over-promotion risks
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "pictures-json" / "reports" / "pipeline_quality_v1_v10_ci_reference_guard1.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_PREFIX = "stage3_she_gap_candidates_reference_guard1"
APPROVED_SHE_STATUSES = ("approved_auto", "approved_manual")

VISIBLE_UNSAFE_TERMS = (
    "없음",
    "부재",
    "미설치",
    "미체결",
    "미착용",
    "노출",
    "손상",
    "파손",
    "방치",
    "누출",
    "불꽃",
    "화염",
    "스파크",
    "젖어",
    "미끄러",
    "과적",
    "붕락",
    "가동 중",
    "접근 중",
    "보호구 없이",
    "차단하지 않고",
    "혼합",
    "장갑 없이",
    "마스크 없이",
)

CONFIRMATION_TERMS = (
    "확인 불가",
    "확인불가",
    "불명",
    "불분명",
    "판단 어려",
    "사진만으로",
    "가능성",
    "여부",
    "일 수",
    "수 있다",
    "처럼 보",
)

CONTEXT_FAMILY_HINTS = {
    "LATHE_MILLING": ["MACHINE", "GRINDING"],
    "SOLDERING_ASSEMBLY": ["WELDING", "ELECTRICAL_WORK"],
    "WAFER_HANDLING": ["CHEMICAL_WORK", "ELECTRICAL_WORK"],
    "INJECTION_MOLDING": ["MACHINE", "HEAT_COLD"],
    "MOLDING_TOOL_CHANGE": ["MACHINE"],
    "COMPOUND_MIXING": ["CHEMICAL_WORK"],
    "EXCAVATION_WORK": ["EXCAVATION"],
    "HEAVY_EQUIPMENT_OP": ["CONSTRUCTION_EQUIP", "VEHICLE"],
    "FORMWORK_ERECTION": ["SCAFFOLD", "CONSTRUCTION_EQUIP"],
    "CONCRETE_POURING": ["CONSTRUCTION_EQUIP"],
    "SCAFFOLD_ERECTION": ["SCAFFOLD"],
    "CRANE_OPERATION": ["CRANE"],
    "ROOFING_WORK": ["SCAFFOLD", "LADDER"],
    "SCAFFOLDING_SHIP": ["SCAFFOLD"],
    "VEHICLE_LIFT_WORK": ["LIFT_WORK", "VEHICLE"],
    "PAINT_BOOTH": ["PAINTING", "CHEMICAL_WORK"],
    "PESTICIDE_APPLICATION": ["PESTICIDE_SPRAY", "CHEMICAL_WORK"],
    "UNDERGROUND_DRILLING": ["EXCAVATION", "CONFINED_SPACE"],
    "SHAFT_HOIST": ["LIFT_WORK", "CONFINED_SPACE"],
    "SHREDDER_OPERATION": ["MACHINE"],
    "COLD_ROOM_WORK": ["COLD_STORAGE"],
    "SCALDING_DEHAIRING": ["HEAT_COLD", "MACHINE"],
    "TRUCK_COUPLING": ["VEHICLE"],
    "SOLVENT_HANDLING": ["CHEMICAL_WORK"],
    "CHEMICAL_SPOTTING": ["CHEMICAL_WORK"],
    "DEEP_FRYER": ["KITCHEN_COOKING", "DEEP_FRYING"],
    "STEAM_KETTLE": ["KITCHEN_COOKING", "HEAT_COLD"],
    "DISHWASHING": ["CLEANING_WET", "KITCHEN_COOKING"],
    "FINISHING_SANDING": ["GRINDING", "DUST"],
    "SEWING_MACHINE": ["MACHINE"],
    "IRONING_STEAM": ["STEAM_IRON", "HEAT_COLD"],
    "PAPER_CUTTING": ["MACHINE", "CUT"],
    "NEEDLESTICK": ["BIOLOGICAL"],
    "MEDICAL_WASTE": ["BIOLOGICAL"],
    "HAZMAT_TRANSPORT": ["CHEMICAL_WORK", "VEHICLE"],
}

SENSITIVE_RUNTIME_EXPANSION_CONTEXTS = {
    "CLEANROOM_OPERATION",
    "DEEP_FRYER",
    "EMBALMING",
    "LATHE_MILLING",
    "PRINTING_PRESS",
    "SOLVENT_HANDLING",
    "UNDERGROUND_DRILLING",
}


class DatabaseUnavailableError(RuntimeError):
    pass


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _contains_any(text_value: str, terms: tuple[str, ...]) -> bool:
    lowered = text_value.lower()
    return any(term.lower() in lowered for term in terms)


def _actual_features(record: dict[str, Any]) -> dict[str, list[str]]:
    return {
        key: _as_list(value)
        for key, value in (record.get("stage2_risk_feature", {}).get("actual_features") or {}).items()
    }


def _stage3_queues(record: dict[str, Any]) -> list[str]:
    return _as_list(record.get("stage3_she", {}).get("queues"))


def _stage2_queues(record: dict[str, Any]) -> list[str]:
    return _as_list(record.get("stage2_risk_feature", {}).get("queues"))


def _query_scalar(db: Any, query: str, params: dict[str, Any]) -> int:
    return int(db.execute(text(query), params).scalar() or 0)


def _she_count_for_context(db: Any, work_context: str | None) -> int:
    if not work_context:
        return 0
    return _query_scalar(
        db,
        """
        SELECT count(*)
        FROM she_catalog
        WHERE status = ANY(:statuses)
          AND superseded_by IS NULL
          AND features->>'work_context' = :work_context
        """,
        {"statuses": list(APPROVED_SHE_STATUSES), "work_context": work_context},
    )


def _she_count_for_context_axis(
    db: Any,
    *,
    work_context: str | None,
    axis: str,
    codes: list[str],
) -> int:
    if not work_context or not codes:
        return 0
    return _query_scalar(
        db,
        f"""
        SELECT count(*)
        FROM she_catalog
        WHERE status = ANY(:statuses)
          AND superseded_by IS NULL
          AND features->>'work_context' = :work_context
          AND features->>:axis = ANY(:codes)
        """,
        {
            "statuses": list(APPROVED_SHE_STATUSES),
            "work_context": work_context,
            "axis": axis,
            "codes": codes,
        },
    )


def _sample_she_for_context(db: Any, work_context: str | None, limit: int = 5) -> list[dict[str, Any]]:
    if not work_context:
        return []
    rows = db.execute(
        text(
            """
            SELECT she_id, name, features, source_sr_ids, visual_triggers, broadness_score
            FROM she_catalog
            WHERE status = ANY(:statuses)
              AND superseded_by IS NULL
              AND features->>'work_context' = :work_context
            ORDER BY broadness_score DESC, she_id
            LIMIT :limit
            """
        ),
        {"statuses": list(APPROVED_SHE_STATUSES), "work_context": work_context, "limit": limit},
    ).mappings()
    return [
        {
            "she_id": row["she_id"],
            "name": row["name"],
            "features": row["features"],
            "source_sr_ids": row["source_sr_ids"] or [],
            "visual_triggers": (row["visual_triggers"] or [])[:5],
            "broadness_score": float(row["broadness_score"] or 0),
        }
        for row in rows
    ]


def _family_she_counts(db: Any, work_context: str | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in CONTEXT_FAMILY_HINTS.get(work_context or "", []):
        counts[candidate] = _she_count_for_context(db, candidate)
    return counts


def classify_record(db: Any, record: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any] | None:
    queues = _stage3_queues(record)
    if not queues:
        return None

    stage2_queues = _stage2_queues(record)
    features = _actual_features(record)
    work_contexts = features.get("work_contexts") or []
    work_context = work_contexts[0] if work_contexts else record.get("work_context")
    accident_types = features.get("accident_types") or []
    hazardous_agents = features.get("hazardous_agents") or []
    text_value = " ".join(
        str(value or "")
        for value in (
            record.get("industry_context"),
            record.get("work_context"),
            record.get("photo_description"),
            record.get("expected_primary_risk"),
            record.get("expected_corrective_direction"),
            record.get("false_positive_risk"),
        )
    )
    has_visible_unsafe_term = _contains_any(text_value, VISIBLE_UNSAFE_TERMS)
    has_confirmation_term = _contains_any(text_value, CONFIRMATION_TERMS)

    if work_context not in cache:
        cache[work_context] = {
            "exact_context_she_count": _she_count_for_context(db, work_context),
            "sample_she": _sample_she_for_context(db, work_context),
            "family_she_counts": _family_she_counts(db, work_context),
        }
    context_info = cache[work_context]
    exact_context_she_count = context_info["exact_context_she_count"]
    exact_context_accident_count = _she_count_for_context_axis(
        db,
        work_context=work_context,
        axis="accident_type",
        codes=accident_types,
    )
    exact_context_agent_count = _she_count_for_context_axis(
        db,
        work_context=work_context,
        axis="hazardous_agent",
        codes=hazardous_agents,
    )

    if "she_missed" in queues:
        if stage2_queues:
            remediation_class = "stage2_feature_gap"
        elif not work_context:
            remediation_class = "missing_work_context"
        elif exact_context_she_count == 0:
            remediation_class = "new_she_pattern_needed"
        elif not accident_types and not hazardous_agents and not has_visible_unsafe_term:
            remediation_class = "work_context_only_signal"
        elif exact_context_accident_count == 0 and exact_context_agent_count == 0:
            remediation_class = "axis_specific_she_gap"
        else:
            remediation_class = "visual_trigger_or_threshold_gap"
    elif "confirmed_downgraded_to_candidate" in queues:
        remediation_class = "confirmation_threshold_gap"
    elif "she_false_positive" in queues or "negative_not_suppressed" in queues:
        remediation_class = "suppression_gap"
    elif "ambiguous_over_promoted" in queues:
        remediation_class = "ambiguity_suppression_gap"
    else:
        remediation_class = "stage3_other_attention"

    if remediation_class == "new_she_pattern_needed":
        suggested_action = "Create candidate SHE pattern for this work_context with evidence; do not use broad parent runtime expansion."
    elif remediation_class == "axis_specific_she_gap":
        suggested_action = "Create or enrich SHE pattern with matching accident/agent axes and source SR evidence."
    elif remediation_class == "visual_trigger_or_threshold_gap":
        suggested_action = "Inspect existing SHE visual_triggers/required cues before changing matcher thresholds."
    elif remediation_class == "confirmation_threshold_gap":
        suggested_action = "Tune visual trigger evidence or confirmation terms; avoid changing actionable recall."
    elif remediation_class.endswith("suppression_gap"):
        suggested_action = "Add negative/ambiguous boundary cues to SHE or matcher suppression rules."
    elif remediation_class == "stage2_feature_gap":
        suggested_action = "Fix Stage 2 feature extraction/normalization first, then re-run Stage 3."
    else:
        suggested_action = "Manual review before runtime change."

    return {
        "version": record.get("version"),
        "case_id": record.get("case_id"),
        "case_type": record.get("case_type"),
        "industry_context": record.get("industry_context"),
        "work_context": work_context,
        "original_work_context": record.get("work_context"),
        "stage2_queues": stage2_queues,
        "stage3_queues": queues,
        "remediation_class": remediation_class,
        "suggested_action": suggested_action,
        "runtime_expansion_risk": "high" if work_context in SENSITIVE_RUNTIME_EXPANSION_CONTEXTS else "normal",
        "accident_types": accident_types,
        "hazardous_agents": hazardous_agents,
        "exact_context_she_count": exact_context_she_count,
        "exact_context_accident_count": exact_context_accident_count,
        "exact_context_agent_count": exact_context_agent_count,
        "family_context_she_counts": context_info["family_she_counts"],
        "sample_existing_she": context_info["sample_she"],
        "has_visible_unsafe_term": has_visible_unsafe_term,
        "has_confirmation_term": has_confirmation_term,
        "top_runtime_she": record.get("stage3_she", {}).get("top_she") or [],
        "photo_description": record.get("photo_description"),
        "expected_primary_risk": record.get("expected_primary_risk"),
    }


def top_items(counter: Counter[Any], limit: int = 25) -> list[dict[str, Any]]:
    return [{"key": str(key), "count": count} for key, count in counter.most_common(limit)]


def build_summary(rows: list[dict[str, Any]], source_report: Path) -> dict[str, Any]:
    by_remediation = Counter(row["remediation_class"] for row in rows)
    by_queue = Counter(queue for row in rows for queue in row["stage3_queues"])
    by_context = Counter(row.get("work_context") or "NONE" for row in rows)
    pure_stage3 = [row for row in rows if not row["stage2_queues"]]
    missing_pattern = [row for row in rows if row["remediation_class"] == "new_she_pattern_needed"]
    existing_pattern_gap = [
        row
        for row in rows
        if row["remediation_class"] in {"visual_trigger_or_threshold_gap", "confirmation_threshold_gap"}
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_report": str(source_report),
        "total_stage3_attention": len(rows),
        "pure_stage3_attention": len(pure_stage3),
        "remediation_class_counts": dict(sorted(by_remediation.items())),
        "stage3_queue_counts": dict(sorted(by_queue.items())),
        "top_contexts": top_items(by_context),
        "top_missing_pattern_contexts": top_items(
            Counter(row.get("work_context") or "NONE" for row in missing_pattern)
        ),
        "top_existing_pattern_gap_contexts": top_items(
            Counter(row.get("work_context") or "NONE" for row in existing_pattern_gap)
        ),
        "high_runtime_expansion_risk_cases": sum(1 for row in rows if row["runtime_expansion_risk"] == "high"),
        "notes": [
            "This report is diagnostic only; it does not update runtime code, DB candidates, or asserted mappings.",
            "Contexts with exact_context_she_count=0 should be treated as ontology/SHE candidate gaps, not automatic parent-context runtime expansions.",
            "Rows with stage2_queues must be fixed upstream before SHE matching quality can be judged.",
        ],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "version",
                "case_id",
                "case_type",
                "industry_context",
                "work_context",
                "stage2_queues",
                "stage3_queues",
                "remediation_class",
                "runtime_expansion_risk",
                "accident_types",
                "hazardous_agents",
                "exact_context_she_count",
                "exact_context_accident_count",
                "exact_context_agent_count",
                "family_context_she_counts",
                "suggested_action",
                "photo_description",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "version": row["version"],
                "case_id": row["case_id"],
                "case_type": row["case_type"],
                "industry_context": row["industry_context"],
                "work_context": row["work_context"],
                "stage2_queues": ",".join(row["stage2_queues"]),
                "stage3_queues": ",".join(row["stage3_queues"]),
                "remediation_class": row["remediation_class"],
                "runtime_expansion_risk": row["runtime_expansion_risk"],
                "accident_types": ",".join(row["accident_types"]),
                "hazardous_agents": ",".join(row["hazardous_agents"]),
                "exact_context_she_count": row["exact_context_she_count"],
                "exact_context_accident_count": row["exact_context_accident_count"],
                "exact_context_agent_count": row["exact_context_agent_count"],
                "family_context_she_counts": json.dumps(row["family_context_she_counts"], ensure_ascii=False, sort_keys=True),
                "suggested_action": row["suggested_action"],
                "photo_description": row["photo_description"],
            })


def write_markdown(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Stage 3 SHE Gap Candidate Report",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- source_report: `{summary['source_report']}`",
        f"- total_stage3_attention: `{summary['total_stage3_attention']}`",
        f"- pure_stage3_attention: `{summary['pure_stage3_attention']}`",
        f"- high_runtime_expansion_risk_cases: `{summary['high_runtime_expansion_risk_cases']}`",
        "",
        "## Remediation Classes",
        "",
        "```json",
        json.dumps(summary["remediation_class_counts"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Stage 3 Queues",
        "",
        "```json",
        json.dumps(summary["stage3_queue_counts"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Top Contexts",
        "",
        "| context | count |",
        "|---|---:|",
    ]
    for item in summary["top_contexts"][:20]:
        lines.append(f"| `{item['key']}` | {item['count']} |")

    lines.extend([
        "",
        "## Missing Pattern Contexts",
        "",
        "| context | count |",
        "|---|---:|",
    ])
    for item in summary["top_missing_pattern_contexts"][:20]:
        lines.append(f"| `{item['key']}` | {item['count']} |")

    lines.extend([
        "",
        "## Existing Pattern / Trigger Gap Contexts",
        "",
        "| context | count |",
        "|---|---:|",
    ])
    for item in summary["top_existing_pattern_gap_contexts"][:20]:
        lines.append(f"| `{item['key']}` | {item['count']} |")

    lines.extend([
        "",
        "## Review Samples",
        "",
    ])
    for row in rows[:60]:
        samples = ", ".join(item["she_id"] for item in row["sample_existing_she"][:3]) or "-"
        lines.append(
            f"- `{row['case_id']}` `{row['remediation_class']}` "
            f"context=`{row['work_context']}` queues={row['stage3_queues']} "
            f"exact_she={row['exact_context_she_count']} exact_acc={row['exact_context_accident_count']} "
            f"exact_agent={row['exact_context_agent_count']} samples={samples}"
        )

    lines.extend([
        "",
        "## Notes",
        "",
    ])
    for note in summary["notes"]:
        lines.append(f"- {note}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Path]:
    report = json.loads(args.input.read_text(encoding="utf-8"))
    records = report.get("records") or []
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    cache: dict[str, Any] = {}
    db = SessionLocal()
    try:
        try:
            db.execute(text("SELECT 1"))
        except OperationalError as exc:
            raise DatabaseUnavailableError(
                "PostgreSQL is not reachable. Start the OHS database before running this report."
            ) from exc

        for record in records:
            row = classify_record(db, record, cache)
            if row:
                rows.append(row)
    finally:
        db.close()

    rows.sort(
        key=lambda row: (
            row["remediation_class"],
            row.get("work_context") or "",
            row.get("version") or "",
            row.get("case_id") or "",
        )
    )
    summary = build_summary(rows, args.input)
    out = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_report": str(args.input),
        "summary": summary,
        "records": rows,
    }

    json_path = args.output_dir / f"{args.report_prefix}.json"
    md_path = args.output_dir / f"{args.report_prefix}.md"
    csv_path = args.output_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, summary, rows)
    write_csv(csv_path, rows)
    return {"json": json_path, "md": md_path, "csv": csv_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_PREFIX)
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
    print("=== Stage 3 SHE Gap Candidates ===")
    print(f"total_stage3_attention: {summary['total_stage3_attention']}")
    print(f"pure_stage3_attention: {summary['pure_stage3_attention']}")
    print(f"remediation: {summary['remediation_class_counts']}")
    print(f"queues: {summary['stage3_queue_counts']}")
    print(f"wrote: {paths['json']}")
    print(f"wrote: {paths['md']}")
    print(f"wrote: {paths['csv']}")


if __name__ == "__main__":
    main()
