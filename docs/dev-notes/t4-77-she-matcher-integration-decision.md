# T4 #1 Decision — 77 SHE Matcher Integration 별도 sprint 이관 (2026-05-19)

## Background

Phase G.4에서 `she_patterns_reasoner_derived` view로 77 pending_review SHE를 노출했음. T4 #1 후속 작업: 이 77개 SHE를 matcher에 통합.

## Test Result (5 SHE batch)

`promote_she_review.py --apply --max-batches 1`로 첫 5 SHE 시도:

| metric | baseline_v3 | T4 #1 batch | delta | verdict |
|---|---|---|---|---|
| **she_accuracy** | 0.5771 | 0.5064 | **-0.0707** | **VETOED** |
| sr_accuracy | 0.7581 | 0.7581 | 0.0000 | ok |
| penalty_accuracy | 0.1835 | 0.4352 | +0.2517 | ok |
| overall_accuracy | 0.1377 | 0.2907 | +0.1530 | ok |
| false_positive_rate | 0.8696 | 0.8696 | 0.0000 | ok |
| false_negative_rate | 0.0625 | 0.0436 | -0.0189 | ok |

**rollback 자동 수행** (T1.A rollback verification 정상 동작).

## Root Cause

5 SHE → -7.07%p ≈ **1.4%p per SHE** regression.

Day 5 lesson 재확인: 77 SHE 전량 → -39.5%p (≈ 0.5%p per SHE, 평균화).
이번 5 SHE batch: -7.07%p (1.4%p per SHE, more recent calibration).

**문제는 promotion이 아닌 matcher 로직**:
- 이 77 SHE는 매우 구체적 (BREAD_SLICER × BLADE_LACERATION 등)
- 그러나 matcher가 partial match 시 broadness ranking 영향
- 1-by-1 promote with tolerance=0.02도 1 SHE만으로 -1.4%p VETOED 가능

## Re-scope

T4 #1을 별도 sprint로 이관:

**필요 작업** (별도 sprint, 1-2주):
1. `she_matcher.py` 로직 분석 — partial match scoring 알고리즘
2. broadness_score를 ranking에 반영 (current matcher가 사용 안 하는 듯)
3. status='approved_derived' 신규 status 도입:
   - matcher가 매칭 시도하지만 lower priority
   - approved_auto가 매칭 못한 경우만 fallback
4. 77 SHE를 approved_derived로 promote (status='approved_derived')
5. Gate 3 통과까지 matcher 튜닝

**대안 (간단)**:
- 77 SHE를 영구적으로 pending_review 유지
- `she_patterns_reasoner_derived` view로만 노출 (architectural marker)
- Phase G의 step 4 입증은 G.1/G.2/G.3로 충분

## 부가 발견: penalty_accuracy 추가 개선 가능성

흥미롭게도 5 SHE promote 시:
- penalty_accuracy: 0.1835 → 0.4352 (+25.17%p, G.3 +27.16%p 대비 -2%p)
- overall_accuracy: 0.1377 → 0.2907 (+15.30%p, G.3 +18.81%p 대비 -3%p)

즉 promote된 5 SHE는 penalty 매칭에 도움이 되지만 SHE 자체 매칭은 손상.
matcher가 새 SHE를 발견하면 잘못된 (broad) SR 매칭을 함.

## Action

- T4 #1 closed (architectural decision: 별도 sprint 필요)
- Tier 5 후보 등록: "SHE matcher broadness-aware refactor"
- promote_she_review.py 인프라는 유지 (rollback 정상 작동)
- 77 SHE는 pending_review + reasoner_derived view 유지

## Related

- [phase-g.4-she-patterns-reasoner-derived.md](phase-g.4-she-patterns-reasoner-derived.md)
- T1.A: `promote_she_review.py` rollback verification (commit 93c49fe)
- F.2 Day 5 lesson (77 SHE 전량 promote → -39.5%p)
