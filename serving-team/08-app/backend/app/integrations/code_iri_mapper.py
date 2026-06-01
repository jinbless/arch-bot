"""Code → OWL IRI Mapping Layer — SSOT 파생 단일 브리지 (Phase 4-B).

OHS faceted 코드(UPPER_SNAKE) ↔ OWL NamedIndividual IRI(CamelCase)의 결정론적 변환.
하드코딩 테이블(구 8/11/13 어휘) 폐지 → 정본 SSOT(shared/reference/canonical-code-vocabulary.json,
KOSHA-22)에서 파생 + 결정적 _camel() casing.

casing 규약 (canonical-code-vocabulary.json): PG/serving = UPPER_SNAKE, ontology IRI = CamelCase.
변환: UPPER_SNAKE → CamelCase = ''.join(p.capitalize() for p in code.split('_'))
  FALL→Fall, CUT_LACERATION→CutLaceration, CAUGHT_IN→CaughtIn, TEMP_EXTREME_CONTACT→TempExtremeContact

axis 처리: fine 코드는 canonical_vocab.to_canonical로 먼저 정본화(교차축 인지) 후 _camel.
  ENTANGLEMENT → CAUGHT_IN → 'CaughtIn',  FORKLIFT_OPERATION → VEHICLE → 'Vehicle'

구 온톨로지 어휘(8-type CamelCase: Crush/Cut/FallingObject/Slip/Ergonomic 등)는 LEGACY_FRAGMENT_TO_CODE로
KOSHA-22 정본에 매핑 — SWRL/restriction/disjoint 마이그레이션(Phase 4-B Stage 3-4)에서 사용.

namespace prefix: sparql_queries.PREFIXES와 일치(hazard:/agent:/context:); TTL은 haz:/ctx: 라벨이나
URI 동일(https://cashtoss.info/ontology/risk/{hazard|agent|context}#).
"""
from __future__ import annotations

import sys
from pathlib import Path

# SSOT 소비자 모듈 로드 (shared/reference)
_SHARED_REF = Path(__file__).resolve().parents[5] / "shared" / "reference"
if str(_SHARED_REF) not in sys.path:
    sys.path.insert(0, str(_SHARED_REF))
import canonical_vocab as _cv  # noqa: E402

# ────────────────────────────────────────────────────────────────────────
# Namespace (prefix label은 sparql_queries.PREFIXES와 동일; URI는 TTL haz:/ctx:와 동일)
# ────────────────────────────────────────────────────────────────────────
_AXIS_PREFIX = {
    "accident_type": "hazard",
    "hazardous_agent": "agent",
    "work_context": "context",
}
NAMESPACES = {
    "hazard":  "https://cashtoss.info/ontology/risk/hazard#",
    "agent":   "https://cashtoss.info/ontology/risk/agent#",
    "context": "https://cashtoss.info/ontology/risk/context#",
}


def _camel(code: str) -> str:
    """UPPER_SNAKE → CamelCase (결정적). FALL→Fall, CUT_LACERATION→CutLaceration."""
    return "".join(p.capitalize() for p in str(code).split("_") if p)


