#!/usr/bin/env python3
"""Suggest CI/SR mapping-review candidates for vetted CI no-action cases.

The output is review material only.  It does not write to PostgreSQL and does
not change runtime behavior, legal/asserted mappings, status, penalty, SHE
approval, or Guide profiles.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgChecklistItem, PgCiSrMapping, PgSafetyRequirement  # noqa: E402

DEFAULT_SEMANTIC_REPORT = PROJECT_ROOT / "pictures-json" / "reports" / "ci_mapping_review_semantic_ci_unrelated_action_filter1.json"
DEFAULT_PIPELINE_REPORT = PROJECT_ROOT / "pictures-json" / "reports" / "pipeline_quality_v1_v10_ci_unrelated_action_filter1.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_PREFIX = "ci_sr_mapping_candidate_review_ci_unrelated_action_filter1"

TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9_]{2,}")
STOP_TOKENS = {
    "한다",
    "있다",
    "위험",
    "작업",
    "장면",
    "직원",
    "작업자",
    "사용",
    "설치",
    "확인",
    "관리",
    "교육",
    "조치",
    "즉시",
    "필수",
    "착용",
    "금지",
    "구역",
    "안전",
    "guide",
}

MANUAL_CI_CANDIDATES: dict[str, list[str]] = {
    "SYN-V7-0312": ["CI-AG11-014"],
    "SYN-V4-0022": ["CI-AG12-007", "CI-AG12-020"],
    "SYN-V4-0027": ["CI-AG12-007"],
    "SYN-V5-0007": ["CI-AG12-008", "CI-AG12-010"],
    "SYN-V5-0021": ["CI-AG12-007", "CI-AG12-020"],
    "SYN-V5-0036": ["CI-AG12-007", "CI-AG12-020"],
    "SYN-V5-0067": ["CI-AG12-007"],
    "SYN-V8-0163": ["CI-AG12-007", "CI-AG12-020"],
    "SYN-V3-0014": ["CI-AG6-006"],
    "SYN-V5-0046": ["CI-BM37-140"],
    "SYN-V5-0116": ["CI-BM37-140"],
    "SYN-V9-0146": ["CI-C113-130"],
    "SYN-V3-0133": ["CI-D28-006", "CI-D28-007"],
    "SYN-V5-0158": ["CI-D28-006", "CI-D28-008"],
    "SYN-V4-0058": ["CI-EG1-038", "CI-EG1-043", "CI-EG1-059"],
    "SYN-V5-0047": ["CI-G11-002", "CI-G11-013", "CI-G11-015"],
    "SYN-V5-0001": ["CI-P22-027", "CI-P22-003", "CI-P22-037"],
    "SYN-V9-0056": ["CI-AG1-001", "CI-AG1-002", "CI-AG1-007", "CI-AG1-036", "CI-AG1-051"],
    "SYN-V9-0057": ["CI-G67-008", "CI-G67-009", "CI-G67-026", "CI-G67-027", "CI-G67-036"],
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
        "ci_mapping_review_semantic_",
        "pipeline_quality_v1_v10_",
        "ci_sr_mapping_candidate_review_",
    ):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def _tokens(text: str | None) -> Counter[str]:
    counter: Counter[str] = Counter()
    for token in TOKEN_RE.findall(text or ""):
        token = token.lower()
        if token in STOP_TOKENS:
            continue
        counter[token] += 1
    return counter


def _token_score(needle: Counter[str], haystack: Counter[str]) -> tuple[int, list[str]]:
    hits = sorted(set(needle) & set(haystack))
    score = sum(min(needle[token], haystack[token]) for token in hits)
    return score, hits


def _load_true_mapping_rows(path: Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    rows = [
        row
        for row in data.get("rows") or []
        if row.get("semantic_category") == "true_ci_mapping_candidate"
    ]
    return sorted(rows, key=lambda row: (str(row.get("top_guide")), str(row.get("case_id"))))


def _load_pipeline_records(path: Path) -> dict[str, dict[str, Any]]:
    data = _load_json(path)
    return {str(row.get("case_id")): row for row in data.get("records") or [] if row.get("case_id")}


def _ci_text(ci: PgChecklistItem) -> str:
    return "\n".join(
        part
        for part in [
            ci.text,
            ci.guide_context,
            ci.additional_detail,
            ci.work_process_phase,
            ci.requirement_type,
            ci.source_section,
        ]
        if part
    )


def _candidate_query_text(row: dict[str, Any], pipeline_record: dict[str, Any] | None) -> str:
    stage5 = (pipeline_record or {}).get("stage5_guide_ci") or {}
    top_procedure = stage5.get("top_procedure") or {}
    top_steps = top_procedure.get("top_steps") or []
    step_text = "\n".join(
        " ".join(str(step.get(key) or "") for key in ("title", "safety_measures"))
        for step in top_steps[:3]
    )
    return "\n".join(
        str(part or "")
        for part in [
            row.get("expected_corrective_direction"),
            row.get("expected_primary_risk"),
            row.get("photo_description"),
            row.get("review_reason"),
            step_text,
        ]
    )


def _suggested_sr_ids(pipeline_record: dict[str, Any] | None) -> list[str]:
    if not pipeline_record:
        return []
    stage5 = pipeline_record.get("stage5_guide_ci") or {}
    top_procedure = stage5.get("top_procedure") or {}
    source_sr_ids = top_procedure.get("source_sr_ids") or []
    stage4 = pipeline_record.get("stage4_sr") or {}
    non_broad = set(stage4.get("non_broad_sr_ids") or stage4.get("sr_ids") or [])
    if source_sr_ids:
        filtered = [sr_id for sr_id in source_sr_ids if sr_id in non_broad]
        return filtered or list(source_sr_ids)
    return list(non_broad)[:10]


def _sr_titles(db: Any, sr_ids: list[str]) -> dict[str, str]:
    if not sr_ids:
        return {}
    rows = db.query(PgSafetyRequirement.identifier, PgSafetyRequirement.title).filter(PgSafetyRequirement.identifier.in_(sr_ids)).all()
    return {sr_id: title for sr_id, title in rows}


def _review_rows(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    semantic_data = _load_json(args.semantic_report)
    semantic_rows = _load_true_mapping_rows(args.semantic_report)
    pipeline_by_case = _load_pipeline_records(args.pipeline_report)
    output_rows: list[dict[str, Any]] = []

    with SessionLocal() as db:
        for row in semantic_rows:
            case_id = str(row["case_id"])
            top_guide = str(row["top_guide"])
            pipeline_record = pipeline_by_case.get(case_id)
            query_text = _candidate_query_text(row, pipeline_record)
            query_tokens = _tokens(query_text)
            sr_ids = _suggested_sr_ids(pipeline_record)
            sr_title_by_id = _sr_titles(db, sr_ids)

            cis = (
                db.query(PgChecklistItem)
                .filter(PgChecklistItem.source_guide == top_guide)
                .order_by(PgChecklistItem.identifier)
                .all()
            )
            ci_ids = [ci.identifier for ci in cis]
            mappings = (
                db.query(PgCiSrMapping.ci_id, PgCiSrMapping.sr_id)
                .filter(PgCiSrMapping.ci_id.in_(ci_ids))
                .all()
                if ci_ids
                else []
            )
            mapped_by_ci: dict[str, set[str]] = defaultdict(set)
            for ci_id, sr_id in mappings:
                mapped_by_ci[ci_id].add(sr_id)

            ci_by_id = {ci.identifier: ci for ci in cis}
            ranked: list[dict[str, Any]] = []
            for ci in cis:
                score, hits = _token_score(query_tokens, _tokens(_ci_text(ci)))
                existing = sorted(mapped_by_ci.get(ci.identifier, set()))
                suggested_overlap = sorted(set(existing) & set(sr_ids))
                ranked.append(
                    {
                        "ci_id": ci.identifier,
                        "score": score,
                        "matched_terms": hits[:20],
                        "text": ci.text,
                        "guide_context": ci.guide_context,
                        "work_process_phase": ci.work_process_phase,
                        "requirement_type": ci.requirement_type,
                        "source_section": ci.source_section,
                        "existing_sr_ids": existing,
                        "existing_suggested_sr_overlap": suggested_overlap,
                        "needs_mapping_review": not suggested_overlap,
                        "selection_method": "token_score",
                    }
                )
            ranked.sort(key=lambda item: (-item["score"], item["ci_id"]))
            manual_ids = MANUAL_CI_CANDIDATES.get(case_id) or []
            manual_candidates: list[dict[str, Any]] = []
            ranked_by_id = {item["ci_id"]: item for item in ranked}
            for manual_id in manual_ids:
                item = ranked_by_id.get(manual_id)
                if not item and manual_id in ci_by_id:
                    ci = ci_by_id[manual_id]
                    existing = sorted(mapped_by_ci.get(ci.identifier, set()))
                    suggested_overlap = sorted(set(existing) & set(sr_ids))
                    item = {
                        "ci_id": ci.identifier,
                        "score": 0,
                        "matched_terms": [],
                        "text": ci.text,
                        "guide_context": ci.guide_context,
                        "work_process_phase": ci.work_process_phase,
                        "requirement_type": ci.requirement_type,
                        "source_section": ci.source_section,
                        "existing_sr_ids": existing,
                        "existing_suggested_sr_overlap": suggested_overlap,
                        "needs_mapping_review": not suggested_overlap,
                        "selection_method": "manual_review_seed",
                    }
                if item:
                    item = {**item, "selection_method": "manual_review_seed"}
                    manual_candidates.append(item)
            manual_seen = {item["ci_id"] for item in manual_candidates}
            top_candidates = manual_candidates + [item for item in ranked if item["ci_id"] not in manual_seen][: max(0, 5 - len(manual_candidates))]
            best = top_candidates[0] if top_candidates else {}
            output_rows.append(
                {
                    "case_id": case_id,
                    "industry_context": row.get("industry_context"),
                    "work_context": row.get("work_context"),
                    "top_guide": top_guide,
                    "top_guide_title": row.get("top_guide_title"),
                    "suggested_sr_ids": sr_ids,
                    "suggested_sr_titles": {sr_id: sr_title_by_id.get(sr_id, "") for sr_id in sr_ids},
                    "top_ci_candidates": top_candidates,
                    "best_ci_id": best.get("ci_id"),
                    "best_ci_score": best.get("score", 0),
                    "best_ci_selection_method": best.get("selection_method"),
                    "best_ci_needs_mapping_review": best.get("needs_mapping_review", True),
                    "best_ci_text": best.get("text"),
                    "review_reason": row.get("review_reason"),
                    "expected_corrective_direction": row.get("expected_corrective_direction"),
                    "photo_description": row.get("photo_description"),
                }
            )

    semantic_summary = semantic_data.get("summary") or {}
    baseline = semantic_summary.get("baseline") or _infer_baseline(args.semantic_report)
    summary = {
        "generated_at": _now(),
        "baseline": baseline,
        "source_semantic_report": _display_path(args.semantic_report),
        "source_pipeline_report": _display_path(args.pipeline_report),
        "review_case_count": len(output_rows),
        "cases_with_ci_candidates": sum(1 for row in output_rows if row["top_ci_candidates"]),
        "manual_seeded_case_count": sum(1 for row in output_rows if row.get("best_ci_selection_method") == "manual_review_seed"),
        "best_candidate_needs_mapping_review": sum(1 for row in output_rows if row["best_ci_needs_mapping_review"]),
        "top_guides": [
            {"key": key, "count": count}
            for key, count in Counter(row["top_guide"] for row in output_rows).most_common()
        ],
        "interpretation": (
            "These rows are candidate review material for CI/SR mapping or candidate-table enrichment. "
            "They are not asserted mappings and should be manually checked before any PG import."
        ),
    }
    return summary, output_rows


def _write_reports(summary: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path, prefix: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{prefix}.json"
    md_path = output_dir / f"{prefix}.md"
    csv_path = output_dir / f"{prefix}.csv"
    json_path.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        f"# CI/SR Mapping Candidate Review: {summary['baseline']}",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- source semantic report: `{summary['source_semantic_report']}`",
        f"- review case count: `{summary['review_case_count']}`",
        f"- cases with CI candidates: `{summary['cases_with_ci_candidates']}`",
        f"- manual seeded cases: `{summary['manual_seeded_case_count']}`",
        f"- best candidate still needs mapping review: `{summary['best_candidate_needs_mapping_review']}`",
        "",
        "## Top Guides",
        "",
    ]
    for item in summary["top_guides"]:
        md_lines.append(f"- `{item['key']}`: `{item['count']}`")
    md_lines.extend(["", "## Candidate Cases", ""])
    for row in rows:
        md_lines.append(
            f"- `{row['case_id']}` top Guide `{row['top_guide']}` best CI `{row['best_ci_id']}` "
            f"method `{row['best_ci_selection_method']}` score `{row['best_ci_score']}` "
            f"needs_mapping_review `{row['best_ci_needs_mapping_review']}`"
        )
        if row.get("best_ci_text"):
            md_lines.append(f"  - {row['best_ci_text']}")
    md_lines.extend(
        [
            "",
            "## Interpretation",
            "",
            summary["interpretation"],
            "",
            "This report is diagnostic only. It does not write to PostgreSQL or update runtime behavior.",
        ]
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    fieldnames = [
        "case_id",
        "industry_context",
        "work_context",
        "top_guide",
        "best_ci_id",
        "best_ci_score",
        "best_ci_selection_method",
        "best_ci_needs_mapping_review",
        "best_ci_text",
        "suggested_sr_ids",
        "review_reason",
        "expected_corrective_direction",
        "photo_description",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "suggested_sr_ids": ",".join(row.get("suggested_sr_ids") or [])})
    return {"json": str(json_path), "md": str(md_path), "csv": str(csv_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-report", type=Path, default=DEFAULT_SEMANTIC_REPORT)
    parser.add_argument("--pipeline-report", type=Path, default=DEFAULT_PIPELINE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_PREFIX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary, rows = _review_rows(args)
    paths = _write_reports(summary, rows, args.output_dir, args.report_prefix)
    print(json.dumps({"summary": summary, "paths": paths}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
