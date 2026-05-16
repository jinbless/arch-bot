#!/usr/bin/env python3
"""Build narrow Stage 3 SHE-to-SR gap support artifacts on top of v13.

The added contexts are Guide-ranking support only.  They repair cases where the
photo-observation substitute text contains a concrete work situation, but the
approved SHE/SR path has no reviewed serving edge yet.  These rows must not
affect finding status, penalty exposure, approved SHE patterns, asserted SR
mappings, or legal evidence.
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


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v13.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v13.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT
    / "data-team/05-enrichment/eval-data"
    / "reports"
    / "stage2_5_no_top_root_cause_stage2_taxonomy_support_v13_narrow5.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v14.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v14.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage3_sr_gap_support_v14_artifacts_narrow6"


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="INDOOR_WELDING_FUME_RESPIRATOR_GAP",
        parents=("WELDING", "CHEMICAL_WORK"),
        aliases=("실내 용접", "용접 흄", "환기팬 미작동", "방진마스크(일반)", "망간", "크롬"),
        profile_alignment_aliases=("수동 금속 아크 용접", "용접 흄", "국소배기", "호흡보호구", "방진마스크"),
        guide_codes=("M-67-2012", "M-74-2011", "E-G-19-2026"),
        source_sr_ids=("SR-CHEMICAL-002", "SR-CHEMICAL-006", "SR-CHEMICAL-008", "SR-PPE-002"),
        trigger_terms=("환기팬이 미작동", "방진마스크(일반)", "흄이 천장 부근", "가시적으로 축적"),
        source_case_ids=("SYN-V7-0016",),
        confidence=0.66,
        rationale="Indoor welding fume with failed ventilation and inadequate respirator is exact Guide support for welding fume/respiratory protection.",
    ),
    SupportSeed(
        child_context="SHARP_METAL_EDGE_HANDLING_PPE_GAP",
        parents=("CUT", "MATERIAL_HANDLING"),
        aliases=("날카로운 절단면", "금속 판재", "날카로운 모서리", "맨손으로 들고", "절상 위험"),
        profile_alignment_aliases=("날카로운 모서리", "절단 보호용 장갑", "수작업", "보호장갑"),
        guide_codes=("M-10-2012", "A-G-12-2026"),
        source_sr_ids=("SR-WORKPLACE-018", "SR-PPE-002"),
        trigger_terms=("날카로운 절단면", "금속 판재", "맨손", "절상 위험", "절단 방지 장갑"),
        source_case_ids=("SYN-V7-0021",),
        confidence=0.66,
        rationale="Sharp metal plate handling with bare hands has a concrete edge-cut cue and supports sharp-edge/PPE Guides only.",
    ),
    SupportSeed(
        child_context="REFLOW_OVEN_RESIDUAL_HEAT_PPE_GAP",
        parents=("HEAT_COLD", "MACHINE", "ELECTRICAL_WORK"),
        aliases=("리플로우 오븐", "reflow oven", "오븐 잔열", "냉각되지 않은 상태", "맨손으로 내부 청소"),
        profile_alignment_aliases=("개인보호구", "보호장갑", "보호구 착용", "내열 장갑"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-HEAT-012", "SR-PPE-002"),
        trigger_terms=("리플로우 오븐", "오븐 잔열", "맨손", "냉각 완료", "방열 장갑"),
        source_case_ids=("SYN-V7-0103",),
        confidence=0.65,
        rationale="Residual-heat reflow-oven cleaning lacks an exact machine Guide, so only the PPE Guide can be used as support.",
    ),
    SupportSeed(
        child_context="WAFER_CARRIER_STAIR_MANUAL_HANDLING",
        parents=("MATERIAL_HANDLING", "LADDER"),
        aliases=("웨이퍼 캐리어", "FOUP", "한 손으로 잡고", "클린룸 계단", "계단을 오르는"),
        profile_alignment_aliases=("인력운반작업", "계단", "통로", "중량물", "운반"),
        guide_codes=("A-G-17-2026", "A-G-2-2025"),
        source_sr_ids=("SR-WORKPLACE-010", "SR-WORKPLACE-012"),
        trigger_terms=("FOUP", "웨이퍼 캐리어", "한 손", "계단", "전용 카트"),
        source_case_ids=("SYN-V7-0111",),
        confidence=0.65,
        rationale="FOUP stair carrying is a narrow manual-handling/access support signal and must not generalize to wafer process hazards.",
    ),
    SupportSeed(
        child_context="EXCAVATOR_SLOPE_SIGNALER_GAP",
        parents=("EXCAVATION", "CONSTRUCTION_EQUIP"),
        aliases=("굴삭기", "법면", "사면", "장비 전복", "유도자 없이", "단독 작업"),
        profile_alignment_aliases=("굴착기", "굴착", "굴착면 기울기", "건설기계", "유도자", "전도방지"),
        guide_codes=("D-C-4-2025", "D-C-11-2026", "C-48-2022"),
        source_sr_ids=("SR-EXCAVATION-010", "SR-EXCAVATION-011", "SR-EXCAVATION-018"),
        trigger_terms=("굴삭기", "법면", "사면", "전복 위험", "유도자 없이"),
        source_case_ids=("SYN-V7-0161",),
        confidence=0.67,
        rationale="Excavator work on a steep slope without a signaler is narrow enough for excavation/construction-machinery Guide support.",
    ),
    SupportSeed(
        child_context="CONFINED_TANK_ATTENDANT_GAP",
        parents=("CONFINED_SPACE", "SHIPYARD"),
        aliases=("카고 탱크", "탱크 내부", "감시인이 이석", "외부 연락 수단 없음", "선박 탱크"),
        profile_alignment_aliases=("밀폐공간", "감시인", "선박", "조선", "작업허가"),
        guide_codes=("E-G-18-2026", "G-116-2014", "B-5-2011"),
        source_sr_ids=("SR-CONFINED-002", "SR-CONFINED-005", "SR-CONFINED-014", "SR-CONFINED-019"),
        trigger_terms=("카고 탱크", "탱크 내부", "감시인", "이석", "외부 연락 수단 없음"),
        source_case_ids=("SYN-V7-0272",),
        confidence=0.67,
        rationale="Ship cargo-tank entry with absent attendant and no communication is confined-space Guide support only.",
    ),
    SupportSeed(
        child_context="SHIP_HEAVY_LIFT_SLING_INSPECTION_GAP",
        parents=("CRANE", "SHIPYARD", "MATERIAL_HANDLING"),
        aliases=("선박 엔진 인양", "수백 톤급", "점검 기록 없음", "안전 계수 불명확"),
        profile_alignment_aliases=("크레인", "달기기구", "줄걸이", "와이어로프", "훅", "샤클", "선박"),
        guide_codes=("B-M-12-2025", "B-M-34-2026", "G-116-2014"),
        source_sr_ids=("SR-CRANE-001", "SR-CRANE-003", "SR-WORKPLACE-010"),
        trigger_terms=("선박 엔진 인양", "안전 계수 불명확", "점검 기록 없음", "수백 톤급"),
        source_case_ids=("SYN-V7-0292",),
        confidence=0.66,
        rationale="Heavy ship-engine lifting with sling inspection uncertainty supports rigging/crane Guides only; it does not assert a legal SR edge.",
    ),
    SupportSeed(
        child_context="VEHICLE_EXPOSED_WIRING_FIRE_GAP",
        parents=("VEHICLE", "ELECTRICAL_WORK", "FIRE_EXPLOSION"),
        aliases=("차량 전기 배선", "노출된 도선", "금속 차체", "테이프 없이", "배선 수리"),
        profile_alignment_aliases=("자동차 정비", "저압전기설비", "절연", "전기", "수리", "정비"),
        guide_codes=("B-M-29-2026", "E-100-2021"),
        source_sr_ids=("SR-ELECTRIC-002", "SR-ELECTRIC-006", "SR-ELECTRIC-008", "SR-FIRE_EXPLOSION-006"),
        trigger_terms=("노출된 도선", "금속 차체", "테이프 없이", "단락", "절연 처리"),
        source_case_ids=("SYN-V7-0317",),
        confidence=0.66,
        rationale="Vehicle repair with exposed wiring near the chassis has concrete vehicle/electrical cues for Guide support.",
    ),
    SupportSeed(
        child_context="SCALDING_TANK_FALL_BURN_GAP",
        parents=("MACHINE", "HEAT_COLD", "LADDER"),
        aliases=("탕박조", "열탕", "조 위에", "내부를 들여다보는"),
        profile_alignment_aliases=("식품가공", "식품", "비상정지장치", "안전난간", "발판"),
        guide_codes=("B-M-6-2025", "A-G-2-2025"),
        source_sr_ids=("SR-MACHINE-001", "SR-MACHINE-004", "SR-HEAT-012"),
        trigger_terms=("탕박조", "열탕", "탕 배출"),
        source_case_ids=("SYN-V8-0113",),
        confidence=0.66,
        rationale="Scalding-tank inspection above hot water has specific food-machine and access cues for top Guide support.",
    ),
    SupportSeed(
        child_context="BINDING_MACHINE_JAM_LOTO_GAP",
        parents=("MACHINE", "PRINTING"),
        aliases=("제본기", "침 박음 장치", "용지 걸림", "기계 미정지", "걸림 제거"),
        profile_alignment_aliases=("인쇄기", "회전말림방호", "저속 이송", "동력통제", "잠금", "표지"),
        guide_codes=("M-193-2020", "B-M-37-2026", "B-M-25-2026"),
        source_sr_ids=("SR-MACHINE-010", "SR-MACHINE-023", "SR-MACHINE-024"),
        trigger_terms=("제본기", "침 박음 장치", "용지 걸림", "기계 미정지", "LOTO"),
        source_case_ids=("SYN-V8-0286",),
        confidence=0.66,
        rationale="Binding-machine jam clearing while running is a printing-machine/rotating-machine LOTO support signal.",
    ),
    SupportSeed(
        child_context="BINDING_MACHINE_HOTMELT_PPE_GAP",
        parents=("MACHINE", "HEAT_COLD", "PRINTING"),
        aliases=("핫멜트 제본기", "고온 접착제", "접착제가 흘러"),
        profile_alignment_aliases=("인쇄기", "보호장갑", "개인보호구", "보호구 착용", "내열 장갑"),
        guide_codes=("M-193-2020", "A-G-12-2026"),
        source_sr_ids=("SR-HEAT-012", "SR-PPE-002"),
        trigger_terms=("핫멜트 제본기", "고온 접착제", "접착제가 흘러"),
        source_case_ids=("SYN-V8-0287",),
        confidence=0.66,
        rationale="Hot-melt binding glue with missing heat gloves supports printing-machine/PPE Guides only.",
    ),
    SupportSeed(
        child_context="PLATE_MAKING_CHEMICAL_PPE_GAP",
        parents=("CHEMICAL_WORK", "PRINTING"),
        aliases=("감광 약품", "약품 도포", "제판", "보안경과 장갑", "피부 손상"),
        profile_alignment_aliases=("개인보호구", "보안경", "보호장갑", "보호구 착용"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-CHEMICAL-002", "SR-CHEMICAL-006", "SR-PPE-002"),
        trigger_terms=("감광 약품", "보안경", "장갑 미착용", "도포 작업", "피부 손상"),
        source_case_ids=("SYN-V8-0296",),
        confidence=0.65,
        rationale="Plate-making photosensitive chemical handling with missing goggles/gloves supports PPE Guide ranking only.",
    ),
    SupportSeed(
        child_context="UV_PLATEMAKING_SHIELDING_PPE_GAP",
        parents=("RADIATION", "PRINTING"),
        aliases=("UV 노광 장치", "UV 차폐", "광원 근처", "제판", "UV 보호 안경"),
        profile_alignment_aliases=("개인보호구", "보안경", "보호안경", "차폐", "보호구 착용"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-RADIATION-001", "SR-RADIATION-002", "SR-PPE-002"),
        trigger_terms=("UV 노광 장치", "UV 차폐 없이", "광원 근처", "UV 보호 안경", "눈·피부 손상"),
        source_case_ids=("SYN-V8-0297",),
        confidence=0.65,
        rationale="UV plate-making exposure without shielding has explicit UV/PPE cues and should not use radioactive-material Guides.",
    ),
)


SUPPORT_REJECTIONS: tuple[dict[str, Any], ...] = (
    {
        "child_context": "SOLDERING_ASSEMBLY",
        "guide_codes": {"G-126-2018", "B-E-21-2026"},
        "reason": "Reflow/soldering review candidates pointed to explosives/explosion-proof electrical Guides; v14 replaces this with narrow PPE support only.",
    },
)


def _reject_stale_support_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    for row in rows:
        row_guides = set(row.get("guide_codes") or [])
        for rule in SUPPORT_REJECTIONS:
            if row.get("child_context") == rule["child_context"] and row_guides & set(rule["guide_codes"]):
                row["review_status"] = "rejected"
                row["allowed_runtime_use"] = "review_only"
                row["v14_rejection_reason"] = rule["reason"]
                rejected.append({
                    "support_id": row.get("support_id"),
                    "child_context": row.get("child_context"),
                    "guide_codes": sorted(row_guides),
                    "reason": rule["reason"],
                })
                break
    return rejected


def build(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    taxonomy = _read_json(args.base_taxonomy)
    support_rows = _read_jsonl(args.base_support)
    no_top_rows = (_read_json(args.no_top_report).get("rows") or [])

    rejected_rows = _reject_stale_support_rows(support_rows)
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

        support_id = f"STAGE3-SR-GAP-SUPPORT-V14-{seed.child_context}"
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
            "candidate_labels": ["stage3_she_to_sr_gap", "guide_support_only", "v14_narrow_support"],
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
    taxonomy["version"] = "v14"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage3_sr_gap_support_v14": "guide_support_only_no_status_penalty_no_asserted_mapping",
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
        "rejected_stale_support_rows": rejected_rows,
        "audit_rows": audit_rows,
        "status_penalty_she_approval_asserted_mapping_update": 0,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_lines = [
        "# Stage3 SR Gap Support v14 Artifact Report",
        "",
        f"- generated_at: `{generated_at}`",
        f"- added_child_context_count: `{len(SUPPORT_SEEDS)}`",
        f"- support_candidate_count: `{len(merged_rows)}`",
        "- status/penalty/SHE approval/asserted mapping update: `0`",
        "",
        "## Rejected Stale Rows",
        "",
    ]
    if rejected_rows:
        for row in rejected_rows:
            md_lines.append(
                f"- `{row['support_id']}` `{row['child_context']}` guides `{', '.join(row['guide_codes'])}`: {row['reason']}"
            )
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
        "rejected_stale_support_rows": summary["rejected_stale_support_rows"],
        "outputs": summary["outputs"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
