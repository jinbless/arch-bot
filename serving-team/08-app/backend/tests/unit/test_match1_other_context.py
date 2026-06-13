"""MATCH-1 (F3) 단위 테스트 — OTHER-context 비단조 강등 구제.

비판 검토 F3: `_classify_match_status`의 work_context 강등 분기가, 입력에서
work_context가 풍부하게 추출될수록 generic(feature work_context=OTHER) 패턴을
일괄 context_only로 강등시켰다(정보 증가가 결론을 제거하는 비단조 FN — OWA→CWA
진리값 규약 §3.4 위반). 합성 corpus는 이 시나리오를 포함하지 않아(F22) 회귀게이트로는
무변화(delta 0)지만, 아래 테스트가 수정의 실제 작동을 양성 증명한다.

핵심 관찰: 라인 637 강등 조건(`work_context not in matched_dims and work_contexts`)은
same_context 논리상 **비-OTHER 패턴으론 도달 불가**(feature_context가 입력에 있으면
work_context가 matched되어 조건 거짓) → 원래부터 OTHER-context만 강등하고 있었다.
MATCH-1은 정확히 그 OTHER 모집단만 교정한다.

실행:
  PYTHONIOENCODING=utf-8 python serving-team/08-app/backend/tests/unit/test_match1_other_context.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.she_matcher import _classify_match_status


def _classify(feature_wc, matched_dims, accident_types, hazardous_agents, work_contexts):
    """F3 시나리오 최소 입력 — 시각단서/ppe/env 없음(분기 격리)."""
    return _classify_match_status(
        features={"work_context": feature_wc, "accident_type": "FALL"},
        matched_dims=matched_dims,
        accident_types=accident_types,
        hazardous_agents=hazardous_agents,
        work_contexts=work_contexts,
        ppe_states=[],
        environmental=[],
        visual_score=0.0,
        visual_cues=[],
    )


def test_other_context_with_input_workcontext_not_demoted():
    """F3 핵심: OTHER-context 패턴 + accident 매치 + 입력 work_context 존재
    → context_only 강등이 아니라 candidate(confirmation_required)."""
    status, reasons = _classify(
        feature_wc="OTHER",
        matched_dims=["accident_type"],          # OTHER는 work_context dim 매치 불가
        accident_types=["FALL"],
        hazardous_agents=[],
        work_contexts=["KITCHEN_COOKING"],        # 입력에 work_context 풍부
    )
    assert status == "candidate", f"기대 candidate, 실제 {status} ({reasons})"
    assert "generic_other_context" in reasons
    assert "confirmation_required" in reasons     # FP 안전: confirmed 직행 아님


def test_monotonicity_workcontext_addition_does_not_flip():
    """비단조성 제거: 동일 OTHER 패턴이 입력 work_context 유무와 무관하게
    context_only로 떨어지지 않는다(정보 추가가 결론을 제거하면 안 됨)."""
    no_wc, _ = _classify("OTHER", ["accident_type"], ["FALL"], [], [])
    with_wc, _ = _classify("OTHER", ["accident_type"], ["FALL"], [], ["KITCHEN_COOKING"])
    # 둘 다 actionable(confirmed/candidate)이어야 — 이전엔 with_wc만 context_only로 flip.
    assert no_wc in {"candidate", "confirmed"}, f"no_wc={no_wc}"
    assert with_wc in {"candidate", "confirmed"}, f"with_wc={with_wc}"
    assert with_wc != "context_only"


def test_other_context_without_feature_signal_stays_context():
    """FP 안전: OTHER 패턴이 accident/agent 단서 없이 work_context만 있으면
    context_only 유지(과잉 promote 방지)."""
    status, reasons = _classify(
        feature_wc="OTHER",
        matched_dims=[],                          # 아무 feature 축도 매치 안 됨
        accident_types=[],
        hazardous_agents=[],
        work_contexts=["KITCHEN_COOKING"],
    )
    assert status == "context_only", f"기대 context_only, 실제 {status} ({reasons})"


def _run():
    tests = [
        test_other_context_with_input_workcontext_not_demoted,
        test_monotonicity_workcontext_addition_does_not_flip,
        test_other_context_without_feature_signal_stays_context,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{'ALL PASS' if not failed else f'{failed} FAILED'} ({len(tests)} tests)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
