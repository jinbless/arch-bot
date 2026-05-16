#!/usr/bin/env python3
"""Add narrow profile-alignment aliases for existing Stage3 Guide support.

The previous support artifacts already contain review-only Stage3 support
rows.  Some exact, trigger-backed rows are still blocked because their child
context codes are English while the Guide usage profiles are Korean.  This
builder adds only curated aliases that already appear in the intended Guide
profile.  It does not add support rows and does not change SHE/SR/legal data.
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


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v3.json"
DEFAULT_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v4.jsonl"
DEFAULT_PROFILES = BACKEND_DIR / "app" / "data" / "guide_domain_profiles.json"
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v4.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage3_support_alignment_aliases_v1"


# Each alias below is chosen because it is present in the intended Guide's
# usage profile and corresponds to an exact trigger-backed support case.
ALIGNMENT_ALIAS_SEEDS: dict[str, dict[str, Any]] = {
    "SHAFT_HOIST": {
        "aliases": ["호이스트", "리프트", "양중기"],
        "guide_codes": ["B-M-7-2026"],
        "reason": "shaft hoist/cage support should align to the general lifting equipment Guide profile.",
    },
    "TABLE_SAW": {
        "aliases": ["둥근톱", "톱날", "목재 둥근톱"],
        "guide_codes": ["M-6-2012", "M-179-2014"],
        "reason": "table saw support should align to woodworking circular-saw Guide profiles.",
    },
    "MEDICAL_WASTE": {
        "aliases": ["혈액 폐기물", "실험폐기물", "혈액원성 병원체"],
        "guide_codes": ["E-M-4-2025"],
        "reason": "medical waste support should align to bloodborne pathogen and laboratory waste controls.",
    },
    "COMPOUND_MIXING": {
        "aliases": ["혼합기", "덮개 인터록", "비상정지버튼"],
        "guide_codes": ["B-M-2-2025"],
        "reason": "compound mixing support should align only to mixer-machine controls, not textile scouring.",
    },
    "STERILIZATION_BLANCHING": {
        "aliases": ["식품가공", "식품기계", "식품"],
        "guide_codes": ["B-M-6-2025"],
        "reason": "retort/blanching cases are food-processing machine support, kept support-only.",
    },
    "SCALDING_DEHAIRING": {
        "aliases": ["식품가공", "식품기계", "식품"],
        "guide_codes": ["B-M-6-2025"],
        "reason": "scalding/dehairing line cases are food-processing machine support, kept support-only.",
    },
    "SLAUGHTER_LINE": {
        "aliases": ["식품가공", "식품기계", "식품"],
        "guide_codes": ["B-M-6-2025"],
        "reason": "slaughter-line machine cases are food-processing machine support, kept support-only.",
    },
}


def _unique(values: list[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _profile_text(profile: dict[str, Any]) -> str:
    bits: list[str] = [
        str(profile.get("domain_family") or ""),
        str(profile.get("usage_summary") or ""),
    ]
    for key in (
        "intended_workplaces",
        "intended_tasks",
        "observable_required_cues",
        "required_context_terms",
        "visual_triggers",
    ):
        value = profile.get(key) or []
        if isinstance(value, list):
            bits.extend(str(item) for item in value if item)
    boundary = profile.get("recommendation_boundary") or {}
    bits.extend(str(item) for item in boundary.get("include_when") or [] if item)
    return " ".join(bits).lower()


def _alias_profile_hits(aliases: list[str], guide_codes: list[str], profiles: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for guide_code in guide_codes:
        profile = profiles.get(guide_code) or {}
        text = _profile_text(profile)
        hits[guide_code] = [alias for alias in aliases if alias.lower() in text]
    return hits


def build(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    taxonomy = _read_json(args.base_taxonomy)
    support_rows = _read_jsonl(args.support)
    profiles = (_read_json(args.profiles).get("profiles") or _read_json(args.profiles))
    child_contexts = taxonomy.setdefault("child_contexts", {})
    aliases = taxonomy.setdefault("aliases", {})
    audit_rows: list[dict[str, Any]] = []

    for child_context, seed in ALIGNMENT_ALIAS_SEEDS.items():
        child_info = child_contexts.setdefault(child_context, {
            "parents": [],
            "candidate_count": 0,
            "allowed_runtime_use": "guide_support_only",
        })
        existing_profile_aliases = _unique(child_info.get("profile_alignment_aliases") or [])
        proposed_aliases = _unique(seed["aliases"])
        guide_codes = _unique(seed["guide_codes"])
        profile_hits = _alias_profile_hits(proposed_aliases, guide_codes, profiles)
        accepted_aliases = _unique([
            alias
            for alias in proposed_aliases
            if any(alias in hits for hits in profile_hits.values())
        ])
        matching_support = [
            row for row in support_rows
            if row.get("child_context") == child_context
            and any(guide_code in (row.get("guide_codes") or []) for guide_code in guide_codes)
        ]
        decision = "applied" if accepted_aliases and matching_support else "blocked"
        if decision == "applied":
            child_info["profile_alignment_aliases"] = _unique([*existing_profile_aliases, *accepted_aliases])
        audit_rows.append({
            "child_context": child_context,
            "decision": decision,
            "accepted_aliases": accepted_aliases,
            "guide_codes": guide_codes,
            "profile_hits": profile_hits,
            "support_row_count": len(matching_support),
            "source_no_top_cases": _unique([
                case_id
                for row in matching_support
                for case_id in row.get("source_no_top_cases") or []
            ]),
            "reason": seed["reason"],
        })

    taxonomy["generated_at"] = generated_at
    taxonomy["version"] = "v4"
    policy = taxonomy.setdefault("policy", {})
    policy["stage3_support_alignment_aliases"] = {
        "runtime_use": "guide_support_only",
        "status_penalty_update": 0,
        "asserted_mapping_update": 0,
        "requires_trigger_backed_support": True,
        "base_taxonomy": str(args.base_taxonomy),
        "support_artifact": str(args.support),
    }
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2), encoding="utf-8")

    applied = [row for row in audit_rows if row["decision"] == "applied"]
    summary = {
        "generated_at": generated_at,
        "policy": policy["stage3_support_alignment_aliases"],
        "seed_count": len(ALIGNMENT_ALIAS_SEEDS),
        "applied_seed_count": len(applied),
        "support_artifact_rows": len(support_rows),
        "taxonomy_child_context_count": len(child_contexts),
        "accepted_alias_count": sum(len(row["accepted_aliases"]) for row in applied),
        "affected_support_row_count": sum(row["support_row_count"] for row in applied),
        "affected_case_count": len({
            case_id
            for row in applied
            for case_id in row.get("source_no_top_cases") or []
        }),
        "outputs": {"taxonomy": str(args.taxonomy_output)},
        "audit_rows": audit_rows,
    }
    return summary


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Stage3 Support Alignment Aliases v1",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Seeds: `{summary['seed_count']}`",
        f"- Applied seeds: `{summary['applied_seed_count']}`",
        f"- Accepted aliases: `{summary['accepted_alias_count']}`",
        f"- Affected support rows: `{summary['affected_support_row_count']}`",
        f"- Affected cases: `{summary['affected_case_count']}`",
        "- Status/penalty/SHE approval/asserted mapping update: `0`",
        "",
        "## Aliases",
        "",
    ]
    for row in summary["audit_rows"]:
        lines.append(
            f"- `{row['child_context']}` {row['decision']} "
            f"aliases={','.join(row['accepted_aliases']) or '-'} "
            f"guides={','.join(row['guide_codes'])}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    fieldnames = [
        "child_context",
        "decision",
        "accepted_aliases",
        "guide_codes",
        "support_row_count",
        "source_no_top_cases",
        "reason",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary["audit_rows"]:
            writer.writerow({
                "child_context": row.get("child_context"),
                "decision": row.get("decision"),
                "accepted_aliases": ";".join(row.get("accepted_aliases") or []),
                "guide_codes": ";".join(row.get("guide_codes") or []),
                "support_row_count": row.get("support_row_count"),
                "source_no_top_cases": ";".join(row.get("source_no_top_cases") or []),
                "reason": row.get("reason"),
            })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-taxonomy", type=Path, default=DEFAULT_BASE_TAXONOMY)
    parser.add_argument("--support", type=Path, default=DEFAULT_SUPPORT)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_TAXONOMY_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build(args)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, summary)
    write_csv(csv_path, summary)
    print("=== Stage3 Support Alignment Aliases ===")
    print(f"seed_count: {summary['seed_count']}")
    print(f"applied_seed_count: {summary['applied_seed_count']}")
    print(f"accepted_alias_count: {summary['accepted_alias_count']}")
    print(f"affected_support_row_count: {summary['affected_support_row_count']}")
    print(f"affected_case_count: {summary['affected_case_count']}")
    print(f"taxonomy_child_context_count: {summary['taxonomy_child_context_count']}")
    print(f"wrote: {args.taxonomy_output}")
    print(f"wrote: {json_path}")
    print(f"wrote: {md_path}")
    print(f"wrote: {csv_path}")


if __name__ == "__main__":
    sys.exit(main())
