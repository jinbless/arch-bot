#!/usr/bin/env python3
"""Build narrow v17 Guide-support artifacts for remaining NO_TOP cases.

v17 continues the SituationFrame strategy: add concrete child contexts and
trigger-backed Guide support rows only for photo-visible work situations.  The
rows remain Guide-ranking support only and must not change SHE status, penalty
exposure, approved SHE patterns, asserted SR mappings, or legal SR evidence.
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


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v16c.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v16c.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT
    / "pictures-json"
    / "reports"
    / "stage2_5_no_top_root_cause_stage3_remaining_gap_support_v16c_narrow8c.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v17b.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v17b.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_REPORT_PREFIX = "stage3_remaining_gap_support_v17b_artifacts_narrow9b"


PROFILE_ALIGNMENT_OVERRIDES: dict[str, tuple[str, ...]] = {
    "NEEDLE_BROKEN": (
        "회전기계",
        "가드",
        "방호설비",
        "보안경",
        "보호구",
        "바늘 파편",
    ),
    "BINDING_MACHINE": (
        "인쇄기",
        "제본기",
        "실린더",
        "연동식 가드",
        "잠금",
        "세척액",
    ),
}


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="HAIR_CHEMICAL_EYE_EXPOSURE",
        parents=("CHEMICAL_WORK", "PERSONAL_SERVICE"),
        aliases=("염색약 눈", "염색약 눈 방향", "고객 눈 근접", "눈 보호 없음", "즉시 세안"),
        profile_alignment_aliases=("개인보호구", "보안경", "보호안경", "세안설비", "비상 세안기", "부식성"),
        guide_codes=("A-G-12-2026", "C-C-16-2026"),
        source_sr_ids=("SR-CHEMICAL-012", "SR-PPE-002", "SR-HAZMAT-013"),
        trigger_terms=("염색약 눈 방향", "눈 보호 없음", "고객 눈 근접", "즉시 세안"),
        source_case_ids=("SYN-V4-0022",),
        confidence=0.66,
        rationale="Hair-dye flow toward the eye with no eye protection is a narrow PPE/eyewash support signal.",
    ),
    SupportSeed(
        child_context="HAIR_WASH_NECK_ERGONOMICS",
        parents=("ERGONOMIC", "PERSONAL_SERVICE"),
        aliases=("목 과굴곡", "세발대", "세발대 가장자리", "장시간 유지", "경추 압박"),
        profile_alignment_aliases=("근골격계", "작업자세", "부적절한 자세", "작업환경개선", "인체공학"),
        guide_codes=("E-G-1-2025", "E-G-4-2025"),
        source_sr_ids=("SR-ERGONOMIC-001", "SR-ERGONOMIC-003", "SR-ERGONOMIC-005"),
        trigger_terms=("목 과굴곡", "세발대 가장자리", "장시간 유지"),
        source_case_ids=("SYN-V4-0037",),
        confidence=0.65,
        rationale="Hair-wash neck over-flexion is retained as ergonomic Guide support only.",
    ),
    SupportSeed(
        child_context="CASHIER_PROLONGED_STANDING",
        parents=("ERGONOMIC", "GENERAL_WORKPLACE"),
        aliases=("계산대 장시간 기립", "장시간 기립 근무", "딱딱한 바닥", "피로 자세", "발 받침대"),
        profile_alignment_aliases=("근골격계", "작업자세", "부적절한 자세", "피로예방매트", "발받침대"),
        guide_codes=("E-G-1-2025", "E-G-4-2025"),
        source_sr_ids=("SR-ERGONOMIC-001", "SR-ERGONOMIC-003", "SR-ERGONOMIC-005"),
        trigger_terms=("장시간 기립 근무", "딱딱한 바닥", "피로 자세"),
        source_case_ids=("SYN-V4-0058",),
        confidence=0.65,
        rationale="Cashier prolonged standing on hard flooring is narrow ergonomic support for MSD prevention Guides.",
    ),
    SupportSeed(
        child_context="PET_GROOMING_BITE",
        parents=("ANIMAL_HANDLING", "PERSONAL_SERVICE"),
        aliases=("개 교상", "고양이 교상", "손 물림", "보호 장갑 미착용", "머즐", "과도 보정"),
        profile_alignment_aliases=("동물 접촉", "동물 이동", "울타리", "다트건", "동물", "교상"),
        guide_codes=("G-70-2011", "A-G-12-2026"),
        source_sr_ids=("SR-PATHOGEN-006", "SR-WORKPLACE-010", "SR-PPE-002"),
        trigger_terms=("교상 발생", "손 물림", "보호 장갑 미착용", "고양이 과도 보정"),
        source_case_ids=("SYN-V5-0061", "SYN-V5-0068"),
        confidence=0.64,
        rationale="Pet grooming bite scenes are animal-contact support only; they do not create an approved animal SHE.",
    ),
    SupportSeed(
        child_context="PET_GROOMING_TABLE_FALL",
        parents=("ANIMAL_HANDLING", "FALL", "PERSONAL_SERVICE"),
        aliases=("미용 테이블", "개 고리 묶임", "테이블 가장자리", "미용사 자리 비움", "목 조임"),
        profile_alignment_aliases=("동물 접촉", "동물 이동", "울타리", "동물", "추락", "작업대"),
        guide_codes=("G-70-2011",),
        source_sr_ids=("SR-FALL-001", "SR-WORKPLACE-010"),
        trigger_terms=("개 고리 묶임", "미용사 자리 비움", "테이블 가장자리 접근"),
        source_case_ids=("SYN-V5-0062",),
        confidence=0.63,
        rationale="Pet grooming table fall/strangulation cues are handled as animal-handling Guide support only.",
    ),
    SupportSeed(
        child_context="BINDING_MACHINE_LOTO_GAP",
        parents=("MACHINE", "PRINTING"),
        aliases=("침 박음 장치", "제본기", "제본 기계", "손 삽입 시도", "LOTO 미적용"),
        profile_alignment_aliases=("인쇄기", "제본기", "연동식 가드", "잠금", "회전말림방호", "저속 이송"),
        guide_codes=("M-193-2020", "B-M-37-2026"),
        source_sr_ids=("SR-MACHINE-002", "SR-MACHINE-010", "SR-MACHINE-023"),
        trigger_terms=("침 박음 장치 가동", "손 삽입 시도", "LOTO 미적용"),
        source_case_ids=("SYN-V8-0286",),
        confidence=0.66,
        rationale="Binding-machine jam removal without LOTO is printing/rotating-machine Guide support only.",
    ),
    SupportSeed(
        child_context="TRUCK_COUPLING_PRETRIP_CHECK",
        parents=("VEHICLE", "MATERIAL_HANDLING"),
        aliases=("트레일러 결합", "킹핀 잠금", "안전핀", "에어 라인", "연결 상태 미점검"),
        profile_alignment_aliases=("운송용 차량", "차량", "트레일러", "적재칸", "테일 리프트"),
        guide_codes=("G-101-2013",),
        source_sr_ids=("SR-VEHICLE-017", "SR-CARGO-010"),
        trigger_terms=("킹핀 잠금", "에어 라인 연결", "트레일러 분리", "연결 상태 미점검"),
        source_case_ids=("SYN-V8-0133",),
        confidence=0.64,
        rationale="Truck coupling pre-trip failure is kept as transport-vehicle Guide support only.",
    ),
    SupportSeed(
        child_context="STEAM_GUN_FACE_BURN_PPE_GAP",
        parents=("HEAT_COLD", "CHEMICAL_WORK"),
        aliases=("스팀 건", "동료 얼굴", "고온 증기 분사", "안면 보호 없음", "스팀 방향"),
        profile_alignment_aliases=("개인보호구", "보안경", "안면 보호대", "보호구 착용", "고열작업"),
        guide_codes=("A-G-12-2026", "E-G-22-2026"),
        source_sr_ids=("SR-HEAT-012", "SR-PPE-002"),
        trigger_terms=("스팀 건 방향 동료 얼굴", "고온 증기 분사", "안면 보호 없음"),
        source_case_ids=("SYN-V8-0168",),
        confidence=0.64,
        rationale="Steam-gun face exposure with no face protection is PPE/heat Guide support only.",
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

    for child_context, profile_aliases in PROFILE_ALIGNMENT_OVERRIDES.items():
        info = child_contexts.setdefault(child_context, {})
        info["profile_alignment_aliases"] = _merge(info.get("profile_alignment_aliases") or [], profile_aliases)

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

        support_id = f"STAGE3-REMAINING-GAP-SUPPORT-V17B-{seed.child_context}"
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
            "candidate_labels": ["stage3_remaining_gap", "guide_support_only", "v17b_narrow_support"],
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
    taxonomy["version"] = "v17b"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage3_remaining_gap_support_v17b": "guide_support_only_no_status_penalty_no_asserted_mapping",
    }

    support_rows_out = sorted(support_by_id.values(), key=lambda row: str(row.get("support_id") or ""))
    args.taxonomy_output.parent.mkdir(parents=True, exist_ok=True)
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(args.support_output, support_rows_out)

    summary = {
        "generated_at": generated_at,
        "version": "v17b",
        "base_taxonomy": str(args.base_taxonomy),
        "base_support": str(args.base_support),
        "no_top_report": str(args.no_top_report),
        "taxonomy_output": str(args.taxonomy_output),
        "support_output": str(args.support_output),
        "support_rows_total": len(support_rows_out),
        "added_support_rows": len(SUPPORT_SEEDS),
        "profile_alignment_overrides": sorted(PROFILE_ALIGNMENT_OVERRIDES),
        "asserted_mapping_updates": 0,
        "status_penalty_changes": 0,
        "audit_rows": audit_rows,
    }

    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps({"summary": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_lines = [
        "# Stage3 Remaining Gap Support v17b Artifacts",
        "",
        f"generated_at: {generated_at}",
        f"base_taxonomy: `{args.base_taxonomy}`",
        f"base_support: `{args.base_support}`",
        f"taxonomy_output: `{args.taxonomy_output}`",
        f"support_output: `{args.support_output}`",
        f"support_rows_total: {len(support_rows_out)}",
        f"added_support_rows: {len(SUPPORT_SEEDS)}",
        "asserted_mapping_updates: 0",
        "status_penalty_changes: 0",
        "",
        "## Added Rows",
        "",
    ]
    for row in audit_rows:
        md_lines.append(
            f"- `{row['child_context']}` cases={row['case_count']} guides={', '.join(row['guide_codes'])} "
            f"source_cases={', '.join(row['source_case_ids'])}"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=[
            "child_context",
            "case_count",
            "source_case_ids",
            "guide_codes",
            "source_sr_ids",
            "trigger_terms",
            "rationale",
        ])
        writer.writeheader()
        for row in audit_rows:
            writer.writerow({
                "child_context": row["child_context"],
                "case_count": row["case_count"],
                "source_case_ids": "|".join(row["source_case_ids"]),
                "guide_codes": "|".join(row["guide_codes"]),
                "source_sr_ids": "|".join(row["source_sr_ids"]),
                "trigger_terms": "|".join(row["trigger_terms"]),
                "rationale": row["rationale"],
            })
    return summary


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
    summary = build(parse_args())
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
