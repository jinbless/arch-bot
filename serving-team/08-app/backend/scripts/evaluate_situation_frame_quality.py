#!/usr/bin/env python3
"""Evaluate SituationFrame extraction on synthetic_observations_v1..v10."""
from __future__ import annotations

import argparse
import csv
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
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.database import SessionLocal  # noqa: E402
from app.services import risk_rule_service, situation_frame_service  # noqa: E402
from app.services.hazard_normalizer import normalize_risk_feature_candidates  # noqa: E402
from app.services.industry_context import infer_industry_context  # noqa: E402
from evaluate_synthetic_guide_recommendations import load_synthetic_rows, synthetic_to_llm_result  # noqa: E402


DEFAULT_INPUT_GLOB = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "synthetic_observations_v*.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_PREFIX = "situation_frame_eval_report.v1"
DEFAULT_BASELINE = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "pipeline_quality_v1_v10_ci_reference_guard1.json"
BROAD_PARENT_CONTEXTS = {"MACHINE", "OTHER", "MATERIAL_HANDLING", "CONSTRUCTION_EQUIP", "EXCAVATION"}


class DatabaseUnavailableError(RuntimeError):
    pass


def _row_text(row: dict[str, Any]) -> str:
    values = [
        row.get("industry_context") or "",
        row.get("work_context") or "",
        row.get("photo_description") or row.get("scene_description") or "",
        row.get("expected_primary_risk") or "",
        row.get("expected_corrective_direction") or "",
        row.get("false_positive_risk") or "",
    ]
    values.extend(row.get("visual_cues") or [])
    values.extend(row.get("uncertain_cues") or [])
    return " ".join(value for value in values if value)


def _load_baseline(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    report = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(row.get("case_id")): row
        for row in report.get("records") or []
        if row.get("case_id")
    }


def build_record(db: Any, row: dict[str, Any], baseline_records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    llm_result = synthetic_to_llm_result(row)
    context_text = _row_text(row)
    visual_cues = [
        cue.get("text")
        for cue in llm_result.get("visual_cues") or []
        if cue.get("text")
    ] or [context_text]
    normalized = normalize_risk_feature_candidates(
        llm_result.get("risk_feature_candidates") or [],
        context_text=context_text,
    )
    canonical = risk_rule_service.apply_risk_rules(normalized, db, allow_context_only_inference=False)
    industry = infer_industry_context(
        work_contexts=canonical.get("work_contexts") or [],
        text=context_text,
        declared=row.get("industry_context"),
    )
    frame = situation_frame_service.build_situation_frame(
        canonical=canonical,
        normalized=normalized,
        visual_cues=visual_cues,
        context_text=context_text,
        industry_contexts=industry.active_industries,
    )
    supports = situation_frame_service.match_guide_support_candidates(
        frame,
        visual_cues=visual_cues,
        context_text=context_text,
        limit=8,
    )
    baseline = baseline_records.get(str(row.get("case_id"))) or {}
    parent_set = set(frame.parent_contexts)
    return {
        "version": row.get("version"),
        "line_no": row.get("line_no"),
        "case_id": row.get("case_id"),
        "case_type": row.get("case_type"),
        "industry_context": row.get("industry_context"),
        "work_context": row.get("work_context"),
        "parent_contexts": frame.parent_contexts,
        "equipment_contexts": frame.equipment_contexts,
        "task_contexts": frame.task_contexts,
        "energy_state": frame.energy_state,
        "control_state": frame.control_state,
        "match_policy": frame.match_policy,
        "support_count": len(supports),
        "top_supports": [
            {
                "support_id": support.get("support_id"),
                "child_context": support.get("child_context"),
                "guide_codes": (support.get("guide_codes") or [])[:5],
                "support_score": support.get("support_score"),
                "reasons": support.get("support_reasons"),
            }
            for support in supports[:3]
        ],
        "collapse_queue": (
            "broad_parent_without_child"
            if parent_set & BROAD_PARENT_CONTEXTS and not frame.equipment_contexts
            else "child_context_available"
            if frame.equipment_contexts
            else "no_broad_parent"
        ),
        "baseline_failure_stages": baseline.get("failure_stages") or [],
        "baseline_primary_failure_stage": baseline.get("primary_failure_stage"),
    }


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_samples": len(records),
        "match_policy_counts": dict(Counter(row["match_policy"] for row in records)),
        "collapse_queue_counts": dict(Counter(row["collapse_queue"] for row in records)),
        "support_count_distribution": dict(Counter(str(row["support_count"]) for row in records)),
        "support_hit_samples": sum(1 for row in records if row["support_count"] > 0),
        "top_parent_contexts": [
            {"key": key, "count": count}
            for key, count in Counter(parent for row in records for parent in row["parent_contexts"]).most_common(30)
        ],
        "top_child_contexts": [
            {"key": key, "count": count}
            for key, count in Counter(child for row in records for child in row["equipment_contexts"]).most_common(30)
        ],
        "baseline_failure_with_support": dict(
            Counter(
                row["baseline_primary_failure_stage"]
                for row in records
                if row["support_count"] > 0 and row.get("baseline_primary_failure_stage")
            )
        ),
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# SituationFrame Evaluation v1",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Total samples: `{summary['total_samples']}`",
        f"- Samples with Guide support candidates: `{summary['support_hit_samples']}`",
        "",
        "## Match Policies",
        "",
    ]
    for key, count in sorted(summary["match_policy_counts"].items()):
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Collapse Queues", ""])
    for key, count in sorted(summary["collapse_queue_counts"].items()):
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Top Child Contexts", ""])
    for row in summary["top_child_contexts"][:20]:
        lines.append(f"- `{row['key']}`: {row['count']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = [
        "version", "line_no", "case_id", "case_type", "industry_context", "work_context",
        "match_policy", "collapse_queue", "support_count", "parent_contexts",
        "equipment_contexts", "task_contexts", "baseline_primary_failure_stage",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow({
                field: json.dumps(row[field], ensure_ascii=False) if isinstance(row.get(field), list) else row.get(field)
                for field in fields
            })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-glob", type=Path, default=DEFAULT_INPUT_GLOB)
    parser.add_argument("--baseline-report", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_synthetic_rows(args.input_glob)
    if args.limit:
        rows = rows[: args.limit]
    baseline = _load_baseline(args.baseline_report)
    db = SessionLocal()
    try:
        try:
            db.execute(text("SELECT 1"))
        except OperationalError as exc:
            raise DatabaseUnavailableError("PostgreSQL is not reachable.") from exc
        records = [build_record(db, row, baseline) for row in rows]
    finally:
        db.close()
    summary = build_summary(records)
    report = {
        "input_pattern": str(args.input_glob),
        "baseline_report": str(args.baseline_report) if args.baseline_report else None,
        "summary": summary,
        "records": records,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.report_prefix}.json"
    md_path = args.output_dir / f"{args.report_prefix}.md"
    csv_path = args.output_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, summary)
    write_csv(csv_path, records)
    print("=== SituationFrame Evaluation ===")
    print(f"total: {summary['total_samples']}")
    print(f"match policies: {summary['match_policy_counts']}")
    print(f"collapse queues: {summary['collapse_queue_counts']}")
    print(f"support hit samples: {summary['support_hit_samples']}")
    print(f"wrote: {json_path}")
    print(f"wrote: {md_path}")
    print(f"wrote: {csv_path}")


if __name__ == "__main__":
    main()
