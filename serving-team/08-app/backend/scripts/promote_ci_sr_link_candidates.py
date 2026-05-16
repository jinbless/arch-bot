#!/usr/bin/env python3
"""Promote a narrow subset of reviewed CI -> SR candidates.

The imported `ci_candidate_review_v1` rows start as `needs_review`, which keeps
them out of serving.  This script promotes only the hand-reviewed direct
CI/SR pairs to `candidate`; it never writes to `ci_sr_mapping`, never sets
`asserted=true`, and can revert the method back to review-only.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.broad_sr_policy import get_broad_sr_ids  # noqa: E402

DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_PREFIX = "ci_sr_candidate_promotion_ci_cross_guide_broad_only_guard1"
DEFAULT_METHOD = "ci_candidate_review_v1"
BASELINE = "ci_cross_guide_broad_only_guard1"

PROMOTE_PAIRS: dict[tuple[str, str], str] = {
    ("CI-AG11-014", "SR-FIRE_EXPLOSION-009"): "hot-work fire prevention is directly tied to welding blanket CI text",
    ("CI-AG11-014", "SR-FIRE_EXPLOSION-017"): "hot-work fire watcher/equipment is directly tied to welding blanket CI text",
    ("CI-AG11-014", "SR-FIRE_EXPLOSION-021"): "hot-work fire prevention equipment is directly tied to welding blanket CI text",
    ("CI-BM37-140", "SR-CONVEYOR-002"): "conveyor emergency stop and guarding are explicit in CI text",
    ("CI-BM37-140", "SR-MACHINE-002"): "machine guarding is explicit in CI text",
    ("CI-BM37-140", "SR-MACHINE-007"): "machine stop/lockout is explicit in CI text",
    ("CI-BM37-140", "SR-MACHINE-009"): "machine work clothing is close enough for the conveyor entanglement review case",
    ("CI-C113-130", "SR-WORKPLACE-001"): "ice/snow slip prevention is explicit in CI text",
    ("CI-D28-006", "SR-FIRE_EXPLOSION-019"): "fire extinguisher placement/signage is explicit in CI text",
    ("CI-D28-007", "SR-FIRE_EXPLOSION-019"): "initial extinguishing media selection is explicit in CI text",
    ("CI-EG1-038", "SR-ERGONOMIC-003"): "standing-work footrest is direct ergonomic work-environment improvement",
    ("CI-EG1-043", "SR-ERGONOMIC-003"): "sit-stand chair is direct ergonomic work-environment improvement",
    ("CI-EG1-059", "SR-ERGONOMIC-003"): "rest breaks are direct ergonomic work-environment improvement",
    ("CI-G11-002", "SR-WORKPLACE-001"): "slip/trip hazard inspection is direct workplace-floor control",
    ("CI-G11-013", "SR-WORKPLACE-001"): "slippery-floor cause assessment is direct workplace-floor control",
    ("CI-P22-003", "SR-CHEMICAL-002"): "dry-cleaning solvent leak prevention is direct source-control evidence",
    ("CI-P22-027", "SR-CHEMICAL-002"): "dry-cleaning ventilation is direct source-control evidence",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def _rows(db: Any, method: str) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            select entity_type, entity_id, guide_code, sr_id, confidence, evidence,
                   source_fields, method, review_status, non_llm_evidence_count, asserted
            from guide_sr_link_candidates
            where method = :method
            order by guide_code, entity_id, sr_id
            """
        ),
        {"method": method},
    ).mappings().all()
    return [dict(row) for row in rows]


def _decision(row: dict[str, Any], broad_sr_ids: set[str]) -> dict[str, Any]:
    key = (str(row["entity_id"]), str(row["sr_id"]))
    if key in PROMOTE_PAIRS:
        return {
            "decision": "promote_candidate",
            "target_review_status": "candidate",
            "reason": PROMOTE_PAIRS[key],
            "risk_note": "serving candidate only; asserted remains false",
        }
    guide_code = str(row.get("guide_code") or "")
    sr_id = str(row.get("sr_id") or "")
    entity_id = str(row.get("entity_id") or "")
    if guide_code == "A-G-12-2026":
        reason = "PPE Guide rows are broad and need observable-cue or guide-support gating before promotion"
    elif sr_id in broad_sr_ids:
        reason = "broad SR row should remain secondary/review-only unless a narrower non-broad signal is proven"
    elif sr_id in {"SR-ERGONOMIC-008", "SR-WORKPLACE-014"}:
        reason = "SR title is only a near analogy for the reviewed CI text"
    elif entity_id in {"CI-G11-015", "CI-P22-037"}:
        reason = "CI text is useful but too generic or partially mismatched for automatic serving promotion"
    else:
        reason = "not in the narrow first-promotion whitelist"
    return {
        "decision": "keep_needs_review",
        "target_review_status": "needs_review",
        "reason": reason,
        "risk_note": "kept out of serving",
    }


