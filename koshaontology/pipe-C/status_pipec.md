# Pipe-C 교차검증 진행 상태

**최종 갱신**: 2026-05-10

## 현재 기준 참고 (2026-05-07)

Pipe-C의 최신 활용 목적은 `Guide/WorkProcess` 중심 개선 절차 추천 품질을 높이는 것이다.

```text
Pipe-A SR/Article
↔ Pipe-B ChecklistItem/WorkProcess/KoshaGuide
→ Pipe-C basedOn 감사/복원/교차검증
→ OHS Guide recommendation 품질 개선
```

전체 Guide JSON 추출 1,038개 기준 clean rebuild가 완료되어, Pipe-C는 기존 796개 기준 basedOn 복원 결과를 그대로 확장하지 않고 후보/evidence 레이어를 감사하는 방향으로 갱신한다.

## 전체 상태: ✅ 1,038 Guide 기준 후보 감사 리포트 추가

| Step | 작업 | 상태 | 결과 |
|---|---|---|---|
| 0 | SR 커버리지 갭 분석 | ✅ | 364/626 SR 커버 (58.1%), 정규화 100% |
| 1 | basedOn 매핑 감사 | ✅ | 의심 2,496건 (27.2%), 약함 5,598건 (61.1%), 정상 1,070건 (11.7%) |
| 2 | DT 중복 탐지 | ✅ | 도메인 내 327그룹 (1,891건), 교차 도메인 141개, 유사 쌍 50개 |
| 3 | basedOn null 복원 | ✅ 과거 적용 | 796개 기준 고신뢰 1,123건 DB 적용 이력. 1,038개 기준에서는 신규 후보 레이어로 재감사 |
| 4 | sr-registry.json | ✅ | 626 SR 통합 레지스트리 (1,270KB) |
| 5 | GuideInterLink | ✅ | 819개 파싱 가이드 기준 135건 상호참조 (DB 89건 적재) |
| 6 | ontology enrichment audit | ✅ | 1,038 Guide 기준 coverage/audit/candidate 리포트 생성 |
| DB | V-C1~V-C10 | ✅ | **10/10 PASS** |

## DB 현황 (1,038 Guide 기준)

- guide_inter_links: 89건 (135건 중 양쪽 가이드 모두 DB 등록된 것만)
- domain_terms.canonical_id: ALTER 완료 (아직 값 미부여)
- Pipe-A 회귀: SR 626, NS 1,229, Articles 1,227 보존
- Pipe-B 회귀: Guide 1,038, CI 54,571, WP 9,320, ES 8,103, DR 3,441, DT 7,728 보존
- `ci_sr_mapping`: 10,682 rows, distinct SR 131/626
- `wp_sr_mapping`: 3,599 rows, distinct SR 129/626
- Guide coverage: CI-SR 연결 없음 380건, WP-SR 연결 없음 437건

## 2026-05-09 Ontology Enrichment Audit

신규 스크립트:

```text
pipe-C/scripts/step6_ontology_enrichment_audit.py
```

신규 리포트:

```text
pipe-C/data/ontology-enrichment-audit-report.json
```

핵심 결과:

| 항목 | 이전 기준 | 현재 |
|---|---:|---:|
| CI feature coverage | 43,465/54,571 | 44,950/54,571 |
| WP feature coverage | 4,606/9,320 | 5,173/9,320 |
| ES feature coverage | 2,341/8,103 | 2,852/8,103 |
| DT feature coverage | 4,422/7,728 | 4,579/7,728 |
| CI-SR distinct SR | 130/626 | 131/626 |
| WP-SR distinct SR | 126/626 | 129/626 |

후보 테이블 현황:

| 후보 테이블 | rows | serving candidates | missing evidence |
|---|---:|---:|---:|
| guide_entity_feature_candidates | 66,105 | 66,105 | 0 |
| guide_sr_link_candidates | 382,510 | 382,510 | 0 |
| guide_visual_trigger_candidates | 12,071 | 12,071 | 0 |

주의:

```text
guide_sr_link_candidates.asserted 16,682건은 기존 asserted mapping을 candidate trace로 가져온 값이 대부분이다.
이번 실행에서 신규로 기존 mapping table에 물리 insert된 asserted 연결은 14건이다.
```

## 2026-05-09 OHS Runtime Feedback

