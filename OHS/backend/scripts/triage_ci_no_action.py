#!/usr/bin/env python3
"""Triage Stage 2~5 CI no-action cases.

This script is diagnostic only.  It does not change serving behavior, asserted
SR mappings, SHE approval, status, penalty, or Guide usage profiles.
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

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgChecklistItem, PgCiSrMapping  # noqa: E402
from app.services.broad_sr_policy import get_broad_sr_ids  # noqa: E402


DEFAULT_PIPELINE_REPORT = PROJECT_ROOT / "pictures-json" / "reports" / "pipeline_quality_v1_v10_ci_broad_sr_guard4.json"
DEFAULT_NO_TOP_ACTIONABILITY = (
    PROJECT_ROOT / "pictures-json" / "reports" / "stage2_5_no_top_actionability_ci_broad_sr_guard4.json"
)
DEFAULT_PROFILES = BACKEND_DIR / "app" / "data" / "guide_domain_profiles.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_PREFIX = "ci_no_action_triage_ci_broad_sr_guard4"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_no_top_rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = _load_json(path)
    return {str(row.get("case_id")): row for row in data.get("rows") or [] if row.get("case_id")}


def _load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    data = _load_json(path)
    profiles = data.get("profiles") if isinstance(data, dict) else {}
    return profiles if isinstance(profiles, dict) else {}


def _guide_ci_stats(db: Any, guide_code: str | None, response_sr_ids: set[str], broad_sr_ids: set[str]) -> dict[str, Any]:
    if not guide_code:
        return {
            "top_guide_ci_count": 0,
            "top_guide_ci_with_sr_mapping_count": 0,
            "top_guide_ci_matching_response_sr_count": 0,
            "top_guide_ci_matching_non_broad_response_sr_count": 0,
            "top_guide_ci_matching_broad_only_count": 0,
        }

    ci_rows = db.query(PgChecklistItem.identifier).filter(PgChecklistItem.source_guide == guide_code).all()
    ci_ids = [row[0] for row in ci_rows]
    if not ci_ids:
        return {
            "top_guide_ci_count": 0,
            "top_guide_ci_with_sr_mapping_count": 0,
            "top_guide_ci_matching_response_sr_count": 0,
            "top_guide_ci_matching_non_broad_response_sr_count": 0,
            "top_guide_ci_matching_broad_only_count": 0,
        }

    mappings = db.query(PgCiSrMapping.ci_id, PgCiSrMapping.sr_id).filter(PgCiSrMapping.ci_id.in_(ci_ids)).all()
    mapped_by_ci: dict[str, set[str]] = defaultdict(set)
    for ci_id, sr_id in mappings:
        mapped_by_ci[ci_id].add(sr_id)

    matching = {ci_id: srs & response_sr_ids for ci_id, srs in mapped_by_ci.items() if srs & response_sr_ids}
    non_broad_matching = {
        ci_id: srs - broad_sr_ids
        for ci_id, srs in matching.items()
        if srs - broad_sr_ids
    }
    broad_only_matching = {
        ci_id: srs
        for ci_id, srs in matching.items()
        if srs and not (srs - broad_sr_ids)
    }
    return {
        "top_guide_ci_count": len(ci_ids),
        "top_guide_ci_with_sr_mapping_count": len(mapped_by_ci),
        "top_guide_ci_matching_response_sr_count": len(matching),
        "top_guide_ci_matching_non_broad_response_sr_count": len(non_broad_matching),
        "top_guide_ci_matching_broad_only_count": len(broad_only_matching),
    }


def _classify_row(
    row: dict[str, Any],
    *,
    no_top_rows: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    guide_stats: dict[str, Any],
) -> tuple[str, str, str, str]:
    stage5 = row["stage5_guide_ci"]
    she = row["stage3_she"]
    sr = row["stage4_sr"]
    top_procedure = stage5.get("top_procedure") or {}
    top_guide = top_procedure.get("guide_code")
    response_has_sr = bool(sr.get("sr_ids") or [])

    if not top_guide:
        no_top = no_top_rows.get(row.get("case_id")) or {}
        actionability_group = no_top.get("actionability_group") or "unreviewed_no_top"
        actionability = no_top.get("actionability") or ""
        if actionability_group == "accepted_empty_top":
            return (
                "no_top_accepted_empty_top",
                "accepted_empty_top",
                actionability,
                "표준절차가 비어 있는 것이 현재 정책상 허용되는 케이스다.",
            )
        return (
            "no_top_source_or_taxonomy_review",
            "source_or_taxonomy_review",
            actionability,
            "현장에 맞는 photo-top Guide가 없거나 source/taxonomy 검토가 먼저 필요하다.",
        )

    if not she.get("has_actionable_she"):
        if response_has_sr:
            return (
                "upstream_she_not_actionable_with_sr",
                "upstream_stage2_3_review",
                "",
                "Guide는 잡혔지만 SHE가 actionable로 확정되지 않아 즉시조치를 만들지 않는 케이스다.",
            )
        return (
            "upstream_she_not_actionable_no_sr",
            "upstream_stage2_3_review",
            "",
            "SHE와 SR이 모두 실행 가능한 상태가 아니므로 CI 보정보다 Stage 2/3 보강 대상이다.",
        )

    if not response_has_sr:
        return (
            "stage4_sr_missing_for_ci",
            "stage4_sr_review",
            "",
            "SHE는 actionable이지만 연결 SR이 없어 CI 생성 근거가 부족하다.",
        )

    if guide_stats["top_guide_ci_count"] == 0:
        return (
            "top_guide_has_no_ci_items",
            "source_or_extraction_review",
            "",
            "top Guide 자체에 ChecklistItem이 없어 즉시조치 원천이 없다.",
        )
    if guide_stats["top_guide_ci_with_sr_mapping_count"] == 0:
        return (
            "top_guide_ci_has_no_sr_mapping",
            "ci_mapping_review",
            "",
            "top Guide에는 CI가 있지만 CI-SR 매핑이 없어 SR 기반 즉시조치로 올라오지 못한다.",
        )
    if guide_stats["top_guide_ci_matching_response_sr_count"] == 0:
        return (
            "top_guide_ci_sr_mapping_gap",
            "ci_mapping_review",
            "",
            "top Guide의 CI-SR 매핑이 현재 SHE/SR 결과와 교차하지 않는다.",
        )
    if (
        guide_stats["top_guide_ci_matching_response_sr_count"]
        and not guide_stats["top_guide_ci_matching_non_broad_response_sr_count"]
    ):
        return (
            "top_guide_ci_broad_only_blocked",
            "ci_mapping_review",
            "",
            "교차 매핑이 broad SR뿐이라 현재 정책상 즉시조치 top 근거로 쓰지 않는다.",
        )

    profile = profiles.get(top_guide) or {}
    role = profile.get("procedure_role") or ""
    return (
        "top_guide_ci_relevance_gate_gap",
        "runtime_repair_candidate",
        "",
        f"top Guide와 non-broad CI-SR 교차는 있으나 role/context/support gate에서 걸린다. procedure_role={role}",
    )


def build_rows(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pipeline = _load_json(args.pipeline_report)
    records = pipeline.get("records") or []
    no_top_rows = _load_no_top_rows(args.no_top_actionability)
    profiles = _load_profiles(args.profiles)
    broad_sr_ids = get_broad_sr_ids()
    rows: list[dict[str, Any]] = []

    with SessionLocal() as db:
        for record in records:
            ci_queues = record["stage5_guide_ci"]["ci"]["queues"]
            if "ci_no_action" not in ci_queues:
                continue
            stage5 = record["stage5_guide_ci"]
            top_procedure = stage5.get("top_procedure") or {}
            top_guide = top_procedure.get("guide_code")
            sr_ids = set(record["stage4_sr"].get("sr_ids") or [])
            guide_stats = _guide_ci_stats(db, top_guide, sr_ids, broad_sr_ids)
            category, repair_group, subcategory, reason = _classify_row(
                record,
                no_top_rows=no_top_rows,
                profiles=profiles,
                guide_stats=guide_stats,
            )
            no_top = no_top_rows.get(record.get("case_id")) or {}
            rows.append(
                {
                    "case_id": record.get("case_id"),
                    "version": record.get("version"),
                    "line_no": record.get("line_no"),
                    "case_type": record.get("case_type"),
                    "industry_context": record.get("industry_context"),
                    "work_context": record.get("work_context"),
                    "primary_failure_stage": record.get("primary_failure_stage"),
                    "triage_category": category,
                    "repair_group": repair_group,
                    "triage_subcategory": subcategory,
                    "triage_reason": reason,
                    "top_guide": top_guide,
                    "top_guide_title": top_procedure.get("title"),
                    "guide_category": stage5.get("guide_category"),
                    "procedure_count": stage5.get("procedure_count"),
                    "has_actionable_she": bool(record["stage3_she"].get("has_actionable_she")),
                    "has_confirmed_she": bool(record["stage3_she"].get("has_confirmed_she")),
                    "sr_count": len(record["stage4_sr"].get("sr_ids") or []),
                    "broad_sr_count": len(record["stage4_sr"].get("broad_sr_ids") or []),
                    "stage2_queues": ",".join(record["stage2_risk_feature"].get("queues") or []),
                    "stage3_queues": ",".join(record["stage3_she"].get("queues") or []),
                    "stage4_queues": ",".join(record["stage4_sr"].get("queues") or []),
                    "stage5_queues": ",".join(stage5.get("queues") or []),
                    "no_top_actionability": no_top.get("actionability"),
                    "no_top_actionability_group": no_top.get("actionability_group"),
                    "photo_description": record.get("photo_description"),
                    "expected_primary_risk": record.get("expected_primary_risk"),
                    "expected_corrective_direction": record.get("expected_corrective_direction"),
                    **guide_stats,
                }
            )

    summary = summarize_rows(rows, pipeline)
    return summary, rows


def _top(counter: Counter, limit: int = 20) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in counter.most_common(limit)]


def summarize_rows(rows: list[dict[str, Any]], pipeline: dict[str, Any]) -> dict[str, Any]:
    category_counts = Counter(row["triage_category"] for row in rows)
    repair_group_counts = Counter(row["repair_group"] for row in rows)
    runtime_repair_rows = [row for row in rows if row["repair_group"] == "runtime_repair_candidate"]
    ci_mapping_rows = [row for row in rows if row["repair_group"] == "ci_mapping_review"]
    upstream_rows = [row for row in rows if row["repair_group"] == "upstream_stage2_3_review"]
    no_top_review_rows = [row for row in rows if row["repair_group"] == "source_or_taxonomy_review"]
    accepted_empty_rows = [row for row in rows if row["repair_group"] == "accepted_empty_top"]
    return {
        "generated_at": _now(),
        "source_pipeline_report": str(DEFAULT_PIPELINE_REPORT.relative_to(PROJECT_ROOT)),
        "source_no_top_actionability_report": str(DEFAULT_NO_TOP_ACTIONABILITY.relative_to(PROJECT_ROOT)),
        "source_pipeline_created_at_utc": pipeline.get("created_at_utc"),
        "baseline": "ci_broad_sr_guard4",
        "total_ci_no_action": len(rows),
        "triage_category_counts": dict(category_counts.most_common()),
        "repair_group_counts": dict(repair_group_counts.most_common()),
        "ci_layer_direct_repair_candidates": len(runtime_repair_rows),
        "ci_mapping_or_candidate_review_candidates": len(ci_mapping_rows),
        "upstream_stage2_3_review_count": len(upstream_rows),
        "no_top_source_or_taxonomy_review_count": len(no_top_review_rows),
        "accepted_empty_top_count": len(accepted_empty_rows),
        "top_guides_in_ci_mapping_review": _top(Counter(row["top_guide"] for row in ci_mapping_rows if row["top_guide"])),
        "top_guides_in_runtime_repair": _top(Counter(row["top_guide"] for row in runtime_repair_rows if row["top_guide"])),
        "industries_in_ci_mapping_review": _top(Counter(row["industry_context"] for row in ci_mapping_rows if row["industry_context"])),
        "industries_in_upstream_review": _top(Counter(row["industry_context"] for row in upstream_rows if row["industry_context"])),
        "interpretation": (
            "Most CI no_action cases are not direct CI scoring failures.  The narrow runtime repair tail is small; "
            "the bigger actionable queue is CI/SR mapping review for top Guides that already have standard procedures."
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
        f"# CI No Action Triage: {summary['baseline']}",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- total_ci_no_action: `{summary['total_ci_no_action']}`",
        f"- direct runtime repair candidates: `{summary['ci_layer_direct_repair_candidates']}`",
        f"- CI mapping/candidate review candidates: `{summary['ci_mapping_or_candidate_review_candidates']}`",
        f"- upstream Stage 2/3 review count: `{summary['upstream_stage2_3_review_count']}`",
        f"- NO_TOP source/taxonomy review count: `{summary['no_top_source_or_taxonomy_review_count']}`",
        f"- accepted empty top count: `{summary['accepted_empty_top_count']}`",
        "",
        "## Triage Categories",
        "",
    ]
    for key, count in summary["triage_category_counts"].items():
        md_lines.append(f"- `{key}`: `{count}`")
    md_lines.extend(["", "## Repair Groups", ""])
    for key, count in summary["repair_group_counts"].items():
        md_lines.append(f"- `{key}`: `{count}`")
    md_lines.extend(["", "## Top Guides In CI Mapping Review", ""])
    for item in summary["top_guides_in_ci_mapping_review"][:12]:
        md_lines.append(f"- `{item['key']}`: `{item['count']}`")
    md_lines.extend(["", "## Runtime Repair Examples", ""])
    for row in [row for row in rows if row["repair_group"] == "runtime_repair_candidate"][:10]:
        md_lines.append(
            f"- `{row['case_id']}` `{row['industry_context']}` `{row['work_context']}` "
            f"top Guide `{row['top_guide']}`: {row['triage_reason']}"
        )
    md_lines.extend(
        [
            "",
            "## Interpretation",
            "",
            summary["interpretation"],
            "",
            "This report is diagnostic only.  It does not update runtime behavior, SHE approval, status, penalty, asserted legal mapping, or Guide profiles.",
        ]
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    fieldnames = [
        "case_id",
        "version",
        "case_type",
        "industry_context",
        "work_context",
        "primary_failure_stage",
        "triage_category",
        "repair_group",
        "triage_subcategory",
        "top_guide",
        "guide_category",
        "procedure_count",
        "has_actionable_she",
        "has_confirmed_she",
        "sr_count",
        "broad_sr_count",
        "top_guide_ci_count",
        "top_guide_ci_with_sr_mapping_count",
        "top_guide_ci_matching_response_sr_count",
        "top_guide_ci_matching_non_broad_response_sr_count",
        "top_guide_ci_matching_broad_only_count",
        "no_top_actionability",
        "no_top_actionability_group",
        "triage_reason",
        "photo_description",
        "expected_corrective_direction",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return {"json": str(json_path), "md": str(md_path), "csv": str(csv_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pipeline-report", type=Path, default=DEFAULT_PIPELINE_REPORT)
    parser.add_argument("--no-top-actionability", type=Path, default=DEFAULT_NO_TOP_ACTIONABILITY)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_PREFIX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary, rows = build_rows(args)
    paths = write_reports(summary, rows, args.output_dir, args.report_prefix)
    print(json.dumps({"summary": summary, "paths": paths}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
