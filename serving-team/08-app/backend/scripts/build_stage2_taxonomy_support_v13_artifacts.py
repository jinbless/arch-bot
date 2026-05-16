#!/usr/bin/env python3
"""Build narrow Stage 2 taxonomy-gap support artifacts on top of v12.

The added rows repair a small set of NO_TOP cases where Stage 1 substitute text
contains a specific, photo-observable child context but the flat Stage 2 feature
codes collapse to broad or missing RiskFeature values.  These rows support
Guide/WP/CI ranking only.  They must not affect finding status, penalty
exposure, approved SHE patterns, asserted SR mappings, or legal evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_stage2_3_support_v8_artifacts import (
    BACKEND_DIR,
    PROJECT_ROOT,
    SupportSeed,
    _merge,
    _read_json,
    _read_jsonl,
    _source_rows,
    _unique,
    _write_jsonl,
)


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v12.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v12.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "stage2_5_no_top_root_cause_stage3_gap_support_v12_narrow4.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v13.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v13.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage2_taxonomy_support_v13_artifacts_narrow5"


ALIAS_REMOVALS: dict[str, tuple[str, ...]] = {
    # Too broad: matched UV/coating text that only said "long-duration work".
    "HOT_GREENHOUSE_HEAT_STRESS": ("장시간 작업",),
    # Too broad: matched crematorium burn scenes merely because heat-resistant
    # gloves were mentioned, even though the Guide is high-temperature dyeing.
    "HIGH_TEMPERATURE_DYEING_HOT_TEXTILE": ("내열 장갑",),
}


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="HIGH_PRESSURE_WATERJET_PPE_GAP",
        parents=("HIGH_PRESSURE_WASH", "PAINTING_WOODWORK", "GENERAL_WORKPLACE"),
        aliases=(
            "고압 워터젯",
            "워터젯",
            "구 도료 제거",
            "노즐이 다리 방향",
        ),
        profile_alignment_aliases=("개인보호구", "보호구 착용", "보호장화", "안전장화", "보호복"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-PPE-002", "SR-WORKPLACE-012"),
        trigger_terms=("고압 워터젯", "노즐이 다리 방향", "발 보호구 미착용", "반동"),
        source_case_ids=("SYN-V6-0112",),
        confidence=0.65,
        rationale="High-pressure waterjet paint removal has explicit recoil/nozzle and missing foot-PPE cues; support only PPE Guide ranking.",
    ),
    SupportSeed(
        child_context="UV_LAMP_EYE_PPE_GAP",
        parents=("RADIATION", "CHEMICAL_WORK"),
        aliases=(
            "UV 노광기",
            "UV 램프",
            "UV 코팅기",
            "UV 차단 안경",
            "UV 차단 보호구",
            "점등 상태",
        ),
        profile_alignment_aliases=("개인보호구", "보안경", "보호안경", "보호구 착용"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-RADIATION-001", "SR-RADIATION-002", "SR-PPE-002"),
        trigger_terms=("UV 차단 안경 없이", "UV 차단 보호구 없이", "UV 램프를 직접", "점등 상태에서 램프"),
        source_case_ids=("SYN-V6-0222", "SYN-V6-0236"),
        confidence=0.65,
        rationale="UV lamp/plate-making scenes with missing UV eye protection support only photo-actionable PPE Guide ranking.",
    ),
    SupportSeed(
        child_context="UV_COATING_OZONE_RESPIRATOR_GAP",
        parents=("CHEMICAL_WORK", "RADIATION"),
        aliases=(
            "UV 코팅기",
            "오존",
            "코팅 완료품",
            "코팅기 내부",
        ),
        profile_alignment_aliases=("호흡보호구", "방독마스크", "정화통", "국소배기"),
        guide_codes=("E-G-19-2026", "A-G-12-2026"),
        source_sr_ids=("SR-CHEMICAL-002", "SR-CHEMICAL-006", "SR-CHEMICAL-008", "SR-PPE-002"),
        trigger_terms=("오존", "방독마스크 없이", "코팅기 내부", "장시간 작업 중"),
        source_case_ids=("SYN-V6-0238",),
        confidence=0.65,
        rationale="UV coating with ozone and missing respirator has explicit respiratory-protection cues; support only Guide ranking.",
    ),
    SupportSeed(
        child_context="FORMALIN_CONTACT_PPE_GAP",
        parents=("CHEMICAL_WORK", "HEALTHCARE"),
        aliases=(
            "포르말린",
            "포름알데히드",
            "방부 처리",
            "내화학 장갑",
        ),
        profile_alignment_aliases=("개인보호구", "보호장갑", "보호복", "보안경"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-CHEMICAL-002", "SR-CHEMICAL-006", "SR-PPE-002"),
        trigger_terms=("맨손으로 포르말린", "포름알데히드 접촉", "포르말린에 노출"),
        source_case_ids=("SYN-V6-0272",),
        confidence=0.65,
        rationale="Formalin handling with bare-hand skin contact has explicit chemical PPE cues; support only PPE Guide ranking.",
    ),
    SupportSeed(
        child_context="COLD_ROOM_PPE_GAP",
        parents=("HEAT_COLD", "COLD_STORAGE"),
        aliases=(
            "급식 냉동 창고",
            "영안실 냉장 보관실",
            "냉장 보관실",
            "냉동 창고",
            "-4°C",
            "-4℃",
            "-18°C",
            "-18℃",
        ),
        profile_alignment_aliases=("개인보호구", "보호장갑", "보호복", "방한복", "방한 장갑"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-PPE-002", "SR-WORKPLACE-012"),
        trigger_terms=("방한복 없이", "방한 장갑 미착용"),
        source_case_ids=("SYN-V6-0281", "SYN-V8-0206"),
        confidence=0.65,
        rationale="Cold-room work with missing cold-protection clothing is narrow enough for PPE Guide support only.",
    ),
    SupportSeed(
        child_context="CREMATORIUM_HOT_SURFACE_PPE_GAP",
        parents=("HEAT_COLD", "BURN"),
        aliases=(
            "화장로",
            "고온 화장로",
            "화장로 문",
            "고온 유골",
            "유골 수습",
        ),
        profile_alignment_aliases=("개인보호구", "보호장갑", "보호복", "내열 장갑"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-HEAT-012", "SR-PPE-002"),
        trigger_terms=("화장로", "내열 장갑 없이", "고온 유골", "맨손"),
        source_case_ids=("SYN-V6-0286", "SYN-V6-0287"),
        confidence=0.65,
        rationale="Crematorium hot-surface or hot-bone handling with missing heat gloves supports only PPE Guide ranking.",
    ),
    SupportSeed(
        child_context="SHARP_FRAGMENT_HAND_PPE_GAP",
        parents=("CUT", "GENERAL_WORKPLACE"),
        aliases=(
            "파손된 웨이퍼",
            "웨이퍼 파편",
            "날카로운 실리콘 파편",
            "파편 수거",
            "방호 장갑",
        ),
        profile_alignment_aliases=("개인보호구", "보호장갑", "보호구 착용"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-PPE-002", "SR-WORKPLACE-012"),
        trigger_terms=("방호 장갑 없이", "맨손으로 날카로운", "실리콘 파편", "파편을 수거"),
        source_case_ids=("SYN-V7-0112",),
        confidence=0.65,
        rationale="Sharp wafer-fragment cleanup with missing hand protection supports only PPE Guide ranking.",
    ),
)


def _remove_aliases(taxonomy: dict[str, Any]) -> list[dict[str, Any]]:
    child_contexts = taxonomy.setdefault("child_contexts", {})
    aliases = taxonomy.setdefault("aliases", {})
    removed: list[dict[str, Any]] = []
    for child, terms in ALIAS_REMOVALS.items():
        term_set = set(terms)
        info = child_contexts.get(child) or {}
        for field in ("aliases", "profile_alignment_aliases"):
            before = list(info.get(field) or [])
            after = [term for term in before if term not in term_set]
            if len(after) != len(before):
                info[field] = after
                removed.append({"child_context": child, "field": field, "removed": sorted(set(before) - set(after))})
        before_aliases = list(aliases.get(child) or [])
        after_aliases = [term for term in before_aliases if term not in term_set]
        if len(after_aliases) != len(before_aliases):
            aliases[child] = after_aliases
            removed.append({"child_context": child, "field": "aliases_map", "removed": sorted(set(before_aliases) - set(after_aliases))})
    return removed


def build(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    taxonomy = _read_json(args.base_taxonomy)
    support_rows = _read_jsonl(args.base_support)
    no_top_rows = (_read_json(args.no_top_report).get("rows") or [])

    alias_cleanup_rows = _remove_aliases(taxonomy)
    child_contexts = taxonomy.setdefault("child_contexts", {})
    parent_contexts = taxonomy.setdefault("parent_contexts", {})
    aliases = taxonomy.setdefault("aliases", {})
    support_by_id = {row.get("support_id"): row for row in support_rows if row.get("support_id")}
    audit_rows: list[dict[str, Any]] = []

    for seed in SUPPORT_SEEDS:
        source_rows = _source_rows(no_top_rows, seed.source_case_ids)
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
        info["candidate_count"] = int(info.get("candidate_count") or 0) + len(source_rows)
        info["allowed_runtime_use"] = "guide_support_only"
        aliases[seed.child_context] = _merge(aliases.get(seed.child_context) or [], child_aliases)
        for parent in seed.parents:
            parent_info = parent_contexts.setdefault(parent, {})
            parent_info["allowed_runtime_use"] = "search_expansion_only"
            parent_info["candidate_count"] = int(parent_info.get("candidate_count") or 0) + len(source_rows)

        support_id = f"STAGE2-TAXONOMY-SUPPORT-V13-{seed.child_context}"
        source_case_ids = _unique([row.get("case_id") for row in source_rows] or list(seed.source_case_ids))
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
            "candidate_labels": ["no_top_repair", "guide_support_only", "v13_stage2_taxonomy_support"],
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
    taxonomy["version"] = "v13"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage2_taxonomy_support_v13": "guide_support_only_no_status_penalty_no_asserted_mapping",
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
        "alias_cleanup_rows": alias_cleanup_rows,
        "audit_rows": audit_rows,
        "status_penalty_she_approval_asserted_mapping_update": 0,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_lines = [
        "# Stage2 Taxonomy Support v13 Artifact Report",
        "",
        f"- generated_at: `{generated_at}`",
        f"- added_child_context_count: `{len(SUPPORT_SEEDS)}`",
        f"- support_candidate_count: `{len(merged_rows)}`",
        "- status/penalty/SHE approval/asserted mapping update: `0`",
        "",
        "## Alias Cleanup",
        "",
    ]
    if alias_cleanup_rows:
        for row in alias_cleanup_rows:
            md_lines.append(f"- `{row['child_context']}` `{row['field']}` removed: `{', '.join(row['removed'])}`")
    else:
        md_lines.append("- none")
    md_lines.extend(["", "## Added Contexts", ""])
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
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "child_context",
                "case_count",
                "source_case_ids",
                "guide_codes",
                "source_sr_ids",
                "trigger_terms",
                "rationale",
            ],
        )
        writer.writeheader()
        for row in audit_rows:
            writer.writerow({
                **row,
                "source_case_ids": "|".join(row["source_case_ids"]),
                "guide_codes": "|".join(row["guide_codes"]),
                "source_sr_ids": "|".join(row["source_sr_ids"]),
                "trigger_terms": "|".join(row["trigger_terms"]),
            })
    summary["outputs"] = {"json": str(json_path), "md": str(md_path), "csv": str(csv_path)}
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-taxonomy", type=Path, default=DEFAULT_BASE_TAXONOMY)
    parser.add_argument("--base-support", type=Path, default=DEFAULT_BASE_SUPPORT)
    parser.add_argument("--no-top-report", type=Path, default=DEFAULT_NO_TOP_REPORT)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_TAXONOMY_OUTPUT)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    args = parser.parse_args()
    summary = build(args)
    print(json.dumps({
        "added_child_context_count": summary["added_child_context_count"],
        "support_candidate_count": summary["support_candidate_count"],
        "alias_cleanup_rows": summary["alias_cleanup_rows"],
        "outputs": summary["outputs"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