def _build_report_rows(db: Any, method: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    broad_sr_ids = get_broad_sr_ids()
    rows = []
    for row in _rows(db, method):
        decision = _decision(row, broad_sr_ids)
        rows.append(
            {
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "guide_code": row["guide_code"],
                "sr_id": row["sr_id"],
                "confidence": str(row["confidence"]),
                "current_review_status": row["review_status"],
                "target_review_status": decision["target_review_status"],
                "decision": decision["decision"],
                "reason": decision["reason"],
                "risk_note": decision["risk_note"],
                "asserted": bool(row["asserted"]),
                "non_llm_evidence_count": row["non_llm_evidence_count"],
                "evidence": row["evidence"],
                "source_fields": row["source_fields"],
            }
        )
    summary = {
        "generated_at": _now(),
        "baseline": BASELINE,
        "method": method,
        "row_count": len(rows),
        "decision_counts": dict(Counter(row["decision"] for row in rows)),
        "target_review_status_counts": dict(Counter(row["target_review_status"] for row in rows)),
        "promoted_row_count": sum(1 for row in rows if row["target_review_status"] == "candidate"),
        "promoted_distinct_ci_count": len(
            {row["entity_id"] for row in rows if row["target_review_status"] == "candidate"}
        ),
        "promoted_distinct_sr_count": len(
            {row["sr_id"] for row in rows if row["target_review_status"] == "candidate"}
        ),
        "policy": "promote only narrow reviewed rows to serving candidate; asserted=false; no ci_sr_mapping write",
    }
    return summary, rows


def _apply_statuses(db: Any, rows: list[dict[str, Any]], method: str, mode: str) -> dict[str, int]:
    before_candidate = db.execute(
        text(
            """
            select count(*) from guide_sr_link_candidates
            where method = :method and review_status in ('candidate', 'asserted')
            """
        ),
        {"method": method},
    ).scalar_one()
    if mode == "revert":
        db.execute(
            text(
                """
                update guide_sr_link_candidates
                set review_status = 'needs_review', asserted = false
                where method = :method
                """
            ),
            {"method": method},
        )
    elif mode == "apply":
        for row in rows:
            db.execute(
                text(
                    """
                    update guide_sr_link_candidates
                    set review_status = :target_review_status, asserted = false
                    where method = :method
                      and entity_type = :entity_type
                      and entity_id = :entity_id
                      and sr_id = :sr_id
                    """
                ),
                {
                    "method": method,
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "sr_id": row["sr_id"],
                    "target_review_status": row["target_review_status"],
                },
            )
    after_candidate = db.execute(
        text(
            """
            select count(*) from guide_sr_link_candidates
            where method = :method and review_status in ('candidate', 'asserted')
            """
        ),
        {"method": method},
    ).scalar_one()
    return {
        "serving_candidate_rows_before": int(before_candidate),
        "serving_candidate_rows_after": int(after_candidate),
    }


def _write_reports(summary: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path, prefix: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{prefix}.json"
    md_path = output_dir / f"{prefix}.md"
    csv_path = output_dir / f"{prefix}.csv"
    json_path.write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )

    md_lines = [
        f"# CI/SR Candidate Promotion: {summary['baseline']}",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- mode: `{summary['mode']}`",
        f"- method: `{summary['method']}`",
        f"- rows: `{summary['row_count']}`",
        f"- decisions: `{summary['decision_counts']}`",
        f"- target statuses: `{summary['target_review_status_counts']}`",
        f"- promoted rows: `{summary['promoted_row_count']}`",
        f"- promoted distinct CI: `{summary['promoted_distinct_ci_count']}`",
        f"- promoted distinct SR: `{summary['promoted_distinct_sr_count']}`",
        f"- apply result: `{summary.get('apply_result')}`",
        "",
        "## Policy",
        "",
        summary["policy"],
        "",
        "Rows not explicitly whitelisted remain `needs_review` and are not used by serving.",
        "",
        "## Promoted Preview",
        "",
    ]
    for row in rows:
        if row["target_review_status"] != "candidate":
            continue
        md_lines.append(
            f"- `{row['entity_id']}` -> `{row['sr_id']}` ({row['guide_code']}): {row['reason']}"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    fieldnames = [
        "entity_type",
        "entity_id",
        "guide_code",
        "sr_id",
        "confidence",
        "current_review_status",
        "target_review_status",
        "decision",
        "reason",
        "risk_note",
        "asserted",
        "non_llm_evidence_count",
        "evidence",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
    return {
        "json": str(json_path.relative_to(PROJECT_ROOT)),
        "md": str(md_path.relative_to(PROJECT_ROOT)),
        "csv": str(csv_path.relative_to(PROJECT_ROOT)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", default=DEFAULT_METHOD)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_PREFIX)
    parser.add_argument(
        "--mode",
        choices=("preview", "apply", "revert"),
        default="preview",
        help="preview writes reports only; apply promotes whitelist; revert returns all method rows to needs_review",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SessionLocal() as db:
        summary, rows = _build_report_rows(db, args.method)
        summary["mode"] = args.mode
        if args.mode in {"apply", "revert"}:
            apply_result = _apply_statuses(db, rows, args.method, args.mode)
            db.commit()
            summary, rows = _build_report_rows(db, args.method)
            summary["mode"] = args.mode
            summary["apply_result"] = apply_result
        else:
            summary["apply_result"] = None
        outputs = _write_reports(summary, rows, args.output_dir, args.report_prefix)
    print(json.dumps({"summary": summary, "outputs": outputs}, ensure_ascii=False, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