ontology enrichment 후보를 OHS 추천 런타임에 연결한 뒤 actual response 240 샘플을 재실행했다.

```text
baseline: actual_response_samples_v1_v10_after_pipeb1038_20260509_072955
ontology_enrichment1: A-G-18 top procedure 33건 -> 51건
ag18_guard2: A-G-18 top procedure 51건 -> 3건
domain_guard2: A-G-18 51건 -> 3건 유지, G-116 5건 -> 0건, A-G-10 14건 -> 3건
```

`A-G-18-2026 항만하역작업`은 `MATERIAL_HANDLING`과 SR-CARGO 후보가 매우 넓어 일반 물류/운반 상황까지 끌어오는 대표 사례였다. OHS 런타임은 이를 개별 if문이 아니라 Guide domain profile rule로 일반화했다. `exclusive` Guide는 필수 문맥이나 업종 alignment가 없으면 후보에서 제외하고, `domain_specific` Guide는 강한 감점을 적용한다. 상태/벌칙 경계는 변경 0건, `negative_false_positive` 10건과 `positive_missed` 2건은 기존 기준과 동일하게 유지됐다.

## 2026-05-10 Synthetic Guide Feedback

synthetic observation v1~v10 2,360건을 Guide 추천 전용 평가 데이터로 사용해 Pipe-B manual usage profile과 OHS runtime의 연결 품질을 다시 검증했다.

```text
usage_profile2: legacy mismatch 1,150 -> current mismatch 361 (68.61% 감소)
usage_profile5: legacy mismatch 1,151 -> current mismatch 220 (80.89% 감소)
usage_profile11: legacy mismatch 1,145 -> current mismatch 165 (85.59% 감소)
actual response 240: status changed 0, negative_false_positive 10, positive_missed 2, ambiguous_over_promoted 5
v10 SHE smoke: recall 100%, FN 0, FP 0
```

신규 리포트:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile5_20260510_000306.md
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile5_20260510_000435.md
pictures-json/reports/synthetic_observations_v10_usage_profile5_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile5_vs_pipeb1038.md
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile11_20260510_011317.md
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile11_20260510_011333.md
pictures-json/reports/synthetic_observations_v10_usage_profile11_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038.md
```

Pipe-C 관점의 해석:

```text
basedOn/asserted mapping을 더 밀어 넣는 것보다, Guide 사용경계와 WorkProcess coverage를 먼저 보강하는 편이 추천 품질에 직접적이다.
NO_TOP은 usage_profile11 기준 395건이며, risk feature alias 확장이 아니라 Guide usage profile, visual trigger, WorkProcess relevance 보강 큐로 관리한다.
context-only/non-actionable SHE는 finding reasoning에는 남기되 Guide 표준절차를 단독 생성하지 않도록 OHS runtime에서 차단한다.
```

## 미처리

- DT canonical_id 값 부여 미실행 (중복 그룹 327개 중 정본 선정 대기)
- guide_inter_links 재생성 필요: 기존 819개 파싱 가이드 기준이므로 1,038개 기준 재감사 필요
- LLM enrichment 30/200/1,038 배치 미실행. 30 Guide pilot은 외부 OpenAI API로 Guide 텍스트가 전송되므로 명시 승인 후 실행
- candidateSR 저매칭 Guide 549건과 SR 미연결 Guide 380건을 우선 수동/LLM 보강 대상으로 삼아야 함
- 중신뢰 candidate는 OHS 추천 점수에는 쓰되 법적 asserted 근거처럼 표시하지 않도록 지속 검증 필요
- Guide domain/industry mismatch 감점 규칙과 actionable SHE Guide gate는 OHS 3차 구조 보강까지 완료. 다음은 usage_profile11 NO_TOP 395 큐를 기준으로 taxonomy/profile/WorkProcess coverage를 보강하고, candidate import 전 WorkProcess coverage를 보강하는 작업

## 도메인별 분석

| 도메인 | CI | SR연결 | 연결률 | basedOn 감사 의심 |
|---|---|---|---|---|
| A | 5,962 | 88 | 15.2% | 273건 |
| B | 10,000 | 94 | 28.9% | 815건 |
| C | 8,238 | 68 | 27.7% | 704건 |
| D | 3,719 | 80 | 35.8% | 174건 |
| E | 7,287 | 50 | 20.2% | 530건 |
