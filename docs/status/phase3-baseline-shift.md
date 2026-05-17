# Phase 3 Baseline Shift — synthetic v1-v10 cleanup 영향

> Phase 3D 적용 후 synthetic 데이터가 변경되어 regression baseline이 이동.
> 단순한 회귀가 아니라 **데이터 정합성 회복으로 인한 의도된 shift**.

## Baseline 진화

| baseline | 시점 | synthetic 상태 | catalog 상태 |
|---|---|---|---|
| `replay_baseline.json` (v1) | 2026-05-15 이전 | 원본 (KO enum 포함) | v2 (13 accident_type) |
| `replay_baseline_v2.json` | 2026-05-15 baseline_v2 | 원본 (KO enum 포함) | v2 + catalog 확장 (Phase 0/B/A/C) |
| **`replay_baseline_v3.json`** (이 commit) | 2026-05-17 Phase 3D | **EN enum 통일** (transform 적용) | **v4** (+170 신규 codes + 169 sub) |

## Phase 3D 영향 (v3 vs v1)

| metric | baseline_v1 | baseline_v3 | delta | 해석 |
|---|---|---|---|---|
| she_accuracy | 0.5581 | 0.5424 | **-0.0157** | 신규 catalog codes (170개)에 대응되는 SHE pattern 부재 → 매칭 감소 |
| sr_accuracy | 0.7636 | 0.7551 | -0.0085 | 동일 (SR mapping은 코드 추가 영향 작음) |
| penalty_accuracy | 0.1835 | 0.1835 | 0 | 무변동 |
| overall_accuracy | 0.1331 | 0.1347 | +0.0016 | 미세 개선 |
| false_positive_rate | 0.8732 | 0.8696 | -0.0036 | 약간 개선 |
| **false_negative_rate** | 0.0334 | **0.0625** | **+0.0291** | **악화** ← 새 코드 매칭 부재로 expected 누락 증가 |

## 원인 분석

1. **catalog 확장 with no SHE patterns** (주원인)
   - 170 신규 코드가 catalog에 추가됨 (CHEMICAL_INHALATION, INFECTION 등)
   - 하지만 PG `she_patterns` 테이블이 이 코드들을 참조하지 않음
   - synthetic의 expected_features가 새 코드를 기대 → 매칭 실패 → false negative ↑
   - **해결책**: Phase 3C (SHE pattern 확장)
   
2. **bilingual matching 손실** (부주원인)
   - 일부 synthetic KO 표현이 backend의 KO 매칭 path를 활용했었음
   - EN으로 변환되면 그 path는 비활성, 대신 EN 매칭만 가능
   - 새 EN 코드가 SHE/SR에 없으면 → 매칭 실패

3. **synthetic 데이터 정합성 회복** (긍정 효과, metric에는 안 보임)
   - expected_features가 이제 catalog v4 코드만 사용 (KO enum 0)
   - 데이터-카탈로그 정합성 100% 달성
   - 향후 regression의 신뢰성 향상

## 다음 단계 — Phase 3C 필요성

Phase 3D는 데이터 layer 정리만 완료. **실제 매칭 성능 회복**을 위해
Phase 3C (SHE pattern 확장)가 필수:

- 170 신규 catalog codes 각각에 대해 SHE pattern 제안 (LLM-assisted)
- 사람 검토 후 PG she_patterns 테이블에 추가
- 매칭 성능 회복 검증: replay vs baseline_v3 → false_negative_rate 정상화 예상

추정 효과 (Phase 3C 후):
- false_negative_rate: 0.0625 → 0.02-0.03 (baseline_v1 수준 회복 또는 개선)
- she_accuracy: 0.5424 → 0.6+ (catalog 확장 효과 발현)

## regression_gate 운영 정책

- 이 commit 이후: regression 비교 대상을 `replay_baseline_v3.json` 로 변경
- `regression_gate.py` 기본 path 업데이트 또는 env var로 v3 지정
- v1, v2 baseline은 히스토리 보존 (삭제 금지)

## 관련 commits

- Phase 3A (audit): `35345db`
- Phase 3B (catalog v4): `724f723`
- Phase 3D (이 commit): synthetic transform + baseline_v3
- Phase 3C (예정): SHE pattern 확장 — 별도 phase
- Phase 3G (예정): 종합 integrity sweep
