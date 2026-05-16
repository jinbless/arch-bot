#!/usr/bin/env python3
"""Triage Stage 5 industry-boundary gaps into structural repair queues.

This audit consumes an existing Stage 2~5 pipeline quality report. It does not
run the product pipeline and does not mutate serving artifacts. The purpose is
to separate the remaining industry-boundary gaps into:

- profile_usage_gap: the Guide may be plausible, but its usage profile evidence
  is too weak for the current scorer/evaluator.
- wrong_guide_boundary: the top Guide survived through SR/CI or generic feature
  overlap without a Guide-specific photo/context signal.
- corpus_or_followup_gap: the row appears to need a more exact corpus/taxonomy
  target, or the current Guide should be follow-up rather than photo top.
- safe_scene_overpromoted: a negative/safe scene still received a standard
  procedure and should be suppressed by safe-context or negative-boundary logic.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_SOURCE_REPORT = (
    REPORTS_DIR / "pipeline_quality_v1_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate.json"
)
DEFAULT_PROFILE_PATH = BACKEND_DIR / "app" / "data" / "guide_domain_profiles.json"
DEFAULT_PHOTO_PATH = BACKEND_DIR / "app" / "data" / "guide_photo_matchability.v1.json"

REFERENCE_ROLES = {
    "measurement_analysis",
    "test_protocol",
    "health_screening",
    "risk_method",
    "document_reference",
    "management_program",
}
SPECIAL_CORPUS_TERMS = (
    "환자",
    "고양이",
    "반려동물",
    "아동",
    "청소년",
    "호스피스",
    "정신건강",
    "재활",
    "마약성",
    "의료기기",
    "연구원",
    "대학원생",
)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _profiles(path: Path) -> dict[str, dict[str, Any]]:
    data = _load_json(path)
    return data.get("profiles") or {}


def _photo_profiles(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = _load_json(path)
    return data.get("profiles") or {}


def _record_text(record: dict[str, Any]) -> str:
    return " ".join(
        str(value)
        for value in (
            record.get("industry_context"),
            record.get("work_context"),
            record.get("photo_description"),
            record.get("expected_primary_risk"),
            record.get("expected_corrective_direction"),
            record.get("false_positive_risk"),
        )
        if value
    ).lower()


def _profile_terms(profile: dict[str, Any] | None) -> list[str]:
    if not profile:
        return []
    terms: list[str] = []
    boundary = profile.get("recommendation_boundary") or {}
    for key in (
        "intended_workplaces",
        "intended_tasks",
        "observable_required_cues",
        "negative_boundaries",
        "domain_terms",
        "visual_trigger_terms",
        "primary_work_process_ids",
    ):
        values = profile.get(key) or []
        if isinstance(values, list):
            terms.extend(str(value) for value in values if value)
    for key in ("required_context_terms", "visual_triggers", "industry_alignment", "include_when"):
        values = boundary.get(key) or []
        if isinstance(values, list):
            terms.extend(str(value) for value in values if value)
    return _unique([term for term in terms if len(term.strip()) >= 2])


def _term_hits(text: str, terms: list[str], limit: int = 8) -> list[str]:
    hits: list[str] = []
    for term in terms:
        lowered = term.lower()
        if lowered and lowered in text and term not in hits:
            hits.append(term)
        if len(hits) >= limit:
            break
    return hits


def _stage2_features(record: dict[str, Any]) -> list[str]:
    actual = (record.get("stage2_risk_feature") or {}).get("actual_features") or {}
    out: list[str] = []
    for key in ("accident_types", "hazardous_agents", "work_contexts"):
        out.extend(str(value) for value in actual.get(key) or [] if value)
    return _unique(out)


def _top_action_guide(record: dict[str, Any]) -> str | None:
    ci = ((record.get("stage5_guide_ci") or {}).get("ci") or {})
    metadata = ci.get("top_action_ci_metadata") or {}
    return metadata.get("source_guide")


def _classify(
    record: dict[str, Any],
    profile: dict[str, Any] | None,
    photo_profile: dict[str, Any] | None,
    profile_hits: list[str],
) -> tuple[str, str, str]:
    stage5 = record.get("stage5_guide_ci") or {}
    reason = str(stage5.get("guide_reason") or "")
    case_type = str(record.get("case_type") or "")
    text = _record_text(record)
    role = str((profile or {}).get("procedure_role") or "field_control")
    photo_matchability = str((photo_profile or {}).get("photo_matchability") or "photo_actionable")

    if case_type == "negative" or reason.startswith("negative case"):
        return (
            "D_safe_scene_overpromoted",
            "negative/safe row received a standard procedure",
            "tighten safe-context suppression or add Guide negative_boundaries",
        )

    if profile_hits:
        return (
            "A_profile_usage_gap",
            "row text has Guide profile terms but evaluator/scorer still marks boundary gap",
            "promote the matched terms into observable_required_cues or primary WorkProcess evidence",
        )

    if role in REFERENCE_ROLES or photo_matchability != "photo_actionable":
        return (
            "C_corpus_or_followup_gap",
            "top Guide is reference/follow-up style or not photo-actionable without explicit context",
            "keep as follow-up/NO_TOP or find a more exact photo-actionable Guide",
        )

    if any(term in text for term in SPECIAL_CORPUS_TERMS):
        return (
            "C_corpus_or_followup_gap",
            "special service/healthcare/research context lacks an exact photo-actionable Guide",
            "do not broaden generic Guide; consider corpus/taxonomy support only if exact evidence exists",
        )

    if "no usage/profile/feature hit" in reason:
        return (
            "B_wrong_guide_boundary",
            "top Guide has no Guide-specific usage/profile/feature hit",
            "strengthen negative_boundaries or require Guide-specific visual/context cues",
        )

    if "reference/method Guide" in reason:
        return (
            "C_corpus_or_followup_gap",
            "method/reference Guide lacks explicit method context",
            "move to follow-up only unless explicit document/method context is present",
        )

    return (
        "B_wrong_guide_boundary",
        "fallback classification for boundary mismatch without profile evidence",
        "inspect SR/CI source and add Guide-specific boundary constraints",
    )


def _priority(queue: str, record: dict[str, Any]) -> str:
    if queue == "D_safe_scene_overpromoted":
        return "high"
    if queue == "B_wrong_guide_boundary" and record.get("case_type") in {"positive", "ambiguous"}:
        return "high"
    if queue == "A_profile_usage_gap":
        return "medium"
    return "medium"


def _row(record: dict[str, Any], profiles: dict[str, dict[str, Any]], photo_profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    stage5 = record.get("stage5_guide_ci") or {}
    top = stage5.get("top_procedure") or {}
    ci = stage5.get("ci") or {}
    code = top.get("guide_code")
    profile = profiles.get(code or "")
    photo_profile = photo_profiles.get(code or "")
    profile_hits = _term_hits(_record_text(record), _profile_terms(profile), limit=8)
    queue, reason, action = _classify(record, profile, photo_profile, profile_hits)
    return {
        "case_id": record.get("case_id"),
        "version": record.get("version"),
        "line_no": record.get("line_no"),
        "case_type": record.get("case_type"),
        "industry_context": record.get("industry_context"),
        "work_context": record.get("work_context"),
        "top_guide": code,
        "top_guide_title": top.get("title"),
        "guide_reason": stage5.get("guide_reason"),
        "triage_queue": queue,
        "triage_reason": reason,
        "suggested_action": action,
        "priority": _priority(queue, record),
        "profile_level": (profile or {}).get("profile_level"),
        "procedure_role": (profile or {}).get("procedure_role"),
        "photo_matchability": (photo_profile or {}).get("photo_matchability"),
        "profile_term_hits": profile_hits,
        "stage2_features": _stage2_features(record),
        "ci_queues": (ci.get("queues") or []),
        "top_action_guide": _top_action_guide(record),
        "top_action_id": ((ci.get("top_action") or {}).get("action_id")),
        "photo_description": record.get("photo_description"),
        "expected_primary_risk": record.get("expected_primary_risk"),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "case_id",
        "version",
        "line_no",
        "case_type",
        "industry_context",
        "work_context",
        "top_guide",
        "top_guide_title",
        "guide_reason",
        "triage_queue",
        "triage_reason",
        "suggested_action",
        "priority",
        "profile_level",
        "procedure_role",
        "photo_matchability",
        "profile_term_hits",
        "stage2_features",
        "ci_queues",
        "top_action_guide",
        "top_action_id",
        "photo_description",
        "expected_primary_risk",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), list) else row.get(key)
                for key in fields
            })


def _write_md(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    by_queue: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_queue[row["triage_queue"]].append(row)
    lines = [
        "# Industry Boundary Gap Triage",
        "",
        f"Generated: {summary['generated_at']}",
        f"Source report: `{summary['source_report']}`",
        "",
        "## Summary",
        "",
        f"- total industry_boundary_gap rows: {summary['total_rows']}",
        f"- high priority rows: {summary['priority_counts'].get('high', 0)}",
        "",
        "## Queue Counts",
        "",
    ]
    for key, value in summary["triage_queue_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Top Guides", ""])
    for key, value in summary["top_guide_counts"][:20]:
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Suggested Repair Order", ""])
    for queue in (
        "D_safe_scene_overpromoted",
        "B_wrong_guide_boundary",
        "A_profile_usage_gap",
        "C_corpus_or_followup_gap",
    ):
        if queue not in by_queue:
            continue
        lines.append(f"### {queue}")
        lines.append("")
        guide_counts = Counter(row["top_guide"] for row in by_queue[queue])
        for guide, count in guide_counts.most_common(10):
            lines.append(f"- `{guide}`: {count}")
        lines.append("")
        for row in by_queue[queue][:8]:
            desc = str(row.get("photo_description") or "").replace("\n", " ")[:180]
            hits = ", ".join(row.get("profile_term_hits") or [])
            lines.append(
                f"- `{row['case_id']}` `{row['case_type']}` top=`{row['top_guide']}` "
                f"action=`{row.get('top_action_guide') or ''}` hits=`{hits}`"
            )
            lines.append(f"  - {desc}")
            lines.append(f"  - action: {row['suggested_action']}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument("--profile-path", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--photo-path", type=Path, default=DEFAULT_PHOTO_PATH)
    parser.add_argument("--report-prefix", default="industry_boundary_gap_triage_ci_wp_relevance8d")
    parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR)
    args = parser.parse_args()

    source = _load_json(args.source_report)
    profiles = _profiles(args.profile_path)
    photo_profiles = _photo_profiles(args.photo_path)
    records = [
        record
        for record in source.get("records") or []
        if (record.get("stage5_guide_ci") or {}).get("guide_category") == "industry_boundary_gap"
    ]
    rows = [_row(record, profiles, photo_profiles) for record in records]
    rows.sort(key=lambda row: (row["triage_queue"], row["top_guide"] or "", row["case_id"] or ""))

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_report": str(args.source_report),
        "total_rows": len(rows),
        "triage_queue_counts": dict(Counter(row["triage_queue"] for row in rows).most_common()),
        "priority_counts": dict(Counter(row["priority"] for row in rows).most_common()),
        "top_guide_counts": Counter(row["top_guide"] for row in rows).most_common(),
        "top_action_guide_counts": Counter(row["top_action_guide"] for row in rows if row.get("top_action_guide")).most_common(),
        "queue_by_top_guide": {
            str(guide): dict(Counter(row["triage_queue"] for row in rows if row.get("top_guide") == guide))
            for guide, _ in Counter(row["top_guide"] for row in rows).most_common()
        },
        "repair_policy": {
            "A_profile_usage_gap": "enrich usage profile and WorkProcess evidence only when the Guide is actually plausible",
            "B_wrong_guide_boundary": "tighten negative boundaries or require Guide-specific visual/context cues",
            "C_corpus_or_followup_gap": "prefer NO_TOP/follow-up/corpus review over broad Guide promotion",
            "D_safe_scene_overpromoted": "tighten safe/negative suppression before adding more Guide evidence",
        },
    }
    payload = {"summary": summary, "rows": rows}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.report_prefix}.json"
    csv_path = args.output_dir / f"{args.report_prefix}.csv"
    md_path = args.output_dir / f"{args.report_prefix}.md"
    _write_json(json_path, payload)
    _write_csv(csv_path, rows)
    _write_md(md_path, summary, rows)
    print(f"industry_boundary_gap rows: {len(rows)}")
    print(f"queues: {summary['triage_queue_counts']}")
    print(f"wrote: {json_path}")
    print(f"wrote: {md_path}")
    print(f"wrote: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
