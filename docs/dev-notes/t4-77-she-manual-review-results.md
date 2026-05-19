# T4 #1 후속 — 77 SHE 수동 검토 결과 (2026-05-19)

## Background

[t4-77-she-matcher-integration-decision.md](t4-77-she-matcher-integration-decision.md)에서 5 SHE batch promote → **-7.07%p VETOED** 후 별도 sprint로 이관. 그 사전 단계로 사용자가 77 SHE를 1차 수동 검토.

**입력**: `data-team/05-enrichment/runtime-artifacts/pending_review_she_for_manual_review.json` (77 SHE, F.2 v3.1 link)
**검토 도구**: standalone HTML viewer (`she_review_ui.html`, 4 decision + freeform note)
**출력**: `data-team/05-enrichment/runtime-artifacts/pending_review_she_REVIEWED.json` (99 KB, 원본 + 결정 + 자동 테마 분류)

## Decision distribution (77/77)

| decision | count | ratio |
|---|---:|---:|
| **approve** | **57** | 74.0% |
| **modify** | **19** | 24.7% |
| **defer** | **1** | 1.3% |
| reject | 0 | 0.0% |

→ 사용자는 패턴 **자체를 폐기할 만큼 비현실적인 것은 없다**고 판단. 다수(57)는 그대로 OK, 일부(19)는 visual_trigger 부정합 보정 필요, 1건은 보류.

## Modify 19건 — 5개 테마 자동 분류

분류 알고리즘: `suggested_changes_text` 한글 키워드 매칭 (안전화/안전모 → A, 사진/찍을 → B, 없어도/다른 종류 → C, 없을/맨손/즉시 녹 → D, 안 맞 → E).

| 테마 | 건수 | 의미 |
|---|---:|---|
| **A. PPE 과도 요구** | **8** | `ppe_state: SAFETY_SHOE_ABSENT/SAFETY_HELMET_ABSENT`가 일반 환경에서까지 hard signal |
| **B. 사진 촬영 불가능 단서** | **3** | 사고 순간, 미세 흔적, 사후 사진 — Vision LLM의 사진 시점 mismatch |
| **C. 과도하게 좁은 조건** | **4** | 특정 물질(납·아크릴레이트)·공간(좁은 기계실)에만 한정 |
| **D. 비현실적 시나리오** | **3** | 물리적/맥락적 비현실 |
| **E. 도메인 자체 불일치** | **1** | features 부정합 (DENTALPROCEDUR) |

### Theme A — PPE 과도 요구 (8건, **matcher refactor 1순위**)

| she_id | work_context | 사용자 코멘트 (요약) |
|---|---|---|
| SHE-CLEANINGWET-6e366c5575 | 음식점 청소 (CLEANING_WET × CUT) | "음식점에서 안전화를 신지 않음" |
| SHE-DISPLAYSETUP-3fe2f9e37b | 일반 창고 진열 | "창고 안전모 착용 요구는 과함" |
| SHE-OBSTRUCTEDVIEW-efc8823aad | 시야 차단 작업 | "운동화여도 위험한 상황" |
| SHE-OVERLOADEDHAND-1470df6a97 | 과적 핸드카트 | "안전화 미착용이 핵심 아님" |
| SHE-POWERRACKSAFET-716a8131d7 | 웨이트 짐 | "맨발은 위험, 안전화까지는 비현실; 운동화 OK" |
| SHE-SLOPERAMP-eb718815af | 경사로 운반 | "안전화 요구는 과함" |
| SHE-STAIRCARRYING-483a6abc08 | 계단 운반 | (동일) |
| SHE-WALKWAYOBSTRUC-757ef5872e | 보행로 장애 | (동일) |

**공통 패턴**: `ppe_state: SAFETY_SHOE_ABSENT`가 visual_trigger로 노출되어 있어, 일반 보행/운반 사진에서 false positive 양산 가능. PPE 절대 부재를 risk signal로 쓰는 게 **broadness를 좁히는 게 아니라 부정확한 매칭을 유도**.

### Theme B — 사진 촬영 불가능 단서 (3건)

| she_id | 문제 단서 |
|---|---|
| SHE-DISPLAYSETUP-c34c9b3805 | "손가락 또는 손바닥 부위의 찰과·절상 흔적" — 사진에서 미세 흔적 식별 불가 |
| SHE-BOXHANDLING-8a9f239d9a | "발 위로 낙하하는 순간" — 시점 mismatch. 대안: "옮기는 박스가 위태로워 보이는" |
| SHE-CONFINEDSPACE-b6fbefaf2c | "실제 사고 후 사진" — 서비스 시나리오(사전 예방)에 부합 안 함 |

### Theme C — 과도하게 좁은 조건 (4건, 일반화 필요)

