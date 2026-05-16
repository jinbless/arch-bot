#!/usr/bin/env python3
"""Sync OHS Guide usage profiles into PostgreSQL.

The source of truth for serving remains the OHS JSON artifact in
``app/data/guide_domain_profiles.json``.  This script materializes the same
baseline into ``guide_usage_profiles`` so that PG, ontology export, and docs can
be verified against the accepted serving baseline.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal, engine  # noqa: E402
from app.db.models import PgGuideUsageProfile  # noqa: E402


DEFAULT_PROFILE_PATH = BACKEND_DIR / "app" / "data" / "guide_domain_profiles.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_BASELINE_ID = "ci_broad_sr_guard4"
DEFAULT_METHOD = "ci_broad_sr_guard4_pg_sync"

ALLOWED_REVIEW_STATUSES = {"candidate", "asserted", "rejected", "needs_review"}
ALLOWED_PHOTO_MATCHABILITY = {
    "photo_actionable",
    "photo_conditional_followup",
    "photo_unmatchable",
}
ALLOWED_TOP_POLICIES = {"allow_photo_top", "suppress_photo_top"}
ALLOWED_FOLLOWUP_POLICIES = {"none", "explicit_context_only"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _as_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text_value = str(value).strip()
    return text_value if text_value else fallback


def load_profile_rows(profile_path: Path, baseline_id: str, method: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError(f"{profile_path} must contain a top-level 'profiles' object")

    rows: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    for guide_code, profile in sorted(profiles.items()):
        if not isinstance(profile, dict):
            violations.append({"guide_code": guide_code, "rule": "profile_object", "detail": "profile is not an object"})
            continue

        usage_summary = _as_text(profile.get("usage_summary"), _as_text(profile.get("title"), guide_code))
        evidence = _as_text(
            profile.get("usage_profile_evidence"),
            _as_text(profile.get("evidence"), usage_summary),
        )
        review_status = _as_text(profile.get("usage_profile_review_status"), "candidate")
        if review_status not in ALLOWED_REVIEW_STATUSES:
            violations.append(
                {
                    "guide_code": guide_code,
                    "rule": "review_status",
                    "detail": f"normalized invalid review status {review_status!r} to 'candidate'",
                }
            )
            review_status = "candidate"

        photo_matchability = _as_text(profile.get("photo_matchability"), "photo_actionable")
        top_policy = _as_text(profile.get("top_procedure_policy"), "allow_photo_top")
        followup_policy = _as_text(profile.get("followup_policy"), "none")
        if photo_matchability not in ALLOWED_PHOTO_MATCHABILITY:
            violations.append({"guide_code": guide_code, "rule": "photo_matchability", "detail": photo_matchability})
        if top_policy not in ALLOWED_TOP_POLICIES:
            violations.append({"guide_code": guide_code, "rule": "top_procedure_policy", "detail": top_policy})
        if followup_policy not in ALLOWED_FOLLOWUP_POLICIES:
            violations.append({"guide_code": guide_code, "rule": "followup_policy", "detail": followup_policy})
        if photo_matchability == "photo_unmatchable" and top_policy != "suppress_photo_top":
            violations.append(
                {
                    "guide_code": guide_code,
                    "rule": "photo_unmatchable_top_policy",
                    "detail": f"photo_unmatchable has top policy {top_policy!r}",
                }
            )
        if not usage_summary:
            violations.append({"guide_code": guide_code, "rule": "usage_summary_required", "detail": "empty"})
        if not evidence:
            violations.append({"guide_code": guide_code, "rule": "evidence_required", "detail": "empty"})

        rows.append(
            {
                "guide_code": guide_code,
                "baseline_id": baseline_id,
                "profile_level": _as_text(profile.get("profile_level"), "general"),
                "domain_family": profile.get("domain_family"),
                "usage_summary": usage_summary,
                "intended_workplaces": _as_list(profile.get("intended_workplaces")),
                "intended_tasks": _as_list(profile.get("intended_tasks")),
                "observable_required_cues": _as_list(profile.get("observable_required_cues")),
                "negative_boundaries": _as_list(profile.get("negative_boundaries") or profile.get("negative_context_terms")),
                "procedure_role": _as_text(profile.get("procedure_role"), "field_control"),
                "photo_matchability": photo_matchability,
                "top_procedure_policy": top_policy,
                "followup_policy": followup_policy,
                "primary_work_process_ids": _as_list(profile.get("primary_work_process_ids")),
                "classification_reason": profile.get("classification_reason"),
                "evidence": evidence,
                "source_fields": _as_list(profile.get("source_fields")),
                "method": method,
                "review_status": review_status,
            }
        )
    return payload, rows, violations


def ensure_schema() -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS guide_usage_profiles (
        guide_code                 VARCHAR(20) PRIMARY KEY REFERENCES kosha_guides(guide_code),
        baseline_id                VARCHAR(80) NOT NULL DEFAULT 'unknown',
        profile_level              VARCHAR(20) NOT NULL DEFAULT 'general',
        domain_family              TEXT,
        usage_summary              TEXT NOT NULL CHECK(length(usage_summary) > 0),
        intended_workplaces        JSONB NOT NULL DEFAULT '[]'::jsonb,
        intended_tasks             JSONB NOT NULL DEFAULT '[]'::jsonb,
        observable_required_cues   JSONB NOT NULL DEFAULT '[]'::jsonb,
        negative_boundaries        JSONB NOT NULL DEFAULT '[]'::jsonb,
        procedure_role             VARCHAR(40) NOT NULL DEFAULT 'field_control',
        photo_matchability         VARCHAR(40) NOT NULL DEFAULT 'photo_actionable',
        top_procedure_policy       VARCHAR(40) NOT NULL DEFAULT 'allow_photo_top',
        followup_policy            VARCHAR(40) NOT NULL DEFAULT 'none',
        primary_work_process_ids   JSONB NOT NULL DEFAULT '[]'::jsonb,
        classification_reason      TEXT,
        evidence                   TEXT NOT NULL CHECK(length(evidence) > 0),
        source_fields              JSONB NOT NULL DEFAULT '[]'::jsonb,
        method                     VARCHAR(40) NOT NULL,
        review_status              VARCHAR(20) NOT NULL DEFAULT 'candidate',
        created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
    alter_statements = (
        "ALTER TABLE guide_usage_profiles ADD COLUMN IF NOT EXISTS baseline_id VARCHAR(80) NOT NULL DEFAULT 'unknown'",
        "ALTER TABLE guide_usage_profiles ADD COLUMN IF NOT EXISTS photo_matchability VARCHAR(40) NOT NULL DEFAULT 'photo_actionable'",
        "ALTER TABLE guide_usage_profiles ADD COLUMN IF NOT EXISTS top_procedure_policy VARCHAR(40) NOT NULL DEFAULT 'allow_photo_top'",
        "ALTER TABLE guide_usage_profiles ADD COLUMN IF NOT EXISTS followup_policy VARCHAR(40) NOT NULL DEFAULT 'none'",
        "ALTER TABLE guide_usage_profiles ADD COLUMN IF NOT EXISTS classification_reason TEXT",
        "ALTER TABLE guide_usage_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        "CREATE INDEX IF NOT EXISTS idx_gup_role ON guide_usage_profiles(procedure_role)",
        "CREATE INDEX IF NOT EXISTS idx_gup_status ON guide_usage_profiles(review_status)",
        "CREATE INDEX IF NOT EXISTS idx_gup_profile ON guide_usage_profiles(profile_level)",
        "CREATE INDEX IF NOT EXISTS idx_gup_baseline ON guide_usage_profiles(baseline_id)",
        "CREATE INDEX IF NOT EXISTS idx_gup_photo ON guide_usage_profiles(photo_matchability, top_procedure_policy)",
    )
    with engine.begin() as conn:
        conn.execute(text(ddl))
        for statement in alter_statements:
            conn.execute(text(statement))


def collect_db_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    guide_codes = {row["guide_code"] for row in rows}
    wp_ids = {
        wp_id
        for row in rows
        for wp_id in row["primary_work_process_ids"]
        if isinstance(wp_id, str) and wp_id.strip()
    }
    with engine.connect() as conn:
        db_guides = {
            row[0]
            for row in conn.execute(text("SELECT guide_code FROM kosha_guides")).all()
        }
        wp_owner_rows = conn.execute(
            text(
                """
                SELECT identifier, source_guide
                FROM work_processes
                WHERE identifier = ANY(:wp_ids)
                """
            ),
            {"wp_ids": list(wp_ids) or ["__none__"]},
        ).all()
        wp_owners = {identifier: source_guide for identifier, source_guide in wp_owner_rows}
        before_count = conn.execute(text("SELECT count(*) FROM guide_usage_profiles")).scalar_one()

    missing_guides = sorted(guide_codes - db_guides)
    missing_wp_ids: list[str] = []
    cross_guide_wp_ids: list[dict[str, str]] = []
    for row in rows:
        for wp_id in row["primary_work_process_ids"]:
            if wp_id not in wp_owners:
                missing_wp_ids.append(wp_id)
            elif wp_owners[wp_id] != row["guide_code"]:
                cross_guide_wp_ids.append(
                    {
                        "guide_code": row["guide_code"],
                        "wp_id": wp_id,
                        "wp_source_guide": wp_owners[wp_id],
                    }
                )
    return {
        "db_guide_count": len(db_guides),
        "db_workprocess_ids_seen": len(wp_owners),
        "table_count_before": before_count,
        "missing_guides": missing_guides,
        "missing_primary_work_process_ids": sorted(set(missing_wp_ids)),
        "cross_guide_primary_work_process_ids": cross_guide_wp_ids,
    }


def upsert_rows(rows: list[dict[str, Any]]) -> int:
    table = PgGuideUsageProfile.__table__
    stmt = pg_insert(table).values(rows)
    update_columns = {
        column.name: getattr(stmt.excluded, column.name)
        for column in table.columns
        if column.name not in {"guide_code", "created_at", "updated_at"}
    }
    update_columns["updated_at"] = func.now()
    stmt = stmt.on_conflict_do_update(index_elements=[table.c.guide_code], set_=update_columns)
    with SessionLocal() as db:
        result = db.execute(stmt)
        db.commit()
        return int(result.rowcount or 0)


def collect_after_counts(baseline_id: str) -> dict[str, Any]:
    with engine.connect() as conn:
        table_count_after = conn.execute(text("SELECT count(*) FROM guide_usage_profiles")).scalar_one()
        baseline_count = conn.execute(
            text("SELECT count(*) FROM guide_usage_profiles WHERE baseline_id = :baseline_id"),
            {"baseline_id": baseline_id},
        ).scalar_one()
        photo_counts = dict(
            conn.execute(
                text(
                    """
                    SELECT photo_matchability, count(*)
                    FROM guide_usage_profiles
                    WHERE baseline_id = :baseline_id
                    GROUP BY photo_matchability
                    ORDER BY photo_matchability
                    """
                ),
                {"baseline_id": baseline_id},
            ).all()
        )
        role_counts = dict(
            conn.execute(
                text(
                    """
                    SELECT procedure_role, count(*)
                    FROM guide_usage_profiles
                    WHERE baseline_id = :baseline_id
                    GROUP BY procedure_role
                    ORDER BY procedure_role
                    """
                ),
                {"baseline_id": baseline_id},
            ).all()
        )
        review_counts = dict(
            conn.execute(
                text(
                    """
                    SELECT review_status, count(*)
                    FROM guide_usage_profiles
                    WHERE baseline_id = :baseline_id
                    GROUP BY review_status
                    ORDER BY review_status
                    """
                ),
                {"baseline_id": baseline_id},
            ).all()
        )
    return {
        "table_count_after": table_count_after,
        "baseline_count": baseline_count,
        "photo_matchability_counts": photo_counts,
        "procedure_role_counts": role_counts,
        "review_status_counts": review_counts,
    }


def write_reports(report_dir: Path, prefix: str, report: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, str]:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"{prefix}.json"
    md_path = report_dir / f"{prefix}.md"
    csv_path = report_dir / f"{prefix}.csv"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        f"# PG Guide Usage Profile Sync: {report['baseline_id']}",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- status: `{report['status']}`",
        f"- dry_run: `{report['dry_run']}`",
        f"- source_profile: `{report['source_profile_path']}`",
        f"- profile_rows: `{report['profile_rows']}`",
        f"- db_guides: `{report['db_context']['db_guide_count']}`",
        f"- table_count_before: `{report['db_context']['table_count_before']}`",
        f"- table_count_after: `{report['after_counts']['table_count_after']}`",
        f"- baseline_count: `{report['after_counts']['baseline_count']}`",
        f"- upsert_rowcount: `{report['upsert_rowcount']}`",
        f"- missing_guides: `{len(report['db_context']['missing_guides'])}`",
        f"- missing_primary_work_process_ids: `{len(report['db_context']['missing_primary_work_process_ids'])}`",
        f"- cross_guide_primary_work_process_ids: `{len(report['db_context']['cross_guide_primary_work_process_ids'])}`",
        f"- validation_violations: `{len(report['validation_violations'])}`",
        "",
        "## Counts",
        "",
        "### Photo Matchability",
        "",
    ]
    for key, value in sorted(report["after_counts"]["photo_matchability_counts"].items()):
        md_lines.append(f"- `{key}`: `{value}`")
    md_lines.extend(["", "### Procedure Role", ""])
    for key, value in sorted(report["after_counts"]["procedure_role_counts"].items()):
        md_lines.append(f"- `{key}`: `{value}`")
    md_lines.extend(["", "## Notes", ""])
    md_lines.append(
        "This sync materializes the OHS serving artifact into PostgreSQL for audit/export alignment. "
        "It does not change SHE approval, status, penalty, asserted legal basedOn, or SR legal evidence."
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "guide_code",
                "profile_level",
                "procedure_role",
                "photo_matchability",
                "top_procedure_policy",
                "followup_policy",
                "review_status",
                "primary_work_process_count",
                "usage_summary",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "guide_code": row["guide_code"],
                    "profile_level": row["profile_level"],
                    "procedure_role": row["procedure_role"],
                    "photo_matchability": row["photo_matchability"],
                    "top_procedure_policy": row["top_procedure_policy"],
                    "followup_policy": row["followup_policy"],
                    "review_status": row["review_status"],
                    "primary_work_process_count": len(row["primary_work_process_ids"]),
                    "usage_summary": row["usage_summary"],
                }
            )
    return {"json": str(json_path), "md": str(md_path), "csv": str(csv_path)}


def build_report(
    *,
    baseline_id: str,
    method: str,
    profile_path: Path,
    payload: dict[str, Any],
    rows: list[dict[str, Any]],
    validation_violations: list[dict[str, Any]],
    db_context: dict[str, Any],
    after_counts: dict[str, Any],
    upsert_rowcount: int,
    dry_run: bool,
) -> dict[str, Any]:
    profile_counter = Counter(row["profile_level"] for row in rows)
    role_counter = Counter(row["procedure_role"] for row in rows)
    photo_counter = Counter(row["photo_matchability"] for row in rows)
    status = "PASS"
    if (
        validation_violations
        or db_context["missing_guides"]
        or db_context["missing_primary_work_process_ids"]
        or db_context["cross_guide_primary_work_process_ids"]
        or after_counts["baseline_count"] not in (0 if dry_run else len(rows), len(rows))
    ):
        status = "FAIL"

    return {
        "generated_at": _now(),
        "baseline_id": baseline_id,
        "method": method,
        "dry_run": dry_run,
        "status": status,
        "source_profile_path": str(profile_path),
        "source_generated_at": payload.get("generated_at"),
        "source_method": payload.get("method"),
        "profile_rows": len(rows),
        "source_guide_count": payload.get("guide_count"),
        "profile_level_counts": dict(profile_counter),
        "procedure_role_counts": dict(role_counter),
        "photo_matchability_counts": dict(photo_counter),
        "db_context": db_context,
        "after_counts": after_counts,
        "upsert_rowcount": upsert_rowcount,
        "validation_violations": validation_violations,
        "runtime_impact": "none_status_penalty_she_sr_unchanged",
        "serving_runtime_source": "OHS JSON artifacts remain the request-path source; PG is synchronized for audit/export alignment.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-path", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--baseline-id", default=DEFAULT_BASELINE_ID)
    parser.add_argument("--method", default=DEFAULT_METHOD)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=f"pg_guide_usage_profiles_sync_{DEFAULT_BASELINE_ID}")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, rows, validation_violations = load_profile_rows(args.profile_path, args.baseline_id, args.method)
    ensure_schema()
    db_context = collect_db_context(rows)

    upsert_rowcount = 0
    if not args.dry_run and not db_context["missing_guides"]:
        upsert_rowcount = upsert_rows(rows)
    after_counts = collect_after_counts(args.baseline_id)

    report = build_report(
        baseline_id=args.baseline_id,
        method=args.method,
        profile_path=args.profile_path,
        payload=payload,
        rows=rows,
        validation_violations=validation_violations,
        db_context=db_context,
        after_counts=after_counts,
        upsert_rowcount=upsert_rowcount,
        dry_run=args.dry_run,
    )
    if not args.no_report:
        paths = write_reports(args.report_dir, args.report_prefix, report, rows)
        report["report_paths"] = paths
        # Refresh JSON with report paths included.
        Path(paths["json"]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({k: report[k] for k in ("status", "baseline_id", "profile_rows", "upsert_rowcount")}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
