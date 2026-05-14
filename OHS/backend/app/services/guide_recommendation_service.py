"""Guide, WorkProcess, and checklist recommendation facade."""
from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import (
    PgChecklistItem,
    PgCiSrMapping,
    PgGuideEntityFeatureCandidate,
    PgGuideSrLinkCandidate,
    PgGuideVisualTriggerCandidate,
    PgKoshaGuide,
    PgWorkProcess,
    PgWpSrMapping,
)
from app.services import hazard_rule_engine
from app.services.broad_sr_policy import (
    fallback_sr_ids,
    get_broad_sr_ids,
    get_secondary_score_multiplier,
    usable_primary_sr_ids,
)
from app.services.guide_domain_profile import evaluate_guide_domain_profile, get_guide_domain_profile
from app.services.guide_photo_matchability import (
    PHOTO_ACTIONABLE,
    PHOTO_CONDITIONAL_FOLLOWUP,
    PHOTO_UNMATCHABLE,
    followup_photo_allowed,
    get_photo_matchability,
    top_photo_allowed,
)
from app.services.industry_context import infer_industry_context, score_industry_alignment
from app.services.situation_frame_service import load_situation_context_taxonomy, match_guide_support_candidates


SERVING_CONFIDENCE = 0.65
SERVING_REVIEW_STATUSES = ("candidate", "asserted")
GENERIC_FEATURE_CODES = {
    "GENERAL_WORKPLACE",
    "CHEMICAL",
    "CHEMICAL_EXPOSURE",
    "CHEMICAL_WORK",
    "FIRE",
    "EXPLOSION",
    "FIRE_EXPLOSION",
    "ELECTRICAL_WORK",
    "ELECTRICITY",
    "MACHINE",
    "ERGONOMIC",
    "VENTILATION_POOR",
}
BROAD_FEATURE_CODES = {
    "FALL",
    "SLIP",
    "COLLISION",
    "FALLING_OBJECT",
    "CRUSH",
    "CUT",
    "COLLAPSE",
    "ERGONOMIC",
    "BURN",
    "ELECTRIC_SHOCK",
    "EXPLOSION",
    "CHEMICAL_EXPOSURE",
    "MATERIAL_HANDLING",
    "MACHINE",
    "VEHICLE",
    "CHEMICAL",
    "FIRE",
    "ELECTRICITY",
    "ELECTRICAL_WORK",
}
WEAK_PROFILE_USAGE_TERMS = {
    "chemical",
    "chemical_process",
    "construction",
    "electrical_maintenance",
    "healthcare",
    "laboratory",
    "manufacturing",
    "화학물질",
    "화재",
    "폭발",
    "가스",
    "증기",
    "환기",
    "방폭",
    "인화성 액체",
    "인화성 가스",
    "인화성",
    "인화성 물질",
    "유기용제",
    "용제",
    "점화원",
    "낙하물",
    "피부",
    "흡입",
    "작업계획",
    "고소 작업",
    "중량물 인력 작업",
    "근골격계",
    "작업환경개선",
    "의학적 조치",
    "해당 작업 또는 설비가 확인되는 사업장",
}
STRICT_PROFILE_USAGE_GATE_FAMILIES = {
    "automotive_partial_spray_painting_isocyanate_solvent_booth_explosion",
    "bulk_oxygen_supply_loX_tank_vaporizer_safety_distance",
    "chemical_laboratory_storage_hood_gas_cylinder_fire_emergency",
    "chemical_protective_glove_selection",
    "construction_rush_work_night_shift_simultaneous_work_fire_fall",
    "ergonomic_msd_prevention_program",
    "excavator_operation_quick_coupler_rops_lifting_attachment",
    "gas_vapor_fire_explosion_design_vent_containment_suppression",
    "interior_ceiling_wall_board_stud_scaffold_temporary_electric",
    "ntr_tunnel_pipe_jacking_hydraulic_jack_grouting_inner_excavation",
    "older_worker_safety_training",
    "small_workplace_fire_explosion_prevention_extinguisher_detector_esv_flame_arrester",
    "warehouse_storage_rack_material_handling",
}
REFERENCE_PROCEDURE_ROLES = {
    "measurement_analysis",
    "test_protocol",
    "health_screening",
    "risk_method",
    "document_reference",
    "management_program",
}
CONTEXTUAL_CI_SAFE_BLOCK_TERMS = (
    "완비",
    "완전히 설치",
    "정상",
    "명확히 분리",
    "접혀",
    "보관 중",
    "준비 중",
    "조립 전",
    "체결되어",
    "컷팅 글러브",
    "미끄럼 방지",
    "착용 완비",
    "차광 커튼",
    "차광막",
    "방화포",
)
CONTEXTUAL_CI_SAFE_NEGATORS = (
    "미설치",
    "미착용",
    "미체결",
    "미흡",
    "부재",
    "불량",
    "누락",
    "없",
    "없이",
    "않",
)
CONTEXTUAL_CI_GENERIC_OBSERVABLES = {"가동 중", "절단", "잠금장치", "잠금 장치"}
STANDARD_GUIDE_SAFE_BLOCK_TERMS = (
    "올바른 장면",
    "정상 장면",
    "정상 상태",
    "정상적으로",
    "정상 작동",
    "정상 조작",
    "작업 완료",
    "작업 완료 상태",
    "아직 진입하지",
    "진입하지 않았다",
    "진입 계획을 수립",
    "지상 작업",
    "확인서 작성",
    "컴퓨터로",
    "안전한 사무",
    "2단짜리 발판 사다리",
    "높이 약 50cm",
    "3점 지지",
    "사다리 하부를 발로 고정",
    "소형 밸브 부품",
    "1~2kg 수준",
    "차단기 off 확인",
    "검전기 확인",
    "loto 태그 부착",
    "보차가 명확히 분리",
    "차량 구역",
    "보행자 구역",
    "방한복·방한 장갑·방한화",
    "비상 개방 버튼 위치를 확인",
    "화재·아크 방지 조치가 완비",
    "비계 조립 전",
    "부품 상태를 확인",
    "정비를 위해 정지된 상태",
    "아무것도 걸려 있지",
    "강제 환기 가동",
    "폭발 분위기 연속 감시",
    "집진기 필터 상태를 점검",
    "교체 완료 후",
    "착용 완비",
    "차광 커튼",
    "차광막",
    "국소 배기 가동",
    "국소 배기 장치가 가동",
    "자동 차광 헬멧",
    "모두 올바르게 착용",
    "작업발판도 안전",
    "손 감지 센서",
    "접혀",
    "접혀 있는 상태로 보관",
    "주변에 사람이 없",
    "보관 상태",
    "점검을 완료",
)
STANDARD_GUIDE_EXPLICIT_SAFE_BLOCK_TERMS = (
    "아직 진입하지",
    "진입하지 않았다",
    "주변에 사람이 없",
    "작업자가 없다",
    "인근 화기 작업 없음",
)
STANDARD_GUIDE_CORPUS_GAP_BLOCK_GROUPS = (
    (
        ("퇴실 체크리스트",),
        ("흄후드", "가스 밸브", "야간 실험"),
    ),
    (
        ("항정신성 약품", "마약성 진통제"),
        ("약품 조제", "조제실", "MSDS"),
    ),
    (
        ("만료된 약품", "의약품 폐기"),
        ("일반 쓰레기봉투", "약품 보관"),
    ),
    (
        ("재활용 선별", "선별장"),
        ("유리병 파편", "유리 파편"),
        ("안전화 미착용", "일반 운동화"),
    ),
)
CONTEXT_REQUIRED_DOMAIN_FAMILIES = {
    "air_jacket_gas_manifold_welding_support",
    "airborne_infectious_disease_workplace_prevention",
    "reused_temporary_equipment_performance_scaffold_shoring_inspection",
    "cold_contact_surface_risk_assessment",
    "pipe_support_installation_welding",
    "small_tank_drum_hot_work",
}
CONTEXT_REQUIRED_FAMILY_FEATURE_ALLOW = {
    "cold_contact_surface_risk_assessment": {"COLD_EXPOSURE"},
}
CI_WP_RELEVANCE_SUPPORT_CONTEXTS = {
    "GREENHOUSE_STRUCTURE_FALL",
    "DRY_CLEANING_STEAM_PIPE_HOT_SURFACE",
}
CI_WP_RELEVANCE_SUPPORT_LABELS = {"v20_actionable_support"}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(v for v in values if v))


