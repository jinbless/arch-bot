#!/usr/bin/env python3
"""Build narrow v20 Guide-support artifacts for actionable remaining NO_TOP cases.

v20 starts from v19 and adds two high-specificity support contexts for cases
where Stage 3 already finds SRs but lacks a Guide-specific anchor.  These rows
are Guide ranking support only and must not affect status, penalty, approved
SHE, or asserted SR evidence.
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
REPORTS_DIR = PROJECT_ROOT / "pictures-json" / "reports"

DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v19.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v19.jsonl"
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v20.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v20.jsonl"
DEFAULT_REPORT_PREFIX = REPORTS_DIR / "stage3_remaining_gap_support_v20_artifacts"


NEW_CHILD_CONTEXTS: dict[str, dict[str, Any]] = {
    "GREENHOUSE_STRUCTURE_FALL": {
        "parents": ["GREENHOUSE_WORK", "FALL_PROTECTION", "GENERAL_WORKPLACE", "OTHER"],
        "aliases": [
            "GREENHOUSE_STRUCTURE_FALL",
            "비닐하우스 골조",
            "온실 골조",
            "골조 보수",
            "파이프 구조물",
            "내부 파이프 구조물",
            "파이프 구조물을 디딤대",
            "디딤대 삼아",
            "천장 부근 작업",
            "추락 방호 없음",
        ],
        "profile_alignment_aliases": [
            "작업발판",
            "이동식비계",
            "비계",
            "강관비계",
            "안전대",
            "추락방지대",
            "구명줄",
        ],
        "allowed_runtime_use": "guide_support_only",
        "candidate_count": 1,
    },
    "DRY_CLEANING_STEAM_PIPE_HOT_SURFACE": {
        "parents": ["DRY_CLEANING_SOLVENT", "HEAT_COLD", "CHEMICAL_WORK"],
        "aliases": [
            "DRY_CLEANING_STEAM_PIPE_HOT_SURFACE",
            "스팀 파이프",
            "스팀 배관",
            "보온재가 벗겨진",
            "보온재 벗겨진",
            "고온부 노출",
            "고온 파이프",
            "고온 배관",
            "팔이 닿",
            "접촉 방지 가드",
        ],
        "profile_alignment_aliases": [
            "드라이크리닝",
            "드라이클리닝",
            "세탁업",
            "유지보수",
            "건조 텀블러",
            "배관",
            "환기시스템",
        ],
        "allowed_runtime_use": "guide_support_only",
        "candidate_count": 1,
    },
}

NEW_SUPPORT_ROWS: list[dict[str, Any]] = [
    {
        "support_id": "STAGE3-REMAINING-GAP-SUPPORT-V20-GREENHOUSE_STRUCTURE_FALL",
        "source_candidate_id": "STAGE3-REMAINING-GAP-SUPPORT-V20-GREENHOUSE_STRUCTURE_FALL",
        "allowed_runtime_use": "guide_support_only",
        "child_context": "GREENHOUSE_STRUCTURE_FALL",
        "parent_contexts": ["GREENHOUSE_WORK", "FALL_PROTECTION", "GENERAL_WORKPLACE", "OTHER"],
        "accident_type": "FALL",
        "hazardous_agent": "OTHER",
        "trigger_terms": [
            "비닐하우스 골조 보수",
            "내부 파이프 구조물",
            "파이프 구조물을 디딤대",
            "디딤대 삼아",
            "천장 부근",
            "추락 방호 없음",
            "이동식 비계",
            "작업 발판",
            "안전대 착용",
        ],
        "require_trigger_match": True,
        "allow_trigger_only_support": True,
        "guide_codes": ["C-49-2012", "D-C-7-2026"],
        "source_sr_ids": ["SR-FALL-001", "SR-FALL-003", "SR-PPE-002"],
        "candidate_labels": ["stage3_remaining_gap", "guide_support_only", "v20_actionable_support"],
        "confidence": 0.67,
        "evidence": (
            "Greenhouse frame repair where a worker uses an internal pipe as a foothold "
            "with no fall protection supports fall-arrest and safe work-platform Guides only."
        ),
        "review_status": "candidate",
        "policy": "support_only_no_status_penalty_no_asserted_sr",
        "source_no_top_cases": ["SYN-V8-0022"],
    },
    {
        "support_id": "STAGE3-REMAINING-GAP-SUPPORT-V20-DRY_CLEANING_STEAM_PIPE_HOT_SURFACE",
        "source_candidate_id": "STAGE3-REMAINING-GAP-SUPPORT-V20-DRY_CLEANING_STEAM_PIPE_HOT_SURFACE",
        "allowed_runtime_use": "guide_support_only",
        "child_context": "DRY_CLEANING_STEAM_PIPE_HOT_SURFACE",
        "parent_contexts": ["DRY_CLEANING_SOLVENT", "HEAT_COLD", "CHEMICAL_WORK"],
        "accident_type": "BURN",
        "hazardous_agent": "HEAT_COLD",
        "trigger_terms": [
            "스팀 파이프 보온재",
            "보온재가 벗겨진",
            "고온부 노출",
            "고온 파이프",
            "고온 배관",
            "팔이 닿",
            "화상",
            "접촉 방지 가드",
            "보온재 즉시 교체",
        ],
        "require_trigger_match": True,
        "allow_trigger_only_support": True,
        "guide_codes": ["P-22-2012"],
        "source_sr_ids": ["SR-HEAT-012", "SR-HEAT-011", "SR-HEAT-005"],
        "candidate_labels": [
            "stage3_remaining_gap",
            "guide_support_only",
            "v20_actionable_support",
            "review_exact_guide_boundary",
        ],
        "confidence": 0.64,
        "evidence": (
            "Dry-cleaning/laundry scene with exposed hot steam piping supports the dry-cleaning "
            "process safety Guide as a narrow first-cycle field-control fallback; exact hot-surface "
            "Guide coverage should still be reviewed."
        ),
        "review_status": "candidate",
        "policy": "support_only_no_status_penalty_no_asserted_sr",
        "source_no_top_cases": ["SYN-V8-0167"],
    },
]


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

    taxonomy["version"] = "v20"
    taxonomy.setdefault("runtime_policies", {})
    taxonomy["runtime_policies"][
        "stage3_remaining_gap_support_v20"
    ] = "guide_support_only_no_status_penalty_no_asserted_mapping"

    child_contexts = taxonomy.setdefault("child_contexts", {})
    aliases = taxonomy.setdefault("aliases", {})
    for child_context, info in NEW_CHILD_CONTEXTS.items():
        child_contexts[child_context] = info
        aliases[child_context] = info["aliases"]

    existing_ids = {row.get("support_id") for row in support_rows}
    for row in NEW_SUPPORT_ROWS:
        if row["support_id"] not in existing_ids:
            support_rows.append(dict(row))

    return taxonomy, support_rows


def write_report(prefix: Path, taxonomy: dict[str, Any], support_rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    support_counts = Counter(label for row in support_rows for label in (row.get("candidate_labels") or []))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": "v20",
        "base_taxonomy": str(args.base_taxonomy.relative_to(PROJECT_ROOT)),
        "base_support": str(args.base_support.relative_to(PROJECT_ROOT)),
        "taxonomy_output": str(args.taxonomy_output.relative_to(PROJECT_ROOT)),
        "support_output": str(args.support_output.relative_to(PROJECT_ROOT)),
        "added_child_contexts": sorted(NEW_CHILD_CONTEXTS),
        "added_support_ids": [row["support_id"] for row in NEW_SUPPORT_ROWS],
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
        "# Stage3 Remaining Gap Support v20 Artifacts",
        "",
        "v20 adds two narrow support-only child contexts for remaining actionable `NO_TOP` cases.",
        "",
        "## Added Contexts",
        "",
        "- `GREENHOUSE_STRUCTURE_FALL` -> `C-49-2012`, `D-C-7-2026`",
        "- `DRY_CLEANING_STEAM_PIPE_HOT_SURFACE` -> `P-22-2012`",
        "",
        "## Guardrails",
        "",
        "- Runtime scope: Guide ranking support only",
        "- Status/penalty/SHE/SR/asserted mapping changes: `0`",
        "- Both rows require explicit trigger matches; parent-only matching remains blocked.",
        "",
        "## Rationale",
        "",
        "`SYN-V8-0022` has an explicit greenhouse-frame high-place fall hazard. "
        "The support routes to fall-arrest and work-platform Guides without approving a new SHE.",
        "",
        "`SYN-V8-0167` has an explicit dry-cleaning/laundry hot steam-pipe contact-burn cue. "
        "The support routes only to the dry-cleaning process Guide and keeps the exact hot-surface "
        "Guide boundary flagged for review.",
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
