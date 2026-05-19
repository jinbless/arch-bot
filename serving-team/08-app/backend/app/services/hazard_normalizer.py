"""LLM 위험 특징 후보를 risk:RiskFeature 계열 코드로 정규화한다.

입력: visual_cues/risk_feature_candidates
출력: SHE/SR 매칭에 사용할 사고유형, 유해인자, 작업맥락 코드
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ALIASES = None
_TAXONOMY = None
_CANDIDATE_ALIASES = None

TEXT_WORK_CONTEXT_HINTS = {
    "ELECTRICAL_WORK": [
        "분전반", "차단기", "활선", "충전부", "접지", "누전", "전기 작업",
        "전선", "케이블", "멀티탭",
    ],
    "LADDER": ["사다리", "발판", "3점 지지", "최상부"],
    "CHEMICAL_WORK": [
        "화학", "MSDS", "드럼", "용제", "분말", "유기용제", "화학물질",
    ],
    "WELDING": ["용접", "아크", "차광", "용접 흄", "흄"],
    "LIFT_WORK": ["리프트", "차량 하부", "잭 스탠드", "고정 핀", "하부 작업"],
    "OIL_DRAIN": ["폐오일", "오일팬", "오일 팬", "오일 드레인", "엔진오일"],
    "TIRE_CHANGE": ["타이어", "공기압", "에어 임팩트", "임팩트 렌치", "고압 에어"],
    "WELDING_REPAIR": ["차체 용접", "연료 탱크", "용접 수리", "용접 불꽃"],
    "EV_BATTERY": ["전기차", "고전압 배터리", "배터리 커버", "절연 장갑"],
    "HAIR_CHEMICAL": ["파마약", "염색약", "미용 약품", "헤어 화학"],
    "NAIL_CHEMICAL": ["네일", "아세톤", "리무버", "젤 네일", "알코올 램프"],
    "HOT_TOOL": ["고데기", "드라이어", "열기구", "고온 도구", "미용기구"],
    "SKIN_DEVICE": ["피부 장비", "레이저", "자외선", "광선 장비", "피부관리"],
    "HAIR_WASH": ["샴푸", "세정", "머리 감기", "샴푸대", "온수"],
    "SHELF_STOCKING": ["진열대", "선반", "상품 진열", "매대", "상부 선반"],
    "NIGHT_SOLO": ["야간", "단독 근무", "심야", "혼자 근무"],
    "COLD_DISPLAY": ["냉장 진열대", "냉동 진열대", "쇼케이스", "냉장고"],
    "BOX_HANDLING": ["박스", "상자", "적재", "운반", "물류 박스"],
    "CASHIER_AREA": ["계산대", "카운터", "전선", "멀티탭", "고객 통로"],
    "SAWING": ["톱", "절단기", "원형톱", "목재 절단", "테이블쏘"],
    "SANDING": ["샌딩", "연마", "분진", "샌더", "목분"],
    "PAINTING_WOODWORK": ["도장", "페인트", "스테인", "희석제", "목공 도장"],
    "LADDER_INTERIOR": ["실내 사다리", "인테리어 사다리", "천장 작업", "벽면 작업"],
    "NAIL_GUN": ["타카", "네일건", "공압 공구", "못 박기", "에어 타카"],
}

TEXT_WORK_CONTEXT_HINTS.update({
    "DRY_CLEANING_SOLVENT": ["드라이클리닝", "PERC", "퍼클로로에틸렌", "세탁 용제"],
    "PRESS_MACHINE": ["프레스", "프레스 기계"],
    "WASHING_MACHINE": ["세탁기"],
    "STEAM_IRON": ["스팀 다리미", "다리미"],
    "CHEMICAL_SPOTTING": ["얼룩 제거", "스팟팅"],
    "GARMENT_SORTING": ["세탁물 분류", "의류 분류"],
    "HIGH_PRESSURE_WASH": ["고압 세척", "고압 세척기"],
    "CHEMICAL_APPLICATION": ["세차 화학약품", "화학 약품 도포"],
    "WAX_POLISHING": ["왁스", "광택"],
    "CONVEYOR_WASH": ["컨베이어 세차"],
    "INTERIOR_CLEANING": ["차량 내부 청소", "실내 청소"],
    "WET_FLOOR_WORK": ["젖은 바닥", "습윤 바닥"],
    "DOG_GROOMING": ["강아지 미용", "애견 미용"],
    "CAT_HANDLING": ["고양이 취급", "고양이 핸들링"],
    "PET_BATHING": ["반려동물 목욕", "펫 목욕"],
    "DRYER_OPERATION": ["건조기", "드라이어"],
    "CAGE_CLEANING": ["케이지 청소"],
    "ANIMAL_FEEDING": ["동물 급식", "사료 급여"],
    "FORKLIFT_OPERATION": ["지게차 작업", "지게차"],
    "HEAVY_LIFTING": ["중량물", "과하중"],
    "HIGH_SHELF_WORK": ["높은 선반", "고소 선반"],
    "LOADING_DOCK": ["하역 도크", "도크"],
    "PACKAGE_SORTING": ["택배 분류", "소포 분류"],
    "CONVEYOR_BELT": ["컨베이어 벨트"],
    "PESTICIDE_SPRAY": ["농약 살포", "살충제 살포"],
    "FARM_MACHINERY": ["농기계", "트랙터", "관리기"],
    "GREENHOUSE_WORK": ["온실", "비닐하우스"],
    "HARVEST_WORK": ["수확", "농경지"],
    "IRRIGATION": ["관개", "수로"],
    "FERTILIZER_HANDLING": ["비료 취급", "비료"],
    "ELECTRICAL_OVERLOAD": ["전기 과부하", "멀티탭 과부하"],
    "FIRE_EVACUATION": ["비상구", "화재 대피", "유도등"],
    "VENTILATION_POOR": ["환기 불량", "밀폐 환기"],
    "CLEANING_NIGHT": ["야간 청소"],
    "CROWD_MANAGEMENT": ["과밀", "밀집 인원"],
    "NOISE_EXPOSURE": ["소음 노출", "고소음"],
    "FUEL_DISPENSING": ["주유", "주유기"],
    "STATIC_ELECTRICITY": ["정전기"],
    "FUEL_SPILL": ["연료 유출", "휘발유 유출"],
    "UNDERGROUND_TANK": ["지하 탱크", "탱크 맨홀"],
    "VAPOR_EXPOSURE": ["유증기", "연료 증기"],
    "NIGHT_SOLO_WORK": ["야간 단독", "심야 단독"],
})

WORK_CONTEXT_CODE_ALIASES = {
    "ELECTRICITY_WORK": "ELECTRICAL_WORK",
    "ELECTRIC_WORK": "ELECTRICAL_WORK",
    "PESTICIDE_APPLICATION": "PESTICIDE_SPRAY",
    "ORCHARD_LADDER": "LADDER",
    "TUNNEL_SUPPORT": "EXCAVATION",
    "SHAFT_HOIST": "CRANE",
    "COMPACTOR_OPERATION": "MACHINE",
    "SHREDDER_OPERATION": "MACHINE",
    "TRUCK_COUPLING": "VEHICLE",
    "PLANER_JOINTER": "SAWING",
    "SEWING_MACHINE": "MACHINE",
    "NEEDLE_BROKEN": "MACHINE",
    "YARN_WINDING": "MACHINE",
    "PAPER_CUTTING": "MACHINE",
    "NEEDLESTICK": "MATERIAL_HANDLING",
    "PATIENT_TRANSFER": "GENERAL_WORKPLACE",
    "MEDICAL_WASTE": "MATERIAL_HANDLING",
    "MEDICATION_HANDLING": "MATERIAL_HANDLING",
    "DYEING_FINISHING": "CHEMICAL_WORK",
    "SOLVENT_CLEANING": "CHEMICAL_WORK",
    "CHEMICAL_MIXING": "CHEMICAL_WORK",
    "SCALDING_DEHAIRING": "MACHINE",
    "CONVEYOR_HOOK": "CONVEYOR_BELT",
    "CARDIO_EQUIPMENT": "MACHINE",
    "CREMATION_FURNACE": "CHEMICAL_WORK",
}

WORK_CONTEXT_CODE_ALIAS_RULES = [
    (("RADIATION_XRAY", "XRAY", "X_RAY", "X-RAY", "PLATE_MAKING", "UV_COATING"), "CHEMICAL_WORK"),
    (("EQUIPMENT_MAINTENANCE", "CHAMBER_MAINTENANCE"), "MACHINE"),
    (("COMPOUND_MIXING", "OPEN_MILL", "KNEE_BAR"), "MACHINE"),
    (("CONFINED", "TANK_ENTRY"), "CONFINED_SPACE"),
    (("SCAFFOLD",), "SCAFFOLD"),
    (("EXCAVATION", "TRENCH", "EARTH_RETAINING", "UNDERGROUND_UTILITY"), "EXCAVATION"),
    (("CRANE",), "CRANE"),
    (("FORKLIFT",), "FORKLIFT_OPERATION"),
    (("CONVEYOR",), "CONVEYOR_BELT"),
    (("LADDER",), "LADDER"),
    (("ROPE", "HIGH_RISE_WINDOW", "ROOF", "ELEVATED", "DECKING"), "ROPE_ACCESS"),
    (("WELDING", "HOT_WORK"), "WELDING"),
    (("ELECTRIC", "ELECTRICAL", "HIGH_VOLTAGE", "ESD", "SOLDER"), "ELECTRICAL_WORK"),
    (("CHEMICAL", "SOLVENT", "ACID", "ETCH", "HF", "LAB_", "REACTOR", "DISTILLATION", "HAZMAT", "INK", "VULCANIZATION", "COMPOUND"), "CHEMICAL_WORK"),
    (("SPRAY_PAINT", "PAINT", "SURFACE_FINISHING", "AIRLESS"), "PAINTING"),
    (("SURFACE_PREP", "GRIND", "SANDING", "POLISH"), "GRINDING"),
    (("KNIFE",), "FOOD_PREP"),
    (("LATHE", "MILLING", "PRESS", "STAMPING", "MACHINE", "MOLD", "EXTRUSION", "SAW", "CUTTER", "SLICER", "GRINDER", "AUTOCLAVE", "STERILIZATION", "FOOD_PROCESSING", "DOUGH", "PRINTING", "FOLDING", "GUILLOTINE", "PACKAGING", "COMPACTOR", "SHREDDER", "PLANER", "JOINTER", "SEWING", "YARN", "PAPER_CUTTING"), "MACHINE"),
    (("FORMWORK", "CONCRETE", "SOIL_COMPACTION", "PUMP_OPERATION"), "CONSTRUCTION_EQUIP"),
    (("REBAR", "STEEL_ERECTION"), "STEELWORK"),
    (("PICKING",), "PACKAGE_SORTING"),
    (("RACKING",), "HIGH_SHELF_WORK"),
    (("MATERIAL", "HANDLING", "HEAVY", "BOX", "STORAGE", "LOADING", "WASTE", "LANDFILL", "RECYCLING", "BODY_TRANSPORT", "MEDICAL_WASTE", "NEEDLESTICK", "SHARPS"), "MATERIAL_HANDLING"),
    (("VEHICLE_LIFT", "ENGINE_OVERHAUL", "BRAKE_EXHAUST"), "LIFT_WORK"),
    (("TIRE_WHEEL",), "TIRE_CHANGE"),
    (("COLD", "FREEZER", "ICE"), "COLD_STORAGE"),
    (("WET", "FLOOR", "CLEANING", "RESTROOM", "SANITATION", "FISH", "POOL", "AQUACULTURE"), "WET_FLOOR_WORK"),
    (("OVEN", "HOT_TRAY", "BAKING", "KITCHEN"), "KITCHEN_COOKING"),
    (("DISPLAY", "SERVING"), "SERVING_FLOOR"),
    (("FREE_WEIGHT",), "HEAVY_LIFTING"),
    (("CARDIO", "CLIMBING", "EXERCISE"), "GENERAL_WORKPLACE"),
    (("FUNERAL", "EMBALMING", "CREMATION", "DENTAL", "CLEANROOM", "FLORAL", "OUTDOOR_PLAY"), "GENERAL_WORKPLACE"),
    (("FUEL", "GAS_STATION"), "FUEL_DISPENSING"),
    (("VENTILATION",), "VENTILATION_POOR"),
    (("NOISE",), "NOISE_EXPOSURE"),
    (("PESTICIDE", "FERTILIZER", "GREENHOUSE", "HARVEST", "IRRIGATION", "FARM"), "HARVEST_WORK"),
]

CONTAINED_ALIAS_MIN_LEN = 2
CONTAINED_ALIAS_BLOCKLIST = {"위험", "작업", "사고", "부상", "접촉", "기타", "확인"}

STAGE2_V2_AXIS_ALIASES = {
    "accident_type": {
        "낙상": "FALL",
        "고소 추락": "FALL",
        "사다리 추락": "FALL",
        "말림": "CRUSH",
        "회전체 부상": "CRUSH",
        "손가락 부상": "CRUSH",
        "절상": "CUT",
        "칼날 절상": "CUT",
        "근골격계 장애": "ERGONOMIC",
        "근골격계 질환": "ERGONOMIC",
        "근골격계 부상": "ERGONOMIC",
        "요추 부상": "ERGONOMIC",
        "고온 화상": "BURN",
        "증기 화상": "BURN",
        "열 화상": "BURN",
        "화학물질 흡입": "CHEMICAL_EXPOSURE",
        "화학 흡입": "CHEMICAL_EXPOSURE",
        "화학 증기 흡입": "CHEMICAL_EXPOSURE",
    }
}

def _load_aliases() -> dict:
    global _ALIASES
    if _ALIASES is None:
        path = Path(__file__).parent.parent / "data" / "risk_feature_aliases.json"
        with open(path, "r", encoding="utf-8") as f:
            _ALIASES = json.load(f)
    return _ALIASES


def _load_taxonomy() -> dict:
    global _TAXONOMY
    if _TAXONOMY is None:
        path = Path(__file__).parent.parent / "data" / "risk_feature_catalog.json"
        with open(path, "r", encoding="utf-8") as f:
            _TAXONOMY = json.load(f)
    return _TAXONOMY


def _load_candidate_aliases() -> dict:
    """Phase F.1 — load risk_feature_aliases_candidates.json (level=candidate aliases).

    Cascade step 4.5: tier1 vetted 직후, contained-term fallback 직전 조회.
    파일 미존재 시 빈 dict 반환 → cascade 영향 0 (R2 no-op invariant).
    """
    global _CANDIDATE_ALIASES
    if _CANDIDATE_ALIASES is None:
        path = Path(__file__).parent.parent / "data" / "risk_feature_aliases_candidates.json"
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _CANDIDATE_ALIASES = json.load(f)
            except Exception:
                _CANDIDATE_ALIASES = {"tier1": {}}
        else:
            _CANDIDATE_ALIASES = {"tier1": {}}
    return _CANDIDATE_ALIASES


def _log_alias_usage(axis: str, code: str, alias: str) -> None:
    """T1.C — Log candidate alias usage to enable promote_aliases.py --auto mode.

    Append per-match to alias_candidate_meta.jsonl. promote_aliases aggregates
    rows to compute meta.uses count + last_used_at timestamp.
    Best-effort: failures don't break normalizer.
    """
    try:
        from datetime import datetime, timezone
        backend_app = Path(__file__).resolve().parents[1]
        for ancestor in backend_app.parents:
            artifacts_dir = ancestor / "data-team" / "05-enrichment" / "runtime-artifacts"
            if artifacts_dir.exists():
                meta_path = artifacts_dir / "alias_candidate_meta.jsonl"
                break
        else:
            return
        ts = datetime.now(timezone.utc).isoformat()
        row = {"ts": ts, "action": "used", "alias": alias, "axis": axis, "code": code}
        with meta_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass  # best-effort, don't break normalizer


def _get_valid_codes(axis: str) -> set:
    """축별 유효 코드 세트 (sub 포함)."""
    tax = _load_taxonomy()
    axis_data = tax.get("axes", {}).get(axis, {})
    codes = set()
    for code, info in axis_data.get("codes", {}).items():
        codes.add(code)
        for sub in info.get("sub", []):
            codes.add(sub)
    return codes


def _stage2_v2_enabled() -> bool:
    return os.getenv("OHS_ENABLE_STAGE2_NORMALIZATION_V2", "").lower() in {"1", "true", "yes", "on"}


def _resolve_work_context_code_alias(raw_text: str, valid: set[str]) -> Optional[str]:
    upper = raw_text.upper().strip()
    mapped = WORK_CONTEXT_CODE_ALIASES.get(upper)
    if mapped in valid:
        return mapped
    for terms, code in WORK_CONTEXT_CODE_ALIAS_RULES:
        if code in valid and any(term in upper for term in terms):
            return code
    return None


def _term_matches_raw(term: str, raw_text: str) -> bool:
    term_text = str(term or "").strip()
    if len(term_text) < CONTAINED_ALIAS_MIN_LEN or term_text in CONTAINED_ALIAS_BLOCKLIST:
        return False
    raw_compact = raw_text.replace(" ", "")
    term_compact = term_text.replace(" ", "")
    return bool(term_compact and (term_compact in raw_compact or raw_compact in term_compact))


def _resolve_alias_code(raw_code: str, axis: str) -> Optional[str]:
    """GPT가 반환한 코드를 정규화. 유효하면 그대로, alias면 해석, 무효면 None."""
    raw_text = str(raw_code or "").strip()
    upper = raw_text.upper()
    lower = raw_text.lower()
    valid = _get_valid_codes(axis)

    # 직접 매칭
    if upper in valid:
        return upper

    # Phase F.1 Day 6.5 — Vision LLM이 'FALLING OBJECT' 같이 공백 들어간 영어 변형 생성하는
    # 패턴 대응. catalog UPPER_SNAKE_CASE 규약에 맞춰 공백→underscore 정규화.
    # 9 production miss 중 'FALLING OBJECT', 'falling object' 등 instant 해결.
    upper_normalized = upper.replace(" ", "_").replace("-", "_")
    if upper_normalized != upper and upper_normalized in valid:
        return upper_normalized

    if _stage2_v2_enabled():
        v2_mapped = STAGE2_V2_AXIS_ALIASES.get(axis, {}).get(raw_text)
        if v2_mapped in valid:
            return v2_mapped

    if axis == "work_context" and _stage2_v2_enabled():
        mapped_context = _resolve_work_context_code_alias(raw_text, valid)
        if mapped_context:
            return mapped_context

    # alias 매핑 (Tier 1): exact first, conservative contained-term fallback second.
    aliases = _load_aliases()
    tier1 = aliases.get("tier1", {}).get(axis, {})
    for code, terms in tier1.items():
        if upper in [str(t).upper() for t in terms] or raw_text in terms:
            return code

    # Step 4.5 (Phase F.1) — candidate aliases (level=candidate, asymmetric trust).
    # tier1 vetted 다음, contained-term fallback 직전. 매칭 시에도 candidate 그대로 사용.
    # 파일 미존재 또는 빈 dict 시 no-op (R2: delta 0 invariant).
    cand_tier1 = _load_candidate_aliases().get("tier1", {}).get(axis, {})
    for code, terms in cand_tier1.items():
        if code not in valid:
            continue
        matched_alias = None
        if upper in [str(t).upper() for t in terms]:
            # Find exact alias that matched (preserving original casing for audit)
            for t in terms:
                if str(t).upper() == upper:
                    matched_alias = t
                    break
        elif raw_text in terms:
            matched_alias = raw_text
        if matched_alias is not None:
            # T1.C — usage tracking for promote_aliases.py --auto (uses >= N rule)
            _log_alias_usage(axis, code, matched_alias)
            return code

    if _stage2_v2_enabled():
        for code, terms in tier1.items():
            if code not in valid:
                continue
            if any(_term_matches_raw(str(term), raw_text) for term in terms):
                return code

    return None


def normalize_risk_feature_candidates(
    candidates: list[dict],
    context_text: str = "",
) -> dict:
    """LLM 후보 목록을 기존 faceted 내부 구조로 변환 후 정규화한다."""
    faceted = {
        "accident_types": [],
        "hazardous_agents": [],
        "work_contexts": [],
        "forced_fit_notes": [],
    }
    axis_to_field = {
        "accident_type": "accident_types",
        "hazardous_agent": "hazardous_agents",
        "work_context": "work_contexts",
    }
    for item in candidates or []:
        axis = item.get("axis")
        field = axis_to_field.get(axis)
        text = item.get("text")
        if field and text:
            faceted[field].append(text)
    return normalize_faceted_hazards(faceted, context_text=context_text)


def normalize_faceted_hazards(
    gpt_faceted: dict,
    context_text: str = "",
) -> dict:
    """위험 특징 후보를 정규화.

    Returns:
        {
            "accident_types": ["FALL", ...],
            "hazardous_agents": ["FIRE", ...],
            "work_contexts": ["SCAFFOLD", ...],
            "forced_fit_notes": [...],
            "unknown_codes": [...],   # 매핑 불가 코드
            "alias_resolved": [...],  # alias로 해석된 코드
        }
    """
    result = {
        "accident_types": [],
        "hazardous_agents": [],
        "work_contexts": [],
        "forced_fit_notes": list(gpt_faceted.get("forced_fit_notes", [])),
        "unknown_codes": [],
        "alias_resolved": [],
    }

    axis_map = {
        "accident_types": "accident_type",
        "hazardous_agents": "hazardous_agent",
        "work_contexts": "work_context",
    }

    for field, axis in axis_map.items():
        raw_codes = gpt_faceted.get(field, [])
        seen = set()
        for raw in raw_codes:
            resolved = _resolve_alias_code(raw, axis)
            if resolved and resolved not in seen:
                seen.add(resolved)
                result[field].append(resolved)
                if resolved != raw.upper().strip():
                    result["alias_resolved"].append(
                        f"{raw} → {resolved} ({axis})"
                    )
            elif not resolved:
                # 다른 축에서 찾기
                found_in_other = False
                for other_field, other_axis in axis_map.items():
                    if other_axis == axis:
                        continue
                    alt = _resolve_alias_code(raw, other_axis)
                    if alt:
                        result[other_field].append(alt)
                        result["alias_resolved"].append(
                            f"{raw} → {alt} (cross-axis: {axis}→{other_axis})"
                        )
                        found_in_other = True
                        break
                if not found_in_other:
                    result["unknown_codes"].append(f"{raw} ({axis})")

    # Tier 2: 문맥 조건부 alias (context_text에서 추가 코드 발견)
    if context_text:
        aliases = _load_aliases()
        text_lower = context_text.lower()
        for entry in aliases.get("tier2", []):
            term = entry["term"]
            if term not in text_lower:
                continue
            ctx_requires = entry.get("context_requires", [])
            if ctx_requires and not any(cr in text_lower for cr in ctx_requires):
                continue
            axis_name = entry["axis"]
            code = entry["code"]
            field = axis_name + "s" if axis_name != "work_context" else "work_contexts"
            if axis_name == "accident_type":
                field = "accident_types"
            elif axis_name == "hazardous_agent":
                field = "hazardous_agents"
            if code not in result.get(field, []):
                result[field].append(code)
                result["alias_resolved"].append(
                    f"tier2: '{term}' + context → {code} ({axis_name})"
                )

    # 중복 제거
    for field in ["accident_types", "hazardous_agents", "work_contexts"]:
        result[field] = list(dict.fromkeys(result[field]))

    if context_text:
        for code, terms in TEXT_WORK_CONTEXT_HINTS.items():
            if code in result["work_contexts"]:
                continue
            if any(term.lower() in text_lower or term in context_text for term in terms):
                result["work_contexts"].append(code)
                result["alias_resolved"].append(
                    f"text-context: {code} (work_context)"
                )
        if len(result["work_contexts"]) > 1 and "GENERAL_WORKPLACE" in result["work_contexts"]:
            result["work_contexts"] = [
                code for code in result["work_contexts"] if code != "GENERAL_WORKPLACE"
            ]

    if result["unknown_codes"]:
        logger.warning(f"[Normalizer] 매핑 불가 코드: {result['unknown_codes']}")
    if result["alias_resolved"]:
        logger.info(f"[Normalizer] Alias 해석: {result['alias_resolved']}")

    return result


# ===== Hazard-Direct Pivot Phase 2 Day 3-4 ===== #
# GPT hazards[].name (자연어) → canonical (3축) 정규화.
# hazard_name_seed.json + risk_feature_aliases.json tier1 재사용.


def normalize_hazards_array(
    hazards: list[dict],
    context_text: str = "",
) -> dict:
    """⭐ Hazard-Direct Pivot — GPT hazards[].name 자연어 → canonical + unknown.

    각 hazard 항목 ({name, risk_level, location, description, preventive_measures})에 대해:
    1. hazard.name → _resolve_alias_code()로 axis별 매핑 (accident_type → hazardous_agent → work_context 순)
    2. 매핑 성공: faceted dict의 해당 field에 누적
    3. 매핑 실패: unknown_hazards에 보존 (closed loop F.1 Gate 1-2 후보)

    이후 normalize_faceted_hazards()를 호출해 기존 canonical 결과 + tier2 context-conditional 부가 alias까지 통합.

    Returns:
        normalize_faceted_hazards() 결과 + 다음 신규 필드:
          - hazard_name_to_codes: {hazard.name: ["axis.code", ...]}  (audit)
          - unknown_hazards: [{name, risk_level, location, description}, ...]
          - hazard_mapping_rate: float (0-1, hazards 중 매핑 성공 비율)
    """
    faceted: dict = {
        "accident_types": [],
        "hazardous_agents": [],
        "work_contexts": [],
        "forced_fit_notes": [],
    }
    unknown_hazards: list[dict] = []
    hazard_to_codes: dict[str, list[str]] = {}
    axis_field_map = {
        "accident_type": "accident_types",
        "hazardous_agent": "hazardous_agents",
        "work_context": "work_contexts",
    }
    total = 0
    matched = 0

    for h in hazards or []:
        name = (h.get("name") or "").strip()
        if not name:
            continue
        total += 1
        matched_axis = None
        matched_code = None
        for axis in ("accident_type", "hazardous_agent", "work_context"):
            code = _resolve_alias_code(name, axis)
            if code:
                matched_axis = axis
                matched_code = code
                break
        if matched_code:
            matched += 1
            field = axis_field_map[matched_axis]  # type: ignore[index]
            if matched_code not in faceted[field]:
                faceted[field].append(matched_code)
            hazard_to_codes.setdefault(name, []).append(f"{matched_axis}.{matched_code}")
        else:
            unknown_hazards.append({
                "name": name,
                "risk_level": h.get("risk_level", ""),
                "location": h.get("location", ""),
                "description": h.get("description", ""),
            })

    canonical = normalize_faceted_hazards(faceted, context_text=context_text)
    canonical["hazard_name_to_codes"] = hazard_to_codes
    canonical["unknown_hazards"] = unknown_hazards
    canonical["hazard_mapping_rate"] = (matched / total) if total > 0 else 0.0
    canonical["hazard_total"] = total
    canonical["hazard_matched"] = matched

    if unknown_hazards:
        logger.warning(
            f"[HazardDirect] 매핑 불가 hazard.name: {[h['name'] for h in unknown_hazards]}"
        )
    if hazard_to_codes:
        logger.info(
            f"[HazardDirect] {matched}/{total} hazard mapped: {hazard_to_codes}"
        )

    return canonical