def _risk_feature_codes(risk_features: list[Any] | None) -> dict[str, set[str]]:
    result = {"accident_type": set(), "hazardous_agent": set(), "work_context": set()}
    for feature in risk_features or []:
        axis = getattr(feature, "axis", None) or (feature.get("axis") if isinstance(feature, dict) else None)
        code = getattr(feature, "code", None) or (feature.get("code") if isinstance(feature, dict) else None)
        if axis in result and code:
            result[axis].add(code)
    return result


def _flat_feature_codes(risk_features: list[Any] | None) -> list[str]:
    codes = []
    for values in _risk_feature_codes(risk_features).values():
        codes.extend(sorted(values))
    return _unique(codes)


def _she_ci_ids(she_matches: list[Any] | None) -> list[str]:
    ci_ids = []
    for match in she_matches or []:
        ci_ids.extend(list(getattr(match, "applies_ci_ids", []) or []))
    return _unique(ci_ids)


def _she_source_guides(she_matches: list[Any] | None) -> list[str]:
    guides = []
    for match in she_matches or []:
        guides.extend(list(getattr(match, "source_guides", []) or []))
    return _unique(guides)


def _visual_bonus(text: str, visual_cues: list[str] | None) -> float:
    if not text or not visual_cues:
        return 0.0
    lower = text.lower()
    hits = sum(1 for cue in visual_cues if cue and cue.lower() in lower)
    return min(0.15, hits * 0.05)


def _is_broad_secondary(sr_id: str | None, broad_sr_ids: set[str], direct_sr_ids: set[str]) -> bool:
    return bool(sr_id and sr_id in broad_sr_ids and sr_id not in direct_sr_ids)


def _non_generic_feature(feature_code: str | None) -> bool:
    return bool(feature_code and feature_code not in GENERIC_FEATURE_CODES)


def _guide_specific_feature(feature_code: str | None) -> bool:
    return bool(_non_generic_feature(feature_code) and feature_code not in BROAD_FEATURE_CODES)


def _context_blob(visual_cues: list[str] | None, context_text: str | None) -> str:
    return " ".join([*(visual_cues or []), context_text or ""]).lower()


def _has_non_negated_safe_context(text: str) -> bool:
    for term in CONTEXTUAL_CI_SAFE_BLOCK_TERMS:
        lowered = term.lower()
        start = text.find(lowered)
        while start >= 0:
            span = text[max(0, start - 16): min(len(text), start + len(lowered) + 16)]
            if not any(negator.lower() in span for negator in CONTEXTUAL_CI_SAFE_NEGATORS):
                return True
            start = text.find(lowered, start + len(lowered))
    return False


def _contextual_ci_fallback_allowed(
    situation_frame: dict | None,
    visual_cues: list[str] | None,
    context_text: str | None,
) -> bool:
    frame = situation_frame if isinstance(situation_frame, dict) else {}
    if frame.get("match_policy") == "status_safe":
        return False
    safe_cues = set(frame.get("safe_cues") or [])
    observable_cues = set(frame.get("observable_cues") or [])
    if safe_cues and (not observable_cues or observable_cues <= CONTEXTUAL_CI_GENERIC_OBSERVABLES):
        return False
    return not _has_non_negated_safe_context(_context_blob(visual_cues, context_text))


def _has_non_negated_terms(
    text: str,
    terms: tuple[str, ...],
    *,
    negators: tuple[str, ...] = CONTEXTUAL_CI_SAFE_NEGATORS,
    window: int = 16,
) -> bool:
    for term in terms:
        lowered = term.lower()
        start = text.find(lowered)
        while start >= 0:
            span = text[max(0, start - window): min(len(text), start + len(lowered) + window)]
            if not any(negator.lower() in span for negator in negators):
                return True
            start = text.find(lowered, start + len(lowered))
    return False


def _standard_procedure_safe_context_blocked(
    situation_frame: dict | None,
    visual_cues: list[str] | None,
    context_text: str | None,
) -> bool:
    text = _context_blob(visual_cues, context_text)
    safe_blocked = _has_non_negated_terms(text, STANDARD_GUIDE_SAFE_BLOCK_TERMS) or _has_non_negated_terms(
        text,
        STANDARD_GUIDE_EXPLICIT_SAFE_BLOCK_TERMS,
        negators=(),
    )
    if safe_blocked:
        return True
    return any(
        all(_has_non_negated_terms(text, tuple(group), negators=()) for group in required_groups)
        for required_groups in STANDARD_GUIDE_CORPUS_GAP_BLOCK_GROUPS
    )


def _matches_visual_trigger(candidate: PgGuideVisualTriggerCandidate, context_blob: str) -> bool:
    if not context_blob:
        return False
    for value in (candidate.trigger_text, candidate.evidence):
        lowered = (value or "").lower()
        if lowered and lowered in context_blob:
            return True
    return False


def _domain_profile_text(
    guide: PgKoshaGuide | None,
    work_processes: list[PgWorkProcess] | None = None,
    profile_bits: list[str] | None = None,
) -> str:
    bits = []
    if guide:
        bits.extend([guide.title or "", guide.sub_category or ""])
    for wp in (work_processes or [])[:8]:
        bits.extend([wp.process_name or "", wp.safety_measures or "", wp.source_section or ""])
    bits.extend(profile_bits or [])
    return " ".join(bits)


def _guide_candidate_profile_bits(db: Session, guide_codes: list[str]) -> dict[str, list[str]]:
    if not guide_codes:
        return {}
    bits: dict[str, list[str]] = defaultdict(list)
    try:
        feature_rows = (
            db.query(
                PgGuideEntityFeatureCandidate.guide_code,
                PgGuideEntityFeatureCandidate.feature_code,
                PgGuideEntityFeatureCandidate.evidence,
            )
            .filter(PgGuideEntityFeatureCandidate.guide_code.in_(guide_codes))
            .filter(PgGuideEntityFeatureCandidate.confidence >= SERVING_CONFIDENCE)
            .filter(PgGuideEntityFeatureCandidate.review_status.in_(SERVING_REVIEW_STATUSES))
            .limit(max(120, len(guide_codes) * 10))
            .all()
        )
        for guide_code, feature_code, evidence in feature_rows:
            bits[guide_code].extend([feature_code or "", evidence or ""])

        trigger_rows = (
            db.query(
                PgGuideVisualTriggerCandidate.guide_code,
                PgGuideVisualTriggerCandidate.trigger_text,
                PgGuideVisualTriggerCandidate.evidence,
            )
            .filter(PgGuideVisualTriggerCandidate.guide_code.in_(guide_codes))
            .filter(PgGuideVisualTriggerCandidate.confidence >= SERVING_CONFIDENCE)
            .filter(PgGuideVisualTriggerCandidate.review_status.in_(SERVING_REVIEW_STATUSES))
            .limit(max(120, len(guide_codes) * 10))
            .all()
        )
        for guide_code, trigger_text, evidence in trigger_rows:
            bits[guide_code].extend([trigger_text or "", evidence or ""])
    except SQLAlchemyError:
        db.rollback()
    return bits



def _manual_profile_terms(profile: dict | None) -> list[str]:
    if not profile:
        return []
    boundary = profile.get("recommendation_boundary") or {}
    terms: list[str] = []
    for key in (
        "required_context_terms",
        "visual_triggers",
        "industry_alignment",
        "intended_workplaces",
        "intended_tasks",
        "observable_required_cues",
    ):
        values = profile.get(key) or []
        if isinstance(values, list):
            terms.extend(str(value) for value in values if value)
    terms.extend(str(value) for value in (boundary.get("include_when") or []) if value)
    if profile.get("guide_code") == "P-55-2012":
        terms = [term for term in terms if term != "황"]
    return _unique([
        term
        for term in terms
        if term.strip().lower() not in WEAK_PROFILE_USAGE_TERMS
    ])


