#!/usr/bin/env python3
"""Apply usage-profile corrections from synthetic Guide attention review.

This script edits only the manual domain-guard batch JSON files.  The changes
tighten recommendation boundaries for Guides that were over-promoted in the
synthetic v1-v10 Guide replay.  They do not create asserted SR mappings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PIPE_B_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PIPE_B_ROOT / "data"
NOTE = "usage_profile_attention_correction_v2"


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def merge_list(target: dict[str, Any], key: str, values: list[str]) -> None:
    target[key] = unique([*list(target.get(key) or []), *values])


def replace_list(target: dict[str, Any], key: str, values: list[str]) -> None:
    target[key] = unique(values)


def append_note(guide: dict[str, Any], text: str) -> None:
    notes = guide.get("notes")
    if isinstance(notes, list):
        if text not in notes:
            notes.append(text)
    elif notes:
        guide["notes"] = unique([str(notes), text])
    else:
        guide["notes"] = [text]


def demote_feature_candidates(guide: dict[str, Any], feature_codes: set[str], reason: str) -> int:
    changed = 0
    for candidate in guide.get("feature_candidates", []) or []:
        if candidate.get("feature_code") not in feature_codes:
            continue
        old_confidence = float(candidate.get("confidence") or 0.0)
        candidate["confidence"] = min(old_confidence, 0.64)
        candidate["review_status"] = "needs_review"
        candidate["evidence"] = f"{candidate.get('evidence') or ''} | {NOTE}: {reason}".strip()
        source_fields = list(candidate.get("source_fields") or [])
        candidate["source_fields"] = unique([*source_fields, "synthetic_v1_v10_attention_review"])
        changed += 1
    return changed


CORRECTIONS: dict[str, dict[str, Any]] = {
    "B-E-3-2025": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "substation_pressurization_positive_pressure",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": [
                "변전실",
                "수변전설비",
                "양압유지",
                "양압설비",
                "양압실",
                "퍼지",
                "보호기체",
                "급기덕트",
                "압력계",
                "가스검지기",
                "방폭 전기실",
            ],
            "industry_alignment": ["변전실", "수변전설비", "방폭 전기실", "양압유지"],
            "negative_context_terms": [
                "일반 전기 작업",
                "일반 분전반",
                "일반 콘센트",
                "멀티탭",
                "전선만 보임",
                "전기실 단서 없음",
                "양압 단서 없음",
                "방폭 단서 없음",
            ],
            "confidence": 0.9,
        },
        "include_when": ["변전실", "수변전설비", "양압유지", "양압설비", "퍼지", "보호기체", "가스검지기"],
        "exclude_when": ["일반 전기 작업", "일반 분전반", "전선만 보임", "양압 단서 없음", "방폭 단서 없음"],
        "demote_features": {"ELECTRICAL_WORK", "EXPLOSION"},
        "demote_reason": "변전실 양압 Guide는 일반 전기/폭발 feature만으로 추천하면 안 된다.",
    },
    "C-C-16-2026": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "chemical_eyewash_shower_corrosive_exposure",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": [
                "세안설비",
                "비상 세안기",
                "긴급샤워기",
                "비상샤워",
                "강산",
                "강염기",
                "부식성",
                "관리대상 유해물질",
                "실험실",
            ],
            "industry_alignment": ["화학물질 취급", "세안설비", "비상샤워", "실험실"],
            "negative_context_terms": [
                "화학물질 단서만 있음",
                "세면대만 보임",
                "급식실 세척대",
                "일반 화장실",
                "비상 세안기 단서 없음",
                "부식성 물질 단서 없음",
            ],
            "confidence": 0.91,
        },
        "include_when": ["세안설비", "비상 세안기", "긴급샤워기", "비상샤워", "강산", "강염기", "부식성", "실험실"],
        "exclude_when": ["화학물질 단서만 있음", "세면대만 보임", "급식실 세척대", "비상 세안기 단서 없음"],
        "demote_features": {"CHEMICAL", "CHEMICAL_EXPOSURE"},
        "demote_reason": "세안설비 Guide는 일반 화학물질/노출 feature만으로 추천하면 안 된다.",
    },
    "A-G-1-2025": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "fall_protection_net_installation",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": [
                "추락방호망",
                "수직형 추락방망",
                "방호망",
                "안전망",
                "테두리 로프",
                "달기 로프",
                "라쳇버클",
                "앵커볼트",
            ],
            "industry_alignment": ["추락방호망", "수직형 추락방망", "안전망 설치"],
            "negative_context_terms": [
                "일반 추락 위험",
                "일반 비계",
                "사다리만 보임",
                "안전대만 보임",
                "방호망 단서 없음",
            ],
            "confidence": 0.9,
        },
        "include_when": ["추락방호망", "수직형 추락방망", "방호망", "안전망", "라쳇버클", "앵커볼트"],
        "exclude_when": ["일반 추락 위험", "일반 비계", "사다리만 보임", "방호망 단서 없음"],
        "demote_features": {"FALL", "SCAFFOLD"},
        "demote_reason": "추락방호망 Guide는 일반 추락/비계 feature만으로 추천하면 안 된다.",
    },
    "B-M-32-2026": {
        "profile": {
            "profile_level": "domain_specific",
            "domain_family": "steel_product_storage",
            "mismatch_policy": "penalize_without_required_context",
            "procedure_role": "field_control",
            "required_context_terms": ["철강제품", "H빔", "형강", "강관", "코일", "봉강", "선반형 적재"],
            "industry_alignment": ["철강제품 적재", "강재 야적", "철강 코일", "H빔 적재"],
            "negative_context_terms": [
                "일반 창고",
                "물류센터",
                "박스만 보임",
                "팔레트만 보임",
                "철강제품 단서 없음",
            ],
            "confidence": 0.87,
        },
        "include_when": ["철강제품", "H빔", "형강", "강관", "코일", "봉강", "선반형 적재"],
        "exclude_when": ["일반 창고", "물류센터", "박스만 보임", "팔레트만 보임", "철강제품 단서 없음"],
        "demote_features": {"FALLING_OBJECT"},
        "demote_reason": "철강제품 적재 Guide는 일반 낙하물 feature만으로 추천하면 안 된다.",
    },
    "G-32-2016": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "pregnant_worker_hazard_management",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "management_program",
            "required_context_terms": [
                "임산부",
                "임신 근로자",
                "모성보호",
                "태아",
                "임산부 작업제한",
                "생식독성",
                "방사선",
            ],
            "industry_alignment": ["임산부 근로자", "모성보호", "임산부 작업관리"],
            "negative_context_terms": [
                "임산부 단서 없음",
                "일반 화학물질",
                "일반 중량물",
                "일반 인간공학",
            ],
            "confidence": 0.88,
        },
        "include_when": ["임산부", "임신 근로자", "모성보호", "태아", "임산부 작업제한", "생식독성"],
        "exclude_when": ["임산부 단서 없음", "일반 화학물질", "일반 중량물", "일반 인간공학"],
        "demote_features": {"CHEMICAL_EXPOSURE", "ERGONOMIC"},
        "demote_reason": "임산부 Guide는 화학/인간공학 feature만으로 추천하면 안 된다.",
    },
    "A-G-15-2026": {
        "profile": {
            "profile_level": "domain_specific",
            "domain_family": "emergency_action_plan_document_and_drill",
            "mismatch_policy": "penalize_without_required_context",
            "procedure_role": "management_program",
            "required_context_terms": [
                "비상조치계획",
                "비상대피 계획",
                "대피도",
                "비상훈련",
                "비상연락망",
                "응급처치",
                "사고 대응",
            ],
            "industry_alignment": ["비상조치계획", "비상대피 계획", "중소규모 사업장"],
            "negative_context_terms": [
                "계획서 단서 없음",
                "대피도 단서 없음",
                "일반 위험 상황",
                "일반 보호구 사진만 있음",
            ],
            "confidence": 0.84,
        },
        "include_when": ["비상조치계획", "비상대피 계획", "대피도", "비상훈련", "비상연락망", "응급처치", "사고 대응"],
        "exclude_when": ["계획서 단서 없음", "대피도 단서 없음", "일반 위험 상황", "일반 보호구 사진만 있음"],
        "demote_features": {"GENERAL_WORKPLACE"},
        "demote_reason": "비상조치계획 Guide는 일반 사업장 feature만으로 추천하면 안 된다.",
    },
    "C-C-92-2026": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "psm_self_audit_document_program",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "document_reference",
            "required_context_terms": [
                "자체감사",
                "공정안전",
                "PSM",
                "감사계획",
                "감사팀",
                "점검표",
                "현장감사",
                "면담",
                "개선조치",
                "감사보고서",
            ],
            "industry_alignment": ["공정안전보고서 대상", "PSM 사업장", "자체감사"],
            "negative_context_terms": [
                "일반 현장 사진",
                "기계만 보임",
                "감사 문서 단서 없음",
                "PSM 단서 없음",
            ],
            "confidence": 0.88,
        },
        "include_when": ["자체감사", "공정안전", "PSM", "감사계획", "감사팀", "점검표", "감사보고서"],
        "exclude_when": ["일반 현장 사진", "기계만 보임", "감사 문서 단서 없음", "PSM 단서 없음"],
        "demote_features": {"GENERAL_WORKPLACE", "CHEMICAL_WORK"},
        "demote_reason": "자체감사 Guide는 일반 현장/화학작업 feature만으로 추천하면 안 된다.",
    },
    "C-18-2015": {
        "profile": {
            "profile_level": "exclusive",
            "domain_family": "construction_design_for_safety_document_review",
            "mismatch_policy": "exclude_without_required_context",
            "procedure_role": "document_reference",
            "required_context_terms": [
                "설계단계",
                "안전보건 설계",
                "설계도서",
                "도면 검토",
                "가설구조물 설계",
                "흙막이 설계",
                "거푸집 설계",
                "작업발판 설계",
            ],
            "industry_alignment": ["건설공사 설계", "설계도서", "가설구조물 설계"],
            "negative_context_terms": [
                "일반 건설현장",
                "시공 중 사진",
                "설계도서 단서 없음",
                "도면 단서 없음",
                "일반 비계",
            ],
            "confidence": 0.86,
        },
        "include_when": ["설계단계", "안전보건 설계", "설계도서", "도면 검토", "가설구조물 설계"],
        "exclude_when": ["일반 건설현장", "시공 중 사진", "설계도서 단서 없음", "도면 단서 없음", "일반 비계"],
        "demote_features": {"GENERAL_WORKPLACE", "SCAFFOLD"},
        "demote_reason": "건설 설계지침은 일반 현장/비계 feature만으로 추천하면 안 된다.",
    },
}


def apply_correction(guide: dict[str, Any], correction: dict[str, Any]) -> int:
    changed = 0
    profile = guide.setdefault("domain_profile", {})
    for key, value in correction["profile"].items():
        if isinstance(value, list):
            replace_list(profile, key, value)
        elif profile.get(key) != value:
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
    append_note(guide, NOTE)
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
