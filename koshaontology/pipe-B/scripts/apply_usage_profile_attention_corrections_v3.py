#!/usr/bin/env python3
"""Second synthetic attention correction pass for Guide usage boundaries.

This pass targets the top residual overexposed Guides from
`synthetic_guide_recommendations_v1_v10_usage_profile2`.  It keeps all changes
candidate-only and never promotes asserted SR mappings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PIPE_B_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PIPE_B_ROOT / "data"
NOTE = "usage_profile_attention_correction_v3"


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def replace_list(target: dict[str, Any], key: str, values: list[str]) -> None:
    target[key] = unique(values)


def merge_list(target: dict[str, Any], key: str, values: list[str]) -> None:
    target[key] = unique([*list(target.get(key) or []), *values])


def append_note(guide: dict[str, Any]) -> None:
    notes = guide.get("notes")
    if isinstance(notes, list):
        if NOTE not in notes:
            notes.append(NOTE)
    elif notes:
        guide["notes"] = unique([str(notes), NOTE])
    else:
        guide["notes"] = [NOTE]


def demote_feature_candidates(guide: dict[str, Any], feature_codes: set[str], reason: str) -> int:
    changed = 0
    for candidate in guide.get("feature_candidates", []) or []:
        if candidate.get("feature_code") not in feature_codes:
            continue
        old_confidence = float(candidate.get("confidence") or 0.0)
        candidate["confidence"] = min(old_confidence, 0.64)
        candidate["review_status"] = "needs_review"
        candidate["evidence"] = f"{candidate.get('evidence') or ''} | {NOTE}: {reason}".strip()
        merge_list(candidate, "source_fields", ["synthetic_v1_v10_attention_review"])
        changed += 1
    return changed


CORRECTIONS: dict[str, dict[str, Any]] = {
    "A-G-12-2026": {
        "profile": {
            "profile_level": "domain_specific",
            "domain_family": "personal_protective_equipment_visible_ppe_gap",
            "mismatch_policy": "penalize_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": [
                "개인보호구",
                "보호구 착용",
                "안전모",
                "보안경",
                "보호장갑",
                "방진마스크",
                "방독마스크",
                "호흡용보호구",
                "귀마개",
                "귀덮개",
            ],
            "industry_alignment": ["보호구 착용", "PPE 관리", "호흡보호구", "청력보호구"],
            "negative_context_terms": [
                "보호구 단서 없음",
                "장비만 보임",
                "통로 위험만 보임",
                "전선만 보임",
                "적재물만 보임",
                "실내 교육 환경",
                "해당 없음",
            ],
            "confidence": 0.86,
        },
        "include_when": ["개인보호구", "보호구 착용", "안전모", "보안경", "보호장갑", "방진마스크", "방독마스크", "귀마개", "귀덮개"],
        "exclude_when": ["보호구 단서 없음", "장비만 보임", "통로 위험만 보임", "전선만 보임", "실내 교육 환경", "해당 없음"],
        "demote_features": {"GENERAL_WORKPLACE", "NOISE"},
        "demote_reason": "PPE Guide는 보호구 자체의 착용·선정·관리 단서가 있어야 추천한다.",
    },
    "A-G-9-2025": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "warehouse_storage_rack_material_handling",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": [
                "창고 적재대",
                "팔레트 적재물",
                "랙",
                "선반",
                "적재 불량",
                "낙하물",
                "산업용 트럭",
                "지게차",
                "고소 작업",
                "중량물 인력 작업",
            ],
            "industry_alignment": ["창고 적재", "물류창고", "랙 적재", "팔레트 적재"],
            "negative_context_terms": [
                "사진에서 관찰 가능한 위험 요소가 없다",
                "없음(지상 물품 정리 작업)",
                "사다리가 보관 중",
                "낮은 위치의 물품",
                "해당 없음",
                "보관 중이고 주변에 사람이 없음",
            ],
            "confidence": 0.88,
        },
        "include_when": ["창고 적재대", "팔레트 적재물", "랙", "선반", "적재 불량", "낙하물", "산업용 트럭", "지게차"],
        "exclude_when": ["사진에서 관찰 가능한 위험 요소가 없다", "사다리가 보관 중", "낮은 위치의 물품", "해당 없음"],
        "demote_features": {"FALLING_OBJECT"},
        "demote_reason": "창고 Guide는 일반 낙하물 feature보다 창고 적재/랙/팔레트 문맥이 우선이다.",
    },
    "C-70-2012": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "cold_storage_insulation_urethane_foam_hot_work_fire_watch",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": [
                "냉동·냉장 물류창고",
                "냉동창고",
                "냉장창고",
                "우레탄폼",
                "단열공사",
                "샌드위치 판넬",
                "화기작업 허가",
                "화재감시인",
                "방화포",
                "방폭등",
            ],
            "industry_alignment": ["냉동창고 단열공사", "냉장창고 단열공사", "우레탄폼 발포"],
            "negative_context_terms": [
                "일반 전기 작업",
                "일반 분전반",
                "일반 용접",
                "우레탄폼 단서 없음",
                "냉동창고 단서 없음",
                "의료기관",
                "복지시설",
            ],
            "confidence": 0.91,
        },
        "include_when": ["냉동·냉장 물류창고", "냉동창고", "냉장창고", "우레탄폼", "단열공사", "샌드위치 판넬", "화재감시인"],
        "exclude_when": ["일반 전기 작업", "일반 분전반", "일반 용접", "우레탄폼 단서 없음", "냉동창고 단서 없음"],
        "demote_features": {"FIRE", "WELDING"},
        "demote_reason": "냉동창고 단열공사 Guide는 일반 화재/용접 feature만으로 추천하면 안 된다.",
    },
    "H-100-2012": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "pcb_waste_handling_work_environment_management",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": [
                "PCBs",
                "PCB 폐기물",
                "PCB 함유폐기물",
                "폐 변압기",
                "무해화 처리",
                "소각설비 해체",
                "다이옥신",
            ],
            "industry_alignment": ["PCB 폐기물 처리", "폐 변압기 해체", "무해화 처리시설"],
            "negative_context_terms": [
                "일반 화학물질",
                "일반 폐기물",
                "밀폐공간",
                "탱크 작업",
                "PCB 단서 없음",
                "동물병원",
                "사회복지관",
            ],
            "confidence": 0.89,
        },
        "include_when": ["PCBs", "PCB 폐기물", "PCB 함유폐기물", "폐 변압기", "무해화 처리", "소각설비 해체", "다이옥신"],
        "exclude_when": ["일반 화학물질", "일반 폐기물", "밀폐공간", "탱크 작업", "PCB 단서 없음"],
        "demote_features": {"CHEMICAL_EXPOSURE", "TOXIC"},
        "demote_reason": "PCBs Guide는 독성/화학 feature만으로 추천하면 안 된다.",
    },
    "A-R-2-2026": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "production_system_lifecycle_safety_document_review",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "document_reference",
            "required_context_terms": [
                "생산시스템 수명주기",
                "수명주기 안전관리",
                "구상 단계",
                "설계 단계",
                "제조 단계",
                "운영 단계",
                "폐기 단계",
                "위험성평가 자료",
            ],
            "industry_alignment": ["생산시스템 수명주기", "설계·제조·운영 단계 위험성평가"],
            "negative_context_terms": ["현장 위험 사진만 있음", "수명주기 문서 없음", "적재물만 보임", "장비만 보임"],
            "confidence": 0.86,
        },
        "include_when": ["생산시스템 수명주기", "수명주기 안전관리", "구상 단계", "설계 단계", "제조 단계", "운영 단계", "위험성평가 자료"],
        "exclude_when": ["현장 위험 사진만 있음", "수명주기 문서 없음", "적재물만 보임", "장비만 보임"],
        "demote_features": set(),
        "demote_reason": "",
    },
    "H-187-2021": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "industrial_accident_first_aid_active_injury",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": [
                "응급처치",
                "부상자",
                "출혈",
                "골절",
                "절단",
                "화상",
                "쇼크",
                "부목",
                "지혈대",
                "응급처치 키트",
            ],
            "industry_alignment": ["산업재해 응급처치", "부상자 응급조치"],
            "negative_context_terms": [
                "사고 전 장면",
                "예방조치만 필요",
                "관찰 가능한 부상 없음",
                "응급처치 단서 없음",
                "해당 없음",
            ],
            "confidence": 0.88,
        },
        "include_when": ["응급처치", "부상자", "출혈", "골절", "절단", "화상", "쇼크", "부목", "지혈대"],
        "exclude_when": ["사고 전 장면", "예방조치만 필요", "관찰 가능한 부상 없음", "응급처치 단서 없음", "해당 없음"],
        "demote_features": set(),
        "demote_reason": "",
    },
    "A-G-14-2026": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "hot_work_welding_fire_prevention",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": [
                "용접",
                "용단",
                "화기작업",
                "불꽃",
                "토치",
                "화재감시자",
                "화기작업 허가",
                "용접 흄",
                "가스용접",
            ],
            "industry_alignment": ["용접·용단", "화기작업", "가스용접"],
            "negative_context_terms": [
                "일반 전기 작업",
                "분전반",
                "콘센트",
                "전선만 보임",
                "용접 단서 없음",
                "화기작업 단서 없음",
            ],
            "confidence": 0.9,
        },
        "include_when": ["용접", "용단", "화기작업", "불꽃", "토치", "화재감시자", "화기작업 허가", "가스용접"],
        "exclude_when": ["일반 전기 작업", "분전반", "콘센트", "전선만 보임", "용접 단서 없음", "화기작업 단서 없음"],
        "demote_features": {"FIRE", "WELDING"},
        "demote_reason": "용접·용단 Guide는 용접/화기작업 문맥 없이 feature만으로 추천하면 안 된다.",
    },
    "E-G-22-2026": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "heat_stress_wbgt_work_environment_management",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": ["고열작업", "WBGT", "열스트레스", "폭염", "열경련", "열탈진", "휴식", "음료 공급"],
            "industry_alignment": ["고열작업", "옥외 폭염작업", "주물·제철·고온공정"],
            "negative_context_terms": ["튀김기", "뜨거운 냄비", "샤브샤브", "스팀 피처", "커피", "일반 화상", "급식실", "외식업"],
            "confidence": 0.86,
        },
        "include_when": ["고열작업", "WBGT", "열스트레스", "폭염", "열경련", "열탈진", "휴식", "음료 공급"],
        "exclude_when": ["튀김기", "뜨거운 냄비", "샤브샤브", "스팀 피처", "커피", "일반 화상", "급식실", "외식업"],
        "demote_features": {"GENERAL_WORKPLACE", "HEAT_COLD"},
        "demote_reason": "고열작업환경 Guide는 조리/뜨거운 물체 화상 feature만으로 추천하면 안 된다.",
    },
    "H-116-2019": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "nitrogen_dioxide_poisoning_emergency_response",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": ["이산화질소", "NO2", "갈색 가스", "중독", "응급대응", "SCBA", "제독", "가스모니터링"],
            "industry_alignment": ["이산화질소 취급", "NO2 누출", "질산 공정"],
            "negative_context_terms": ["동물 교상", "고양이", "개", "할큄", "교상", "일반 독성", "이산화질소 단서 없음"],
            "confidence": 0.9,
        },
        "include_when": ["이산화질소", "NO2", "갈색 가스", "중독", "응급대응", "SCBA", "제독", "가스모니터링"],
        "exclude_when": ["동물 교상", "고양이", "개", "할큄", "교상", "이산화질소 단서 없음"],
        "demote_features": {"CHEMICAL_EXPOSURE", "TOXIC"},
        "demote_reason": "이산화질소 Guide는 일반 독성 feature만으로 추천하면 안 된다.",
    },
    "M-62-2012": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "woodworking_machine_noise_control",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": ["목공용 기계", "목재가공", "둥근톱", "대패", "톱", "소음관리", "청력보호구", "방음"],
            "industry_alignment": ["목재가공", "가구 제조", "목공용 기계"],
            "negative_context_terms": ["일반 기계", "치퍼", "에어레이터", "하수처리장", "끼임 위험이 중심", "목공용 기계 단서 없음"],
            "confidence": 0.88,
        },
        "include_when": ["목공용 기계", "목재가공", "둥근톱", "대패", "톱", "소음관리", "청력보호구", "방음"],
        "exclude_when": ["일반 기계", "치퍼", "에어레이터", "하수처리장", "끼임 위험이 중심", "목공용 기계 단서 없음"],
        "demote_features": {"NOISE"},
        "demote_reason": "목공용 기계 소음 Guide는 일반 기계소음 feature만으로 추천하면 안 된다.",
    },
    "D-C-7-2026": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "scaffold_structure_and_work_platform",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": ["비계", "강관비계", "시스템비계", "이동식비계", "작업발판", "벽이음", "교차가새"],
            "industry_alignment": ["비계 작업", "건설 비계", "작업발판"],
            "negative_context_terms": ["사다리", "연장 사다리", "A형 사다리", "비계 단서 없음", "일반 추락"],
            "confidence": 0.88,
        },
        "include_when": ["비계", "강관비계", "시스템비계", "이동식비계", "작업발판", "벽이음", "교차가새"],
        "exclude_when": ["사다리", "연장 사다리", "A형 사다리", "비계 단서 없음", "일반 추락"],
        "demote_features": {"FALL"},
        "demote_reason": "비계 Guide는 사다리/일반 추락 feature만으로 추천하면 안 된다.",
    },
}


def apply_correction(guide: dict[str, Any], correction: dict[str, Any]) -> int:
    changed = 0
    profile = guide.setdefault("domain_profile", {})
    for key, value in correction["profile"].items():
        if isinstance(value, list):
            replace_list(profile, key, value)
        else:
            profile[key] = value
        changed += 1
    merge_list(profile, "source_fields", ["synthetic_v1_v10_attention_review"])
    evidence = profile.get("evidence") or guide.get("title") or guide.get("guide_code")
    if NOTE not in str(evidence):
        profile["evidence"] = f"{evidence} | {NOTE}"

    boundary = guide.setdefault("recommendation_boundary", {})
    replace_list(boundary, "include_when", correction["include_when"])
    replace_list(boundary, "exclude_when", correction["exclude_when"])
    boundary["runtime_use"] = "candidate_domain_guard_only"
    boundary["legal_asserted_use"] = False

    changed += demote_feature_candidates(
        guide,
        set(correction.get("demote_features") or set()),
        correction.get("demote_reason") or "feature-only serving demotion",
    )
    append_note(guide)
    return changed


def main() -> None:
    touched: dict[str, str] = {}
    for path in sorted(DATA_DIR.glob("manual-enrichment-domain-guard-batch-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = 0
        for guide in data.get("guides", []) or []:
            guide_code = guide.get("guide_code")
            correction = CORRECTIONS.get(guide_code)
            if not correction:
                continue
            changed += apply_correction(guide, correction)
            touched[guide_code] = path.name
        if changed:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    missing = sorted(set(CORRECTIONS) - set(touched))
    print(f"Updated {len(touched)} guides")
    for guide_code, path_name in sorted(touched.items()):
        print(f"- {guide_code}: {path_name}")
    if missing:
        raise SystemExit(f"Missing corrections for: {', '.join(missing)}")


if __name__ == "__main__":
    main()
