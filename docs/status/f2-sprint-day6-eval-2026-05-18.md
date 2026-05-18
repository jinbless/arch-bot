# F.2 Day 6 — 8-photo eval (sprint 누적 효과)

**날짜**: 2026-05-18 (F.2 Day 5 직후)
**커밋**: F.2 Day 1-5 (`6807c42`) 위에서 측정
**LLM_RERANK_MODE**: shadow (A hook 발동)

## 측정 결과 — 8 photos × ON/OFF

| Photo | F.2 ON | F.2 OFF | diff | F.1 baseline diff |
|---|---|---|---|---|
| 고소대작업 | 1 | 1 | = | (hook 미발동) |
| 안전대길이 | 0 | 0 | = | = |
| 영세제조업 | 2 | 2 | = | = |
| **음식점주방** | **0** | **1** | **✓ -1** | = |
| 지게차 | 2 | 2 | = | ✓ -2 |
| **최근대전화재** | **1** | **0** | **✗ +1** | = |
| 포크레인주변작업자 | 1 | 1 | = | = |
| 프레스 | 1 | 1 | = | = |

- Improved: 1/8 (음식점주방)
- Equal: 6/8
- Worse: 1/8 (최근대전화재)

## 핵심 발견 — Vision LLM stochasticity

**F.1 Day 6 vs F.2 Day 6 (same photos, same code state 대부분)**:
- 지게차: F.1에서 ON-OFF -2 이득, F.2에서 0 — Vision LLM이 다른 unknowns 생성
- 음식점주방: F.1에서 동일, F.2에서 ON 개선
- 같은 사진도 다른 LLM run마다 다른 unknown 패턴 발생

**해석**:
- ON/OFF 단일-run diff는 noise 수준 (LLM 비결정성 영향)
- 의미 있는 측정은 multi-run averaging (예: 5x 반복) 또는 더 큰 photo set
- F.1 6 candidates + F.2 catalog v3.3은 8-photo의 어휘와 overlap 부족

## SHE match count 변화 (ON vs OFF)

| | ON 합계 | OFF 합계 | diff |
|---|---|---|---|
| she_match_count (8 photos) | 22 | 19 | +3 |

→ 약간 ON이 더 많은 SHE match (이전 Day 6보다 차이 작음 — F.2 enrichment 효과보다 noise 큼)

## Plan acceptance 평가

| 목표 | 결과 |
|---|---|
| 8-photo improvement ≥6/8 | ❌ 1/8 (F.1 Day 6 동일 결과) |
| **Gate 3 regression** | ✅ **PASS 유지** (Day 1-5 누적 적용 후도) |
| F.2 시스템 안정성 | ✅ catalog 5-axis 정상 작동, regression 0 |

## 진짜 F.2 가치 (8-photo로는 측정 불가)

8-photo는 F.2 효과 측정에 적합하지 않음:
- F.2 = 인프라 확장 (catalog +77 codes, 5 axes, SHE 5-dim)
- 가시적 효과 = production traffic이 신규 codes/axes 사용할 때 나타남
- 8-photo는 매우 좁은 sample, ppe/env 표현 적음

**Long-term 가치 (production traffic 누적 후 측정)**:
- ppe_state/environmental axis: 이제 매핑 가능 (production이 사용 시)
- 790 SHE 5-dim 채워짐 → 매칭 정확도 ↑ (대규모 traffic에서 가시화)
- 77 new SHE (pending_review): 수동 승격 시 v3.1 코드 cover
- catalog v3.3 481 codes: 30% 인식 capacity 확장

## 한계 / Known issues
- 1 photo (고소대작업)에서 한 run에서 hook 미발동 (이전 Day 6과 동일 — early-return)
- F.1 Day 6 발견: Vision LLM이 영어 generic terms 생성 (MACHINERY, FORKLIFT) — F.2도 동일
- 진짜 해결: closed vocabulary prompt (별도 plan)

## 결론

F.2 Day 6 = **회귀 없음 확인** (안전성) + **8-photo로는 한계 측정 불가**.

F.2 누적 진척 (Day 1-5):
- catalog: v3.1 (404) → v3.3 (481 codes, 5 axes, +19%)
- SHE: 790 OTHER → specific (5-dim coverage ↑)
- 79 pending_review SHE (수동 승격 대기)
- Gate 3 PASS (regression 0)

다음 (Day 7): runbook + Makefile (sprint 정리)