def _support_child_profile_aligned(child_context: str | None, profile: dict | None) -> bool:
    if not child_context or not profile:
        return False
    profile_text = " ".join([
        str(profile.get("domain_family") or ""),
        str(profile.get("usage_summary") or ""),
        *(_manual_profile_terms(profile) or []),
    ]).lower()
    if not profile_text:
        return False
    child = str(child_context).lower()
    child_forms = _unique([child, child.replace("_", " ")])
    taxonomy = load_situation_context_taxonomy()
    aliases = (taxonomy.get("aliases") or {}).get(str(child_context)) or []
    child_info = (taxonomy.get("child_contexts") or {}).get(str(child_context)) or {}
    profile_aliases = child_info.get("profile_alignment_aliases") or []
    child_forms.extend(str(alias).lower() for alias in aliases if len(str(alias)) >= 2)
    child_forms.extend(str(alias).lower() for alias in profile_aliases if len(str(alias)) >= 2)
    if any(form and form in profile_text for form in child_forms):
        return True
    child_tokens = [
        token
        for token in re.split(r"[^a-z0-9가-힣]+", child)
        if len(token) >= 4
    ]
    return any(token in profile_text for token in child_tokens)


def _term_hits(text: str, terms: list[str], limit: int = 3) -> list[str]:
    hits: list[str] = []
    lowered_text = (text or "").lower()
    for term in terms:
        lowered = term.lower()
        if lowered in lowered_text and term not in hits:
            hits.append(term)
        if len(hits) >= limit:
            break
    return hits


def _support_context_terms(support_signal: dict[str, Any] | None) -> list[str]:
    if not support_signal:
        return []
    child_context = str(support_signal.get("child_context") or "")
    taxonomy = load_situation_context_taxonomy()
    child_info = (taxonomy.get("child_contexts") or {}).get(child_context) or {}
    terms: list[str] = [child_context, child_context.replace("_", " ")]
    terms.extend(str(value) for value in (taxonomy.get("aliases") or {}).get(child_context) or [])
    terms.extend(str(value) for value in child_info.get("aliases") or [])
    terms.extend(str(value) for value in child_info.get("profile_alignment_aliases") or [])
    terms.extend(str(value) for value in support_signal.get("trigger_hits") or [])
    return _unique([term for term in terms if len(str(term).strip()) >= 2])


def _score_usage_profile(
    profile: dict | None,
    *,
    visual_cues: list[str] | None,
    context_text: str | None,
    feature_codes: list[str],
    industry_contexts: list[str] | None,
) -> tuple[float, list[str], bool]:
    if not profile:
        return 0.0, [], False
    context = _context_blob(visual_cues, context_text)
    profile_terms = _manual_profile_terms(profile)
    term_hits = _term_hits(context, profile_terms, limit=4)
    profile_feature_codes = set(profile.get("feature_codes") or [])
    feature_hits = sorted(set(feature_codes) & profile_feature_codes)
    non_generic_feature_hits = [code for code in feature_hits if _guide_specific_feature(code)]
    industry_hits = _term_hits(
        " ".join([*(industry_contexts or []), context_text or ""]).lower(),
        [str(value) for value in (profile.get("industry_alignment") or []) if value],
        limit=2,
    )
    role = str(profile.get("procedure_role") or "field_control")
    if role in REFERENCE_PROCEDURE_ROLES and not (term_hits or industry_hits):
        return 0.0, [], False
    if str(profile.get("profile_level") or "general") == "exclusive" and not term_hits:
        return 0.0, [], False
    if not (term_hits or non_generic_feature_hits):
        return 0.0, [], False

    score = min(
        0.32,
        len(term_hits) * 0.045
        + len(non_generic_feature_hits) * 0.055
        + len(industry_hits) * 0.025,
    )
    if score <= 0:
        return 0.0, [], False
    reasons = []
    if term_hits:
        reasons.append(f"usage profile terms:{','.join(term_hits[:2])}")
    if non_generic_feature_hits:
        reasons.append(f"usage profile features:{','.join(non_generic_feature_hits[:2])}")
    if industry_hits:
        reasons.append(f"usage profile industry:{','.join(industry_hits[:2])}")
    return score, reasons, bool(term_hits or non_generic_feature_hits or industry_hits)


def _support_profile_usage_signal(
    support_signal: dict[str, Any] | None,
    profile: dict | None,
) -> tuple[float, list[str], bool]:
    """Allow tightly curated Guide support to satisfy the usage gate.

    This is intentionally narrower than normal profile-term matching.  It only
    applies when a support candidate is trigger-backed, has a non-broad SR, and
    the SituationFrame child context is aligned with the Guide usage profile.
    """
    if not support_signal or not profile:
        return 0.0, [], False
    if not support_signal.get("has_trigger_hit"):
        return 0.0, [], False
    if not support_signal.get("has_non_broad_support_sr"):
        return 0.0, [], False
    if float(support_signal.get("support_score") or 0) < _support_signal_score_threshold(support_signal):
        return 0.0, [], False
    child_context = support_signal.get("child_context")
    if not _support_child_profile_aligned(child_context, profile):
        return 0.0, [], False
    return (
        0.08,
        [f"usage profile support alignment:{child_context}"],
        True,
    )


def _support_signal_score_threshold(support_signal: dict[str, Any] | None) -> float:
    if support_signal and support_signal.get("match_policy") == "confirmation_required":
        return 0.54
    return 0.78


def _trigger_backed_support_profile_override(
    support_signal: dict[str, Any] | None,
    profile: dict | None,
) -> bool:
    return bool(
        support_signal
        and support_signal.get("has_trigger_hit")
        and float(support_signal.get("support_score") or 0) >= _support_signal_score_threshold(support_signal)
        and support_signal.get("has_non_broad_support_sr")
        and _support_child_profile_aligned(
            support_signal.get("child_context"),
            profile,
        )
    )


def _strict_profile_usage_required(profile: dict | None) -> bool:
    if not profile:
        return False
    family = str(profile.get("domain_family") or "")
    if family in STRICT_PROFILE_USAGE_GATE_FAMILIES:
        return True
    level = str(profile.get("profile_level") or "general")
    role = str(profile.get("procedure_role") or "field_control")
    return role in REFERENCE_PROCEDURE_ROLES or level == "exclusive"


def _ci_wp_relevance_support_allowed(support_signal: dict[str, Any] | None) -> bool:
    if not support_signal:
        return False
    child_context = str(support_signal.get("child_context") or "")
    labels = {str(label) for label in (support_signal.get("candidate_labels") or [])}
    return child_context in CI_WP_RELEVANCE_SUPPORT_CONTEXTS or bool(labels & CI_WP_RELEVANCE_SUPPORT_LABELS)


def _reference_role_context_hit(profile: dict | None, visual_cues: list[str] | None, context_text: str | None) -> bool:
    if not profile:
        return True
    role = str(profile.get("procedure_role") or "field_control")
    if role not in REFERENCE_PROCEDURE_ROLES:
        return True
    role_terms = {
        "measurement_analysis": ["작업환경측정", "분석", "시료", "검량선", "측정", "분석기", "계측", "모니터링"],
        "test_protocol": ["시험", "독성시험", "평가시험", "실험", "프로토콜"],
        "health_screening": ["건강진단", "검진", "의학적", "문진", "검사"],
        "risk_method": ["위험성평가", "평가 방법", "리스크 평가", "체크리스트 방법"],
        "document_reference": ["문서", "양식", "기록", "보고서", "매뉴얼"],
        "management_program": ["계획", "계획서", "프로그램", "절차서", "관리방안", "비상대피", "비상조치"],
    }.get(role, [])
    return bool(_term_hits(_context_blob(visual_cues, context_text), role_terms, limit=1))


def _ci_reference_role_allowed(
    profile: dict | None,
    visual_cues: list[str] | None,
    context_text: str | None,
    *,
    has_she_cue: bool = False,
) -> bool:
    if has_she_cue or not profile:
        return True
    role = str(profile.get("procedure_role") or "field_control")
    if role not in REFERENCE_PROCEDURE_ROLES:
        return True
    return _reference_role_context_hit(profile, visual_cues, context_text)


def _ci_context_bonus(
    ci: PgChecklistItem,
    profile: dict | None,
    visual_cues: list[str] | None,
    context_text: str | None,
) -> tuple[float, list[str]]:
    ci_text = (ci.text or "").lower()
    if not ci_text:
        return 0.0, []
    context = _context_blob(visual_cues, context_text)
    profile_terms = _manual_profile_terms(profile)
    context_profile_terms = _term_hits(context, profile_terms, limit=8)
    ci_profile_hits = _term_hits(ci_text, context_profile_terms, limit=3)
    ci_visual_hits = _term_hits(ci_text, [cue for cue in (visual_cues or []) if cue], limit=3)
    bonus = min(0.22, len(ci_profile_hits) * 0.075 + len(ci_visual_hits) * 0.045)
    reasons = []
    if ci_profile_hits:
        reasons.append(f"CI profile term:{','.join(ci_profile_hits[:2])}")
    if ci_visual_hits:
        reasons.append(f"CI visual term:{','.join(ci_visual_hits[:2])}")
    return bonus, reasons