# ────────────────────────────────────────────────────────────────────────
# 구 온톨로지 어휘(8-type CamelCase + agent 변종) → KOSHA-22 정본 UPPER 코드.
# SWRL/restriction/disjoint 마이그레이션용. work_context는 이미 _camel(SSOT)와 정합 → 매핑 불필요.
# ────────────────────────────────────────────────────────────────────────
LEGACY_FRAGMENT_TO_CODE: dict[str, tuple[str, str]] = {
    # accident_type (구 8-type + 단발 CamelCase 개체)
    "Fall":            ("accident_type", "FALL"),
    "Slip":            ("accident_type", "SLIP_TRIP"),
    "Collision":       ("accident_type", "COLLISION"),
    "FallingObject":   ("accident_type", "STRUCK_BY"),
    "Crush":           ("accident_type", "CAUGHT_IN"),       # 구 Crush = legacy CAUGHT_IN
    "Cut":             ("accident_type", "CUT_LACERATION"),
    "Collapse":        ("accident_type", "COLLAPSE"),
    "Ergonomic":       ("accident_type", "ERGONOMIC_STRAIN"),
    "Explosion":       ("accident_type", "EXPLOSION"),
    "ElectricShock":   ("accident_type", "ELECTRIC_SHOCK"),
    "ChemicalExposure":("accident_type", "CHEMICAL_EXPOSURE"),
    "ColdExposure":    ("accident_type", "TEMP_EXTREME_CONTACT"),
    "Burn":            ("accident_type", "TEMP_EXTREME_CONTACT"),  # 화상(접촉) → 이상온도접촉
    "FoodContamination": ("accident_type", "OTHER_ACCIDENT"),     # KOSHA-22 외 → 기타
    # hazardous_agent (SSOT 외 변종)
    "Corrosion":       ("hazardous_agent", "CHEMICAL"),
    "ArcFlash":        ("hazardous_agent", "ELECTRICITY"),
}


def legacy_to_canonical(fragment: str) -> tuple[str, str] | None:
    """구 IRI fragment(CamelCase, 예: 'Crush') → (정본축, KOSHA-22 UPPER 코드).

    매핑 없으면 None (이미 정본 CamelCase거나 미지). 마이그레이션 스크립트에서
    'haz:Crush' → 'haz:CaughtIn' 치환에 사용.
    """
    return LEGACY_FRAGMENT_TO_CODE.get(fragment)


def legacy_fragment_to_iri_fragment(fragment: str) -> str | None:
    """구 fragment → 신 CamelCase fragment (예: 'Crush'→'CaughtIn', 'FallingObject'→'StruckBy')."""
    m = LEGACY_FRAGMENT_TO_CODE.get(fragment)
    return _camel(m[1]) if m else None


# ────────────────────────────────────────────────────────────────────────
# 핵심 변환 — (axis, code) → IRI. fine 코드는 canonical_vocab로 정본화(교차축 인지) 후 _camel.
# ────────────────────────────────────────────────────────────────────────
def _resolve_same_axis(axis: str, code: str) -> str | None:
    """code를 axis 내 정본 코드로 환원. 교차축이면 None(per-axis API 계약 보존)."""
    a2, c2 = _cv.to_canonical(axis, code)
    return c2 if a2 == axis else None


def iri_fragment(axis: str, code: str) -> str | None:
    """(axis, code) → CamelCase fragment (axis 내 정본). 교차축이면 None."""
    c = _resolve_same_axis(axis, code)
    return _camel(c) if c else None


def to_prefixed(axis: str, code: str) -> str | None:
    """(axis, code) → prefixed IRI (예: 'hazard:CaughtIn'). 교차축이면 None."""
    frag = iri_fragment(axis, code)
    if not frag:
        return None
    return f"{_AXIS_PREFIX[axis]}:{frag}"


def to_iri(axis: str, code: str) -> str | None:
    """(axis, code) → full IRI (예: 'https://.../hazard#CaughtIn'). 교차축이면 None."""
    frag = iri_fragment(axis, code)
    if not frag:
        return None
    return f"{NAMESPACES[_AXIS_PREFIX[axis]]}{frag}"


def fine_iri_fragment(axis: str, code: str) -> str | None:
    """same-axis fine 코드 → 원본 fine CamelCase fragment(fold 안 함). canonical/교차축/UNKNOWN이면 None.

    iri_fragment(canonical로 fold)과 짝 — fine 보존 ABox emit용. cv.same_axis_fine과 동일 정의
    (taxonomy fine⊑canonical · allowlist와 정합). 예: FALL_FROM_HEIGHT→'FallFromHeight'(haz:Fall 자식).
    """
    return _camel(code) if code in _cv.same_axis_fine(axis) else None


