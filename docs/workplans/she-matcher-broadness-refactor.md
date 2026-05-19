# SHE Matcher Broadness-aware Refactor (T4 #1 후속 sprint)

> **Status**: 계획 (사용자 승인 대기)
> **Trigger**: [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md) — 77 SHE 수동 검토 결과 (approve 57 / modify 19 / defer 1)
> **Predecessor**: [t4-77-she-matcher-integration-decision.md](../dev-notes/t4-77-she-matcher-integration-decision.md) — T4 #1 sprint VETOED (-7.07%p) 이관 결정
> **Predicted duration**: 1-2 weeks
> **Predicted cost**: $0 (코드/검증만)

---

## Background

### 사실 정리

1. T4 #1 sprint에서 pending_review 77 SHE를 5-by-5 batch로 promote 시도 → **첫 5 batch에서 she_accuracy -7.07%p VETOED, rollback 자동 수행**.
2. 사용자 77 수동 검토 (2026-05-19) 결과:
   - approve **57** (74%, 패턴 자체 OK)
   - modify **19** (25%, visual_trigger 부정합)
   - defer **1** (1%, 추가 검토 필요)
   - reject **0**
3. modify 19건 중 **8건이 "PPE 과도 요구" 테마** (`SAFETY_SHOE_ABSENT` 등 PPE 부재를 hard signal로 사용 → 일반 환경에서 false positive).
4. `she_matcher.py`는 `UNSAFE_PPE_STATES` set (HELMET_MISSING, SAFETY_SHOES_MISSING 등 8 states)을 hardcoded — PPE 부재가 매칭 score에 직접 가중.

### 핵심 가설

> **broadness가 큰 SHE(0.55) 패턴이 PPE 부재 signal에 과민하게 반응 → 일반 보행/계단/창고 사진까지 매칭 → SHE accuracy 회귀.**

본 sprint는 위 가설을 코드/검증으로 입증하고, matcher refactor로 해결.

---

## Goal

1. **PPE state weakening**: PPE 부재를 hard requirement에서 weak signal로 강등. 다른 6 axis가 매칭되면 PPE 부재 여부와 무관하게 후보 SHE에 포함.
2. **broadness-aware ranking**: `broadness_score`를 matcher 후보 정렬 가중치로 반영. broad pattern은 specific pattern보다 후순위.
3. **`status='approved_derived'` 신규**: matcher가 매칭 시도하지만 priority 낮음. `approved_auto`가 매칭 못한 경우만 fallback.

### Acceptance criteria

| # | 기준 | 검증 |
|---|---|---|
| AC-1 | approve 57 batch promote → Gate 3 PASS (she_accuracy regression ≤ 0.02) | `promote_she_review.py --apply --only-from-review-json REVIEWED.json` |
| AC-2 | modify 19 visual_trigger patch 후 promote → Gate 3 PASS | (Step 3 patch 생성 후 동일 명령) |
| AC-3 | 77 SHE 전부 통합 후 baseline 대비 she_accuracy 변동 ≤ 0.05 | `regression_gate.py` vs `replay_baseline_v3.json` |
| AC-4 | overall_accuracy / penalty_accuracy regression ≤ 0.02 | (동일) |
| AC-5 | PPE 부재 시 matcher가 "거의 모든 사진" 매칭 안 함 (false_positive_rate ≤ baseline + 0.05) | replay synthetic |

---

## Phases

### Day 1 — Diagnostic: PPE 부재 signal 영향 정량화

- `she_matcher.py` 매칭 로직 readthrough + 점수 계산 식 추출
- `UNSAFE_PPE_STATES` 매칭이 score에 기여하는 비중 측정 (replay synthetic 한 번 + score breakdown 출력)
- T4 #1 first batch 5 SHE 중 어떤 게 -7.07%p에 기여했는지 audit log 분석
- 결과: `docs/dev-notes/she-matcher-ppe-signal-analysis.md`

### Day 2 — PPE state weakening 구현

- `she_matcher.py`에 PPE state weight parameter 추가 (default 1.0 → 0.3 또는 0)
- 매칭 후보 산출 시 PPE state는 ranking에만 영향, 후보 포함/제외 결정에는 무관
- 단위 테스트: 일반 보행 사진(PPE 없음, 위험 없음)이 SHE 매칭 안 됨
- 단위 테스트: 위험 환경 + PPE 부재 사진이 여전히 SHE 매칭

### Day 3 — broadness-aware ranking 구현

- `she_matcher.py` ranking 함수에 broadness_score 가중치 추가
  - `final_score = base_score × (1 - broadness_score × broadness_penalty)`
  - default `broadness_penalty=0.3` (0.55 broadness → 16.5% 페널티)
- 후보 SHE 정렬 시 specific pattern 우선
- 단위 테스트: 같은 axis 매칭 시 broadness 낮은 SHE 먼저

### Day 4 — `status='approved_derived'` 신규 도입

