#!/usr/bin/env python3
"""Build narrow Stage2/3 NO_TOP support artifacts on top of v9.

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


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v9.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v9.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT / "pictures-json" / "reports" / "stage2_5_no_top_root_cause_stage2_3_support_v9_narrow4.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v10.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v10.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_REPORT_PREFIX = "stage2_3_support_v10_artifacts_narrow2"


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="FOOD_SLICER_POWERED_CLEANING",
        parents=("MACHINE", "FOOD_PREP"),
        aliases=(
            "전동 슬라이서",
            "슬라이서 전원",
            "날 주변을 행주",
            "날 주변 청소",
            "조리도구 날",
        ),
        profile_alignment_aliases=("식품가공용 기계", "식품절단기", "칼날", "절단", "세척", "청소", "보호장갑"),
        guide_codes=("B-M-6-2025", "A-G-5-2025"),
        source_sr_ids=("SR-MACHINE-010", "SR-MACHINE-023", "SR-MACHINE-024"),
        trigger_terms=("전원이 켜진 상태", "전원을 끄지 않고"),
        source_case_ids=("SYN-V3-0115",),
        confidence=0.65,
        rationale="Powered food-slicer cleaning is a narrow cooking-tool/machine support signal; it must not generalize to all powered cleaning.",
    ),
    SupportSeed(
        child_context="BAKERY_OVEN_HOT_TRAY_BURN",
        parents=("FOOD_PREP", "HEAT_COLD"),
        aliases=(
            "데크 오븐",
            "베이킹 팬",
            "방열 장갑",
            "고온 트레이",
            "오븐 온도",
            "트레이 운반",
        ),
        profile_alignment_aliases=("조리도구", "오븐", "고온", "화상", "방열장갑", "운반"),
        guide_codes=("A-G-5-2025", "A-G-10-2025"),
        source_sr_ids=("SR-PPE-002", "SR-HEAT-012", "SR-CARGO-003"),
        trigger_terms=("데크 오븐", "베이킹 팬", "맨손", "방열 장갑", "고온 트레이", "시야가 완전히 차단"),
        source_case_ids=("SYN-V6-0001", "SYN-V6-0022"),
        confidence=0.65,
        rationale="Bakery oven and hot-tray scenes have direct heat/PPE/handling cues suitable for cooking-tool Guide support only.",
    ),
    SupportSeed(
        child_context="SMALL_SERVER_ELECTRICAL_OVERLOAD",
        parents=("ELECTRICAL_WORK", "FIRE_EXPLOSION"),
        aliases=(
            "멀티탭 하나에 고용량 서버",
            "멀티탭 과열",
            "과열로 변색",
            "서버실 멀티탭",
            "종이 상자가 쌓",
        ),
        profile_alignment_aliases=("과전류", "배선차단기", "전기설비", "과열", "차단기", "전선"),
        guide_codes=("E-116-2021", "E-57-2020", "E-85-2017"),
        source_sr_ids=("SR-ELECTRIC-002", "SR-ELECTRIC-006", "SR-FIRE_EXPLOSION-006"),
        trigger_terms=("멀티탭 하나", "고용량 서버", "과열로 변색", "서버실", "종이 상자"),
        source_case_ids=("SYN-V5-0151",),
        confidence=0.65,
        rationale="Server-room outlet overload scenes are narrow electrical-overcurrent support signals, not generic office electrical matching.",
    ),
    SupportSeed(
        child_context="ELEVATED_WELDING_FALL_CONTROL",
        parents=("WELDING", "SCAFFOLD", "FALL"),
        aliases=(
            "고소 용접",
            "달비계 위에서 용접",
            "안전고리 미체결",
            "선박 외판 용접",
            "와이어로프 용단",
        ),
        profile_alignment_aliases=("용접", "용단", "고소작업", "달비계", "안전대", "추락", "와이어로프"),
        guide_codes=("C-108-2017", "A-G-14-2026", "G-116-2014"),
        source_sr_ids=("SR-FALL-001", "SR-FALL-002", "SR-FIRE_EXPLOSION-006", "SR-HEAT-012"),
        trigger_terms=("용단 위험", "안전고리가 체결되지", "선박 외판 용접 중 고소", "매달림 비계"),
        source_case_ids=("SYN-V7-0227", "SYN-V7-0228", "SYN-V7-0276"),
        confidence=0.65,
        rationale="Elevated welding scenes with fall-arrest or conductive-rope cues are narrow construction/shipyard welding support signals.",
    ),
    SupportSeed(
        child_context="AUTOMOTIVE_TIRE_WHEEL_SERVICE",
        parents=("VEHICLE", "MACHINE", "MATERIAL_HANDLING"),
        aliases=(
            "타이어 공기 주입",
            "규정 압력",
            "타이어 측면 균열",
            "대형 타이어",
            "타이어 탈착",
            "혼자 들어 굴리",
        ),
        profile_alignment_aliases=("타이어", "차량정비", "공기주입", "압력", "탈착", "중량물"),
        guide_codes=("B-M-29-2026", "G-55-2012"),
        source_sr_ids=("SR-MACHINE-001", "SR-CARGO-003", "SR-CARGO-004"),
        trigger_terms=("타이어 공기 주입", "규정 압력", "측면에 균열", "대형 타이어", "타이어 탈착", "혼자 들어"),
        source_case_ids=("SYN-V7-0326", "SYN-V7-0328"),
        confidence=0.65,
        rationale="Automotive tire inflation and heavy tire handling scenes are narrow vehicle-maintenance Guide support signals.",
    ),
    SupportSeed(
        child_context="SILICA_DUST_BLASTING",
        parents=("SANDING", "CHEMICAL_WORK"),
        aliases=(
            "실리카 분진",
            "블라스팅",
            "blast cleaning",
            "철가루·모래 비산",
            "암석 파쇄",
            "분진 측정 결과",
            "방진 마스크가 아닌 일반 면 마스크",
        ),
        profile_alignment_aliases=("실리카", "분진", "블라스팅", "방진마스크", "국소배기", "분진 발생"),
        guide_codes=("G-106-2013",),
        source_sr_ids=("SR-CHEMICAL-002", "SR-CHEMICAL-006", "SR-CHEMICAL-008"),
        trigger_terms=("블라스팅", "blast cleaning", "철가루·모래", "암석 파쇄", "노출 기준의 3배", "일반 면 마스크"),
        source_case_ids=("SYN-V7-0286", "SYN-V8-0046"),
        confidence=0.65,
        rationale="Visible blasting/rock-crushing dust scenes should support the photo-actionable silica-dust Guide, not health-screening Guides.",
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

        support_id = f"STAGE2-3-SUPPORT-V10-{seed.child_context}"
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
            "candidate_labels": ["no_top_repair", "guide_support_only", "v10_narrow_support"],
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
    taxonomy["version"] = "v10"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage2_3_support_v10": "guide_support_only_no_status_penalty_no_asserted_mapping",
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
        "# Stage2/3 Support v10 Artifact Report",
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
