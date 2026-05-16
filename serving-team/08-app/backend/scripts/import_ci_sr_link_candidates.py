#!/usr/bin/env python3
"""Import reviewed CI -> SR link candidates into guide_sr_link_candidates.

This script imports review-only candidates.  It never writes to ci_sr_mapping,
never asserts legal links, and never changes SHE/status/penalty/runtime scoring.
Rows are stored with review_status=needs_review and asserted=false.
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

DEFAULT_REVIEW_REPORT = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "ci_sr_mapping_candidate_review_ci_unrelated_action_filter1.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_PREFIX = "pg_ci_sr_link_candidates_ci_unrelated_action_filter1"
DEFAULT_METHOD = "ci_candidate_review_v1"

CASE_SR_IDS: dict[str, list[str]] = {
    "SYN-V7-0312": ["SR-FIRE_EXPLOSION-009", "SR-FIRE_EXPLOSION-017", "SR-FIRE_EXPLOSION-021"],
    "SYN-V4-0022": ["SR-PPE-002", "SR-CHEMICAL-026"],
    "SYN-V4-0027": ["SR-PPE-002"],
    "SYN-V5-0007": ["SR-PPE-002", "SR-FIRE_EXPLOSION-030"],
    "SYN-V5-0021": ["SR-PPE-002", "SR-CHEMICAL-023", "SR-CHEMICAL-026"],
    "SYN-V5-0036": ["SR-PPE-002", "SR-CHEMICAL-023", "SR-CHEMICAL-026"],
    "SYN-V5-0067": ["SR-PPE-002", "SR-PPE-004"],
    "SYN-V8-0163": ["SR-PPE-002", "SR-CHEMICAL-023", "SR-CHEMICAL-026"],
    "SYN-V3-0014": ["SR-PPE-002"],
    "SYN-V5-0046": ["SR-MACHINE-002", "SR-MACHINE-007", "SR-CONVEYOR-002"],
    "SYN-V5-0116": ["SR-MACHINE-002", "SR-MACHINE-009", "SR-CONVEYOR-002"],
    "SYN-V9-0146": ["SR-WORKPLACE-001"],
    "SYN-V3-0133": ["SR-FIRE_EXPLOSION-019", "SR-WORKPLACE-014"],
    "SYN-V4-0058": ["SR-ERGONOMIC-003", "SR-ERGONOMIC-008"],
    "SYN-V5-0047": ["SR-WORKPLACE-001"],
    "SYN-V5-0001": ["SR-CHEMICAL-002", "SR-CHEMICAL-025", "SR-CHEMICAL-026"],
}

CASE_CI_SR_IDS: dict[str, dict[str, list[str]]] = {
    "SYN-V5-0158": {
        "CI-D28-006": ["SR-FIRE_EXPLOSION-019"],
        "CI-D28-008": ["SR-FIRE_EXPLOSION-019"],
    },
    "SYN-V9-0056": {
        "CI-AG1-001": ["SR-WORKPLACE-011"],
        "CI-AG1-002": ["SR-WORKPLACE-011"],
        "CI-AG1-007": ["SR-WORKPLACE-011"],
        "CI-AG1-051": ["SR-WORKPLACE-007", "SR-WORKPLACE-011"],
    },
    "SYN-V9-0057": {
        "CI-G67-008": ["SR-WORKPLACE-018"],
        "CI-G67-009": ["SR-WORKPLACE-007"],
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _infer_baseline(path: Path) -> str:
    name = path.stem
    for prefix in (
        "ci_sr_mapping_candidate_review_",
        "pg_ci_sr_link_candidates_",
    ):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def _manual_ci_candidates(row: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        candidate
        for candidate in row.get("top_ci_candidates") or []
        if candidate.get("selection_method") == "manual_review_seed"
    ]
    if candidates:
        return candidates
    return [
        {
            "ci_id": row.get("best_ci_id"),
            "text": row.get("best_ci_text"),
            "selection_method": row.get("best_ci_selection_method") or "manual_review_seed",
        }
    ] if row.get("best_ci_id") else []


def _build_candidate_rows(review_report: Path, method: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = _load_json(review_report)
    review_summary = data.get("summary") or {}
    baseline = review_summary.get("baseline") or _infer_baseline(review_report)
    source_rows = data.get("rows") or []
    raw_rows: list[dict[str, Any]] = []
    missing_sr_map: list[str] = []

    for row in source_rows:
        case_id = str(row.get("case_id"))
        case_ci_sr_ids = CASE_CI_SR_IDS.get(case_id) or {}
        case_sr_ids = CASE_SR_IDS.get(case_id)
        if not case_ci_sr_ids and not case_sr_ids:
            missing_sr_map.append(case_id)
            continue
        for ci in _manual_ci_candidates(row):
            ci_id = str(ci.get("ci_id"))
            sr_ids = case_ci_sr_ids.get(ci_id) or case_sr_ids or []
            if not sr_ids:
                continue
            for sr_id in sr_ids:
                raw_rows.append(
                    {
                        "entity_type": "CI",
                        "entity_id": ci_id,
                        "guide_code": row.get("top_guide"),
                        "sr_id": sr_id,
                        "confidence": "0.7000",
                        "evidence": (
                            f"{case_id}: {row.get('review_reason') or ''} "
                            f"CI={ci_id}: {ci.get('text') or row.get('best_ci_text') or ''}"
                        ).strip(),
                        "source_fields": {
                            "baseline": baseline,
                            "source_report": _display_path(review_report),
                            "case_id": case_id,
                            "industry_context": row.get("industry_context"),
                            "work_context": row.get("work_context"),
                            "top_guide": row.get("top_guide"),
                            "ci_selection_method": ci.get("selection_method"),
                            "expected_corrective_direction": row.get("expected_corrective_direction"),
                            "photo_description": row.get("photo_description"),
                        },
                        "method": method,
                        "review_status": "needs_review",
                        "non_llm_evidence_count": 2,
                        "asserted": False,
                    }
                )
    if missing_sr_map:
        raise RuntimeError(f"Missing CASE_SR_IDS entries: {missing_sr_map}")

    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in raw_rows:
        key = (row["entity_type"], row["entity_id"], row["sr_id"], row["method"])
        if key not in grouped:
            grouped[key] = {
                **row,
                "evidence_parts": [row["evidence"]],
                "source_fields": {
                    **row["source_fields"],
                    "case_ids": [row["source_fields"]["case_id"]],
                    "cases": [row["source_fields"]],
                },
            }
            continue
        existing = grouped[key]
        existing["evidence_parts"].append(row["evidence"])
        existing["source_fields"]["case_ids"].append(row["source_fields"]["case_id"])
        existing["source_fields"]["cases"].append(row["source_fields"])
    output_rows: list[dict[str, Any]] = []
    for row in grouped.values():
        evidence_parts = row.pop("evidence_parts")
        row["evidence"] = " | ".join(evidence_parts)
        output_rows.append(row)
    output_rows.sort(key=lambda row: (row["guide_code"], row["entity_id"], row["sr_id"]))

    summary = {
        "generated_at": _now(),
        "baseline": baseline,
        "source_review_report": _display_path(review_report),
        "method": method,
        "review_status": "needs_review",
        "asserted": False,
        "source_case_count": len(source_rows),
        "raw_candidate_row_count": len(raw_rows),
        "candidate_row_count": len(output_rows),
        "distinct_ci_count": len({row["entity_id"] for row in output_rows}),
        "distinct_sr_count": len({row["sr_id"] for row in output_rows}),
        "rows_by_guide": dict(Counter(row["guide_code"] for row in output_rows).most_common()),
        "rows_by_sr": dict(Counter(row["sr_id"] for row in output_rows).most_common()),
        "policy": "review-only candidate import; no ci_sr_mapping insert; asserted=false; serving-ineligible needs_review",
    }
    return summary, output_rows


def _validate_refs(db: Any, rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    guide_codes = sorted({row["guide_code"] for row in rows})
    ci_ids = sorted({row["entity_id"] for row in rows})
    sr_ids = sorted({row["sr_id"] for row in rows})
    existing_guides = {
        value
        for (value,) in db.execute(
            text("select guide_code from kosha_guides where guide_code = any(:ids)"),
            {"ids": guide_codes},
        ).fetchall()
    }
    existing_cis = {
        value
        for (value,) in db.execute(
            text("select identifier from checklist_items where identifier = any(:ids)"),
            {"ids": ci_ids},
        ).fetchall()
    }
    existing_srs = {
        value
        for (value,) in db.execute(
            text("select identifier from safety_requirements where identifier = any(:ids)"),
            {"ids": sr_ids},
        ).fetchall()
    }
    return {
        "missing_guides": [guide for guide in guide_codes if guide not in existing_guides],
        "missing_cis": [ci for ci in ci_ids if ci not in existing_cis],
        "missing_srs": [sr for sr in sr_ids if sr not in existing_srs],
    }


def _replace_method_rows(db: Any, rows: list[dict[str, Any]], method: str) -> dict[str, int]:
    before = db.execute(
        text("select count(*) from guide_sr_link_candidates where method = :method"),
        {"method": method},
    ).scalar_one()
    db.execute(text("delete from guide_sr_link_candidates where method = :method"), {"method": method})
    for row in rows:
        db.execute(
            text(
                """
                insert into guide_sr_link_candidates
                  (entity_type, entity_id, guide_code, sr_id, confidence, evidence,
                   source_fields, method, review_status, non_llm_evidence_count, asserted)
                values
                  (:entity_type, :entity_id, :guide_code, :sr_id, :confidence, :evidence,
                   cast(:source_fields as jsonb), :method, :review_status,
                   :non_llm_evidence_count, :asserted)
                """
            ),
            {
                **row,
                "confidence": Decimal(row["confidence"]),
                "source_fields": json.dumps(row["source_fields"], ensure_ascii=False),
            },
        )
    after = db.execute(
        text("select count(*) from guide_sr_link_candidates where method = :method"),
        {"method": method},
    ).scalar_one()
    return {"deleted_existing_rows": int(before), "inserted_rows": int(after)}


def _write_reports(summary: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path, prefix: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{prefix}.json"
    md_path = output_dir / f"{prefix}.md"
    csv_path = output_dir / f"{prefix}.csv"
    json_path.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        f"# PG CI/SR Link Candidate Import: {summary['baseline']}",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- mode: `{summary['mode']}`",
        f"- method: `{summary['method']}`",
        f"- review_status: `{summary['review_status']}`",
        f"- asserted: `{summary['asserted']}`",
        f"- source cases: `{summary['source_case_count']}`",
        f"- candidate rows: `{summary['candidate_row_count']}`",
        f"- distinct CI: `{summary['distinct_ci_count']}`",
        f"- distinct SR: `{summary['distinct_sr_count']}`",
        f"- missing refs: `{summary['missing_refs']}`",
        "",
        "## Rows By Guide",
        "",
    ]
    for key, count in summary["rows_by_guide"].items():
        md_lines.append(f"- `{key}`: `{count}`")
    md_lines.extend(["", "## Import Result", ""])
    if summary.get("import_result"):
        for key, value in summary["import_result"].items():
            md_lines.append(f"- `{key}`: `{value}`")
    else:
        md_lines.append("- dry-run only")
    md_lines.extend(
        [
            "",
            "This report is review-only. It does not insert into `ci_sr_mapping`, does not assert legal links, and does not change serving behavior.",
        ]
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    fieldnames = [
        "entity_type",
        "entity_id",
        "guide_code",
        "sr_id",
        "confidence",
        "method",
        "review_status",
        "non_llm_evidence_count",
        "asserted",
        "evidence",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return {"json": str(json_path), "md": str(md_path), "csv": str(csv_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-report", type=Path, default=DEFAULT_REVIEW_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--method", default=DEFAULT_METHOD)
    parser.add_argument("--apply", action="store_true", help="Replace same-method review candidates in PostgreSQL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary, rows = _build_candidate_rows(args.review_report, args.method)
    summary["mode"] = "apply" if args.apply else "dry_run"
    with SessionLocal() as db:
        missing_refs = _validate_refs(db, rows)
        summary["missing_refs"] = missing_refs
        if any(missing_refs.values()):
            raise RuntimeError(f"Missing references: {missing_refs}")
        if args.apply:
            summary["import_result"] = _replace_method_rows(db, rows, args.method)
            db.commit()
        else:
            summary["import_result"] = None
    paths = _write_reports(summary, rows, args.output_dir, args.report_prefix)
    print(json.dumps({"summary": summary, "paths": paths}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