| she_id | 좁은 조건 | 일반화 방향 |
|---|---|---|
| SHE-COMPRESSIONDEV-e7351932ea | "좁은 기계실" 한정 | 좁은 기계실 외 공간도 위험 |
| SHE-CONFINEDCOATIN-da85e838ef | "납 도료 + 회백색 분진" | 다른 도료/색상도 위험 |
| SHE-CONFINEDCOATIN-fc99086394 | "아크릴레이트만" | 다른 화학물질도 위험 |
| SHE-INTERLOCKBYPAS-ac30fa32ae | "바닥에 어지럽게 놓인 공구·전선" | 그게 없어도 위험 |

### Theme D — 비현실적 시나리오 (3건)

| she_id | 문제 |
|---|---|
| SHE-BREADSLICER-d9856258a4 | "슬라이서 주변 어지럽게 놓인 청소도구" — 없을 가능성이 더 큼 |
| SHE-CHEMICALCLEANI-0d81697d9b | "맨손으로 농축 알칼리 용기" — 물리적 비현실 (즉시 손 손상) |
| SHE-CLEANINGWET-532fa157a6 | "젖은 바닥에서 아동이 뛰는" — 산업안전 도메인 외 |

### Theme E — 도메인 자체 불일치 (1건)

| she_id | 문제 |
|---|---|
| SHE-DENTALPROCEDUR-798a8c199d | "치과 진료실 + 방치된 아말감 캡슐 + 다른 features" 조합 부정합 |

## Defer (1건)

| she_id |
|---|
| SHE-DENTALPROCEDUR-c1cd69a159 |

→ 별도 검토 필요. matcher refactor 후 데이터 기반 자동 판정 가능 여부 재평가.

## T4 #1 sprint VETOED 원인 재해석

이전 sprint에서 발견했던 **"5 SHE batch promote → -7.07%p, she_accuracy 0.5771 → 0.5064 VETOED"** (rollback 자동 수행):

| 가설 | 본 검토 결과로 본 타당성 |
|---|---|
| 5개 중 PPE 과도 패턴(Theme A) 다수 포함 | 매우 가능. SLOPERAMP/STAIRCARRYING/WALKWAYOBSTRUC 등이 5 batch에 들어갔을 가능성 큼 |
| matcher가 SAFETY_SHOE_ABSENT를 강한 매칭 signal로 사용 | Theme A 8건 모두 동일 패턴 → matcher 로직 자체 문제 |
| broadness_score (0.55)가 matcher score에 반영되지 않음 | T4 #1 dev-note 가설과 정합. 우선순위 ranking 부재 |

## Matcher refactor 핵심 가설 (Step 4 sprint plan 대상)

1. **PPE state weakening**: `ppe_state` axis를 hard requirement에서 weak signal로 강등. 다른 6 axis (work_context/accident_type/hazardous_agent/agent_state/environmental/work_activity)가 매칭되면 PPE 부재 여부와 관계없이 SHE 매칭 후보. PPE 부재는 risk_score 보정 인자로만 사용.
2. **broadness-aware ranking**: matcher의 후보 SHE 정렬 시 `broadness_score` 가중치 적용. broad pattern(0.55)은 specific pattern(0.4-) 대비 후순위.
3. **status='approved_derived' 신규**: matcher가 매칭 시도하지만 priority 낮음. `approved_auto`가 매칭 못한 경우만 fallback.

## Acceptance criteria (Step 4 sprint)

- approve 57 SHE batch promote → Gate 3 PASS (she_accuracy regression ≤ 0.02)
- modify 19 SHE도 patch 후 promote 시도 → Gate 3 PASS
- 전체 77 SHE 통합 후 baseline 대비 she_accuracy 변동 ≤ 0.05

## Step 2 결과 — Approve 57 batch promote 재시도 (2026-05-19 06:30, VETOED)

`promote_she_review.py --apply --only-from-review-json REVIEWED.json`

approve 57 중 wc/at='OTHER' 16개 제외 → **41 SHE 대상**, broadness ASC 정렬 후 5-by-5 batch.

**Batch 1/9** (가장 specific 5 SHE):
- SHE-HOPPERBLADEWOR-ab29dbacc1 (HOPPER_BLADE_WORK × BLADE_LACERATION)
- SHE-AIRLESSSPRAYER-7c2df46ba3 (AIRLESS_SPRAYER × EYE_VISION_DAMAGE)
- SHE-AWKWARDPOSTURE-adab8dd396 (AWKWARD_POSTURE × ERGONOMIC)
- SHE-BIOMEDICALWAST-5a543367ab (BIOMEDICAL_WASTE × EYE_FOREIGN_BODY)
- SHE-BIOMEDICALWAST-6945865bd7 (BIOMEDICAL_WASTE × CUT)

