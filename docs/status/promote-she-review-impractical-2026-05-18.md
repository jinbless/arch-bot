# promote_she_review.py — 77 pending SHE 활성화 시도 결과

**날짜**: 2026-05-18 (Hybrid sprint Day 1)
**결론**: Day 5 자동 생성 77 SHE는 **현재 형태로 production 활성화 불가**. promote_she_review.py 인프라는 작동하나 입력 데이터(SHE)가 over-broad.

## 시도 과정

### Attempt 1: 5 batch random (broadness ASC)
- Batch: 2 with `wc='OTHER'` + 3 specific
- 결과: **she_accuracy -7.84%p (vetoed)** → auto-rollback

### Attempt 2: 5 specific only (OTHER 제외)
- Filter: `wc != 'OTHER' AND at != 'OTHER'`
- Batch: AIRLESS_SPRAYER, AWKWARD_POSTURE_WORK, BIOMEDICAL_WASTE × 3 (모두 specific work_context + accident_type)
- 결과: **she_accuracy -10.76%p (vetoed)** → auto-rollback

## 진단

**Day 5 자동 생성 SHE의 문제**:
- broadness_score 0.6 (default) — 기존 specific SHE(0.5-0.625)보다 약간 높음
- 8-axis 중 일부 'OTHER' 또는 generic 값 (agent_state, work_activity 등)
- visual_triggers는 OK이지만 matcher score 계산이 8-axis dim 기반

**matcher 영향 메커니즘**:
- broad OR query → 새 SHE가 후보 pool에 다수 진입
- 8-dim score 계산에서 새 SHE가 expected SHE보다 high score
- top-N ranking에서 expected가 밀려나 false_negative ↑

## 대응 결정

### 단기 (이번 sprint)
- ❌ promote_she_review 폐기 (현재 77 SHE 입력에는 불가)
- ✅ promote_she_review.py 인프라 보존 (향후 더 narrow 한 SHE에 활용)
- ✅ Sprint pivot: Day 3 (closed vocabulary prompt)로 즉시 전환

### 중기 (별도 plan)
77 pending_review SHE 활용 옵션:
1. **broadness_score 일괄 0.2-0.3로 낮춤** → SHE matching power 의도적 약화 (테스트 가치)
2. **link_v31_codes_to_she.py v2 — visual_triggers 더 강조 + axes 더 specific 요구**
3. **Manual review 후 individual selective promotion** (시간 큼, 가치 의문)
4. **유지** — catalog 정보 측면 (v3.1 코드가 SHE에 referenced 됨) 그대로 보존

### 장기 (architectural)
자동 SHE 생성 시 matcher impact 예측 모델 필요:
- broadness_score 알고리즘 재설계 (자동 생성은 0.3 default)
- pre-INSERT regression simulation
- 매칭 ranking 보정 (status='approved_auto'에도 sub-tier 도입)

## 산출
- `data-team/05-enrichment/llm-scripts/promote_she_review.py` (인프라 보존)
- `runtime-artifacts/promote_she_review_audit.jsonl` (2 batch FAIL 기록)
- 본 보고서

## 다음 (Sprint 진행)
**Day 3**: closed vocabulary prompt 설계 + openai_client.py 테스트
**Day 4-5**: A/B testing
**Day 6**: 8-photo + production 측정
**Day 7**: runbook + Makefile