def _ci_support_bonus(
    ci: PgChecklistItem,
    support_signal: dict[str, Any] | None,
    profile: dict | None,
) -> tuple[float, list[str]]:
    ci_text = " ".join(filter(None, [ci.text, ci.source_section])).lower()
    if not ci_text:
        return 0.0, []
    terms = _support_context_terms(support_signal)
    if support_signal and _support_profile_usage_signal(support_signal, profile)[0] > 0:
        terms.extend(_manual_profile_terms(profile))
    hits = _term_hits(ci_text, _unique(terms), limit=4)
    if not hits:
        return 0.0, []
    return min(0.28, len(hits) * 0.09), [f"CI support term:{','.join(hits[:2])}"]


def _section_matches(section: str | None, candidate_sections: list[str]) -> bool:
    if not section:
        return False
    normalized = str(section).strip()
    if not normalized:
        return False
    for candidate in candidate_sections:
        other = str(candidate or "").strip()
        if not other:
            continue
        if normalized == other or normalized.startswith(f"{other}.") or other.startswith(f"{normalized}."):
            return True
    return False


def _rank_work_processes(
    work_processes: list[PgWorkProcess],
    *,
    profile: dict | None,
    visual_cues: list[str] | None,
    context_text: str | None,
    wp_sr_map: dict[str, set[str]],
) -> list[PgWorkProcess]:
    if not work_processes:
        return []
    primary_ids = set((profile or {}).get("primary_work_process_ids") or [])
    profile_terms = _manual_profile_terms(profile)
    context = _context_blob(visual_cues, context_text)
    ranked: list[tuple[float, int, PgWorkProcess]] = []
    for index, wp in enumerate(work_processes):
        wp_text = " ".join(filter(None, [wp.process_name, wp.safety_measures, wp.source_section])).lower()
        score = 0.0
        if wp.identifier in primary_ids:
            score += 1.2
        if wp_sr_map.get(wp.identifier):
            score += 0.7
        score += min(0.45, len(_term_hits(wp_text, profile_terms, limit=6)) * 0.075)
        score += min(0.35, len(_term_hits(context, [wp.process_name or "", wp.source_section or ""], limit=4)) * 0.08)
        ranked.append((score, int(wp.process_order or index + 1), wp))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [wp for _, _, wp in ranked]

