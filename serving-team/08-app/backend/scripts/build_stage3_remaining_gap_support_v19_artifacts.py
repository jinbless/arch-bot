#!/usr/bin/env python3
"""Build narrow v19 Guide-support artifacts for remaining NO_TOP cases.

v19 starts from v18 and adds one high-specificity support context for dropped
tools during building/facility high-place maintenance.  It is Guide ranking
support only and must not affect status, penalty, approved SHE, or asserted SRs.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parents[1]
REPORTS_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"

DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v18.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v18.jsonl"
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v19.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v19.jsonl"
DEFAULT_REPORT_PREFIX = REPORTS_DIR / "stage3_remaining_gap_support_v19_artifacts"


NEW_CHILD_CONTEXT = {
    "parents": ["MAINTENANCE_HEIGHT", "GENERAL_WORKPLACE", "OTHER"],
    "aliases": [
        "MAINTENANCE_HEIGHT_DROPPED_TOOL",
        "고소 작업 중 공구",
        "공구가 아래로 떨어질 위험",
        "낙하 공구",
        "공구 낙하",
        "낙하물 방지 조치 없음",
        "하부 인원 부상",
        "공구 안전 줄",
    ],
    "profile_alignment_aliases": [
        "건물 관리",
        "시설물 관리",
        "수공구",
        "공구",
        "고소",
        "전구 교체",
    ],
    "allowed_runtime_use": "guide_support_only",
    "candidate_count": 1,
}

NEW_SUPPORT_ROW = {
    "support_id": "STAGE3-REMAINING-GAP-SUPPORT-V19-MAINTENANCE_HEIGHT_DROPPED_TOOL",
    "source_candidate_id": "STAGE3-REMAINING-GAP-SUPPORT-V19-MAINTENANCE_HEIGHT_DROPPED_TOOL",
    "allowed_runtime_use": "guide_support_only",
    "child_context": "MAINTENANCE_HEIGHT_DROPPED_TOOL",
    "parent_contexts": ["MAINTENANCE_HEIGHT", "GENERAL_WORKPLACE", "OTHER"],
    "accident_type": "OTHER",
    "hazardous_agent": "OTHER",
    "trigger_terms": [
        "고소 작업 중 공구",
        "공구가 아래로 떨어질 위험",
        "낙하 공구",
        "낙하물 방지 조치 없음",
        "하부 인원 부상",
        "공구 안전 줄",
        "하부 접근 통제",
    ],
    "require_trigger_match": True,
    "allow_trigger_only_support": True,
    "guide_codes": ["G-60-2012", "G-44-2011"],
    "source_sr_ids": ["SR-WORKPLACE-018", "SR-FALL-001", "SR-PPE-002"],
    "candidate_labels": ["stage3_remaining_gap", "guide_support_only", "v19_narrow_support"],
    "confidence": 0.66,
    "evidence": (
        "Building/facility high-place work with an explicit dropped-tool cue supports "
        "building management and hand-tool safety Guides only."
    ),
    "review_status": "candidate",
    "policy": "support_only_no_status_penalty_no_asserted_sr",
    "source_no_top_cases": ["SYN-V8-0323"],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def build_artifacts(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    taxonomy = json.loads(args.base_taxonomy.read_text(encoding="utf-8"))
    support_rows = load_jsonl(args.base_support)

    taxonomy["version"] = "v19"
    taxonomy.setdefault("runtime_policies", {})
    taxonomy["runtime_policies"][
        "stage3_remaining_gap_support_v19"
    ] = "guide_support_only_no_status_penalty_no_asserted_mapping"
    taxonomy.setdefault("child_contexts", {})["MAINTENANCE_HEIGHT_DROPPED_TOOL"] = NEW_CHILD_CONTEXT
    taxonomy.setdefault("aliases", {})["MAINTENANCE_HEIGHT_DROPPED_TOOL"] = NEW_CHILD_CONTEXT["aliases"]

    existing_ids = {row.get("support_id") for row in support_rows}
    if NEW_SUPPORT_ROW["support_id"] not in existing_ids:
        support_rows.append(dict(NEW_SUPPORT_ROW))

    return taxonomy, support_rows


def write_report(prefix: Path, taxonomy: dict[str, Any], support_rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    support_counts = Counter(label for row in support_rows for label in (row.get("candidate_labels") or []))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": "v19",
        "base_taxonomy": str(args.base_taxonomy.relative_to(PROJECT_ROOT)),
        "base_support": str(args.base_support.relative_to(PROJECT_ROOT)),
        "taxonomy_output": str(args.taxonomy_output.relative_to(PROJECT_ROOT)),
        "support_output": str(args.support_output.relative_to(PROJECT_ROOT)),
        "added_child_contexts": ["MAINTENANCE_HEIGHT_DROPPED_TOOL"],
        "added_support_ids": [NEW_SUPPORT_ROW["support_id"]],
        "support_row_count": len(support_rows),
        "candidate_label_counts": dict(sorted(support_counts.items())),
        "policy": {
            "status_penalty_she_sr_changes": 0,
            "asserted_mapping_updates": 0,
            "runtime_use": "Guide ranking support only",
        },
    }
    prefix.with_suffix(".json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Stage3 Remaining Gap Support v19 Artifacts",
        "",
        "- Added child context: `MAINTENANCE_HEIGHT_DROPPED_TOOL`",
        f"- Added support row: `{NEW_SUPPORT_ROW['support_id']}`",
        "- Guide support: `G-60-2012`, `G-44-2011`",
        "- Runtime scope: Guide ranking support only",
        "- Status/penalty/SHE/SR/asserted mapping changes: `0`",
        "",
        "## Rationale",
        "",
        "`SYN-V8-0323` is a hospital facility-management scene where tools may fall during high-place work. "
        "The previous candidate pointed at an exterior-wall painting Guide. v19 keeps the trigger narrow and "
        "routes the support to building-management and hand-tool safety Guides instead.",
        "",
    ]
    prefix.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-taxonomy", type=Path, default=DEFAULT_BASE_TAXONOMY)
    parser.add_argument("--base-support", type=Path, default=DEFAULT_BASE_SUPPORT)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_TAXONOMY_OUTPUT)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--report-prefix", type=Path, default=DEFAULT_REPORT_PREFIX)
    args = parser.parse_args()

    taxonomy, support_rows = build_artifacts(args)
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_jsonl(args.support_output, support_rows)
    write_report(args.report_prefix, taxonomy, support_rows, args)
    print(f"Wrote {args.taxonomy_output} and {args.support_output}")


if __name__ == "__main__":
    main()
