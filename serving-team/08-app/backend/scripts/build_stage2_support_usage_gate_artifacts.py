#!/usr/bin/env python3
"""Build narrow Stage2 support usage-gate artifacts.

The output extends the accepted v4 SituationFrame artifacts without changing
SHE status, penalty exposure, asserted SR mappings, or legal evidence.  It adds
only two kinds of support:

- profile-alignment aliases for already accepted support child contexts
- a small number of exact, photo-observable Stage2 child contexts whose Guide
  boundary is narrow enough to use as Guide ranking support
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v4.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v4.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "stage2_5_no_top_root_cause_stage3_support_alias2.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v5.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v5.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage2_support_usage_gate_artifacts_v1"


@dataclass(frozen=True)
class ExistingContextUpdate:
    child_context: str
    profile_alignment_aliases: tuple[str, ...] = ()
    extraction_aliases: tuple[str, ...] = ()
    allow_trigger_only_support: bool = False


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
    allow_trigger_only_support: bool = True


EXISTING_UPDATES: tuple[ExistingContextUpdate, ...] = (
    ExistingContextUpdate(
        child_context="AIRLESS_SPRAYER",
        profile_alignment_aliases=("분무장비", "분무공정", "도장 공정", "분무", "스프레이", "도료"),
        allow_trigger_only_support=True,
    ),
    ExistingContextUpdate(
        child_context="SPRAY_PAINTING",
        profile_alignment_aliases=("분무장비", "분무공정", "도장 공정", "분무", "스프레이", "도료"),
    ),
    ExistingContextUpdate(
        child_context="COLD_ROOM_ACCESS",
        profile_alignment_aliases=("냉동설비", "냉동 시스템", "냉장", "냉동", "저온", "비상 해제"),
        allow_trigger_only_support=True,
    ),
    ExistingContextUpdate(
        child_context="CHEMICAL_MIXING_CLEANER",
        extraction_aliases=("세제 보충", "라벨 불일치", "원래 표시와 다른 세제", "빈 용기에 다른 세제"),
        profile_alignment_aliases=("청소원", "청소", "세제", "화학물질", "라벨", "건강장해"),
        allow_trigger_only_support=True,
    ),
    ExistingContextUpdate(
        child_context="RECYCLING_SORT",
        profile_alignment_aliases=("생활폐기물", "폐기물 수거", "폐기물 처리", "선별", "압축", "압착기"),
    ),
    ExistingContextUpdate(
        child_context="LANDFILL_OPERATION",
        profile_alignment_aliases=("산업폐기물", "폐기물 처리", "매립", "폐기물", "사면"),
    ),
)


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="AUTOCLAVE_STERILIZATION",
        parents=("MACHINE", "CHEMICAL_WORK"),
        aliases=("AUTOCLAVE_STERILIZATION", "오토클레이브", "autoclave", "고압 증기 멸균기", "멸균기"),
        profile_alignment_aliases=("오토클레이브", "Autoclave", "압력용기", "고압 증기", "멸균"),
        guide_codes=("B-M-27-2026",),
        source_sr_ids=("SR-FIRE_EXPLOSION-049", "SR-CHEMICAL-011", "SR-MACHINE-003"),
        trigger_terms=("오토클레이브", "autoclave", "고압 증기 멸균기", "증기가 분출", "고온 멸균", "과압", "압력 상승"),
        work_contexts=("AUTOCLAVE_STERILIZATION",),
        accident_type="BURN",
        hazardous_agent="HEAT_COLD",
        confidence=0.66,
        rationale="Autoclave hazards have an exact photo-actionable Guide boundary and should support top procedures when the fixture names autoclave/steam/overpressure.",
    ),
    SupportSeed(
        child_context="MEDICAL_ELECTRICAL_EQUIPMENT",
        parents=("ELECTRICAL_WORK", "MACHINE"),
        aliases=("ACUPUNCTURE_WORK", "전침", "전기 침", "전극", "의료용 전기", "의료 전기 시스템"),
        profile_alignment_aliases=("의료용 전기", "의료 전기", "전극", "전원", "환자환경"),
        guide_codes=("E-134-2013",),
        source_sr_ids=("SR-ELECTRIC-024", "SR-ELECTRIC-011", "SR-ELECTRIC-008"),
        trigger_terms=("전침", "전극", "전원 ON", "전원을 차단하지 않고", "전기 침", "장비를 정지하지 않고"),
        work_contexts=("ACUPUNCTURE_WORK",),
        accident_type="ELECTRIC_SHOCK",
        hazardous_agent="ELECTRICITY",
        confidence=0.63,
        rationale="Electro-acupuncture is treated only as medical electrical-equipment Guide support, not as a new approved SHE pattern.",
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


def _source_rows(no_top_rows: list[dict[str, Any]], work_contexts: tuple[str, ...]) -> list[dict[str, Any]]:
    wanted = set(work_contexts)
    return [
        row for row in no_top_rows
        if row.get("primary_root_cause") == "stage2_taxonomy_or_normalization_gap"
        and row.get("case_type") == "positive"
        and row.get("work_context") in wanted
    ]


def _merge_terms(existing: list[str] | None, additions: tuple[str, ...] | list[str]) -> list[str]:
    return _unique([*(existing or []), *additions])


def build(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    taxonomy = _read_json(args.base_taxonomy)
    support_rows = _read_jsonl(args.base_support)
    no_top = _read_json(args.no_top_report)
    no_top_rows = no_top.get("rows") or []

    child_contexts = taxonomy.setdefault("child_contexts", {})
    parent_contexts = taxonomy.setdefault("parent_contexts", {})
    aliases = taxonomy.setdefault("aliases", {})
    support_by_id = {row.get("support_id"): row for row in support_rows if row.get("support_id")}
    audit_rows: list[dict[str, Any]] = []

    for update in EXISTING_UPDATES:
        info = child_contexts.setdefault(update.child_context, {})
        info["profile_alignment_aliases"] = _merge_terms(
            info.get("profile_alignment_aliases") or [],
            update.profile_alignment_aliases,
        )
        info["aliases"] = _merge_terms(info.get("aliases") or [], update.extraction_aliases)
        aliases[update.child_context] = _merge_terms(aliases.get(update.child_context) or [], update.extraction_aliases)
        affected_rows = 0
        for row in support_by_id.values():
            if row.get("child_context") == update.child_context and update.allow_trigger_only_support:
                row["allow_trigger_only_support"] = True
                affected_rows += 1
        audit_rows.append({
            "child_context": update.child_context,
            "kind": "existing_update",
            "extraction_aliases_added": list(update.extraction_aliases),
            "profile_alignment_aliases_added": list(update.profile_alignment_aliases),
            "allow_trigger_only_support": update.allow_trigger_only_support,
            "affected_support_rows": affected_rows,
            "source_case_ids": [],
        })

    added_support_rows = []
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

        case_ids = _unique([row.get("case_id") for row in source_rows])
        support_row = {
            "support_id": f"STAGE2-USAGE-GATE-{seed.child_context}",
            "source_candidate_id": f"STAGE2-USAGE-GATE-{seed.child_context}",
            "allowed_runtime_use": "guide_support_only",
            "child_context": seed.child_context,
            "parent_contexts": list(seed.parents),
            "accident_type": seed.accident_type,
            "hazardous_agent": seed.hazardous_agent,
            "trigger_terms": _unique([*seed.trigger_terms, *[row.get("photo_description") for row in source_rows]]),
            "require_trigger_match": True,
            "allow_trigger_only_support": seed.allow_trigger_only_support,
            "guide_codes": list(seed.guide_codes),
            "source_sr_ids": list(seed.source_sr_ids),
            "candidate_labels": ["stage2_taxonomy_gap", "guide_support_only", "usage_gate_preview"],
            "confidence": seed.confidence,
            "evidence": seed.rationale,
            "review_status": "candidate",
            "policy": "stage2_usage_gate_support_only_no_status_penalty_no_asserted_sr",
            "source_no_top_cases": case_ids,
        }
        support_by_id[support_row["support_id"]] = support_row
        added_support_rows.append(support_row)
        audit_rows.append({
            "child_context": seed.child_context,
            "kind": "new_support_seed",
            "case_count": len(source_rows),
            "source_case_ids": case_ids,
            "guide_codes": list(seed.guide_codes),
            "source_sr_ids": list(seed.source_sr_ids),
            "profile_alignment_aliases_added": list(seed.profile_alignment_aliases),
            "allow_trigger_only_support": seed.allow_trigger_only_support,
        })

    merged_support_rows = sorted(
        support_by_id.values(),
        key=lambda row: (str(row.get("child_context") or ""), str(row.get("support_id") or "")),
    )
    taxonomy["generated_at"] = generated_at
    taxonomy["version"] = "v5"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage2_support_usage_gate": {
            "runtime_use": "guide_support_only",
            "status_penalty_update": 0,
            "asserted_mapping_update": 0,
            "new_context_count": len(SUPPORT_SEEDS),
            "profile_alignment_only": True,
            "trigger_only_support": "curated_rows_only",
            "source_baseline": str(args.no_top_report),
        },
    }
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_jsonl(args.support_output, merged_support_rows)

    summary = {
        "generated_at": generated_at,
        "base_taxonomy": str(args.base_taxonomy),
        "base_support": str(args.base_support),
        "input_no_top_rows": len(no_top_rows),
        "existing_context_updates": len(EXISTING_UPDATES),
        "new_support_seed_count": len(SUPPORT_SEEDS),
        "base_support_rows": len(support_rows),
        "merged_support_rows": len(merged_support_rows),
        "added_support_rows": len(added_support_rows),
        "taxonomy_child_context_count": len(child_contexts),
        "covered_no_top_case_count": len({case for row in added_support_rows for case in row.get("source_no_top_cases") or []}),
        "allow_trigger_only_support_rows": sum(1 for row in merged_support_rows if row.get("allow_trigger_only_support")),
        "status_penalty_she_approval_asserted_mapping_update": 0,
        "outputs": {
            "taxonomy": str(args.taxonomy_output),
            "support_candidates": str(args.support_output),
        },
        "audit_rows": audit_rows,
    }
    return summary


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Stage2 Support Usage Gate Artifacts",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Existing context updates: `{summary['existing_context_updates']}`",
        f"- New support seeds: `{summary['new_support_seed_count']}`",
        f"- Added support rows: `{summary['added_support_rows']}`",
        f"- Merged support rows: `{summary['merged_support_rows']}`",
        f"- Covered NO_TOP cases by new seeds: `{summary['covered_no_top_case_count']}`",
        f"- Trigger-only support rows: `{summary['allow_trigger_only_support_rows']}`",
        "- Status/penalty/SHE approval/asserted mapping update: `0`",
        "",
        "## Audit Rows",
        "",
    ]
    for row in summary["audit_rows"]:
        lines.append(
            f"- `{row['child_context']}` {row['kind']} "
            f"cases={row.get('case_count', '-')} guides={','.join(row.get('guide_codes') or []) or '-'} "
            f"trigger_only={row.get('allow_trigger_only_support')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    fieldnames = [
        "child_context",
        "kind",
        "case_count",
        "source_case_ids",
        "guide_codes",
        "source_sr_ids",
        "profile_alignment_aliases_added",
        "extraction_aliases_added",
        "allow_trigger_only_support",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary["audit_rows"]:
            writer.writerow({
                "child_context": row.get("child_context"),
                "kind": row.get("kind"),
                "case_count": row.get("case_count"),
                "source_case_ids": ";".join(row.get("source_case_ids") or []),
                "guide_codes": ";".join(row.get("guide_codes") or []),
                "source_sr_ids": ";".join(row.get("source_sr_ids") or []),
                "profile_alignment_aliases_added": ";".join(row.get("profile_alignment_aliases_added") or []),
                "extraction_aliases_added": ";".join(row.get("extraction_aliases_added") or []),
                "allow_trigger_only_support": row.get("allow_trigger_only_support"),
            })


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
    args = parse_args()
    summary = build(args)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, summary)
    write_csv(csv_path, summary)
    print("=== Stage2 Support Usage Gate Artifact Build ===")
    for key in (
        "existing_context_updates",
        "new_support_seed_count",
        "added_support_rows",
        "merged_support_rows",
        "covered_no_top_case_count",
        "allow_trigger_only_support_rows",
        "taxonomy_child_context_count",
    ):
        print(f"{key}: {summary[key]}")
    print(f"wrote: {args.taxonomy_output}")
    print(f"wrote: {args.support_output}")
    print(f"wrote: {json_path}")
    print(f"wrote: {md_path}")
    print(f"wrote: {csv_path}")


if __name__ == "__main__":
    sys.exit(main())