def get_immediate_checklist_items(
    db: Session,
    sr_ids: list[str],
    direct_sr_ids: list[str] | None = None,
    limit: int = 12,
    risk_features: list[Any] | None = None,
    she_matches: list[Any] | None = None,
    visual_cues: list[str] | None = None,
    industry_contexts: list[str] | None = None,
    context_text: str | None = None,
    preferred_guide_codes: list[str] | None = None,
    situation_frame: dict | None = None,
    allow_contextual_ci_fallback: bool = False,
) -> list[dict]:
    """Return immediate actions with SHE/SR/feature evidence scoring.

    Existing asserted CI→SR rows remain the strongest source. Candidate rows
    improve recall but keep their confidence/evidence separate.
    """
    if not sr_ids and not she_matches and not risk_features:
        return []

    scores: dict[str, float] = defaultdict(float)
    sr_by_ci: dict[str, set[str]] = defaultdict(set)
    evidence_by_ci: dict[str, list[str]] = defaultdict(list)
    ci_rows: dict[str, PgChecklistItem] = {}
    direct_sr_set = set(direct_sr_ids or [])
    broad_sr_ids = get_broad_sr_ids()
    broad_multiplier = get_secondary_score_multiplier()
    pending_broad_scores: dict[str, float] = defaultdict(float)
    pending_broad_sr_by_ci: dict[str, set[str]] = defaultdict(set)
    pending_broad_evidence: dict[str, list[str]] = defaultdict(list)
    pending_broad_rows: dict[str, PgChecklistItem] = {}
    guide_specific_ci_ids: set[str] = set()
    pending_generic_feature_scores: dict[str, float] = defaultdict(float)
    pending_generic_feature_evidence: dict[str, list[str]] = defaultdict(list)
    pending_generic_feature_rows: dict[str, PgChecklistItem] = {}
    support_signal_by_guide: dict[str, dict[str, Any]] = {}
    support_matches = match_guide_support_candidates(
        situation_frame,
        visual_cues=visual_cues,
        context_text=context_text,
        require_observable_cue=True,
    )
    for support in support_matches:
        child_context = str(support.get("child_context") or "")
        support_score = float(support.get("support_score") or support.get("confidence") or 0)
        support_sr_ids = set(support.get("source_sr_ids") or [])
        has_non_broad_support_sr = bool(support_sr_ids - broad_sr_ids)
        for guide_code in support.get("guide_codes") or []:
            current = support_signal_by_guide.get(guide_code)
            if not current or support_score > float(current.get("support_score") or 0):
                support_signal_by_guide[guide_code] = {
                    "child_context": child_context,
                    "support_score": support_score,
                    "has_trigger_hit": bool(support.get("trigger_hits") or []),
                    "trigger_hits": list(support.get("trigger_hits") or []),
                    "has_non_broad_support_sr": has_non_broad_support_sr,
                    "match_policy": support.get("match_policy"),
                    "candidate_labels": list(support.get("candidate_labels") or []),
                }
            elif has_non_broad_support_sr:
                current["has_non_broad_support_sr"] = True
                current["candidate_labels"] = _unique(
                    [*(current.get("candidate_labels") or []), *(support.get("candidate_labels") or [])]
                )

    if sr_ids:
        rows = (
            db.query(PgChecklistItem, PgCiSrMapping.sr_id)
            .join(PgCiSrMapping, PgCiSrMapping.ci_id == PgChecklistItem.identifier)
            .filter(PgCiSrMapping.sr_id.in_(sr_ids))
            .limit(limit * 6)
            .all()
        )
        for ci, sr_id in rows:
            if _is_broad_secondary(sr_id, broad_sr_ids, direct_sr_set):
                pending_broad_rows[ci.identifier] = ci
                pending_broad_sr_by_ci[ci.identifier].add(sr_id)
                pending_broad_scores[ci.identifier] += 0.85 * broad_multiplier
                pending_broad_evidence[ci.identifier].append("broad asserted CI-SR")
                continue
            ci_rows[ci.identifier] = ci
            sr_by_ci[ci.identifier].add(sr_id)
            scores[ci.identifier] += 0.85 * (broad_multiplier if sr_id in broad_sr_ids else 1.0)
            evidence_by_ci[ci.identifier].append("asserted CI-SR")
            guide_specific_ci_ids.add(ci.identifier)

    she_ids = _she_ci_ids(she_matches)
    if she_ids:
        for ci in (
            db.query(PgChecklistItem)
            .filter(PgChecklistItem.identifier.in_(she_ids))
            .limit(limit * 3)
            .all()
        ):
            ci_rows[ci.identifier] = ci
            scores[ci.identifier] += 1.0
            evidence_by_ci[ci.identifier].append("SHE related checklist cue")
            guide_specific_ci_ids.add(ci.identifier)

    feature_codes = _flat_feature_codes(risk_features)
    try:
        if sr_ids:
            candidate_rows = (
                db.query(PgChecklistItem, PgGuideSrLinkCandidate)
                .join(PgGuideSrLinkCandidate, PgGuideSrLinkCandidate.entity_id == PgChecklistItem.identifier)
                .filter(PgGuideSrLinkCandidate.entity_type == "CI")
                .filter(PgGuideSrLinkCandidate.sr_id.in_(sr_ids))
                .filter(PgGuideSrLinkCandidate.confidence >= SERVING_CONFIDENCE)
                .filter(PgGuideSrLinkCandidate.review_status.in_(SERVING_REVIEW_STATUSES))
                .limit(limit * 6)
                .all()
            )
            for ci, candidate in candidate_rows:
                if _is_broad_secondary(candidate.sr_id, broad_sr_ids, direct_sr_set):
                    pending_broad_rows[ci.identifier] = ci
                    pending_broad_sr_by_ci[ci.identifier].add(candidate.sr_id)
                    pending_broad_scores[ci.identifier] += float(candidate.confidence or 0) * 0.8 * broad_multiplier
                    pending_broad_evidence[ci.identifier].append(candidate.evidence)
                    continue
                ci_rows[ci.identifier] = ci
                sr_by_ci[ci.identifier].add(candidate.sr_id)
                multiplier = broad_multiplier if candidate.sr_id in broad_sr_ids else 1.0
                scores[ci.identifier] += float(candidate.confidence or 0) * 0.8 * multiplier
                evidence_by_ci[ci.identifier].append(candidate.evidence)
                guide_specific_ci_ids.add(ci.identifier)

        if feature_codes:
            feature_rows = (
                db.query(PgChecklistItem, PgGuideEntityFeatureCandidate)
                .join(PgGuideEntityFeatureCandidate, PgGuideEntityFeatureCandidate.entity_id == PgChecklistItem.identifier)
                .filter(PgGuideEntityFeatureCandidate.entity_type == "CI")
                .filter(PgGuideEntityFeatureCandidate.feature_code.in_(feature_codes))
                .filter(PgGuideEntityFeatureCandidate.confidence >= SERVING_CONFIDENCE)
                .filter(PgGuideEntityFeatureCandidate.review_status.in_(SERVING_REVIEW_STATUSES))
                .limit(limit * 8)
                .all()
            )
            for ci, candidate in feature_rows:
                if _guide_specific_feature(candidate.feature_code):
                    ci_rows[ci.identifier] = ci
                    scores[ci.identifier] += float(candidate.confidence or 0) * 0.25
                    evidence_by_ci[ci.identifier].append(candidate.evidence)
                    guide_specific_ci_ids.add(ci.identifier)
                    continue
                pending_generic_feature_rows[ci.identifier] = ci
                pending_generic_feature_scores[ci.identifier] += float(candidate.confidence or 0) * 0.12
                pending_generic_feature_evidence[ci.identifier].append(candidate.evidence)
    except SQLAlchemyError:
        db.rollback()

    for identifier, pending_score in pending_generic_feature_scores.items():
        if identifier not in guide_specific_ci_ids and scores.get(identifier, 0.0) <= 0:
            continue
        ci_rows[identifier] = ci_rows.get(identifier) or pending_generic_feature_rows[identifier]
        scores[identifier] += pending_score
        evidence_by_ci[identifier].extend(pending_generic_feature_evidence.get(identifier, []))

    for identifier, pending_score in pending_broad_scores.items():
        if identifier not in guide_specific_ci_ids and scores.get(identifier, 0.0) <= 0:
            continue
        ci_rows[identifier] = ci_rows.get(identifier) or pending_broad_rows[identifier]
        scores[identifier] += pending_score
        sr_by_ci[identifier].update(pending_broad_sr_by_ci.get(identifier, set()))
        evidence_by_ci[identifier].extend(pending_broad_evidence.get(identifier, []))

    safe_fallback_sr_ids = fallback_sr_ids(sr_ids)
    if not ci_rows and safe_fallback_sr_ids and not preferred_guide_codes:
        return hazard_rule_engine.get_checklist_from_srs(db, safe_fallback_sr_ids, limit=limit)

    ranked = []
    for identifier, ci in ci_rows.items():
        score = scores[identifier] + _visual_bonus(ci.text or "", visual_cues)
        ranked.append((score, identifier, ci))
    ranked.sort(key=lambda row: row[0], reverse=True)

    source_guides = _unique([ci.source_guide for _, _, ci in ranked if ci.source_guide])
    guides = (
        {
            guide.guide_code: guide
            for guide in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(source_guides)).all()
        }
        if source_guides
        else {}
    )
    profile_bits = _guide_candidate_profile_bits(db, source_guides)

    results = []
    result_ids: set[str] = set()
    for score, identifier, ci in ranked:
        guide = guides.get(ci.source_guide)
        manual_profile = get_guide_domain_profile(ci.source_guide)
        domain_decision = evaluate_guide_domain_profile(
            guide_code=ci.source_guide,
            title=guide.title if guide else None,
            profile_text=_domain_profile_text(guide, profile_bits=profile_bits.get(ci.source_guide, [])),
            industry_contexts=industry_contexts,
            risk_feature_codes=feature_codes,
            visual_cues=visual_cues,
            context_text=context_text,
        )
        has_she_cue = any("SHE related checklist cue" in item for item in evidence_by_ci.get(identifier, []))
        if not _ci_reference_role_allowed(manual_profile, visual_cues, context_text, has_she_cue=has_she_cue):
            continue
        if domain_decision.exclude or (domain_decision.alignment == "domain_mismatch" and not has_she_cue):
            continue
        results.append({
            "identifier": ci.identifier,
            "text": ci.text,
            "binding_force": ci.binding_force,
            "source_guide": ci.source_guide,
            "source_section": ci.source_section,
            "source_sr_ids": sorted(sr_by_ci.get(identifier, set())),
            "relevance_score": round(min(0.99, score / 2.0), 4),
            "evidence_summary": "; ".join(_unique(evidence_by_ci.get(identifier, []))[:3]),
        })
        result_ids.add(ci.identifier)
        if len(results) >= limit:
            break

    primary_fallback_sr_ids = usable_primary_sr_ids(sr_ids, direct_sr_ids)
    if len(results) < limit and preferred_guide_codes and primary_fallback_sr_ids:
        preferred = _unique(preferred_guide_codes)[:2]
        fallback_rows = (
            db.query(PgChecklistItem, PgCiSrMapping.sr_id)
            .join(PgCiSrMapping, PgCiSrMapping.ci_id == PgChecklistItem.identifier)
            .filter(PgChecklistItem.source_guide.in_(preferred))
            .filter(PgCiSrMapping.sr_id.in_(primary_fallback_sr_ids))
            .limit(max(20, (limit - len(results)) * 6))
            .all()
        )
        fallback_scores: dict[str, float] = defaultdict(float)
        fallback_srs: dict[str, set[str]] = defaultdict(set)
        fallback_ci: dict[str, PgChecklistItem] = {}
        fallback_evidence: dict[str, list[str]] = defaultdict(list)
        preferred_rank = {guide_code: index for index, guide_code in enumerate(preferred)}
        for ci, sr_id in fallback_rows:
            if ci.identifier in result_ids:
                continue
            manual_profile = get_guide_domain_profile(ci.source_guide)
            if not _ci_reference_role_allowed(manual_profile, visual_cues, context_text):
                continue
            context_bonus, context_evidence = _ci_context_bonus(ci, manual_profile, visual_cues, context_text)
            fallback_ci[ci.identifier] = ci
            fallback_srs[ci.identifier].add(sr_id)
            fallback_scores[ci.identifier] += 0.58 + context_bonus
            fallback_evidence[ci.identifier].extend(context_evidence)
        fallback_ranked = sorted(
            fallback_ci.items(),
            key=lambda item: (
                -fallback_scores[item[0]],
                preferred_rank.get(item[1].source_guide or "", 99),
                item[1].identifier,
            ),
        )
        for identifier, ci in fallback_ranked:
            if identifier in result_ids:
                continue
            results.append({
                "identifier": ci.identifier,
                "text": ci.text,
                "binding_force": ci.binding_force,
                "source_guide": ci.source_guide,
                "source_section": ci.source_section,
                "source_sr_ids": sorted(fallback_srs.get(identifier, set())),
                "relevance_score": round(min(0.82, 0.48 + fallback_scores[identifier] * 0.04), 4),
                "evidence_summary": "; ".join(
                    ["domain-safe top Guide CI-SR fallback", *_unique(fallback_evidence.get(identifier, []))[:2]]
                ),
            })
            result_ids.add(identifier)
            if len(results) >= limit:
                break

    if len(results) < limit and preferred_guide_codes:
        preferred = _unique(preferred_guide_codes)[:3]
        eligible_guides: list[str] = []
        guide_profiles: dict[str, dict | None] = {}
        guide_support: dict[str, dict[str, Any] | None] = {}
        guide_support_allowed: dict[str, bool] = {}
        guide_contextual_allowed: dict[str, bool] = {}
        for guide_code in preferred:
            manual_profile = get_guide_domain_profile(guide_code)
            support_signal = support_signal_by_guide.get(guide_code)
            if not _ci_reference_role_allowed(manual_profile, visual_cues, context_text):
                continue
            support_score, _, support_signal_ok = _support_profile_usage_signal(support_signal, manual_profile)
            usage_score, _, usage_signal_ok = _score_usage_profile(
                manual_profile,
                visual_cues=visual_cues,
                context_text=context_text,
                feature_codes=feature_codes,
                industry_contexts=industry_contexts,
            )
            if support_signal_ok and support_score > 0 and not _ci_wp_relevance_support_allowed(support_signal):
                support_signal_ok = False
                support_score = 0.0
            support_allowed = support_signal_ok and support_score > 0
            contextual_allowed = (
                allow_contextual_ci_fallback
                and _contextual_ci_fallback_allowed(situation_frame, visual_cues, context_text)
                and usage_signal_ok
                and usage_score >= 0.08
            )
            if not (support_allowed or contextual_allowed):
                continue
            guide_profiles[guide_code] = manual_profile
            guide_support[guide_code] = support_signal
            guide_support_allowed[guide_code] = support_allowed
            guide_contextual_allowed[guide_code] = contextual_allowed
            eligible_guides.append(guide_code)

        if eligible_guides:
            wp_rows = (
                db.query(PgWorkProcess)
                .filter(PgWorkProcess.source_guide.in_(eligible_guides))
                .order_by(PgWorkProcess.source_guide, PgWorkProcess.process_order)
                .all()
            )
            wp_by_guide: dict[str, list[PgWorkProcess]] = defaultdict(list)
            for wp in wp_rows:
                wp_by_guide[wp.source_guide].append(wp)
            preferred_sections: dict[str, list[str]] = {}
            for guide_code in eligible_guides:
                ranked_wps = _rank_work_processes(
                    wp_by_guide.get(guide_code, []),
                    profile=guide_profiles.get(guide_code),
                    visual_cues=visual_cues,
                    context_text=context_text,
                    wp_sr_map=defaultdict(set),
                )
                preferred_sections[guide_code] = _unique(
                    [wp.source_section for wp in ranked_wps[:3] if wp.source_section]
                )

            local_rows = (
                db.query(PgChecklistItem)
                .filter(PgChecklistItem.source_guide.in_(eligible_guides))
                .limit(max(80, (limit - len(results)) * 30))
                .all()
            )
            local_ci_ids = [ci.identifier for ci in local_rows]
            local_ci_srs: dict[str, set[str]] = defaultdict(set)
            if local_ci_ids:
                for mapping in db.query(PgCiSrMapping).filter(PgCiSrMapping.ci_id.in_(local_ci_ids)).all():
                    local_ci_srs[mapping.ci_id].add(mapping.sr_id)
            preferred_rank = {guide_code: index for index, guide_code in enumerate(eligible_guides)}
            local_scores: dict[str, float] = defaultdict(float)
            local_reasons: dict[str, list[str]] = defaultdict(list)
            local_ci: dict[str, PgChecklistItem] = {}
            for ci in local_rows:
                if ci.identifier in result_ids:
                    continue
                mapped_srs = local_ci_srs.get(ci.identifier, set())
                if mapped_srs and mapped_srs <= broad_sr_ids:
                    continue
                manual_profile = guide_profiles.get(ci.source_guide)
                support_signal = guide_support.get(ci.source_guide)
                support_allowed = guide_support_allowed.get(ci.source_guide or "", False)
                contextual_allowed = guide_contextual_allowed.get(ci.source_guide or "", False)
                context_bonus, context_evidence = _ci_context_bonus(ci, manual_profile, visual_cues, context_text)
                support_bonus, support_evidence = _ci_support_bonus(ci, support_signal, manual_profile)
                section_bonus = 0.10 if _section_matches(
                    ci.source_section,
                    preferred_sections.get(ci.source_guide or "", []),
                ) else 0.0
                if support_allowed:
                    if support_bonus <= 0 and context_bonus <= 0:
                        continue
                elif contextual_allowed:
                    if context_bonus <= 0:
                        continue
                else:
                    continue
                binding_bonus = 0.08 if str(ci.binding_force or "").upper() == "MANDATORY" else 0.0
                local_ci[ci.identifier] = ci
                local_scores[ci.identifier] += 0.42 + context_bonus + support_bonus + section_bonus + binding_bonus
                if mapped_srs:
                    sr_by_ci[ci.identifier].update(mapped_srs)
                if context_evidence:
                    local_reasons[ci.identifier].extend(context_evidence)
                if support_evidence:
                    local_reasons[ci.identifier].extend(support_evidence)
                if section_bonus:
                    local_reasons[ci.identifier].append("CI section matches ranked WP")
            local_ranked = sorted(
                local_ci.items(),
                key=lambda item: (
                    -local_scores[item[0]],
                    preferred_rank.get(item[1].source_guide or "", 99),
                    0 if str(item[1].binding_force or "").upper() == "MANDATORY" else 1,
                    item[1].identifier,
                ),
            )
            for identifier, ci in local_ranked:
                if identifier in result_ids:
                    continue
                results.append({
                    "identifier": ci.identifier,
                    "text": ci.text,
                    "binding_force": ci.binding_force,
                    "source_guide": ci.source_guide,
                    "source_section": ci.source_section,
                    "source_sr_ids": sorted(sr_by_ci.get(identifier, set())),
                    "relevance_score": round(min(0.78, 0.42 + local_scores[identifier] * 0.08), 4),
                    "evidence_summary": "; ".join(
                        ["guide-local contextual CI fallback", *_unique(local_reasons.get(identifier, []))[:3]]
                    ),
                })
                result_ids.add(identifier)
                if len(results) >= limit:
                    break
    return results


