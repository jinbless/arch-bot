#!/usr/bin/env python3
"""Triage remaining Stage 2 taxonomy/normalization NO_TOP gaps.

This script is intentionally an audit helper, not a runtime rule generator.
It classifies the remaining Stage 2 NO_TOP cases so we do not fix metrics by
adding broad aliases that later over-promote unrelated Guides.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_SOURCE = REPORTS_DIR / "stage2_5_no_top_root_cause_stage3_safe_cue_negation_fix2.json"
DEFAULT_PREFIX = REPORTS_DIR / "stage2_taxonomy_gap_triage_stage3_safe_cue_negation_fix2"


TRIAGE: dict[str, dict[str, Any]] = {
    "SYN-V10-0122": {
        "decision": "management_followup_only",
        "recommended_action": "no_photo_top_support",
        "suggested_child_context": "CRISIS_CLIENT_HOME_VISIT_TWO_PERSON",
        "candidate_guides": ["H-37-2021", "H-57-2023"],
        "reason": (
            "The observation describes two-person home visit planning and prior risk sharing. "
            "It is a management/follow-up context, not a photo-observable unsafe field control."
        ),
    },
    "SYN-V10-0288": {
        "decision": "fixture_or_safe_controlled_positive",
        "recommended_action": "keep_no_top",
        "suggested_child_context": "MEDICAL_AIR_MATTRESS_PUMP_MAINTENANCE",
        "candidate_guides": [],
        "reason": (
            "The text contains explicit safe controls: power disconnected, gloves, and a planned inspection. "
            "Adding MACHINE aliases here would over-promote general machine Guides."
        ),
    },
    "SYN-V6-0163": {
        "decision": "non_kosha_photo_top_gap",
        "recommended_action": "keep_no_top",
        "suggested_child_context": "POOL_DRAIN_SUCTION_ENTRAPMENT",
        "candidate_guides": [],
        "reason": (
            "A damaged pool drain cover is a real facility safety issue, but no photo-actionable KOSHA Guide "
            "has been identified in the current corpus."
        ),
    },
    "SYN-V6-0167": {
        "decision": "candidate_requires_guide_review",
        "recommended_action": "review_before_support_candidate",
        "suggested_child_context": "CLIMBING_WALL_LOOSE_HOLD_FALL",
        "candidate_guides": ["G-11-2017", "M-59-2012"],
        "reason": (
            "The current climbing-wall support only covers mat/floor defects. A loose hold is a distinct "
            "child context and needs Guide evidence before scoring support is added."
        ),
    },
    "SYN-V6-0172": {
        "decision": "non_kosha_photo_top_gap",
        "recommended_action": "keep_no_top",
        "suggested_child_context": "GROUP_EXERCISE_CLASS_COLLISION",
        "candidate_guides": [],
        "reason": (
            "Class participant collision is plausible safety content but currently lacks a specific KOSHA "
            "photo-actionable Guide boundary."
        ),
    },
    "SYN-V6-0243": {
        "decision": "chemical_profile_gap_needs_guide_review",
        "recommended_action": "review_before_support_candidate",
        "suggested_child_context": "DENTAL_AMALGAM_MERCURY_WASTE_VENTILATION",
        "candidate_guides": ["H-15-2021"],
        "reason": (
            "The matching Guide found so far is measurement/analysis oriented. It should not become a top "
            "photo procedure unless a field-control Guide is identified."
        ),
    },
    "SYN-V6-0307": {
        "decision": "non_kosha_photo_top_gap",
        "recommended_action": "keep_no_top",
        "suggested_child_context": "PLAYGROUND_SWING_CHAIN_FAILURE",
        "candidate_guides": [],
        "reason": (
            "Outdoor play equipment failure is not currently backed by a KOSHA Guide suitable for worker "
            "photo-based top procedure recommendation."
        ),
    },
    "SYN-V6-0311": {
        "decision": "expected_risk_outside_ohs_boundary",
        "recommended_action": "keep_no_top",
        "suggested_child_context": "DAYCARE_CLEANER_RESIDUE_CHILD_EXPOSURE",
        "candidate_guides": ["H-25-2011"],
        "reason": (
            "H-25 may support worker cleaning exposure, but the synthetic case expects child exposure after "
            "cleaning. That is outside the current OHS worker-photo Guide boundary."
        ),
    },
    "SYN-V6-0323": {
        "decision": "non_kosha_photo_top_gap",
        "recommended_action": "keep_no_top",
        "suggested_child_context": "DAYCARE_FURNITURE_TIP_OVER",
        "candidate_guides": [],
        "reason": (
            "Child furniture tip-over is a facility/childcare safety issue, but no worker OHS photo-actionable "
            "Guide boundary is available."
        ),
    },
    "SYN-V6-0327": {
        "decision": "document_or_admin_only",
        "recommended_action": "keep_no_top",
        "suggested_child_context": "DAYCARE_MEDICATION_CONSENT_ADMIN",
        "candidate_guides": [],
        "reason": (
            "Medication consent is administrative and not photo-observable field-control content for KOSHA "
            "Guide top procedures."
        ),
    },
    "SYN-V6-0328": {
        "decision": "document_or_admin_only",
        "recommended_action": "keep_no_top",
        "suggested_child_context": "DAYCARE_EMERGENCY_MEDICATION_EXPIRY",
        "candidate_guides": [],
        "reason": (
            "Expired emergency medicine stock is management/healthcare administration. It should not pull a "
            "field-control Guide to the top without a separate service-domain ontology expansion."
        ),
    },
}


def load_source(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows") or data.get("cases") or []
    return [
        row
        for row in rows
        if row.get("repair_lane") == "stage2_taxonomy_or_normalization_gap"
        or row.get("root_cause") == "stage2_taxonomy_or_normalization_gap"
        or row.get("primary_root_cause") == "stage2_taxonomy_or_normalization_gap"
    ]


def summarize_case(row: dict[str, Any]) -> str:
    for key in ("photo_description", "observation", "context_text", "description", "work_context"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    details = row.get("details")
    if isinstance(details, dict):
        for key in ("photo_description", "observation", "context_text", "description", "work_context"):
            value = details.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def build_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in source_rows:
        case_id = str(row.get("case_id") or row.get("id") or "")
        triage = TRIAGE.get(case_id)
        if not triage:
            triage = {
                "decision": "unclassified",
                "recommended_action": "manual_review_required",
                "suggested_child_context": "",
                "candidate_guides": [],
                "reason": "No curated triage entry exists for this case.",
            }
        output.append(
            {
                "case_id": case_id,
                "version": row.get("version"),
                "industry_context": row.get("industry_context"),
                "work_context": row.get("work_context"),
                "expected_primary_risk": row.get("expected_primary_risk"),
                "failure_tags": row.get("failure_tags") or row.get("stage2_failure_tags"),
                "stage2_queues": row.get("stage2_queues"),
                "frame_parent_contexts": row.get("frame_parent_contexts"),
                "profile_candidate_count": row.get("profile_candidate_count"),
                "summary_text": summarize_case(row),
                "decision": triage["decision"],
                "recommended_action": triage["recommended_action"],
                "suggested_child_context": triage["suggested_child_context"],
                "candidate_guides": triage["candidate_guides"],
                "runtime_top_support_allowed": False,
                "reason": triage["reason"],
            }
        )
    return output


def write_json(path: Path, rows: list[dict[str, Any]], source: Path) -> None:
    decision_counts = Counter(row["decision"] for row in rows)
    action_counts = Counter(row["recommended_action"] for row in rows)
    payload = {
        "baseline": "stage3_safe_cue_negation_fix2",
        "source_report": str(source.relative_to(PROJECT_ROOT)),
        "total_stage2_taxonomy_gap_cases": len(rows),
        "decision_counts": dict(sorted(decision_counts.items())),
        "recommended_action_counts": dict(sorted(action_counts.items())),
        "runtime_policy": {
            "auto_runtime_support_rows": 0,
            "status_or_penalty_changes": 0,
            "note": (
                "These cases should not be fixed by broad alias expansion. Candidate support requires "
                "Guide evidence and a photo-actionable boundary review."
            ),
        },
        "next_recommended_queue": [
            "Review Stage 3/SR remaining NO_TOP cases before adding any Stage 2 broad aliases.",
            "Only add support candidates for cases with a specific child context plus photo-actionable Guide evidence.",
        ],
        "rows": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "case_id",
        "version",
        "industry_context",
        "work_context",
        "expected_primary_risk",
        "decision",
        "recommended_action",
        "suggested_child_context",
        "candidate_guides",
        "runtime_top_support_allowed",
        "reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            record = {key: row.get(key) for key in fields}
            record["candidate_guides"] = ";".join(row.get("candidate_guides") or [])
            writer.writerow(record)


def write_md(path: Path, rows: list[dict[str, Any]], source: Path) -> None:
    decision_counts = Counter(row["decision"] for row in rows)
    action_counts = Counter(row["recommended_action"] for row in rows)
    lines = [
        "# Stage 2 Taxonomy Gap Triage - stage3_safe_cue_negation_fix2",
        "",
        f"- Source report: `{source.relative_to(PROJECT_ROOT)}`",
        f"- Cases reviewed: `{len(rows)}`",
        "- Runtime support rows added: `0`",
        "- Status/penalty/SHE/SR changes: `0`",
        "",
        "## Summary",
        "",
        "| bucket | count |",
        "|---|---:|",
    ]
    for key, count in sorted(decision_counts.items()):
        lines.append(f"| `{key}` | {count} |")
    lines.extend(["", "## Recommended Actions", "", "| action | count |", "|---|---:|"])
    for key, count in sorted(action_counts.items()):
        lines.append(f"| `{key}` | {count} |")
    lines.extend(
        [
            "",
            "## Case Triage",
            "",
            "| case | decision | action | child context | candidate guides | reason |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        guides = ", ".join(row.get("candidate_guides") or []) or "-"
        reason = str(row.get("reason") or "").replace("|", "/")
        lines.append(
            "| `{case}` | `{decision}` | `{action}` | `{child}` | {guides} | {reason} |".format(
                case=row["case_id"],
                decision=row["decision"],
                action=row["recommended_action"],
                child=row["suggested_child_context"],
                guides=guides,
                reason=reason,
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The remaining Stage 2 taxonomy gap cases are mostly outside the current worker-photo KOSHA Guide boundary, "
            "or they require Guide evidence before support scoring can be safely added. Broad parent aliases such as "
            "`MACHINE`, `CHEMICAL_WORK`, or generic service-sector terms should not be expanded from this set.",
            "",
            "Next work should move to the smaller Stage 3/SR NO_TOP queues, where several cases are more likely to have "
            "photo-actionable Guide support without weakening the status boundary.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-prefix", type=Path, default=DEFAULT_PREFIX)
    args = parser.parse_args()

    source_rows = load_source(args.source)
    rows = build_rows(source_rows)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output_prefix.with_suffix(".json"), rows, args.source)
    write_csv(args.output_prefix.with_suffix(".csv"), rows)
    write_md(args.output_prefix.with_suffix(".md"), rows, args.source)
    print(f"Wrote {len(rows)} triage rows to {args.output_prefix}.*")


if __name__ == "__main__":
    main()
