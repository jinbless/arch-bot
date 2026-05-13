#!/usr/bin/env python3
"""Build narrow Stage 2 taxonomy-gap Guide support artifacts on top of v14.

The added contexts repair cases where the synthetic Stage-1 substitute text
contains a concrete service/healthcare/lab procedure cue, but the flat
RiskFeature vocabulary collapses it to GENERAL_WORKPLACE/CHEMICAL_WORK or no
runtime catalog feature.  The rows are Guide-ranking support only: no finding
status, penalty exposure, approved SHE pattern, asserted SR mapping, or legal
evidence is changed.
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


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v14.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v14.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT
    / "pictures-json"
    / "reports"
    / "stage2_5_no_top_root_cause_stage3_sr_gap_support_v14_narrow6b.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v15.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v15.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_REPORT_PREFIX = "stage2_taxonomy_gap_support_v15_artifacts_narrow7b"


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="CARE_LONE_WORKER_NIGHT_MONITORING",
        parents=("GENERAL_WORKPLACE",),
        aliases=(
            "야간 당직 직원",
            "아동 야간 보호 모니터링",
            "입원 재활 환자 모니터링",
            "비상연락망",
            "비상 연락망",
            "2인 1조로 위기 이용자 가정 방문",
            "이용자 자해 위기",
        ),
        profile_alignment_aliases=("단독작업자", "정기 연락", "비상조치절차", "무전기", "CCTV"),
        guide_codes=("X-41-2011",),
        source_sr_ids=("SR-WORKPLACE-016", "SR-WORKPLACE-017", "SR-MGMT-005"),
        trigger_terms=(
            "야간 당직",
            "비상연락망",
            "비상 연락망",
            "2인 1조로 위기 이용자 가정 방문",
            "이용자 자해 위기",
            "입원 재활 환자 모니터링",
        ),
        source_case_ids=("SYN-V10-0098", "SYN-V10-0122", "SYN-V10-0123", "SYN-V10-0162"),
        confidence=0.66,
        rationale=(
            "Night/social-care monitoring and crisis home-visit scenes are support-only matches for lone-worker monitoring and emergency contact procedures."
        ),
    ),
    SupportSeed(
        child_context="CLIENT_AGGRESSION_EMERGENCY_RESPONSE",
        parents=("GENERAL_WORKPLACE",),
        aliases=(
            "공격성 이력",
            "공격적 행동",
            "섬망 환자",
            "비상벨 위치",
            "방어적 자리 배치",
            "안전 프로토콜",
            "2인 체계로 대응",
        ),
        profile_alignment_aliases=("폭력 리스크", "비상조치절차", "정기 연락", "CCTV"),
        guide_codes=("X-41-2011", "H-203-2018"),
        source_sr_ids=("SR-WORKPLACE-016", "SR-WORKPLACE-017", "SR-MGMT-005"),
        trigger_terms=(
            "공격성 이력",
            "공격적 행동",
            "섬망 환자",
            "비상벨",
            "방어적 자리 배치",
            "2인 체계",
            "안전 프로토콜",
        ),
        source_case_ids=("SYN-V10-0121", "SYN-V10-0277"),
        confidence=0.65,
        rationale=(
            "Client/patient aggression response with emergency alarm or two-person protocol supports worker emergency-response procedures only."
        ),
    ),
    SupportSeed(
        child_context="CHEMICAL_CLEANER_PPE_VENTILATION",
        parents=("CHEMICAL_WORK",),
        aliases=(
            "곰팡이 제거제",
            "염소 성분",
            "화장실 곰팡이 제거제",
        ),
        profile_alignment_aliases=("개인보호구", "보호장갑", "방진마스크", "호흡용보호구"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-CHEMICAL-001", "SR-CHEMICAL-006", "SR-PPE-002"),
        trigger_terms=(
            "곰팡이 제거제",
            "환기창을 열고",
            "방진마스크",
            "니트릴 장갑",
            "염소 성분",
        ),
        source_case_ids=("SYN-V10-0133",),
        confidence=0.65,
        rationale=(
            "Mold-remover cleaning with explicit ventilation and respiratory/hand PPE cues supports PPE selection/use guidance only."
        ),
    ),
    SupportSeed(
        child_context="LAB_EYEWASH_SHOWER_INSPECTION",
        parents=("CHEMICAL_WORK", "GENERAL_WORKPLACE"),
        aliases=(
            "비상 샤워기",
            "비상샤워",
            "세안기",
            "세안설비",
            "주간 작동 점검",
            "이상 없음을 기록",
            "세안기 사용법",
        ),
        profile_alignment_aliases=("세안설비", "비상 세안기", "긴급샤워기", "비상샤워", "실험실"),
        guide_codes=("C-C-16-2026", "G-82-2018"),
        source_sr_ids=("SR-HAZMAT-013", "SR-PROHIBITED_CHEM-010", "SR-WORKPLACE-016"),
        trigger_terms=(
            "비상 샤워기",
            "비상샤워",
            "세안기",
            "세안설비",
            "주간 작동 점검",
            "세안기 사용법",
        ),
        source_case_ids=("SYN-V10-0206", "SYN-V10-0326"),
        confidence=0.66,
        rationale=(
            "Laboratory eyewash/emergency-shower inspection or training has direct Guide-specific cues and is support-only for Guide ranking."
        ),
    ),
    SupportSeed(
        child_context="GLUTARALDEHYDE_DISINFECTION_PPE_VENTILATION",
        parents=("CHEMICAL_WORK", "BIOLOGICAL"),
        aliases=(
            "글루타르알데히드",
            "수술 기구 소독",
            "글루타르알데히드 사용",
        ),
        profile_alignment_aliases=("개인보호구", "보안경", "보호장갑", "방진마스크", "호흡용보호구"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-CHEMICAL-001", "SR-CHEMICAL-006", "SR-PPE-002"),
        trigger_terms=(
            "글루타르알데히드",
            "수술 기구 소독",
            "고글",
            "니트릴 장갑",
            "방진마스크",
            "환기를 확보",
        ),
        source_case_ids=("SYN-V10-0252",),
        confidence=0.65,
        rationale=(
            "Glutaraldehyde disinfection with explicit eye/hand/respiratory PPE and ventilation cues supports PPE guidance only; measurement-analysis Guides remain excluded from top photo recommendations."
        ),
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

        support_id = f"STAGE2-TAXONOMY-GAP-SUPPORT-V15-{seed.child_context}"
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
            "candidate_labels": ["stage2_taxonomy_gap", "guide_support_only", "v15_narrow_support"],
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
    taxonomy["version"] = "v15"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage2_taxonomy_gap_support_v15": "guide_support_only_no_status_penalty_no_asserted_mapping",
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
        "excluded_not_repaired_examples": [
            "SYN-V6-0163 pool-drain suction: no sufficiently aligned KOSHA field-control Guide in the current 1,038 profile set.",
            "SYN-V6-0167 climbing hold loose: no sufficiently aligned KOSHA field-control Guide; generic fall/access Guides would be misleading.",
            "SYN-V6-0307/0311/0323/0327/0328 child-public-safety cases: not repaired through worker OHS Guide ranking.",
        ],
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_lines = [
        "# Stage2 Taxonomy Gap Support v15 Artifact Report",
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
    md_lines.extend(["## Explicitly Not Repaired", ""])
    for item in summary["excluded_not_repaired_examples"]:
        md_lines.append(f"- {item}")
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
        "status_penalty_she_approval_asserted_mapping_update": summary[
            "status_penalty_she_approval_asserted_mapping_update"
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
