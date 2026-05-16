#!/usr/bin/env python3
"""Build narrow Stage 3 remaining-gap Guide support artifacts on top of v15.

The added rows target remaining NO_TOP cases where the synthetic observation
has a concrete, photo-visible task cue, but the approved SHE/SR path still does
not materialize a Guide.  These rows are Guide-ranking support only: no finding
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


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v15.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v15.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT
    / "data-team/05-enrichment/eval-data"
    / "reports"
    / "stage2_5_no_top_root_cause_stage2_taxonomy_gap_support_v15_narrow7b.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v16c.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v16c.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage3_remaining_gap_support_v16c_artifacts_narrow8c"

SKIPPED_SUPPORT_CONTEXTS = {
    # v16b created a useful EV no-top repair, but also pushed an existing
    # positive EV case from B-E-10 to an unrelated welding-fire-blanket Guide.
    # Hold this context until the electrical-vs-arc feature bridge is repaired.
    "EV_BATTERY",
}


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="WAFER_HANDLING",
        parents=("MACHINE", "ROBOT", "SEMICONDUCTOR"),
        aliases=(
            "웨이퍼 자동 이송 로봇",
            "웨이퍼 이송 로봇",
            "로봇 암",
            "안전 센서 우회",
            "센서 우회 스위치",
            "동작 중인 구역",
            "무단 진입",
        ),
        profile_alignment_aliases=("산업용 로봇", "로봇", "매니퓰레이터", "안전 펜스", "비상 정지", "광전자식 방호장치"),
        guide_codes=("M-61-2017",),
        source_sr_ids=("SR-ROBOT-002", "SR-ROBOT-003", "SR-ROBOT-001"),
        trigger_terms=("안전 센서 우회", "센서 우회 스위치", "무단 진입"),
        source_case_ids=("SYN-V7-0113",),
        confidence=0.67,
        rationale=(
            "Wafer-transfer robot operation with sensor bypass and worker entry is a narrow robot/interlock support signal."
        ),
    ),
    SupportSeed(
        child_context="EV_BATTERY",
        parents=("ELECTRICAL_WORK", "VEHICLE"),
        aliases=(
            "고전압 배터리",
            "EV 배터리",
            "400V 이상",
            "전기 단자",
            "일반 면 장갑",
            "대형 버스 고전압 배터리",
        ),
        profile_alignment_aliases=("충전전로", "절연용 보호구", "절연공구", "활선작업", "자동차 정비", "배터리"),
        guide_codes=("B-E-11-2026", "B-E-10-2026"),
        source_sr_ids=("SR-ELECTRIC-021", "SR-ELECTRIC-023", "SR-ELECTRIC-010"),
        trigger_terms=("절연 장갑 없이", "맨손", "일반 면 장갑", "전기 단자를 만지는", "절연 공구 미사용"),
        source_case_ids=("SYN-V7-0316",),
        confidence=0.66,
        rationale=(
            "Vehicle high-voltage battery work with ordinary gloves has explicit electrical PPE and isolation cues."
        ),
    ),
    SupportSeed(
        child_context="PROCESS_DUST_RESPIRATOR_GAP",
        parents=("SANDING", "CHEMICAL_WORK", "DUST"),
        aliases=("규산 분진", "실리카 분진", "고분진 구간", "방진마스크를 턱 아래", "규폐증"),
        profile_alignment_aliases=("실리카 분진", "호흡성 결정형 실리카", "호흡용 보호구", "방진마스크", "밀착도 검사", "분진"),
        guide_codes=("G-106-2013", "E-G-19-2026", "A-G-12-2026"),
        source_sr_ids=("SR-DUST-009", "SR-DUST-008", "SR-DUST-006"),
        trigger_terms=("방진마스크를 턱 아래", "턱 아래로 내려", "분진 흡입", "규폐증"),
        source_case_ids=("SYN-V8-0047",),
        confidence=0.67,
        rationale=(
            "Silica-heavy dust work with a respirator worn under the chin supports silica-dust and respiratory-protection Guides."
        ),
    ),
    SupportSeed(
        child_context="UV_LAMP_EYE_PPE_GAP",
        parents=("RADIATION", "MACHINE", "GENERAL_WORKPLACE"),
        aliases=("UV 살균등", "자외선 살균등", "살균 터널", "UV 차단 고글", "자외선", "UV 보호복"),
        profile_alignment_aliases=("개인보호구", "보안경", "보호안경", "보호구 착용", "차폐", "방사선"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-RADIATION-001", "SR-PPE-002"),
        trigger_terms=("UV 차단 고글 미착용", "가동 중인 살균 터널", "점검 목적으로 들어가", "눈·피부 화상"),
        source_case_ids=("SYN-V7-0068",),
        confidence=0.65,
        rationale=(
            "UV sterilizer entry with missing UV eye protection is retained as PPE Guide support; measurement-analysis UV Guides remain excluded from photo top."
        ),
    ),
    SupportSeed(
        child_context="YARN_WINDING",
        parents=("MACHINE", "TEXTILE"),
        aliases=("실 권선", "실 권선기", "권선 작업", "실 끊김", "실 재연결", "가동 중 기계에 손"),
        profile_alignment_aliases=("회전기계", "회전체", "가드", "방호설비", "말림", "권선기", "잠금", "표지"),
        guide_codes=("B-M-37-2026", "B-M-25-2026"),
        source_sr_ids=("SR-MACHINE-002", "SR-MACHINE-010", "SR-ROBOT-003"),
        trigger_terms=("실 끊김", "가동 중 기계에 손", "손을 넣어", "실 재연결", "LOTO 미적용"),
        source_case_ids=("SYN-V8-0267",),
        confidence=0.66,
        rationale=(
            "Yarn winding re-threading while running is a narrow rotating-machine/LOTO support signal, not a new approved SHE."
        ),
    ),
    SupportSeed(
        child_context="HARVEST_ERGONOMIC_SQUAT_POSTURE",
        parents=("ERGONOMIC", "HARVEST_WORK"),
        aliases=("고추 수확", "쪼그려 앉아", "장시간 작업", "중간 휴식 없이", "무릎 관절"),
        profile_alignment_aliases=("근골격계질환", "부적절한 자세", "작업환경개선", "휴식", "작업자세", "인체공학"),
        guide_codes=("E-G-4-2025", "E-G-1-2025"),
        source_sr_ids=("SR-ERGONOMIC-003", "SR-ERGONOMIC-005", "SR-ERGONOMIC-001"),
        trigger_terms=("쪼그려 앉아", "몇 시간째", "중간 휴식 없이", "무릎 관절"),
        source_case_ids=("SYN-V5-0137",),
        confidence=0.65,
        rationale=(
            "Harvest work with prolonged squatting is support-only for ergonomic/MSD prevention Guides."
        ),
    ),
    SupportSeed(
        child_context="FURNITURE_ADHESIVE_SPLASH_EYE_PPE",
        parents=("CHEMICAL_WORK", "MACHINE"),
        aliases=("가구 조립 접착제", "접착제 도포", "압착기 작동", "얼굴에 비산", "눈 화학 손상"),
        profile_alignment_aliases=("개인보호구", "보안경", "보호장갑", "안면 보호대", "보호구 착용"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-CHEMICAL-012", "SR-CHEMICAL-001", "SR-PPE-002"),
        trigger_terms=("얼굴에 비산", "눈 화학 손상", "보안경 미착용", "안면 보호대 미착용"),
        source_case_ids=("SYN-V8-0237",),
        confidence=0.65,
        rationale=(
            "Furniture adhesive squeezed by a press and splashing toward the face is narrow PPE support for eye/face protection."
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
        if seed.child_context in SKIPPED_SUPPORT_CONTEXTS:
            continue
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

        support_id = f"STAGE3-REMAINING-GAP-SUPPORT-V16C-{seed.child_context}"
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
            "candidate_labels": ["stage3_remaining_gap", "guide_support_only", "v16c_narrow_support"],
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
    taxonomy["version"] = "v16c"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage3_remaining_gap_support_v16c": "guide_support_only_no_status_penalty_no_asserted_mapping",
    }

    support_rows_out = sorted(support_by_id.values(), key=lambda row: str(row.get("support_id") or ""))
    args.taxonomy_output.parent.mkdir(parents=True, exist_ok=True)
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(args.support_output, support_rows_out)

    summary = {
        "generated_at": generated_at,
        "version": "v16c",
        "base_taxonomy": str(args.base_taxonomy),
        "base_support": str(args.base_support),
        "no_top_report": str(args.no_top_report),
        "taxonomy_output": str(args.taxonomy_output),
        "support_output": str(args.support_output),
        "support_rows_total": len(support_rows_out),
        "added_support_rows": len(audit_rows),
        "skipped_support_contexts": sorted(SKIPPED_SUPPORT_CONTEXTS),
        "asserted_mapping_updates": 0,
        "status_penalty_changes": 0,
        "audit_rows": audit_rows,
    }
    write_report(args.report_dir, args.report_prefix, summary, audit_rows)
    return summary


def write_report(report_dir: Path, prefix: str, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"{prefix}.json"
    md_path = report_dir / f"{prefix}.md"
    csv_path = report_dir / f"{prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
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
        for row in rows:
            writer.writerow({
                key: json.dumps(row[key], ensure_ascii=False) if isinstance(row.get(key), list) else row.get(key)
                for key in writer.fieldnames
            })
    lines = [
        "# Stage 3 Remaining-Gap Support v16c",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- base_taxonomy: `{summary['base_taxonomy']}`",
        f"- base_support: `{summary['base_support']}`",
        f"- support_rows_total: `{summary['support_rows_total']}`",
        f"- added_support_rows: `{summary['added_support_rows']}`",
        f"- skipped_support_contexts: `{', '.join(summary['skipped_support_contexts'])}`",
        "- asserted_mapping_updates: `0`",
        "- status_penalty_changes: `0`",
        "",
        "## Added Rows",
        "",
        "| child context | cases | guides | SRs |",
        "| --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| `{}` | {} | {} | {} |".format(
                row["child_context"],
                row["case_count"],
                ", ".join(f"`{code}`" for code in row["guide_codes"]),
                ", ".join(f"`{sr_id}`" for sr_id in row["source_sr_ids"]),
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    print(json.dumps({k: v for k, v in summary.items() if k != "audit_rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