def get_standard_guides(
    db: Session,
    sr_ids: list[str],
    direct_sr_ids: list[str] | None = None,
    limit: int = 6,
    industry_contexts: list[str] | None = None,
    risk_features: list[Any] | None = None,
    she_matches: list[Any] | None = None,
    visual_cues: list[str] | None = None,
    context_text: str | None = None,
    situation_frame: dict | None = None,
    apply_photo_top_gate: bool = True,
    allow_support_without_observable_cue: bool = False,
) -> list[dict]:
    """Return Guide recommendations centered on WorkProcess steps."""
    industry_contexts = industry_contexts or []
    guide_scores: dict[str, float] = defaultdict(float)
    guide_reasons: dict[str, list[str]] = defaultdict(list)
    wp_sr_map: dict[str, set[str]] = defaultdict(set)
    feature_codes = _flat_feature_codes(risk_features)
    direct_sr_set = set(direct_sr_ids or [])
    broad_sr_ids = get_broad_sr_ids()
    broad_multiplier = get_secondary_score_multiplier()
    primary_sr_ids = usable_primary_sr_ids(sr_ids, direct_sr_ids)
    safe_fallback_sr_ids = fallback_sr_ids(sr_ids)
    pending_broad_scores: dict[str, float] = defaultdict(float)
    pending_broad_reasons: dict[str, list[str]] = defaultdict(list)
    pending_broad_wp_sr_map: dict[str, set[str]] = defaultdict(set)
    pending_broad_wp_source: dict[str, str] = {}
    pending_generic_feature_scores: dict[str, float] = defaultdict(float)
    pending_generic_feature_reasons: dict[str, list[str]] = defaultdict(list)
    guide_specific_signals: set[str] = set()
    usage_profile_signals: set[str] = set()
    support_signal_by_guide: dict[str, dict[str, Any]] = {}
    context_blob = _context_blob(visual_cues, context_text)
    she_source_guides = _she_source_guides(she_matches)
    support_matches = match_guide_support_candidates(
        situation_frame,
        visual_cues=visual_cues,
        context_text=context_text,
        require_observable_cue=not allow_support_without_observable_cue,
    )
    support_guide_codes = {
        guide_code
        for support in support_matches
        for guide_code in (support.get("guide_codes") or [])
    }
    support_only_mode = bool(support_matches) and not sr_ids and not she_source_guides
    if not sr_ids and not she_source_guides and not support_matches:
        return []
    if _standard_procedure_safe_context_blocked(situation_frame, visual_cues, context_text):
        return []

    for guide_code in she_source_guides:
        guide_scores[guide_code] += 1.0
        guide_reasons[guide_code].append("SHE source guide")
        guide_specific_signals.add(guide_code)

    for support in support_matches:
        guide_codes = support.get("guide_codes") or []
        child_context = str(support.get("child_context") or "")
        support_score = float(support.get("support_score") or support.get("confidence") or 0)
        trigger_hits = support.get("trigger_hits") or []
        support_sr_ids = set(support.get("source_sr_ids") or [])
        has_non_broad_support_sr = bool(support_sr_ids - broad_sr_ids)
        for guide_code in guide_codes[:8]:
            guide_scores[guide_code] += min(0.16, support_score * 0.18)
            if trigger_hits:
                guide_reasons[guide_code].append(f"SituationFrame trigger support:{child_context}")
            else:
                guide_reasons[guide_code].append(f"SituationFrame child support:{child_context}")
            guide_specific_signals.add(guide_code)
            current = support_signal_by_guide.get(guide_code)
            if not current or support_score > float(current.get("support_score") or 0):
                support_signal_by_guide[guide_code] = {
                    "child_context": child_context,
                    "support_score": support_score,
                    "has_trigger_hit": bool(trigger_hits),
                    "trigger_hits": list(trigger_hits),
                    "has_non_broad_support_sr": has_non_broad_support_sr,
                    "match_policy": support.get("match_policy"),
                    "candidate_labels": list(support.get("candidate_labels") or []),
                }
            elif has_non_broad_support_sr:
                current["has_non_broad_support_sr"] = True
                current["candidate_labels"] = _unique(
                    [*(current.get("candidate_labels") or []), *(support.get("candidate_labels") or [])]
                )

    if sr_ids:
        rows = (
            db.query(PgWorkProcess, PgWpSrMapping.sr_id)
            .join(PgWpSrMapping, PgWpSrMapping.wp_id == PgWorkProcess.identifier)
            .filter(PgWpSrMapping.sr_id.in_(sr_ids))
            .limit(limit * 20)
            .all()
        )
        for wp, sr_id in rows:
            if _is_broad_secondary(sr_id, broad_sr_ids, direct_sr_set):
                pending_broad_scores[wp.source_guide] += 0.35 * broad_multiplier
                pending_broad_reasons[wp.source_guide].append("broad asserted WP-SR")
                pending_broad_wp_sr_map[wp.identifier].add(sr_id)
                pending_broad_wp_source[wp.identifier] = wp.source_guide
                continue
            guide_scores[wp.source_guide] += 0.35 * (broad_multiplier if sr_id in broad_sr_ids else 1.0)
            guide_reasons[wp.source_guide].append("asserted WP-SR")
            wp_sr_map[wp.identifier].add(sr_id)
            guide_specific_signals.add(wp.source_guide)

    try:
        if sr_ids:
            candidate_rows = (
                db.query(PgGuideSrLinkCandidate)
                .filter(PgGuideSrLinkCandidate.entity_type.in_(["WP", "GUIDE", "CI"]))
                .filter(PgGuideSrLinkCandidate.sr_id.in_(sr_ids))
                .filter(PgGuideSrLinkCandidate.confidence >= SERVING_CONFIDENCE)
                .filter(PgGuideSrLinkCandidate.review_status.in_(SERVING_REVIEW_STATUSES))
                .limit(limit * 30)
                .all()
            )
            for candidate in candidate_rows:
                weight = 0.34 if candidate.entity_type == "WP" else 0.18
                if _is_broad_secondary(candidate.sr_id, broad_sr_ids, direct_sr_set):
                    pending_broad_scores[candidate.guide_code] += (
                        float(candidate.confidence or 0) * weight * broad_multiplier
                    )
                    pending_broad_reasons[candidate.guide_code].append(f"broad {candidate.entity_type} SR candidate")
                    if candidate.entity_type == "WP":
                        pending_broad_wp_sr_map[candidate.entity_id].add(candidate.sr_id)
                        pending_broad_wp_source[candidate.entity_id] = candidate.guide_code
                    continue
                multiplier = broad_multiplier if candidate.sr_id in broad_sr_ids else 1.0
                guide_scores[candidate.guide_code] += float(candidate.confidence or 0) * weight * multiplier
                guide_reasons[candidate.guide_code].append(f"{candidate.entity_type} SR candidate")
                if candidate.entity_type == "WP":
                    wp_sr_map[candidate.entity_id].add(candidate.sr_id)
                guide_specific_signals.add(candidate.guide_code)

        if feature_codes:
            feature_rows = (
                db.query(PgGuideEntityFeatureCandidate)
                .filter(PgGuideEntityFeatureCandidate.entity_type.in_(["WP", "GUIDE", "CI"]))
                .filter(PgGuideEntityFeatureCandidate.feature_code.in_(feature_codes))
                .filter(PgGuideEntityFeatureCandidate.confidence >= SERVING_CONFIDENCE)
                .filter(PgGuideEntityFeatureCandidate.review_status.in_(SERVING_REVIEW_STATUSES))
                .limit(limit * 50)
                .all()
            )
            for candidate in feature_rows:
                if support_only_mode and candidate.guide_code not in support_guide_codes:
                    continue
                weight = 0.16 if candidate.entity_type == "WP" else 0.08
                if _guide_specific_feature(candidate.feature_code):
                    guide_scores[candidate.guide_code] += float(candidate.confidence or 0) * weight
                    guide_reasons[candidate.guide_code].append(f"{candidate.entity_type} feature")
                    guide_specific_signals.add(candidate.guide_code)
                    continue
                pending_generic_feature_scores[candidate.guide_code] += float(candidate.confidence or 0) * weight * 0.5
                pending_generic_feature_reasons[candidate.guide_code].append(f"generic {candidate.entity_type} feature")

        if context_blob:
            trigger_rows = (
                db.query(PgGuideVisualTriggerCandidate)
                .filter(PgGuideVisualTriggerCandidate.confidence >= SERVING_CONFIDENCE)
                .filter(PgGuideVisualTriggerCandidate.review_status.in_(SERVING_REVIEW_STATUSES))
                .limit(800)
                .all()
            )
            for candidate in trigger_rows:
                if support_only_mode and candidate.guide_code not in support_guide_codes:
                    continue
                if not _matches_visual_trigger(candidate, context_blob):
                    continue
                weight = 0.18 if candidate.entity_type == "WP" else 0.10
                guide_scores[candidate.guide_code] += float(candidate.confidence or 0) * weight
                guide_reasons[candidate.guide_code].append(f"{candidate.entity_type} visual trigger")
                guide_specific_signals.add(candidate.guide_code)
    except SQLAlchemyError:
        db.rollback()

    candidate_guide_codes = set(guide_scores) | set(pending_broad_scores) | set(pending_generic_feature_scores)
    for guide_code in sorted(candidate_guide_codes):
        usage_score, usage_reasons, usage_signal = _score_usage_profile(
            get_guide_domain_profile(guide_code),
            visual_cues=visual_cues,
            context_text=context_text,
            feature_codes=feature_codes,
            industry_contexts=industry_contexts,
        )
        if usage_score <= 0:
            usage_score, usage_reasons, usage_signal = _support_profile_usage_signal(
                support_signal_by_guide.get(guide_code),
                get_guide_domain_profile(guide_code),
            )
        if usage_score <= 0:
            continue
        guide_scores[guide_code] += usage_score
        guide_reasons[guide_code].extend(usage_reasons)
        if usage_signal:
            guide_specific_signals.add(guide_code)
            usage_profile_signals.add(guide_code)

    for guide_code, pending_score in pending_generic_feature_scores.items():
        if guide_code not in guide_specific_signals and guide_scores.get(guide_code, 0.0) <= 0:
            continue
        guide_scores[guide_code] += pending_score
        guide_reasons[guide_code].extend(pending_generic_feature_reasons.get(guide_code, []))

    for guide_code, pending_score in pending_broad_scores.items():
        if guide_code not in guide_specific_signals and guide_scores.get(guide_code, 0.0) <= 0:
            continue
        guide_scores[guide_code] += pending_score
        guide_reasons[guide_code].extend(pending_broad_reasons.get(guide_code, []))
    for wp_id, pending_srs in pending_broad_wp_sr_map.items():
        source_guide = pending_broad_wp_source.get(wp_id)
        if source_guide and source_guide not in guide_specific_signals:
            continue
        wp_sr_map[wp_id].update(pending_srs)

    if safe_fallback_sr_ids:
        for row in hazard_rule_engine.get_guides_from_srs(
            db,
            safe_fallback_sr_ids,
            limit=max(limit, 8),
            industry_contexts=industry_contexts,
        ):
            guide_code = row.get("guide_code")
            if not guide_code:
                continue
            guide_scores[guide_code] += float(row.get("relevance_score", 0) or 0) * 0.4
            guide_reasons[guide_code].append("CI-SR fallback")
            guide_specific_signals.add(guide_code)

    if not guide_scores:
        return []

    guide_codes = list(guide_scores)
    guides = {
        guide.guide_code: guide
        for guide in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(guide_codes)).all()
    }
    wp_rows = (
        db.query(PgWorkProcess)
        .filter(PgWorkProcess.source_guide.in_(guide_codes))
        .order_by(PgWorkProcess.source_guide, PgWorkProcess.process_order)
        .all()
    )
    wp_by_guide: dict[str, list[PgWorkProcess]] = defaultdict(list)
    for wp in wp_rows:
        wp_by_guide[wp.source_guide].append(wp)

    # Fill source_sr_ids for displayed steps even when they came from asserted mapping only.
    wp_ids = [wp.identifier for wp in wp_rows]
    if wp_ids:
        for mapping in db.query(PgWpSrMapping).filter(PgWpSrMapping.wp_id.in_(wp_ids)).all():
            if not sr_ids or mapping.sr_id in sr_ids:
                wp_sr_map[mapping.wp_id].add(mapping.sr_id)

    ci_by_guide: dict[str, set[str]] = defaultdict(set)
    if safe_fallback_sr_ids:
        rows = (
            db.query(PgChecklistItem.source_guide, PgChecklistItem.identifier)
            .join(PgCiSrMapping, PgCiSrMapping.ci_id == PgChecklistItem.identifier)
            .filter(PgCiSrMapping.sr_id.in_(safe_fallback_sr_ids))
            .limit(200)
            .all()
        )
        for guide_code, ci_id in rows:
            ci_by_guide[guide_code].add(ci_id)

    profile_bits = _guide_candidate_profile_bits(db, guide_codes)
    ranked_guides = []
    for guide_code, raw_score in guide_scores.items():
        guide = guides.get(guide_code)
        if not guide:
            continue
        manual_profile = get_guide_domain_profile(guide_code)
        domain_decision = evaluate_guide_domain_profile(
            guide_code=guide_code,
            title=guide.title,
            profile_text=_domain_profile_text(
                guide,
                work_processes=wp_by_guide.get(guide_code, []),
                profile_bits=profile_bits.get(guide_code, []),
            ),
            industry_contexts=industry_contexts,
            risk_feature_codes=feature_codes,
            visual_cues=visual_cues,
            context_text=context_text,
        )
        domain_overridden_by_support = False
        if domain_decision.exclude or domain_decision.alignment == "domain_mismatch":
            support_signal = support_signal_by_guide.get(guide_code) or {}
            trigger_backed_support = _trigger_backed_support_profile_override(support_signal, manual_profile)
            if trigger_backed_support:
                domain_overridden_by_support = True
                guide_reasons[guide_code].append(
                    f"support trigger profile-aligned domain override:{support_signal.get('child_context')}"
                )
            else:
                continue
        if (
            _strict_profile_usage_required(manual_profile)
            and guide_code not in usage_profile_signals
            and not _trigger_backed_support_profile_override(
                support_signal_by_guide.get(guide_code),
                manual_profile,
            )
        ):
            continue
        if (
            manual_profile
            and manual_profile.get("domain_family") in CONTEXT_REQUIRED_DOMAIN_FAMILIES
            and guide_code not in she_source_guides
            and guide_code not in support_guide_codes
            and not _term_hits(_context_blob(visual_cues, context_text), _manual_profile_terms(manual_profile), limit=1)
            and not (
                set(feature_codes)
                & CONTEXT_REQUIRED_FAMILY_FEATURE_ALLOW.get(str(manual_profile.get("domain_family")), set())
            )
        ):
            continue
        if (
            manual_profile
            and str(manual_profile.get("profile_level") or "general") == "general"
            and guide_code not in she_source_guides
            and guide_code not in support_guide_codes
            and guide_code not in usage_profile_signals
        ):
            continue
        if not _reference_role_context_hit(manual_profile, visual_cues, context_text):
            continue
        photo_policy = get_photo_matchability(guide_code, manual_profile)
        photo_matchability = str(photo_policy.get("photo_matchability") or PHOTO_ACTIONABLE)
        photo_lane = "primary"
        if apply_photo_top_gate:
            if top_photo_allowed(guide_code, manual_profile):
                photo_lane = "primary"
            elif followup_photo_allowed(
                guide_code,
                manual_profile,
                visual_cues=visual_cues,
                context_text=context_text,
            ):
                photo_lane = "followup"
            else:
                guide_reasons[guide_code].append(f"photo_matchability suppressed:{photo_matchability}")
                continue
        guide_industry = infer_industry_context(text=" ".join(filter(None, [guide.title, guide.sub_category])))
        industry_adjustment, industry_alignment, _ = score_industry_alignment(
            guide_industry.active_industries,
            industry_contexts,
        )
        if domain_decision.family and not domain_overridden_by_support:
            guide_reasons[guide_code].append(
                f"{domain_decision.level}:{domain_decision.alignment}:{domain_decision.family}"
            )
        displayed_alignment = (
            "domain_match"
            if domain_overridden_by_support
            else (
            domain_decision.alignment
            if domain_decision.alignment != "general"
            else industry_alignment
            )
        )
        final_score = min(
            0.99,
            max(0.0, 0.45 + raw_score * 0.12 + industry_adjustment + domain_decision.score_adjustment),
        )
        if apply_photo_top_gate and photo_matchability == PHOTO_CONDITIONAL_FOLLOWUP:
            final_score = min(final_score, 0.62)
            guide_reasons[guide_code].append("photo_matchability followup")
        elif apply_photo_top_gate and photo_matchability == PHOTO_UNMATCHABLE:
            final_score = min(final_score, 0.56)
            guide_reasons[guide_code].append("photo_matchability explicit reference followup")
        ranked_guides.append((final_score, displayed_alignment, guide_code, guide, photo_lane, photo_matchability))
    ranked_guides.sort(key=lambda row: row[0], reverse=True)
    if apply_photo_top_gate:
        primary_guides = [row for row in ranked_guides if row[4] == "primary"]
        followup_guides = [row for row in ranked_guides if row[4] == "followup"]
        selected_guides = primary_guides[:limit]
        if selected_guides and len(selected_guides) < limit and followup_guides:
            selected_guides.extend(followup_guides[:1])
    else:
        selected_guides = ranked_guides[:limit]

    results = []
    for final_score, industry_alignment, guide_code, guide, _photo_lane, _photo_matchability in selected_guides:
        steps = []
        manual_profile = get_guide_domain_profile(guide_code)
        ranked_work_processes = _rank_work_processes(
            wp_by_guide.get(guide_code, []),
            profile=manual_profile,
            visual_cues=visual_cues,
            context_text=context_text,
            wp_sr_map=wp_sr_map,
        )
        for wp in ranked_work_processes[:8]:
            steps.append({
                "step_id": wp.identifier,
                "order": int(wp.process_order or len(steps) + 1),
                "title": wp.process_name,
                "safety_measures": wp.safety_measures,
                "source_section": wp.source_section,
                "source_sr_ids": sorted(wp_sr_map.get(wp.identifier, set())),
            })
        source_sr_ids = sorted({sr for step in steps for sr in step.get("source_sr_ids", [])})
        results.append({
            "guide_code": guide.guide_code,
            "title": guide.title,
            "classification": guide.domain,
            "industry_alignment": industry_alignment,
            "relevant_sections": [step.get("source_section") for step in steps if step.get("source_section")],
            "relevance_score": round(final_score, 4),
            "mapping_type": "she_sr_wp_guide",
            "ci_hit_count": len(ci_by_guide.get(guide_code, set())),
            "work_process_steps": steps,
            "source_sr_ids": source_sr_ids or primary_sr_ids[:5],
            "source_ci_ids": sorted(ci_by_guide.get(guide_code, set()))[:12],
            "evidence_summary": "; ".join(_unique(guide_reasons.get(guide_code, []))[:4]),
        })
    return results
