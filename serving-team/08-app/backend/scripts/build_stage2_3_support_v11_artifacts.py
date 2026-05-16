#!/usr/bin/env python3
"""Build narrow Stage2 taxonomy-gap support artifacts on top of v10.

The added rows are Guide-ranking support only. They do not broaden
RiskFeature normalization, SHE status, penalty exposure, asserted SR mappings,
or legal evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_stage2_3_support_v8_artifacts import (
    PROJECT_ROOT,
    BACKEND_DIR,
    SupportSeed,
    _merge,
    _read_json,
    _read_jsonl,
    _source_rows,
    _unique,
    _write_jsonl,
)


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v10.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v10.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "stage2_5_no_top_root_cause_stage2_3_support_v10_narrow2.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v11.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v11.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage2_3_support_v11_artifacts_stage2_narrow3"


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="SHARP_GLASS_MANUAL_HANDLING",
        parents=("MATERIAL_HANDLING", "CUT"),
        aliases=(
            "판유리",
            "큰 판유리",
            "유리 가장자리",
            "깨진 유리",
            "날카롭게 깨",
            "절단 보호 장갑",
        ),
        profile_alignment_aliases=(
            "날카로운 모서리",
            "수작업",
            "절단 보호용 장갑",
            "핸드패드",
            "수공구",
            "파편",
        ),
        guide_codes=("M-10-2012", "G-44-2011"),
        source_sr_ids=("SR-PPE-002", "SR-CARGO-003"),
        trigger_terms=("판유리", "큰 판유리", "유리 가장자리", "날카롭게 깨"),
        source_case_ids=("SYN-V6-0027",),
        confidence=0.65,
        rationale="Broken plate-glass manual handling has visible sharp-edge and manual-handling cues; use only for Guide ranking support.",
    ),
    SupportSeed(
        child_context="LEAD_PAINT_GRINDING_DUST",
        parents=("SANDING", "CHEMICAL_WORK", "MACHINE"),
        aliases=(
            "전동 그라인더",
            "도료 분진",
            "납 함유",
            "납 도료",
            "구 도료 분진",
        ),
        profile_alignment_aliases=(
            "휴대용 연삭기",
            "연삭기",
            "분진",
            "호흡보호구",
            "방진마스크",
            "보호안경",
        ),
        guide_codes=("B-M-39-2026", "E-G-19-2026"),
        source_sr_ids=("SR-CHEMICAL-002", "SR-CHEMICAL-006", "SR-MACHINE-010", "SR-PPE-002"),
        trigger_terms=("전동 그라인더", "도료 분진", "납 함유", "납 도료", "구 도료 분진"),
        source_case_ids=("SYN-V6-0111",),
        confidence=0.65,
        rationale="Lead-paint grinding dust has explicit grinder, dust, lead-suspect coating, and respiratory/PPE cues.",
    ),
    SupportSeed(
        child_context="ICE_PICK_FRAGMENT_EYE",
        parents=("GENERAL_WORKPLACE", "MATERIAL_HANDLING"),
        aliases=(
            "아이스픽",
            "얼음 파편",
            "얼음 덩어리",
            "대형 얼음",
        ),
        profile_alignment_aliases=("수공구", "파편", "보호안경", "해머", "칼", "타격공구"),
        guide_codes=("G-44-2011",),
        source_sr_ids=("SR-PPE-002", "SR-WORKPLACE-012"),
        trigger_terms=("아이스픽", "얼음 파편", "얼음 덩어리", "대형 얼음"),
        source_case_ids=("SYN-V6-0127",),
        confidence=0.65,
        rationale="Ice-pick fragmentation is a narrow hand-tool flying-fragment support signal for eye/PPE controls.",
    ),
    SupportSeed(
        child_context="CLIMBING_WALL_FALL_SURFACE",
        parents=("FALL", "GENERAL_WORKPLACE"),
        aliases=(
            "클라이밍 월",
            "안전 매트",
            "매트 없는 구역",
            "바닥 딱딱한 부분",
        ),
        profile_alignment_aliases=("넘어짐", "미끄러짐", "걸림", "바닥", "매트", "추락", "위험요소"),
        guide_codes=("G-11-2017", "M-59-2012"),
        source_sr_ids=("SR-FALL-001", "SR-FALL-003", "SR-FALL-006"),
        trigger_terms=("클라이밍 월", "안전 매트", "매트 없는 구역", "바닥 딱딱한 부분"),
        source_case_ids=("SYN-V6-0166",),
        confidence=0.65,
        rationale="Climbing-wall mat and floor-surface defects are visible fall-surface support cues; hold-defect cases remain out of this support row.",
    ),
    SupportSeed(
        child_context="CHAIR_STACK_MANUAL_CARRY",
        parents=("MATERIAL_HANDLING", "COLLISION"),
        aliases=(
            "무거운 의자",
            "의자 배치",
            "의자 낙하",
            "대량으로 겹쳐",
            "겹쳐 든 의자",
        ),
        profile_alignment_aliases=("인력운반", "중량물", "들기작업", "운반", "적재", "박스형 화물"),
        guide_codes=("A-G-17-2026",),
        source_sr_ids=("SR-CARGO-003", "SR-CARGO-004", "SR-WORKPLACE-012"),
        trigger_terms=("무거운 의자", "의자 배치", "의자 낙하", "겹쳐 든 의자"),
        source_case_ids=("SYN-V6-0293",),
        confidence=0.65,
        rationale="Stacked-chair manual carrying has explicit heavy/manual carry and blocked-visibility cues suitable for material-handling Guide support.",
    ),
)


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

        support_id = f"STAGE2-3-SUPPORT-V11-{seed.child_context}"
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
            "candidate_labels": ["no_top_repair", "guide_support_only", "v11_stage2_narrow_support"],
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
    taxonomy["version"] = "v11"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage2_3_support_v11": "guide_support_only_no_status_penalty_no_asserted_mapping",
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
        "# Stage2/3 Support v11 Artifact Report",
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
        "outputs": summary["outputs"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
