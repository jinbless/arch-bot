#!/usr/bin/env python3
"""Build narrow Stage 3 SHE-gap support artifacts on top of v11.

The added rows repair NO_TOP cases where non-broad SRs already exist but no
actionable SHE/source Guide anchors the standard-procedure ranking.  These rows
are Guide-ranking support only.  They do not broaden RiskFeature normalization,
SHE status, penalty exposure, asserted SR mappings, or legal evidence.
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


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v11.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v11.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "stage2_5_no_top_root_cause_stage2_3_support_v11_narrow3.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v12.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v12.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage3_gap_support_v12_artifacts_narrow4"


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="LASER_SKIN_EYE_PPE_GAP",
        parents=("RADIATION", "SKIN_DEVICE", "GENERAL_WORKPLACE"),
        aliases=(
            "레이저 피부 관리",
            "레이저 피부",
            "레이저 시술",
            "레이저 기기",
            "시술자·고객",
            "보안경",
        ),
        profile_alignment_aliases=("개인보호구", "보안경", "보호구 착용", "보호안경"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-RADIATION-001", "SR-RADIATION-002", "SR-PPE-002"),
        trigger_terms=("보안경을 착용하지", "보안경 미착용", "모두 보안경을 착용하지", "맨눈"),
        source_case_ids=("SYN-V4-0033",),
        confidence=0.65,
        rationale="Laser skin-treatment eye exposure has explicit laser and eyewear cues; support only PPE Guide ranking.",
    ),
    SupportSeed(
        child_context="HIGH_PRESSURE_WASH_ELECTRICAL_PANEL",
        parents=("HIGH_PRESSURE_WASH", "ELECTRICAL_WORK", "WET_FLOOR_WORK"),
        aliases=(
            "고압 세척기",
            "고압 물줄기",
            "전기 제어함",
            "전기 패널",
            "제어함 침수",
            "차수 커버",
        ),
        profile_alignment_aliases=("고압 스팀 청소기", "물기", "누전차단기", "전기설비", "저압전기설비"),
        guide_codes=("E-2-2012", "E-100-2021"),
        source_sr_ids=("SR-ELECTRIC-002", "SR-ELECTRIC-006", "SR-WORKPLACE-012"),
        trigger_terms=("전기 제어함 방향", "제어함에 물", "전기 제어함에 물", "차수 커버 설치"),
        source_case_ids=("SYN-V7-0082",),
        confidence=0.66,
        rationale="High-pressure washing toward an electrical control box is a narrow electrical/water support signal.",
    ),
    SupportSeed(
        child_context="PROCESS_DUST_RESPIRATOR_GAP",
        parents=("SANDING", "CHEMICAL_WORK", "DUST"),
        aliases=(
            "곡물 분진",
            "플라스틱 분진",
            "가황 촉진제 분진",
            "고분진 구간",
            "방진마스크 미착용",
            "방진마스크 없이",
            "턱 아래로 내려",
        ),
        profile_alignment_aliases=("호흡보호구", "방진마스크", "분진", "밀착도 검사", "호흡용 보호구"),
        guide_codes=("E-G-19-2026", "A-G-12-2026"),
        source_sr_ids=("SR-CHEMICAL-002", "SR-CHEMICAL-006", "SR-CHEMICAL-008", "SR-PPE-002"),
        trigger_terms=(
            "방진마스크 없이",
            "방진마스크 미착용",
            "턱 아래로 내려",
            "분진 농도 가시적",
            "분진이 다량",
            "분진 흡입",
            "국소 배기 없음",
            "개방 용기에서 계량",
        ),
        source_case_ids=("SYN-V7-0088", "SYN-V7-0143", "SYN-V7-0146", "SYN-V8-0047"),
        confidence=0.65,
        rationale="Visible process dust with absent or misused respirator supports respiratory-protection Guide ranking only.",
    ),
    SupportSeed(
        child_context="UNDERGROUND_LIVE_CABLE_EXCAVATION",
        parents=("ELECTRICAL_WORK", "EXCAVATION"),
        aliases=(
            "지하 전력 케이블",
            "활선 케이블",
            "굴착 접근",
            "케이블 확인",
            "절연 장갑",
            "검전기",
        ),
        profile_alignment_aliases=("충전전로", "활선작업", "절연공구", "절연용 보호구", "검전기", "전원 차단"),
        guide_codes=("B-E-11-2026", "B-E-10-2026"),
        source_sr_ids=("SR-ELECTRIC-002", "SR-ELECTRIC-006", "SR-EXCAVATION-010"),
        trigger_terms=("활선 케이블", "절연 장갑 없이", "손으로 케이블", "케이블 절연 손상"),
        source_case_ids=("SYN-V7-0167",),
        confidence=0.66,
        rationale="Underground excavation around possible live power cable has explicit live-cable and insulated-PPE cues.",
    ),
    SupportSeed(
        child_context="ACID_ETCHING_CONCRETE_CONTACT",
        parents=("CHEMICAL_WORK", "CONSTRUCTION_EQUIP"),
        aliases=(
            "콘크리트 산 세척",
            "acid etching",
            "묽은 염산",
            "염산 용액",
            "내산 장갑",
        ),
        profile_alignment_aliases=("묽은 염산", "세척용 묽은 염산", "조적공사", "피부", "장갑"),
        guide_codes=("C-64-2018", "A-G-12-2026"),
        source_sr_ids=("SR-CHEMICAL-002", "SR-CHEMICAL-006", "SR-PPE-002"),
        trigger_terms=("묽은 염산 용액을 맨손", "맨손으로 취급", "내산 장갑 미착용", "acid etching"),
        source_case_ids=("SYN-V7-0202",),
        confidence=0.65,
        rationale="Concrete acid-etching with hydrochloric acid and missing acid-resistant gloves is a narrow construction chemical support signal.",
    ),
    SupportSeed(
        child_context="COLD_STORAGE_ELECTRICAL_PANEL_MOISTURE",
        parents=("ELECTRICAL_WORK", "COLD_STORAGE", "MATERIAL_HANDLING"),
        aliases=(
            "냉동 창고",
            "전기 설비 패널",
            "전기 패널",
            "결빙",
            "수분 부착",
            "패널 문",
        ),
        profile_alignment_aliases=("전기설비 정비", "예방정비", "개폐장치", "수변전설비", "저압전기설비", "누전차단기"),
        guide_codes=("B-E-16-2026", "E-100-2021"),
        source_sr_ids=("SR-ELECTRIC-002", "SR-ELECTRIC-006", "SR-WORKPLACE-012"),
        trigger_terms=("수분이 부착", "패널 문을 열어", "전기 작업 시도", "결빙으로 수분"),
        source_case_ids=("SYN-V7-0267",),
        confidence=0.65,
        rationale="Moisture or ice on an electrical panel in cold storage is a narrow electrical-maintenance support signal.",
    ),
    SupportSeed(
        child_context="ENGINE_AIR_IMPACT_FRAGMENT_EYE",
        parents=("VEHICLE", "MACHINE", "LIFT_WORK"),
        aliases=(
            "에어 임팩트 렌치",
            "엔진 볼트",
            "볼트가 튕겨",
            "금속 파편",
            "보안경 미착용",
        ),
        profile_alignment_aliases=("차량정비", "전기기계", "배기가스", "자동차 정비", "보안경", "개인보호구"),
        guide_codes=("G-55-2012", "A-G-12-2026"),
        source_sr_ids=("SR-MACHINE-010", "SR-PPE-002", "SR-WORKPLACE-012"),
        trigger_terms=("볼트가 튕겨", "금속 파편 비산", "보안경을 미착용", "보안경 미착용"),
        source_case_ids=("SYN-V7-0308",),
        confidence=0.65,
        rationale="Air-impact wrench bolt ejection has explicit vehicle-repair and flying-fragment eye-protection cues.",
    ),
    SupportSeed(
        child_context="HOT_GREENHOUSE_HEAT_STRESS",
        parents=("GREENHOUSE_WORK", "HEAT_COLD"),
        aliases=(
            "비닐하우스",
            "40°C",
            "40℃",
            "얼굴이 붉",
            "수분 보충 없이",
            "장시간 작업",
        ),
        profile_alignment_aliases=("고열작업", "폭염", "열스트레스", "열탈진", "휴식", "음료 공급"),
        guide_codes=("E-G-22-2026",),
        source_sr_ids=("SR-HEAT-012", "SR-WORKPLACE-012"),
        trigger_terms=("수분 보충 없이", "얼굴이 붉", "땀을 과도하게", "40°C 이상 추정", "40℃ 이상 추정"),
        source_case_ids=("SYN-V8-0021",),
        confidence=0.65,
        rationale="Hot greenhouse work with visible heat-stress cues supports high-heat work-environment controls.",
    ),
    SupportSeed(
        child_context="COMPRESSED_AIR_HOSE_WHIP",
        parents=("MACHINE", "PRESSURE_VESSEL", "OTHER"),
        aliases=(
            "고압 에어 호스",
            "에어 호스",
            "채찍처럼",
            "연결 부위",
            "호스 연결 클램프",
            "착암 드릴",
        ),
        profile_alignment_aliases=("압축공기", "공기압 시스템", "압축공기 관로", "채찍 현상", "호스"),
        guide_codes=("M-103-2017", "G-17-2017"),
        source_sr_ids=("SR-MACHINE-010", "SR-WORKPLACE-012"),
        trigger_terms=("채찍처럼", "연결 부위가 느슨", "고압 에어 호스 연결", "호스 연결 클램프"),
        source_case_ids=("SYN-V8-0033",),
        confidence=0.65,
        rationale="Loose high-pressure air-hose whip is a narrow pneumatic-system support signal.",
    ),
    SupportSeed(
        child_context="COLD_STORAGE_ICY_FLOOR_BOX_HANDLING",
        parents=("BOX_HANDLING", "MATERIAL_HANDLING", "FALL"),
        aliases=(
            "냉동 창고",
            "바닥 결빙",
            "냉동 박스",
            "일반 안전화",
            "결빙 구역",
        ),
        profile_alignment_aliases=("넘어짐", "미끄러짐", "바닥", "물기", "작업장 통로", "미끄럼방지"),
        guide_codes=("G-11-2017", "A-G-2-2025"),
        source_sr_ids=("SR-FALL-001", "SR-FALL-003", "SR-CARGO-003"),
        trigger_terms=("바닥 결빙 명확", "결빙 구역", "일반 안전화", "방한화가 아닌"),
        source_case_ids=("SYN-V7-0078",),
        confidence=0.65,
        rationale="Icy floor while carrying cold-storage boxes is a narrow slip/trip support signal.",
    ),
    SupportSeed(
        child_context="BOX_CARRY_STAIRS_VISIBILITY",
        parents=("BOX_HANDLING", "MATERIAL_HANDLING", "FALL"),
        aliases=(
            "20kg 박스",
            "박스를 안고 계단",
            "계단을 내려가",
            "발을 헛디디",
            "시야 확보",
            "핸드레일",
        ),
        profile_alignment_aliases=("박스형 화물", "인력운반작업", "중량물", "계단", "통로", "핸드레일"),
        guide_codes=("A-G-17-2026", "A-G-2-2025"),
        source_sr_ids=("SR-CARGO-003", "SR-FALL-001", "SR-WORKPLACE-012"),
        trigger_terms=("20kg 박스", "박스를 안고 계단", "계단을 내려가다 발을 헛디디", "발을 헛디디"),
        source_case_ids=("SYN-V8-0138",),
        confidence=0.65,
        rationale="Manual box carrying on stairs with misstep/visibility cues supports manual-handling and access-route Guides.",
    ),
    SupportSeed(
        child_context="HIGH_TEMPERATURE_DYEING_HOT_TEXTILE",
        parents=("CHEMICAL_WORK", "HEAT_COLD", "MACHINE"),
        aliases=(
            "고온 염색 기계",
            "고온 염색기",
            "뜨거운 원단",
            "맨손으로 꺼내",
            "내열 장갑",
        ),
        profile_alignment_aliases=("고온 염색기", "고온 염색", "스팀", "도어 잠금장치", "원단", "압력용기"),
        guide_codes=("B-M-15-2026",),
        source_sr_ids=("SR-HEAT-012", "SR-MACHINE-010", "SR-PPE-002"),
        trigger_terms=("고온 염색 기계", "뜨거운 원단", "맨손으로 꺼내", "내열 장갑 착용 및 냉각"),
        source_case_ids=("SYN-V8-0252",),
        confidence=0.66,
        rationale="Hot textile removal from high-temperature dyeing equipment has explicit machine/heat/PPE cues.",
    ),
    SupportSeed(
        child_context="STEAM_IRON_BURN_TRIP",
        parents=("STEAM_IRON", "HEAT_COLD", "FALL"),
        aliases=(
            "산업용 스팀 다리미",
            "스팀 다리미",
            "고온 스팀 노즐",
            "스팀 노즐",
            "스팀 다리미 호스",
            "호스가 통로",
        ),
        profile_alignment_aliases=("스팀", "화상", "넘어짐", "걸림", "통로", "고열작업"),
        guide_codes=("M-124-2012", "G-11-2017"),
        source_sr_ids=("SR-HEAT-012", "SR-FALL-001", "SR-WORKPLACE-012"),
        trigger_terms=("고온 스팀 노즐을 손 방향", "스팀 건 선단", "호스가 통로", "걸려 넘어질"),
        source_case_ids=("SYN-V8-0261", "SYN-V8-0262"),
        confidence=0.65,
        rationale="Industrial steam-iron nozzle and hose-trip scenes are narrow textile heat/trip support signals.",
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

        support_id = f"STAGE3-GAP-SUPPORT-V12-{seed.child_context}"
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
            "candidate_labels": ["no_top_repair", "guide_support_only", "v12_stage3_gap_support"],
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
    taxonomy["version"] = "v12"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage3_gap_support_v12": "guide_support_only_no_status_penalty_no_asserted_mapping",
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
        "# Stage3 Gap Support v12 Artifact Report",
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
