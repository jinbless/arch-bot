"""위험 코드 정본(canonical) 어휘 단일 소비자 모듈 — SSOT.

모든 태깅/normalizer/export/guardrail이 이 모듈로만 코드를 정본화한다(하드코딩 금지).
SSOT 데이터: 같은 디렉토리 canonical-code-vocabulary.json (build_canonical_vocabulary.py 산출).

설계:
- accident_type 정본 = KOSHA-22 공식(frozen 외부 표준). 확장은 UNCLASSIFIED 하위.
- hazardous_agent / work_context 정본 = 우리 taxonomy(확장 가능).
- 미분류는 pending(open) class(UNKNOWN_*/UNCLASSIFIED) — 억지 배정 금지, continual learning이 빈도+클러스터로 승격.
- rollup 값은 "CODE"(동일축) 또는 "axis:CODE"(교차축).
- additive: fine 코드는 호출측에서 보존. 본 모듈은 "매칭/조인용 canonical"만 산출.

사용:
    import sys; sys.path.insert(0, "<repo>/shared/reference"); import canonical_vocab as cv
    cv.to_canonical("accident_type", "ENTANGLEMENT")  # -> ("accident_type", "CAUGHT_IN")
    cv.to_canonical("hazardous_agent", "SHARP_BLADE")  # -> ("accident_type", "CUT_LACERATION")  (교차축)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

_PATH = Path(__file__).resolve().parent / "canonical-code-vocabulary.json"
_DATA: Optional[dict] = None


def _load() -> dict:
    global _DATA
    if _DATA is None:
        _DATA = json.loads(_PATH.read_text(encoding="utf-8"))
    return _DATA


def axes() -> list[str]:
    return list(_load()["axes"].keys())


def canonical_set(axis: str) -> set[str]:
    """해당 축의 정본 코드 집합(pending bucket 포함)."""
    return set(_load()["axes"][axis]["canonical"])


def pending_bucket(axis: str) -> str:
    """미분류 open-class 토큰 (예: work_context→UNKNOWN_CONTEXT)."""
    return _load()["axes"][axis]["pending_bucket"]


def meta_set(axis: str) -> set[str]:
    """관리/기타 의사코드 (위험축 아님, 예: work_context→SAFETY_MGMT/PPE_MGMT/OTHER).

    canonical은 아니나 rollup 항등(자기 자신)이라 to_canonical이 pending으로 떨어뜨리지
    않는 정당한 축 값. SR/Guide가 실사용 → 정합 검증(SHACL allowlist)에서 canonical과 함께 허용.
    """
    return set(_load()["axes"][axis].get("wc_meta", []))


def to_canonical(axis: str, code: str) -> tuple[str, str]:
    """fine/원시 코드 → (정본축, 정본코드). 교차축이면 축이 바뀐다.

    rollup에 없으면 해당 축 pending bucket으로 (open-class). 호출측은 fine 코드를
    별도로 보존해야 한다(additive). 이미 정본이면 그대로 반환.
    """
    ax = _load()["axes"].get(axis)
    if ax is None:
        return (axis, code)
    if code in ax["canonical"]:
        return (axis, code)
    val = ax["rollup"].get(code)
    if not val:
        return (axis, ax["pending_bucket"])
    if ":" in val:
        a2, c2 = val.split(":", 1)
        return (a2, c2)
    return (axis, val)


def canonicalize_list(axis: str, codes) -> dict[str, list[str]]:
    """fine 코드 리스트 → 축별 정본 코드 dedup. 교차축 재배치 반영.

    반환: {target_axis: [canonical codes...]} — 태깅 시 *_canonical 컬럼 채움에 사용.
    """
    out: dict[str, set[str]] = {}
    for c in codes or []:
        a2, c2 = to_canonical(axis, c)
        out.setdefault(a2, set()).add(c2)
    return {a: sorted(v) for a, v in out.items()}


def is_pending(axis: str, code: str) -> bool:
    return code == pending_bucket(axis) or to_canonical(axis, code)[1] == pending_bucket(axis)


def is_canonical(axis: str, code: str) -> bool:
    return code in canonical_set(axis)


def _camel(code: str) -> str:
    return "".join(p.capitalize() for p in str(code).split("_") if p)


def same_axis_fine(axis: str) -> set[str]:
    """축 내 fine 코드 집합 — canonical 아님 + 같은 축 canonical로 rollup + fragment 구별.
    fine⊑canonical taxonomy(gen_facet_taxonomy) · fine IRI emit(code_iri_mapper.fine_iri_fragment) ·
    canonical-code allowlist(gen_canonical_code_shape)의 공통 SSOT. cross-axis(예: agent SHARP_BLADE→
    accident)·UNKNOWN rollup·canonical 자기자신은 제외."""
    ax = _load()["axes"].get(axis)
    if ax is None:
        return set()
    canon = set(ax["canonical"])
    out: set[str] = set()
    for fine in ax.get("rollup", {}):
        if fine in canon:
            continue
        a2, c2 = to_canonical(axis, fine)
        if a2 != axis or _camel(fine) == _camel(c2):
            continue
        out.add(fine)
    return out


if __name__ == "__main__":  # 자체 점검
    tests = [
        ("accident_type", "ENTANGLEMENT", ("accident_type", "CAUGHT_IN")),
        ("accident_type", "FALL_ON_GROUND", ("accident_type", "FALL")),
        ("work_context", "FORKLIFT_OPERATION", ("work_context", "VEHICLE")),
        ("hazardous_agent", "SHARP_BLADE", ("accident_type", "CUT_LACERATION")),
        ("hazardous_agent", "BENZENE", ("hazardous_agent", "CHEMICAL")),
    ]
    ok = True
    for axis, code, exp in tests:
        got = to_canonical(axis, code)
        flag = "OK" if got == exp else "FAIL"
        if got != exp:
            ok = False
        print(f"  [{flag}] {axis}.{code} -> {got} (expect {exp})")
    print("self-test:", "PASS" if ok else "FAIL")
