#!/usr/bin/env python3
"""Build narrow domain support artifacts on top of SituationFrame v5.

This artifact generation keeps the runtime boundary conservative:
- no approved SHE changes
- no asserted SR mapping changes
- no status or penalty use

The added rows only help Guide/WP/CI ranking when a photo-observable child
context and trigger phrase are both present.
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

DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v5.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v5.jsonl"
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v6.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v6.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage3_domain_support_v6_artifacts"


@dataclass(frozen=True)
class DomainSupportSeed:
    child_context: str
    parents: tuple[str, ...]
    aliases: tuple[str, ...]
    profile_alignment_aliases: tuple[str, ...]
    guide_codes: tuple[str, ...]
    source_sr_ids: tuple[str, ...]
    trigger_terms: tuple[str, ...]
    confidence: float
    rationale: str


SEEDS: tuple[DomainSupportSeed, ...] = (
    DomainSupportSeed(
        child_context="SPRAY_PAINTING",
        parents=("CHEMICAL_WORK", "PAINTING_WOODWORK"),
        aliases=(
            "스프레이 도장",
            "도장 스프레이",
            "분무도장",
            "분무 도장",
            "도장 부스",
            "도장부스",
            "스프레이건",
            "스프레이 건",
            "에어리스 스프레이",
            "도료 미스트",
            "래커 시너",
            "에폭시 도료",
        ),
        profile_alignment_aliases=(
            "도장 공정",
            "분무공정",
            "분무부스",
            "스프레이 도장",
            "도장부스",
            "인화성 용제",
            "방폭",
            "환기",
        ),
        guide_codes=("B-E-17-2026", "P-6-2011", "G-117-2014", "M-77-2011", "E-74-2011"),
        source_sr_ids=(
            "SR-FIRE_EXPLOSION-006",
            "SR-FIRE_EXPLOSION-007",
            "SR-FIRE_EXPLOSION-008",
            "SR-ELECTRIC-011",
            "SR-ELECTRIC-024",
            "SR-CHEMICAL-002",
        ),
        trigger_terms=(
            "스프레이 도장",
            "분무 도장",
            "도장 부스",
            "도장부스",
            "인화성 용제",
            "용제 증기",
            "도료 미스트",
            "비방폭",
            "방폭",
            "점화원",
            "환기 없는",
            "환기 미흡",
            "에어리스 스프레이",
            "래커 시너",
            "에폭시 도료",
        ),
        confidence=0.67,
        rationale=(
            "Spray-painting fire/explosion scenes have photo-observable booth, solvent, mist, "
            "ventilation, and ignition-source cues. Use as Guide support only."
        ),
    ),
    DomainSupportSeed(
        child_context="DRY_CLEANING_SOLVENT",
        parents=("CHEMICAL_WORK",),
        aliases=(
            "드라이클리닝",
            "드라이크리닝",
            "세탁 용제",
            "솔벤트",
            "드라이클리닝 기계",
            "드라이크리닝 기계",
            "용제 증기",
            "건조 텀블러",
        ),
        profile_alignment_aliases=(
            "드라이크리닝",
            "드라이클리닝",
            "용제",
            "솔벤트",
            "건조 텀블러",
            "환기시스템",
            "점화원",
        ),
        guide_codes=("P-22-2012",),
        source_sr_ids=(
            "SR-CHEMICAL-002",
            "SR-CHEMICAL-006",
            "SR-CHEMICAL-008",
            "SR-ELECTRIC-011",
            "SR-FIRE_EXPLOSION-008",
            "SR-FIRE_EXPLOSION-019",
        ),
        trigger_terms=(
            "용제 증기",
            "인화성 용제",
            "전기 히터",
            "점화원",
            "환기 미흡",
            "환기 없이",
            "건조 텀블러",
            "솔벤트",
        ),
        confidence=0.66,
        rationale=(
            "Dry-cleaning solvent/ignition scenes are narrow enough for P-22 Guide support "
            "when solvent-machine or solvent-vapor cues are visible."
        ),
    ),
    DomainSupportSeed(
        child_context="PESTICIDE_APPLICATION",
        parents=("CHEMICAL_WORK", "GREENHOUSE_WORK"),
        aliases=(
            "농약 살포",
            "농약방제",
            "방제작업",
            "살충제",
            "훈증제",
            "연무기",
            "비닐하우스 살포",
            "농약",
        ),
        profile_alignment_aliases=(
            "농약",
            "방제작업",
            "훈증",
            "출입제한기간",
            "보호구",
            "비닐하우스",
        ),
        guide_codes=("W-19-2012",),
        source_sr_ids=("SR-CHEMICAL-024", "SR-CHEMICAL-025", "SR-CHEMICAL-026", "SR-HAZMAT-017"),
        trigger_terms=(
            "농약 살포",
            "살충제",
            "훈증제",
            "연무기",
            "방제작업",
            "환기 없이",
            "재진입",
            "비닐하우스",
        ),
        confidence=0.66,
        rationale=(
            "Pesticide/greenhouse re-entry scenes should support W-19 only when pesticide "
            "application or fumigation cues are explicitly visible."
        ),
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


def build(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    taxonomy = _read_json(args.base_taxonomy)
    support_rows = _read_jsonl(args.base_support)

    child_contexts = taxonomy.setdefault("child_contexts", {})
    parent_contexts = taxonomy.setdefault("parent_contexts", {})
    aliases = taxonomy.setdefault("aliases", {})
    support_by_id = {row.get("support_id"): row for row in support_rows if row.get("support_id")}
    audit_rows: list[dict[str, Any]] = []

    for seed in SEEDS:
        child_aliases = _unique([
            seed.child_context,
            seed.child_context.replace("_", " "),
            seed.child_context.lower(),
            seed.child_context.lower().replace("_", " "),
            *seed.aliases,
        ])
        info = child_contexts.setdefault(seed.child_context, {})
        info["parents"] = _merge(info.get("parents") or [], seed.parents)
        info["aliases"] = _merge(info.get("aliases") or [], child_aliases)
        info["profile_alignment_aliases"] = _merge(
            info.get("profile_alignment_aliases") or [],
            seed.profile_alignment_aliases,
        )
        info["allowed_runtime_use"] = "guide_support_only"
        info["candidate_count"] = int(info.get("candidate_count") or 0) + 1
        aliases[seed.child_context] = _merge(aliases.get(seed.child_context) or [], child_aliases)
        for parent in seed.parents:
            parent_info = parent_contexts.setdefault(parent, {})
            parent_info["allowed_runtime_use"] = "search_expansion_only"
            parent_info["candidate_count"] = int(parent_info.get("candidate_count") or 0) + 1

        support_id = f"STAGE3-DOMAIN-SUPPORT-{seed.child_context}"
        support_by_id[support_id] = {
            "support_id": support_id,
            "source_candidate_id": support_id,
            "allowed_runtime_use": "guide_support_only",
            "child_context": seed.child_context,
            "parent_contexts": list(seed.parents),
            "accident_type": "OTHER",
            "hazardous_agent": "OTHER",
            "trigger_terms": list(seed.trigger_terms),
            "require_trigger_match": True,
            "allow_trigger_only_support": True,
            "guide_codes": list(seed.guide_codes),
            "source_sr_ids": list(seed.source_sr_ids),
            "candidate_labels": ["stage3_domain_gap", "guide_support_only", "v6_domain_support"],
            "confidence": seed.confidence,
            "evidence": seed.rationale,
            "review_status": "candidate",
            "policy": "domain_support_only_no_status_penalty_no_asserted_sr",
        }
        audit_rows.append({
            "support_id": support_id,
            "child_context": seed.child_context,
            "aliases_added": list(seed.aliases),
            "profile_alignment_aliases_added": list(seed.profile_alignment_aliases),
            "guide_codes": list(seed.guide_codes),
            "source_sr_ids": list(seed.source_sr_ids),
            "trigger_terms": list(seed.trigger_terms),
            "confidence": seed.confidence,
        })

    taxonomy["generated_at"] = generated_at
    taxonomy["version"] = "v6"
    taxonomy["policy"] = {
        "basis": "stage3_domain_support_v6",
        "runtime_use": "guide_support_only",
        "status_penalty_use": "forbidden",
        "asserted_mapping_updates": 0,
    }

    support_rows_out = sorted(
        support_by_id.values(),
        key=lambda row: (str(row.get("child_context") or ""), str(row.get("support_id") or "")),
    )
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(args.support_output, support_rows_out)

    summary = {
        "generated_at": generated_at,
        "base_taxonomy": str(args.base_taxonomy),
        "base_support": str(args.base_support),
        "taxonomy_output": str(args.taxonomy_output),
        "support_output": str(args.support_output),
        "base_support_count": len(support_rows),
        "output_support_count": len(support_rows_out),
        "added_support_count": len(SEEDS),
        "asserted_mapping_updates": 0,
        "status_penalty_changes": 0,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_report = args.report_dir / f"{args.report_prefix}.json"
    md_report = args.report_dir / f"{args.report_prefix}.md"
    csv_report = args.report_dir / f"{args.report_prefix}.csv"
    json_report.write_text(
        json.dumps({"summary": summary, "rows": audit_rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["support_id", "child_context", "guide_codes", "confidence"])
        writer.writeheader()
        for row in audit_rows:
            writer.writerow({
                "support_id": row["support_id"],
                "child_context": row["child_context"],
                "guide_codes": "|".join(row["guide_codes"]),
                "confidence": row["confidence"],
            })
    md_report.write_text(
        "\n".join([
            "# Stage 3 Domain Support v6 Artifact Audit",
            "",
            f"- generated_at: `{generated_at}`",
            f"- base_support_count: `{len(support_rows)}`",
            f"- output_support_count: `{len(support_rows_out)}`",
            f"- added_support_count: `{len(SEEDS)}`",
            "- asserted_mapping_updates: `0`",
            "- status_penalty_changes: `0`",
            "",
            "## Added Support Rows",
            "",
            *[
                f"- `{row['support_id']}` -> {', '.join(row['guide_codes'])}"
                for row in audit_rows
            ],
            "",
        ]),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-taxonomy", type=Path, default=DEFAULT_BASE_TAXONOMY)
    parser.add_argument("--base-support", type=Path, default=DEFAULT_BASE_SUPPORT)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_TAXONOMY_OUTPUT)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    return parser.parse_args()


def main() -> int:
    summary = build(parse_args())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