| metric | baseline_v3 | post-batch1 | delta | verdict |
|---|---:|---:|---:|---|
| **she_accuracy** | 0.5771 | 0.4754 | **-0.1017** | **VETOED** |
| sr_accuracy | 0.7581 | 0.7581 | 0.0000 | ok |
| penalty_accuracy | 0.1835 | 0.4233 | **+0.2398** | ok (penalty 보너스 재확인) |
| overall_accuracy | 0.1377 | 0.2869 | +0.1492 | ok |
| false_positive_rate | 0.8696 | 0.8696 | 0.0000 | ok |
| false_negative_rate | 0.0625 | 0.0581 | -0.0044 | ok |

→ **rollback 자동 수행, 5/5 SHE pending_review 복원 검증.** Batch 2-9 미진입.

## 누적 audit history 분석 (5회 시도, 모두 VETOED)

| # | 시점 | SHE 5개 | Δshe_accuracy | 비고 |
|---|---|---|---:|---|
| 1 | 2026-05-18 05:03 | OTHER+AIRLESS+AISLE | -0.0784 | 첫 시도 |
| 2 | 2026-05-18 05:07 | AIRLESS+AWKWARD+BIO×3 | -0.1076 | broadness 재정렬 |
| 3 | 2026-05-19 04:06 | BREAD+CLEAN+DISPLAY+HOPPER+AIRLESS | -0.0707 | T4 #1 sprint |
| 4 | 2026-05-19 04:15 | (동일) | -0.0707 | retry |
| 5 | **2026-05-19 06:30** | **HOPPER+AIRLESS+AWKWARD+BIO×2 (manual review 후)** | **-0.1017** | **Step 2 본 시도** |

**일관된 패턴**:
1. 5번 모두 상이한 SHE 조합 (manual review 결과 적용 포함) → 동일하게 -7~-10%p
2. **penalty_accuracy는 항상 +20%p 이상** (promote 시 SR/penalty 매칭 자동 개선) ← 시사점
3. 가장 specific한 broadness 5개로 시도해도 회귀

## 결론 (Step 2 실패의 의미)

> **Manual review로 problematic SHE를 제거하는 것만으로는 promote 불가능.**
> **she_matcher.py 자체 로직 (broadness/PPE 처리) 문제가 본질.**

= [she-matcher-broadness-refactor.md](../workplans/she-matcher-broadness-refactor.md) sprint **prerequisite로 확정** (Step 4 plan의 가설 강력 입증).

## Action items 추적

| # | 작업 | 상태 | 비고 |
|---|---|---|---|
| 1 | Manual review dev-note 작성 (이 문서) | ✅ 완료 | — |
| 2 | approve 57 batch promote 재시도 | ✅ 완료 (VETOED) | Batch 1만 -10.17%p → rollback. 본 문서 위 section 참조 |
| 3 | modify 19 patch proposal 생성 | ✅ 완료 | `pending_review_she_PATCH_PROPOSAL.json` (PG-only, ontology 영향 없음) |
| 4 | matcher broadness-aware refactor sprint plan | ✅ 완료 | `docs/workplans/she-matcher-broadness-refactor.md`. **Step 2 결과로 prerequisite 확정** |
| 5 | defer 1건 close-out | ⏳ Step 5 | matcher refactor 후 재검토 권장 |
| 6 | Ontology TTL/SHACL 검토 | ✅ 완료 (PG-only로 충분) | 77 SHE는 정본 TTL에 없음. architectural debt 3가지 별도 정리 — 본 문서 아래 section 참조 |

## Ontology TTL/SHACL 검토 결과

| 정본 위치 | 77 SHE 포함 | 변경 필요? |
|---|:---:|---|
| `data-team/05-enrichment/she-data/she-instances-v1.ttl` | ❌ | 부재 — `link_v31_codes_to_she.py` PG INSERT만, TTL export 없음 |
| `kosha-ontology-v2.formatted.ttl` TBox | ✅ (class/property) | ❌ 변경 불필요 (schema는 OK) |
| `serving-validation-shapes-v3.ttl` SHACL | ❌ SHE shape 부재 | architectural debt |

**결론**: modify 19 patch는 인스턴스 값 수정 (features/visual_triggers) → schema 변경 0. PG-only로 충분.

**Architectural debt** (matcher refactor sprint와 병행 또는 후행 권장):
- A. PG → TTL re-export script 부재 (`data-team/04-ontology-export/` placeholder)
- B. SHACL shape for `she:SituationalHazardPattern` 부재
- C. promote된 SHE의 ontology export 정책 부재 (`approved_auto`만 / `approved_derived`도?)

## Related

- [t4-77-she-matcher-integration-decision.md](t4-77-she-matcher-integration-decision.md) — T4 #1 sprint 이관 결정
- [phase-g.4-she-patterns-reasoner-derived.md](phase-g.4-she-patterns-reasoner-derived.md) — 77 SHE view 노출
- `data-team/05-enrichment/runtime-artifacts/pending_review_she_REVIEWED.json` — 사용자 검토 결과
- `data-team/05-enrichment/runtime-artifacts/she_review_ui.html` — 검토 UI (single-file)
