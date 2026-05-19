"""Hazard-Direct Pivot Phase 2 Day 3-4 — normalize_hazards_array() 단위 테스트.

검증:
- moellab 8 photo의 21 unique hazard.name이 모두 매핑되는가 (AC-2 ≥ 85% → 목표 100%)
- unknown_hazards 빈 결과 (vetted seed + manual override 후)
- hazard_mapping_rate = 1.0
- 빈 hazards[] 처리
- 같은 hazard.name 여러 번 입력 시 dedup

실행:
  PYTHONIOENCODING=utf-8 python serving-team/08-app/backend/tests/unit/test_normalize_hazards_array.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.hazard_normalizer import normalize_hazards_array


def _moellab_names() -> list[dict]:
    """`.compare_moellab/*.json` 8개에서 모든 hazards 수집 (37 items)."""
    # parents: [0]unit [1]tests [2]backend [3]08-app [4]serving-team [5]worktree-root
    repo_root = Path(__file__).resolve().parents[5]
    compare_dir = repo_root / ".compare_moellab"
    out: list[dict] = []
    for fp in sorted(compare_dir.glob("*.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        for h in (data.get("hazards") or []):
            out.append(h)
    return out


def test_all_moellab_hazards_map():
    hazards = _moellab_names()
    assert hazards, "moellab raw 응답 8개에서 hazards 수집 실패"
    result = normalize_hazards_array(hazards)
    rate = result["hazard_mapping_rate"]
    print(f"  mapping rate: {result['hazard_matched']}/{result['hazard_total']} = {rate:.1%}")
    print(f"  unique mappings: {len(result['hazard_name_to_codes'])}")
    print(f"  unknown: {[h['name'] for h in result['unknown_hazards']]}")
    # AC-2: ≥ 85% — vetted seed + manual override 후 100% 목표
    assert rate >= 0.85, f"mapping rate {rate:.1%} < 85% (AC-2)"
    # 추가 기대: 100% 매핑 (vetted seed 21/21 등재)
    assert rate == 1.0, f"vetted seed 후 100% 매핑 목표, 실제 {rate:.1%}"


def test_canonical_has_accident_types():
    hazards = _moellab_names()
    result = normalize_hazards_array(hazards)
    # moellab 응답에 추락/낙하물/감전/끼임 등이 다수 — accident_types에 누적
    assert len(result["accident_types"]) >= 6, f"accident_types {result['accident_types']}"


def test_empty_hazards():
    result = normalize_hazards_array([])
    assert result["hazard_total"] == 0
    assert result["hazard_mapping_rate"] == 0.0
    assert result["accident_types"] == []
    assert result["unknown_hazards"] == []


def test_dedup_same_name():
    hazards = [
        {"name": "추락", "risk_level": "high", "location": "...", "description": "", "preventive_measures": []},
        {"name": "추락", "risk_level": "medium", "location": "...", "description": "", "preventive_measures": []},
    ]
    result = normalize_hazards_array(hazards)
    # '추락'은 alias DB에 FALL (기존) 또는 FALL_FROM_HEIGHT 둘 다 등록 → 둘 중 하나로 매핑
    matched = result["accident_types"]
    assert matched, "accident_types 비어있음"
    assert any(c in ("FALL", "FALL_FROM_HEIGHT") for c in matched), f"FALL 또는 FALL_FROM_HEIGHT 기대, 실제 {matched}"
    # 같은 hazard.name 두 번 입력 → 코드는 한 번만 누적
    assert sum(1 for c in matched if c in ("FALL", "FALL_FROM_HEIGHT")) == 1
    # hazard별 audit은 2건 (총 호출 횟수)
    assert len(result["hazard_name_to_codes"].get("추락", [])) == 2


def test_unknown_hazard_captured():
    hazards = [
        {"name": "추락", "risk_level": "high", "location": "...", "description": "", "preventive_measures": []},
        {"name": "완전히_없는_위험_라벨_xyz", "risk_level": "low", "location": "loc",
         "description": "desc", "preventive_measures": []},
    ]
    result = normalize_hazards_array(hazards)
    assert result["hazard_matched"] == 1
    assert result["hazard_total"] == 2
    assert len(result["unknown_hazards"]) == 1
    assert result["unknown_hazards"][0]["name"] == "완전히_없는_위험_라벨_xyz"


if __name__ == "__main__":
    tests = [
        test_all_moellab_hazards_map,
        test_canonical_has_accident_types,
        test_empty_hazards,
        test_dedup_same_name,
        test_unknown_hazard_captured,
    ]
    failures = []
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except AssertionError as e:  # noqa: PERF203
            failures.append(t.__name__)
            print(f"[FAIL] {t.__name__}: {e}")
    print(f"--- {len(tests) - len(failures)}/{len(tests)} PASS ---")
    sys.exit(1 if failures else 0)