def to_fine_prefixed(axis: str, code: str) -> str | None:
    """(axis, code) → fine prefixed IRI(예: 'hazard:FallFromHeight'). same-axis fine만, else None."""
    frag = fine_iri_fragment(axis, code)
    return f"{_AXIS_PREFIX[axis]}:{frag}" if frag else None


def to_prefixed_cross_axis(axis: str, code: str) -> str | None:
    """교차축까지 따라가는 변환(예: agent SHARP_BLADE → 'hazard:CutLaceration').

    ABox export 등 교차축 재배치가 필요한 곳에서 사용. per-axis SPARQL 슬롯에는 to_prefixed 사용.
    """
    a2, c2 = _cv.to_canonical(axis, code)
    if a2 not in _AXIS_PREFIX:
        return None
    return f"{_AXIS_PREFIX[a2]}:{_camel(c2)}"


# ────────────────────────────────────────────────────────────────────────
# Backward-compat (sparql_queries.py가 사용) — 이제 KOSHA-22 정본 인지.
# ────────────────────────────────────────────────────────────────────────
def accident_type_to_prefixed(code: str) -> str | None:
    return to_prefixed("accident_type", code)


def accident_type_to_iri(code: str) -> str | None:
    return to_iri("accident_type", code)


def hazardous_agent_to_prefixed(code: str) -> str | None:
    return to_prefixed("hazardous_agent", code)


def hazardous_agent_to_iri(code: str) -> str | None:
    return to_iri("hazardous_agent", code)


def work_context_to_prefixed(code: str) -> str | None:
    return to_prefixed("work_context", code)


def work_context_to_iri(code: str) -> str | None:
    return to_iri("work_context", code)


# ────────────────────────────────────────────────────────────────────────
# 검증/내보내기 helper
# ────────────────────────────────────────────────────────────────────────
def all_canonical_iris() -> list[tuple[str, str, str]]:
    """모든 정본 (axis, UPPER_code, prefixed_IRI). TBox 생성 + smoke test ASK용."""
    out: list[tuple[str, str, str]] = []
    for axis in ("accident_type", "hazardous_agent", "work_context"):
        for code in sorted(_cv.canonical_set(axis)):
            out.append((axis, code, f"{_AXIS_PREFIX[axis]}:{_camel(code)}"))
    return out


if __name__ == "__main__":
    # self-test
    cases = [
        ("accident_type", "FALL", "hazard:Fall"),
        ("accident_type", "CUT_LACERATION", "hazard:CutLaceration"),
        ("accident_type", "CAUGHT_IN", "hazard:CaughtIn"),
        ("accident_type", "ENTANGLEMENT", "hazard:CaughtIn"),      # fine → canonical
        ("accident_type", "TEMP_EXTREME_CONTACT", "hazard:TempExtremeContact"),
        ("hazardous_agent", "HEAT_COLD", "agent:HeatCold"),
        ("hazardous_agent", "CHEMICAL", "agent:Chemical"),
        ("work_context", "FORKLIFT_OPERATION", "context:Vehicle"),  # fine → canonical
        ("work_context", "CONSTRUCTION_EQUIP", "context:ConstructionEquip"),
    ]
    ok = True
    for axis, code, exp in cases:
        got = to_prefixed(axis, code)
        flag = "OK" if got == exp else "FAIL"
        if got != exp:
            ok = False
        print(f"  [{flag}] {axis}.{code} -> {got} (expect {exp})")
    # legacy 매핑
    legacy_cases = [("Crush", "CaughtIn"), ("FallingObject", "StruckBy"), ("Cut", "CutLaceration"), ("Slip", "SlipTrip")]
    for frag, exp in legacy_cases:
        got = legacy_fragment_to_iri_fragment(frag)
        flag = "OK" if got == exp else "FAIL"
        if got != exp:
            ok = False
        print(f"  [{flag}] legacy {frag} -> {got} (expect {exp})")
    print(f"\ntotal canonical IRIs: {len(all_canonical_iris())} (expect 23+10+29=62)")
    print("self-test:", "PASS" if ok else "FAIL")
