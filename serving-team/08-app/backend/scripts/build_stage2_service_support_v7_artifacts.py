#!/usr/bin/env python3
"""Build narrow Stage2 service-support artifacts on top of SituationFrame v6.

The added contexts are Guide-ranking support only.  They do not broaden
RiskFeature normalization, SHE status, penalty exposure, asserted SR mappings,
or legal evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v6.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v6.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "stage2_5_no_top_root_cause_stage3_domain_support2_confirmation_gate2.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v7.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v7.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage2_service_support_v7_artifacts"


@dataclass(frozen=True)
class SupportSeed:
    child_context: str
    parents: tuple[str, ...]
    aliases: tuple[str, ...]
    profile_alignment_aliases: tuple[str, ...]
    guide_codes: tuple[str, ...]
    source_sr_ids: tuple[str, ...]
    trigger_terms: tuple[str, ...]
    work_contexts: tuple[str, ...]
    accident_type: str
    hazardous_agent: str
    confidence: float
    rationale: str


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="DISPLAY_ELECTRICAL_MAINTENANCE",
        parents=("ELECTRICAL_WORK", "GENERAL_WORKPLACE"),
        aliases=(
            "ELECTRICAL_HAZARD",
            "진열장 내부 조명",
            "진열장 조명",
            "조명 교체",
            "소켓",
            "통전 소켓",
            "콘센트",
            "안전 덮개",
            "전원 미차단",
            "전원을 차단하지 않고",
        ),
        profile_alignment_aliases=(
            "배선기구",
            "플러그",
            "콘센트",
            "소켓",
            "스냅스위치",
            "덮개판",
            "박스",
        ),
        guide_codes=("E-31-2014",),
        source_sr_ids=("SR-ELECTRIC-001", "SR-ELECTRIC-002", "SR-ELECTRIC-003", "SR-ELECTRIC-013"),
        trigger_terms=(
            "전원을 차단하지 않고",
            "전원 미차단",
            "소켓",
            "콘센트",
            "조명 교체",
            "안전 덮개",
            "맨손",
            "젓가락",
        ),
        work_contexts=("DISPLAY_SETUP", "ELECTRICAL_HAZARD"),
        accident_type="ELECTRIC_SHOCK",
        hazardous_agent="ELECTRICITY",
        confidence=0.67,
        rationale="Display-light and exposed outlet scenes are narrow photo-observable wiring-device maintenance contexts.",
    ),
    SupportSeed(
        child_context="BUILDING_CLEANING_FLOOR_MACHINE",
        parents=("MACHINE", "GENERAL_WORKPLACE", "CLEANING_WET"),
        aliases=(
            "FLOOR_MACHINE",
            "폴리셔",
            "왁스 폴리셔",
            "바닥 광택",
            "계단 청소기",
        ),
        profile_alignment_aliases=(
            "청소작업",
            "건물 청소",
            "바닥 광택",
            "진공청소기",
            "청소도구",
            "기계사용",
            "쓰레기 수거",
        ),
        guide_codes=("H-25-2011",),
        source_sr_ids=("SR-MACHINE-007", "SR-WORKPLACE-001", "SR-ERGONOMIC-007"),
        trigger_terms=(
            "폴리셔",
            "왁스 폴리셔",
            "계단 청소기",
            "바닥 광택",
            "반동",
            "고객",
            "안전 차단",
        ),
        work_contexts=("FLOOR_MACHINE",),
        accident_type="OTHER",
        hazardous_agent="OTHER",
        confidence=0.65,
        rationale="Floor-polisher and stair-cleaner scenes fit the building-cleaner Guide boundary as support-only procedure recommendations.",
    ),
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _unique(values: list[Any] | tuple[Any, ...]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _merge(existing: list[Any] | None, additions: tuple[Any, ...] | list[Any]) -> list[str]:
    return _unique([*(existing or []), *additions])


def _source_rows(no_top_rows: list[dict[str, Any]], work_contexts: tuple[str, ...]) -> list[dict[str, Any]]:
    wanted = set(work_contexts)
    return [
        row for row in no_top_rows
        if row.get("primary_root_cause") == "stage2_taxonomy_or_normalization_gap"
        and row.get("case_type") == "positive"
        and row.get("work_context") in wanted
    ]


def build(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    taxonomy = _read_json(args.base_taxonomy)
    support_rows = _read_jsonl(args.base_support)
    no_top_rows = (_read_json(args.no_top_report).get("rows") or [])

    child_contexts = taxonomy.setdefault("child_contexts", {})
    parent_contexts = taxonomy.setdefault("parent_contexts", {})
    aliases = taxonomy.setdefault("aliases", {})
    support_by_id = {row.get("support_id"): row for row in support_rows if row.get("support_id")}
    audit_rows: list[dict[str, Any]] = []

    for seed in SUPPORT_SEEDS:
        source_rows = _source_rows(no_top_rows, seed.work_contexts)
        child_aliases = _unique([
            seed.child_context,
            seed.child_context.replace("_", " "),
            seed.child_context.lower(),
            seed.child_context.lower().replace("_", " "),
            *seed.aliases,
        ])
        child_contexts[seed.child_context] = {
            "parents": list(seed.parents),
            "aliases": child_aliases,
            "profile_alignment_aliases": list(seed.profile_alignment_aliases),
            "candidate_count": len(source_rows),
            "allowed_runtime_use": "guide_support_only",
        }
        aliases[seed.child_context] = child_aliases
        for parent in seed.parents:
            info = parent_contexts.setdefault(parent, {})
            info["allowed_runtime_use"] = "search_expansion_only"
            info["candidate_count"] = int(info.get("candidate_count") or 0) + len(source_rows)

        source_case_ids = _unique([row.get("case_id") for row in source_rows])
        support_by_id[f"STAGE2-SERVICE-SUPPORT-{seed.child_context}"] = {
            "support_id": f"STAGE2-SERVICE-SUPPORT-{seed.child_context}",
            "source_candidate_id": f"STAGE2-SERVICE-SUPPORT-{seed.child_context}",
            "allowed_runtime_use": "guide_support_only",
            "child_context": seed.child_context,
            "parent_contexts": list(seed.parents),
            "accident_type": seed.accident_type,
            "hazardous_agent": seed.hazardous_agent,
            "trigger_terms": list(seed.trigger_terms),
            "require_trigger_match": True,
            "allow_trigger_only_support": True,
            "guide_codes": list(seed.guide_codes),
            "source_sr_ids": list(seed.source_sr_ids),
            "candidate_labels": ["stage2_taxonomy_gap", "guide_support_only", "service_context"],
            "confidence": seed.confidence,
            "evidence": seed.rationale,
            "review_status": "candidate",
            "policy": "support_only_no_status_penalty_no_asserted_sr",
            "source_no_top_cases": source_case_ids,
        }
        audit_rows.append({
            "child_context": seed.child_context,
            "case_count": len(source_rows),
            "source_case_ids": source_case_ids,
            "guide_codes": list(seed.guide_codes),
            "source_sr_ids": list(seed.source_sr_ids),
            "trigger_terms": list(seed.trigger_terms),
            "rationale": seed.rationale,
        })

    taxonomy["generated_at"] = generated_at
    taxonomy["version"] = "v7"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage2_service_support_v7": "guide_support_only_no_status_penalty_no_asserted_mapping",
    }

    merged_rows = sorted(
        support_by_id.values(),
        key=lambda row: (str(row.get("child_context") or ""), str(row.get("support_id") or "")),
    )
    args.taxonomy_output.parent.mkdir(parents=True, exist_ok=True)
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(args.support_output, merged_rows)

    summary = {
        "generated_at": generated_at,
        "base_taxonomy": str(args.base_taxonomy),
        "base_support": str(args.base_support),
        "taxonomy_output": str(args.taxonomy_output),
        "support_output": str(args.support_output),
        "added_child_context_count": len(SUPPORT_SEEDS),
        "support_candidate_count": len(merged_rows),
        "audit_rows": audit_rows,
        "status_penalty_she_approval_asserted_mapping_update": 0,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_lines = [
        "# Stage2 Service Support v7 Artifact Report",
        "",
        f"- generated_at: `{generated_at}`",
        f"- added_child_context_count: `{len(SUPPORT_SEEDS)}`",
        f"- support_candidate_count: `{len(merged_rows)}`",
        "- status/penalty/SHE approval/asserted mapping update: `0`",
        "",
        "## Added Contexts",
        "",
    ]
    for row in audit_rows:
        md_lines.extend([
            f"### {row['child_context']}",
            "",
            f"- cases: `{row['case_count']}`",
            f"- source_case_ids: `{', '.join(row['source_case_ids'])}`",
            f"- guide_codes: `{', '.join(row['guide_codes'])}`",
            f"- source_sr_ids: `{', '.join(row['source_sr_ids'])}`",
            f"- rationale: {row['rationale']}",
            "",
        ])
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["child_context", "case_count", "source_case_ids", "guide_codes", "source_sr_ids", "rationale"],
        )
        writer.writeheader()
        for row in audit_rows:
            writer.writerow({
                "child_context": row["child_context"],
                "case_count": row["case_count"],
                "source_case_ids": ",".join(row["source_case_ids"]),
                "guide_codes": ",".join(row["guide_codes"]),
                "source_sr_ids": ",".join(row["source_sr_ids"]),
                "rationale": row["rationale"],
            })
    return {"summary": summary, "outputs": {"json": json_path, "md": md_path, "csv": csv_path}}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-taxonomy", type=Path, default=DEFAULT_BASE_TAXONOMY)
    parser.add_argument("--base-support", type=Path, default=DEFAULT_BASE_SUPPORT)
    parser.add_argument("--no-top-report", type=Path, default=DEFAULT_NO_TOP_REPORT)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_TAXONOMY_OUTPUT)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    return parser.parse_args()


def main() -> None:
    result = build(parse_args())
    print(json.dumps({
        "added_child_context_count": result["summary"]["added_child_context_count"],
        "support_candidate_count": result["summary"]["support_candidate_count"],
        "outputs": {key: str(value) for key, value in result["outputs"].items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