- PG `she_catalog.status` 컬럼 enum 확장: `approved_auto` / `approved_derived` / `pending_review` / `rejected_manual`
- `promote_she_from_review.py` (Step 2 wrapper) 확장: approve 57 → `approved_derived`로 promote 옵션
- matcher 로직: `approved_auto` 우선 매칭 → 매칭 없을 시 `approved_derived` fallback
- 단위 테스트: `approved_auto` SHE 있을 때 `approved_derived` 미반환

### Day 5 — Approve 57 promote + Gate 3 (AC-1)

- `promote_she_review.py --apply --only-from-review-json REVIEWED.json`
- 9 batches × 5 SHE × Gate 3
- 전체 PASS 시 audit log 분석 + dev-note 업데이트
- FAIL 시 audit에서 문제 SHE 식별 + 추가 modify 후보 등록

### Day 6 — Modify 19 visual_trigger patch + promote (AC-2)

- 사용자 `suggested_changes_text` 기반 5개 테마별 patch 생성:
  - Theme A (8): `visual_triggers`에서 PPE 부재 단서 자동 제거 + `ppe_state` axis 비워두기
  - Theme B (3): 해당 trigger 삭제
  - Theme C (4): `features` axis 일반화 (특정 물질/공간 한정 제거)
  - Theme D (3): 사용자 reason 기반 수동 patch
  - Theme E (1): features 부정합 SHE는 별도 작업 (또는 reject)
- patch 적용 후 `promote_she_review.py` 재실행

### Day 7 — Full 77 통합 검증 + 정본 문서 (AC-3/4/5)

- 모든 promote 결과 정리 + Gate 3 최종 측정
- `docs/dev-notes/she-matcher-broadness-refactor-results.md` 작성
- 정본 문서 갱신:
  - `docs/status/current-session.md` Tier 5 closure
  - `docs/status/evaluation-baseline.md` post-refactor metrics
  - `docs/workplans/llm-accelerated-ontology-engineering.md` Status 표
- main merge + GitHub push

---

## Risks + Mitigations

| Risk | Probability | 대응 |
|---|---|---|
| PPE weakening 시 위험 환경 + PPE 부재 case 매칭 약화 | 중 | weight=0.3으로 유지(완전 무시 아님). AC-5로 false_negative 모니터 |
| broadness penalty 0.3이 너무 강해서 broad SHE 영구 불매칭 | 중 | A/B 테스트: penalty 0.1/0.2/0.3 비교 후 최적 |
| `approved_derived` 도입으로 인한 PG migration 위험 | 낮 | ALTER TABLE 1줄 + CHECK constraint 확장 |
| modify 19 patch 자동 생성 시 사용자 의도 오해 | 중 | patch 적용 전 dry-run + 사용자 확인 step |

---

## Critical files

### 수정 대상 (코드)
```
serving-team/08-app/backend/app/services/she_matcher.py    (1순위, 핵심)
serving-team/08-app/backend/app/db/models.py               (status enum 확장)
data-team/05-enrichment/llm-scripts/promote_she_review.py  (approved_derived 옵션)
```

### 신규 (코드/스크립트)
```
data-team/05-enrichment/llm-scripts/patch_she_visual_triggers.py  (Day 6)
serving-team/07-materialization/pg-sync-scripts/migrate_she_status_enum.sql  (Day 4)
```

### 신규 (검증)
```
serving-team/08-app/backend/tests/test_she_matcher_broadness.py  (Day 2-3 unit)
docs/dev-notes/she-matcher-ppe-signal-analysis.md  (Day 1)
docs/dev-notes/she-matcher-broadness-refactor-results.md  (Day 7)
```

---

## Limits / Scope

### 명시 제외
- LLM 호출 추가 0 (코드 로직 + replay only)
- SHE 추가 생성 0 (기존 77 SHE만 대상)
- F.2 catalog 변경 0 (taxonomy 그대로)
- 새 ontology TBox 변경 0
- frontend 변경 0

### Dependent (sprint 시작 전 필요)
- Step 2 (approve 57 promote) 결과 — 본 sprint plan의 진단 입력
- defer 1건 close-out 결정

### Critical path

```
Day 1 (diagnostic)
  ↓
Day 2 (PPE) ─┬─→ Day 5 (promote 57)
             │
Day 3 (broadness)
  ↓
Day 4 (status enum) ──→ Day 6 (modify 19 patch + promote)
                          ↓
                        Day 7 (verify + docs)
```

Day 2/3은 병렬 가능. Day 5/6은 sequential (matcher refactor 적용 후 promote).

---

## Future follow-ups (out of scope)

- R-4~R-30 SWRL OWL serialization batch 변환 (별도 sprint)
- OSHA admin penalty Pipe-A 확장 (T4 #2 후속, 4-6h)
- Phase J OBO Foundry (별도 plan)

---

## 결정 필요 항목 (사용자 선택)

1. **broadness_penalty 초기값**: 0.1 (보수적) / **0.3 (권장)** / 0.5 (공격적)?
2. **`approved_derived` 도입 시점**: Day 4 (계획대로) / 본 sprint 후 별도 sprint?
3. **Theme E (1건 features 부정합)**: modify patch 시도 / 단순 reject?
4. **Step 5 defer 1건 (SHE-DENTALPROCEDUR-c1cd69a159)**: 본 sprint 진입 전 결정 / 후행?
