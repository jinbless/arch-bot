#!/usr/bin/env python3
"""Triage Stage 2~5 CI guide-boundary mismatch cases.

This script is diagnostic only. It does not change serving behavior, asserted
SR mappings, SHE approval, status, penalty, or Guide usage profiles.
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

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgChecklistItem  # noqa: E402


DEFAULT_PIPELINE_REPORT = (
    PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "pipeline_quality_v1_v10_ci_candidate_promotion_v1.json"
)
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_PREFIX = "ci_boundary_mismatch_triage_ci_candidate_promotion_v1"


CASE_REVIEW: dict[str, dict[str, str]] = {
    "SYN-0042": {
        "triage_group": "preferred_guide_ci_rank_gap",
        "repair_hint": "Prefer or boost same-top-Guide CI-EG19 respiratory/engineering-control items over unrelated G-93 elderly-work CI.",
        "example_reason": "Top Guide E-G-19 is aligned with dust/respirator context, but top CI came from G-93.",
    },
    "SYN-V10-0003": {
        "triage_group": "guide_or_source_gap",
        "repair_hint": "Review whether conveyor Guide B-M-33 should survive for care-facility transfer assistance; likely Guide profile/source gap.",
        "example_reason": "Material-handling parent context drifted into conveyor guidance for a care-assistance scene.",
    },
    "SYN-V10-0146": {
        "triage_group": "preferred_guide_ci_rank_gap",
        "repair_hint": "Prefer same Guide A-G-20 grating/opening protection CIs when the top Guide is retained, or suppress immediate action if safe cues dominate.",
        "example_reason": "Top Guide has source CI IDs, but the selected CI came from G-36 traffic/pedestrian control.",
    },
    "SYN-V10-0204": {
        "triage_group": "ambiguous_or_source_gap",
        "repair_hint": "Add/verify lab gas-cylinder handling CI support before promoting an immediate action; ambiguous cylinder state should not borrow G-93.",
        "example_reason": "P-76 lab Guide is plausible, but no same-guide CI was attached to the procedure.",
    },
    "SYN-V2-0025": {
        "triage_group": "preferred_guide_ci_rank_gap",
        "repair_hint": "Prefer same-top-Guide G-106 dust/silica CI IDs over unrelated C-C-80 process-safety checklist items.",
        "example_reason": "Top Guide has source CI IDs for dust control, but selected CI is a process-safety evaluation item.",
    },
    "SYN-V2-0044": {
        "triage_group": "top_guide_local_ci_gap",
        "repair_hint": "Review G-67 exterior-cleaning/falling-object CI support for lower-area control and tool fall prevention.",
        "example_reason": "Rope-access Guide is plausible, but immediate action is generic signal-person training.",
    },
    "SYN-V2-0089": {
        "triage_group": "ambiguous_or_source_gap",
        "repair_hint": "Treat uncertain ladder-angle scenes as clarification/no-immediate unless a ladder-specific Guide/CI is supported.",
        "example_reason": "Ambiguous ladder case drifted to tower-crane access passage and elderly-worker CI.",
    },
    "SYN-V3-0089": {
        "triage_group": "source_or_taxonomy_gap",
        "repair_hint": "Delivery-rider load/ergonomics has no strong photo-actionable Guide path; keep out of generic signal-person CI.",
        "example_reason": "Courier bag weight uncertainty drifted to wood-panel stacking and traffic signaling.",
    },
    "SYN-V4-0015": {
        "triage_group": "ambiguous_or_source_gap",
        "repair_hint": "Use welding-gas hose specific support only when hose damage/leak cue is explicit; otherwise clarification.",
        "example_reason": "Welding blanket Guide is near the work domain, but the top CI is a generic risk-control design option.",
    },
    "SYN-V5-0068": {
        "triage_group": "source_or_taxonomy_gap",
        "repair_hint": "Pet-shop animal bite scenes need source/taxonomy support; zoo Guide analogy should not borrow G-120 time-management CI.",
        "example_reason": "The Guide is an analogy, not a direct photo-actionable procedure for pet grooming.",
    },
    "SYN-V5-0142": {
        "triage_group": "preferred_guide_ci_rank_gap",
        "repair_hint": "Prefer same-top-Guide C-52 night-work lighting/access-control CIs over generic high-place housekeeping.",
        "example_reason": "Night-work Guide has source CI IDs, but G-93 elderly-worker CI won.",
    },
    "SYN-V5-0201": {
        "triage_group": "top_guide_local_ci_gap",
        "repair_hint": "Review gasoline vapor/fueling-station exposure CI support; H-115 hydrogen-cyanide tank purge must not be borrowed.",
        "example_reason": "Gas-station Guide is plausible, but selected CI is a chemical-specific confined/tank purge item.",
    },
    "SYN-V6-0011": {
        "triage_group": "source_or_taxonomy_gap",
        "repair_hint": "Bread-slicer cleaning needs machine child-context support; demolition Guide C-47 should not drive bakery slicer actions.",
        "example_reason": "Machine parent context collapsed into demolition guidance.",
    },
    "SYN-V6-0254": {
        "triage_group": "source_or_taxonomy_gap",
        "repair_hint": "Dental sharps disposal needs medical sharps/source support; keep generic/demolition actions out.",
        "example_reason": "Sharps-handling ambiguity has no strong current Guide/CI path.",
    },
    "SYN-V7-0007": {
        "triage_group": "top_guide_local_ci_gap",
        "repair_hint": "Review B-M-36 press mold replacement/safety-block/slide-pin CIs and prevent G-120 time-management fallback.",
        "example_reason": "Top Guide is correct for press work, but selected CI is unrelated management guidance.",
    },
    "SYN-V7-0168": {
        "triage_group": "guide_or_source_gap",
        "repair_hint": "Confined-space manhole work should not route through transmission-tower foundation Guide unless explicit excavation/foundation cues exist.",
        "example_reason": "Selected CI is partly confined-space relevant, but source Guide boundary is wrong.",
    },
    "SYN-V7-0283": {
        "triage_group": "top_guide_local_ci_gap",
        "repair_hint": "Review D-C-7 scaffold/tool-fall/lower-area CIs and prevent C-C-80 process-safety fallback.",
        "example_reason": "Top scaffold Guide is plausible, but process-safety checklist item won.",
    },
    "SYN-V8-0208": {
        "triage_group": "preferred_guide_ci_rank_gap",
        "repair_hint": "Prefer same-top-Guide A-G-9 warehouse/step-platform/stocking CIs over G-93 generic work simplification.",
        "example_reason": "Top Guide has many source CI IDs, but unrelated elderly-worker CI won.",
    },
    "SYN-V9-0183": {
        "triage_group": "top_guide_local_ci_gap",
        "repair_hint": "Review A-G-18 port crane wire-replacement CI support for two-person/wind/falling-object controls.",
        "example_reason": "Port Guide is correct, but top CI is generic signal-person training.",
    },
    "SYN-V9-0297": {
        "triage_group": "top_guide_local_ci_gap",
        "repair_hint": "Review G-11 slip-prevention cleanup/signage CIs and prevent G-87 ladder/elderly-worker fallback.",
        "example_reason": "Slip-prevention Guide is correct, but selected CI is unrelated ladder/stair two-person work.",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _infer_baseline(path: Path) -> str:
    name = path.stem
    prefix = "pipeline_quality_v1_v10_"
    return name[len(prefix):] if name.startswith(prefix) else name


def _ci_texts(db: Any, ci_ids: list[str], limit: int = 8) -> list[dict[str, str]]:
    if not ci_ids:
        return []
    rows = (
        db.query(PgChecklistItem)
        .filter(PgChecklistItem.identifier.in_(ci_ids[:limit]))
        .order_by(PgChecklistItem.identifier)
        .all()
    )
    return [
        {
            "ci_id": row.identifier,
            "source_guide": row.source_guide,
            "source_section": row.source_section,
            "text": row.text,
        }
        for row in rows
    ]


def _guide_ci_count(db: Any, guide_code: str | None) -> int:
    if not guide_code:
        return 0
    return db.query(PgChecklistItem).filter(PgChecklistItem.source_guide == guide_code).count()


def build_rows(pipeline_report: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pipeline = _load_json(pipeline_report)
    records = pipeline.get("records") or []
    rows: list[dict[str, Any]] = []

    with SessionLocal() as db:
        for record in records:
            ci = record["stage5_guide_ci"]["ci"]
            if "ci_guide_boundary_mismatch" not in ci.get("queues", []):
                continue
            top_procedure = record["stage5_guide_ci"].get("top_procedure") or {}
            top_action = ci.get("top_action") or {}
            top_meta = ci.get("top_action_ci_metadata") or {}
            source_ci_ids = list(top_procedure.get("source_ci_ids") or [])
            review = CASE_REVIEW.get(str(record.get("case_id"))) or {
                "triage_group": "unreviewed",
                "repair_hint": "Manual review required.",
                "example_reason": "No case-specific review note yet.",
            }
            candidate_ci = _ci_texts(db, source_ci_ids)
            rows.append(
                {
                    "case_id": record.get("case_id"),
                    "version": record.get("version"),
                    "line_no": record.get("line_no"),
                    "case_type": record.get("case_type"),
                    "industry_context": record.get("industry_context"),
                    "work_context": record.get("work_context"),
                    "triage_group": review["triage_group"],
                    "repair_hint": review["repair_hint"],
                    "example_reason": review["example_reason"],
                    "top_guide": top_procedure.get("guide_code"),
                    "top_guide_title": top_procedure.get("title"),
                    "top_guide_category": record["stage5_guide_ci"].get("guide_category"),
                    "top_guide_reason": record["stage5_guide_ci"].get("guide_reason"),
                    "top_guide_source_ci_count": len(source_ci_ids),
                    "top_guide_total_ci_count": _guide_ci_count(db, top_procedure.get("guide_code")),
                    "top_guide_source_ci_ids": source_ci_ids,
                    "top_guide_source_ci_examples": candidate_ci[:5],
                    "top_action_id": top_action.get("action_id"),
                    "top_action_title": top_action.get("title"),
                    "top_action_source_guide": top_meta.get("source_guide"),
                    "top_action_source_guide_category": ci.get("top_action_source_guide_category"),
                    "top_action_same_as_top_procedure": ci.get("top_action_same_as_top_procedure"),
                    "top_action_evidence": top_action.get("description"),
                    "stage2_queues": record["stage2_risk_feature"].get("queues") or [],
                    "stage3_queues": record["stage3_she"].get("queues") or [],
                    "stage4_queues": record["stage4_sr"].get("queues") or [],
                    "stage5_queues": record["stage5_guide_ci"].get("queues") or [],
                    "ci_queues": ci.get("queues") or [],
                    "photo_description": record.get("photo_description"),
                    "expected_primary_risk": record.get("expected_primary_risk"),
                    "expected_corrective_direction": record.get("expected_corrective_direction"),
                }
            )

    summary = summarize_rows(rows, pipeline, pipeline_report)
    return summary, rows


def _top(counter: Counter, limit: int = 20) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in counter.most_common(limit)]


def summarize_rows(rows: list[dict[str, Any]], pipeline: dict[str, Any], pipeline_report: Path) -> dict[str, Any]:
    triage_counts = Counter(row["triage_group"] for row in rows)
    with_source_ci = [row for row in rows if row["top_guide_source_ci_count"] > 0]
    source_ci_absent = [row for row in rows if row["top_guide_source_ci_count"] == 0]
    return {
        "generated_at": _now(),
        "baseline": _infer_baseline(pipeline_report),
        "source_pipeline_report": _display_path(pipeline_report),
        "source_pipeline_created_at_utc": pipeline.get("created_at_utc"),
        "total_ci_guide_boundary_mismatch": len(rows),
        "triage_group_counts": dict(triage_counts.most_common()),
        "with_top_guide_source_ci_ids": len(with_source_ci),
        "without_top_guide_source_ci_ids": len(source_ci_absent),
        "top_action_source_guide_category_counts": dict(
            Counter(row["top_action_source_guide_category"] for row in rows).most_common()
        ),
        "top_action_source_guides": _top(Counter(row["top_action_source_guide"] for row in rows), limit=12),
        "top_guides": _top(Counter(row["top_guide"] for row in rows), limit=20),
        "next_action": (
            "Do not bulk-promote generic CI aliases. First fix the narrow rank gap where top procedures already expose "
            "source_ci_ids, then review top-guide-local CI support for B-M-36, D-C-7, G-11, A-G-18, G-67, E-13/P-76."
        ),
    }


def write_reports(summary: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path, prefix: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{prefix}.json"
    md_path = output_dir / f"{prefix}.md"
    csv_path = output_dir / f"{prefix}.csv"

    payload = {"summary": summary, "rows": rows}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        f"# CI Guide Boundary Mismatch Triage: {summary['baseline']}",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- source_pipeline_report: `{summary['source_pipeline_report']}`",
        f"- total_ci_guide_boundary_mismatch: `{summary['total_ci_guide_boundary_mismatch']}`",
        f"- with top Guide source_ci_ids: `{summary['with_top_guide_source_ci_ids']}`",
        f"- without top Guide source_ci_ids: `{summary['without_top_guide_source_ci_ids']}`",
        "",
        "## Triage Groups",
        "",
    ]
    for key, count in summary["triage_group_counts"].items():
        md_lines.append(f"- `{key}`: `{count}`")
    md_lines.extend(["", "## Top Action Source Guide Categories", ""])
    for key, count in summary["top_action_source_guide_category_counts"].items():
        md_lines.append(f"- `{key}`: `{count}`")
    md_lines.extend(["", "## Cases", ""])
    for row in rows:
        md_lines.extend(
            [
                f"### {row['case_id']} - {row['triage_group']}",
                "",
                f"- scene: `{row['industry_context']}` / `{row['work_context']}` / `{row['case_type']}`",
                f"- top Guide: `{row['top_guide']}`",
                f"- top action: `{row['top_action_id']}` from `{row['top_action_source_guide']}`",
                f"- top Guide source_ci_ids: `{row['top_guide_source_ci_count']}`",
                f"- reason: {row['example_reason']}",
                f"- repair hint: {row['repair_hint']}",
                "",
            ]
        )
    md_lines.extend(
        [
            "## Interpretation",
            "",
            summary["next_action"],
            "",
            "This report is diagnostic only. It does not update runtime behavior, SHE approval, status, penalty, asserted legal mapping, or Guide profiles.",
        ]
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    fieldnames = [
        "case_id",
        "version",
        "case_type",
        "industry_context",
        "work_context",
        "triage_group",
        "top_guide",
        "top_guide_category",
        "top_guide_source_ci_count",
        "top_guide_total_ci_count",
        "top_action_id",
        "top_action_source_guide",
        "top_action_source_guide_category",
        "repair_hint",
        "example_reason",
        "photo_description",
        "expected_corrective_direction",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    checksums = {path.name: _sha256(path) for path in [json_path, md_path, csv_path]}
    return {
        "json": str(json_path),
        "md": str(md_path),
        "csv": str(csv_path),
        "checksums": json.dumps(checksums, ensure_ascii=False, sort_keys=True),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pipeline-report", type=Path, default=DEFAULT_PIPELINE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_PREFIX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary, rows = build_rows(args.pipeline_report)
    paths = write_reports(summary, rows, args.output_dir, args.report_prefix)
    print(json.dumps({"summary": summary, "paths": paths}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
