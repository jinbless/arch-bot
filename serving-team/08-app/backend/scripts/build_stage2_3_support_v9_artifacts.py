#!/usr/bin/env python3
"""Build narrow Stage2/3 NO_TOP support artifacts on top of v8.

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


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v8.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v8.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "stage2_5_no_top_root_cause_stage2_3_support_v8_narrow2.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v9.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v9.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage2_3_support_v9_artifacts_narrow4"


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="SPORTS_FACILITY_SLIP_TRIP",
        parents=("GENERAL_WORKPLACE", "MATERIAL_HANDLING"),
        aliases=(
            "헬스장 바닥",
            "스포츠시설 바닥",
            "자유중량 구역",
            "프리웨이트존",
            "덤벨 방치",
            "바닥에 흩어진 덤벨",
            "미끄럼 방지 타일",
            "마모된 타일",
            "미끄러운 바닥",
            "요가 매트 없이",
            "밸런스 포즈",
            "고무 매트 들림",
        ),
        profile_alignment_aliases=("미끄럼", "넘어짐", "걸림", "바닥", "정리정돈", "통행로", "미끄럼 방지"),
        guide_codes=("G-11-2017", "M-59-2012"),
        source_sr_ids=("SR-FALL-001", "SR-FALL-003", "SR-FALL-006"),
        trigger_terms=(
            "바닥에 흩어진 덤벨",
            "덤벨 위로",
            "통행 경로",
            "미끄럼 방지 타일이 마모",
            "마모된 타일",
            "미끄러운 바닥",
            "요가 매트 없이",
            "밸런스 포즈 중 미끄",
            "고무 매트 들림",
        ),
        source_case_ids=("SYN-V6-0151", "SYN-V6-0162", "SYN-V6-0173"),
        confidence=0.65,
        rationale="Sports-facility slip/trip scenes have explicit floor, dumbbell, tile, or exercise-surface cues; use only for Guide ranking support.",
    ),
    SupportSeed(
        child_context="CARDIO_EQUIPMENT_POWERED_MAINTENANCE",
        parents=("MACHINE", "ELECTRICAL_WORK"),
        aliases=(
            "트레드밀 전원 ON",
            "트레드밀 벨트",
            "벨트 아래 청소",
            "로잉 머신",
            "로잉 머신 수리",
            "커패시터 잔류 전압",
            "펌프 전원 ON",
            "임펠러 주변 손",
            "플러그 미분리",
        ),
        profile_alignment_aliases=("컨베이어", "벨트", "롤러", "전원차단", "잠금", "정비", "감전", "협착"),
        guide_codes=("B-M-33-2026", "B-E-10-2026", "B-E-14-2026"),
        source_sr_ids=(
            "SR-MACHINE-010",
            "SR-MACHINE-023",
            "SR-MACHINE-024",
            "SR-ELECTRIC-007",
            "SR-ELECTRIC-010",
        ),
        trigger_terms=(
            "트레드밀 전원 ON",
            "전원이 켜진 상태",
            "벨트 아래 청소",
            "손을 벨트",
            "전원 ON 상태",
            "로잉 머신 수리",
            "플러그 미분리",
            "커패시터 잔류 전압",
            "펌프 전원 ON",
            "임펠러 주변 손",
        ),
        source_case_ids=("SYN-V6-0156", "SYN-V6-0157", "SYN-V6-0176", "SYN-V6-0178"),
        confidence=0.65,
        rationale="Powered maintenance/cleaning scenes for cardio or small powered equipment are child-context signals for machine/electrical Guide support only.",
    ),
    SupportSeed(
        child_context="NEEDLESTICK_SHARPS_DISPOSAL",
        parents=("CHEMICAL_WORK", "MATERIAL_HANDLING"),
        aliases=(
            "주사침",
            "사용한 침",
            "침(acupuncture needle)",
            "침을 일반 쓰레기통",
            "날카로운 의료 폐기물",
        ),
        profile_alignment_aliases=("주사침", "의료폐기물", "샤프스", "날카로운 물체", "손상예방"),
        guide_codes=("E-M-3-2025", "E-M-4-2025"),
        source_sr_ids=("SR-PATHOGEN-001", "SR-PATHOGEN-002", "SR-PATHOGEN-006", "SR-CHEMICAL-002"),
        trigger_terms=("주사침", "사용한 침", "침(acupuncture needle)", "일반 쓰레기통"),
        source_case_ids=("SYN-V6-0253",),
        confidence=0.65,
        rationale="Needle/sharps disposal scenes are narrow support-only signals for healthcare needlestick prevention Guides.",
    ),
    SupportSeed(
        child_context="BLOOD_CONTAMINATED_WASTE_HANDLING",
        parents=("CHEMICAL_WORK", "MATERIAL_HANDLING"),
        aliases=(
            "의료 폐기물",
            "감염성 폐기물",
            "혈액 오염",
            "오염 세탁물",
            "혈액 오염 시트",
        ),
        profile_alignment_aliases=("의료폐기물", "혈액", "감염", "보호장갑", "오염 세탁물", "가검물"),
        guide_codes=("E-M-4-2025", "H-138-2021"),
        source_sr_ids=("SR-PATHOGEN-001", "SR-PATHOGEN-002", "SR-PATHOGEN-006", "SR-CHEMICAL-002"),
        trigger_terms=(
            "맨손",
            "방호 장갑 없이",
            "보호장갑 없이",
            "내화학 장갑 없이",
        ),
        source_case_ids=("SYN-V8-0062", "SYN-V8-0326"),
        confidence=0.65,
        rationale="Healthcare waste or contaminated laundry scenes require both healthcare/blood-waste context and unsafe bare-hand/PPE-missing cues before Guide support is used.",
    ),
    SupportSeed(
        child_context="FLAMMABLE_CHEMICAL_SMOKING",
        parents=("CHEMICAL_WORK", "FIRE_EXPLOSION"),
        aliases=(
            "인화성 물질 옆 흡연",
            "담배를 피우",
            "흡연",
            "인화성 경고",
            "폐유기용제",
            "잉크 저장",
            "드럼 옆",
            "용제 보관",
        ),
        profile_alignment_aliases=("인화성", "유기용제", "화재", "폭발", "착화원", "저장", "폐유기용제"),
        guide_codes=("D-28-2012", "P-50-2012"),
        source_sr_ids=("SR-FIRE_EXPLOSION-006", "SR-FIRE_EXPLOSION-007", "SR-FIRE_EXPLOSION-008", "SR-CHEMICAL-002"),
        trigger_terms=("인화성 물질", "담배를 피우", "흡연", "인화성 경고", "폐유기용제", "잉크 저장", "드럼 옆"),
        source_case_ids=("SYN-V8-0072", "SYN-V8-0278"),
        confidence=0.65,
        rationale="Smoking/ignition near flammable chemical storage is a narrow photo-observable support signal for fire/explosion and hazardous-waste Guides.",
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

        support_id = f"STAGE2-3-SUPPORT-V9-{seed.child_context}"
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
            "candidate_labels": ["no_top_repair", "guide_support_only", "v9_narrow_support"],
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
    taxonomy["version"] = "v9"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage2_3_support_v9": "guide_support_only_no_status_penalty_no_asserted_mapping",
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
        "# Stage2/3 Support v9 Artifact Report",
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
