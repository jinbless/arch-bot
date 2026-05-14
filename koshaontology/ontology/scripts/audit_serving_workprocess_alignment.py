#!/usr/bin/env python3
"""Audit serving Guide profile primary WorkProcess links against base TTL.

This is a validation/support script, not a runtime path. It explains whether
the current OHS serving Guide profiles are ahead of the core
kosha-instances.ttl materialization, and whether missing WorkProcess IDs still
exist in the Pipe-B source JSON.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdflib import Graph, Namespace, RDF


BASELINE_ID = "context_safe_gate1"

ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_DIR = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "OHS" / "backend" / "app" / "data" / "guide_domain_profiles.json"
BASE_TTL_PATH = ONTOLOGY_DIR / "kosha-instances.ttl"
REPORT_JSON_PATH = ONTOLOGY_DIR / "serving-workprocess-alignment-context_safe_gate1.json"
REPORT_MD_PATH = ONTOLOGY_DIR / "serving-workprocess-alignment-context_safe_gate1.md"
REPORT_CSV_PATH = ONTOLOGY_DIR / "serving-workprocess-alignment-context_safe_gate1.csv"

GUIDE = Namespace("https://cashtoss.info/ontology/guide#")


def local_name(uri: Any) -> str:
    text = str(uri)
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    return text.rsplit("/", 1)[-1]


def load_profiles() -> dict[str, dict[str, Any]]:
    data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("guide_domain_profiles.json does not contain a profiles object")
    return profiles


def load_base_ttl() -> tuple[set[str], dict[str, set[str]]]:
    graph = Graph()
    graph.parse(BASE_TTL_PATH, format="turtle")
    guide_codes = {local_name(uri) for uri in graph.subjects(RDF.type, GUIDE.KoshaGuide)}
    wp_to_guides: dict[str, set[str]] = defaultdict(set)
    for guide_uri, wp_uri in graph.subject_objects(GUIDE.hasWorkProcess):
        wp_to_guides[local_name(wp_uri)].add(local_name(guide_uri))
    return guide_codes, wp_to_guides


def load_source_workprocesses(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    source_file = profile.get("source_file")
    if not source_file:
        return {}
    path = ROOT / "koshaontology" / source_file
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("workProcesses") or []
    return {
        str(row.get("identifier")): row
        for row in rows
        if row.get("identifier")
    }


def classify_link(
    guide_code: str,
    wp_id: str,
    base_guides: set[str],
    base_wp_to_guides: dict[str, set[str]],
    source_wps: dict[str, dict[str, Any]],
) -> str:
    owners = base_wp_to_guides.get(wp_id, set())
    if guide_code in owners:
        return "present_in_base_ttl_same_guide"
    if owners:
        return "present_in_base_ttl_other_guide"
    if wp_id in source_wps:
        if guide_code not in base_guides:
            return "source_present_base_guide_missing"
        return "source_present_base_wp_missing"
    if guide_code not in base_guides:
        return "missing_source_and_base_guide_missing"
    return "missing_in_source_and_base"


def build_report() -> dict[str, Any]:
    profiles = load_profiles()
    base_guides, base_wp_to_guides = load_base_ttl()

    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    guide_counts: Counter[str] = Counter()
    missing_by_guide: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    source_wp_total = 0
    source_guides_with_wp = 0
    source_file_missing = 0

    for guide_code, profile in sorted(profiles.items()):
        source_wps = load_source_workprocesses(profile)
        if source_wps:
            source_guides_with_wp += 1
            source_wp_total += len(source_wps)
        elif profile.get("source_file"):
            source_file_missing += 1

        primary_ids = [str(v) for v in (profile.get("primary_work_process_ids") or []) if v]
        primary_titles = [str(v) for v in (profile.get("primary_work_process_titles") or []) if v]
        for index, wp_id in enumerate(primary_ids, start=1):
            source_wp = source_wps.get(wp_id) or {}
            status = classify_link(guide_code, wp_id, base_guides, base_wp_to_guides, source_wps)
            status_counts[status] += 1
            if status != "present_in_base_ttl_same_guide":
                guide_counts[guide_code] += 1
            owners = sorted(base_wp_to_guides.get(wp_id, set()))
            row = {
                "baseline_id": BASELINE_ID,
                "guide_code": guide_code,
                "title": profile.get("title"),
                "profile_level": profile.get("profile_level"),
                "procedure_role": profile.get("procedure_role"),
                "photo_matchability": profile.get("photo_matchability"),
                "primary_rank": index,
                "wp_id": wp_id,
                "profile_wp_title": primary_titles[index - 1] if index - 1 < len(primary_titles) else None,
                "source_wp_title": source_wp.get("processName"),
                "source_wp_section": source_wp.get("sourceSection"),
                "base_ttl_owners": owners,
                "status": status,
            }
            rows.append(row)
            if status != "present_in_base_ttl_same_guide":
                missing_by_guide[guide_code].append(row)

    hard_statuses = {
        "present_in_base_ttl_other_guide",
        "missing_in_source_and_base",
        "missing_source_and_base_guide_missing",
    }
    source_present_statuses = {
        "source_present_base_wp_missing",
        "source_present_base_guide_missing",
    }
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_id": BASELINE_ID,
        "profile_count": len(profiles),
        "base_ttl_guide_count": len(base_guides),
        "base_ttl_workprocess_count": len(base_wp_to_guides),
        "source_guides_with_workprocesses": source_guides_with_wp,
        "source_workprocess_count_for_profiles": source_wp_total,
        "source_file_missing_count": source_file_missing,
        "primary_workprocess_link_count": len(rows),
        "status_counts": dict(status_counts),
        "affected_guide_count": len(guide_counts),
        "hard_issue_count": sum(status_counts.get(status, 0) for status in hard_statuses),
        "source_present_base_missing_count": sum(status_counts.get(status, 0) for status in source_present_statuses),
        "top_affected_guides": [
            {"guide_code": guide_code, "missing_primary_workprocess_count": count}
            for guide_code, count in guide_counts.most_common(30)
        ],
        "interpretation": (
            "source_present_base_* means the serving profile points to a WorkProcess that exists in "
            "Pipe-B ci-output but is absent from the current base kosha-instances.ttl materialization."
        ),
    }
    return {
        "summary": summary,
        "rows": rows,
        "affected_guides": {
            guide_code: items
            for guide_code, items in sorted(missing_by_guide.items())
        },
    }


def write_outputs(report: dict[str, Any]) -> None:
    REPORT_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = [
        "baseline_id",
        "guide_code",
        "title",
        "profile_level",
        "procedure_role",
        "photo_matchability",
        "primary_rank",
        "wp_id",
        "profile_wp_title",
        "source_wp_title",
        "source_wp_section",
        "base_ttl_owners",
        "status",
    ]
    with REPORT_CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in report["rows"]:
            out = dict(row)
            out["base_ttl_owners"] = "|".join(out.get("base_ttl_owners") or [])
            writer.writerow(out)

    summary = report["summary"]
    lines = [
        "# Serving WorkProcess Alignment Audit",
        "",
        f"- baseline: `{summary['baseline_id']}`",
        f"- generated_at: `{summary['generated_at']}`",
        f"- profiles: `{summary['profile_count']}`",
        f"- base TTL Guides: `{summary['base_ttl_guide_count']}`",
        f"- base TTL WorkProcesses: `{summary['base_ttl_workprocess_count']}`",
        f"- source WorkProcesses for profiles: `{summary['source_workprocess_count_for_profiles']}`",
        f"- primary WorkProcess links: `{summary['primary_workprocess_link_count']}`",
        f"- affected Guides: `{summary['affected_guide_count']}`",
        f"- hard issue count: `{summary['hard_issue_count']}`",
        f"- source-present/base-missing count: `{summary['source_present_base_missing_count']}`",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in sorted(summary["status_counts"].items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Top Affected Guides", ""])
    for item in summary["top_affected_guides"][:20]:
        lines.append(f"- `{item['guide_code']}`: {item['missing_primary_workprocess_count']}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            summary["interpretation"],
            "",
            "If most rows are `source_present_base_wp_missing` or `source_present_base_guide_missing`, "
            "the correct next step is to regenerate the core Guide A-Box from Pipe-B/PG source data. "
            "Do not hand-edit generated TTL.",
            "",
            "## Sample Rows",
            "",
        ]
    )
    sample_rows = [row for row in report["rows"] if row["status"] != "present_in_base_ttl_same_guide"][:50]
    for row in sample_rows:
        lines.append(
            f"- `{row['guide_code']}` `{row['wp_id']}` {row['status']} "
            f"/ profile title: {row.get('profile_wp_title') or '-'} / source title: {row.get('source_wp_title') or '-'}"
        )
    while lines and lines[-1] == "":
        lines.pop()
    REPORT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_outputs(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"wrote: {REPORT_JSON_PATH}")
    print(f"wrote: {REPORT_MD_PATH}")
    print(f"wrote: {REPORT_CSV_PATH}")


if __name__ == "__main__":
    main()
