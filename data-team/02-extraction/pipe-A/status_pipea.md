# KOSHA 온톨로지 Pipe A — 진행 상태

> 최종 업데이트: 2026-04-25
> 계획서: plan_pipea.md

## 현재 기준 참고 (2026-05-07)

Pipe-A의 최신 역할은 법령/SR/벌칙의 source of truth를 제공하는 것이다.

```text
law:Article
→ law:NormStatement
→ sr:SafetyRequirement
→ pen:PenaltyRule / PenaltyCondition
→ OHS PenaltyPath 응답 모델
```

주의:

- 이 문서의 `penalty_routes`는 과거 추출 중간 산출물/DB 테이블명을 설명한다.
- 최신 온톨로지 구조에서는 `PenaltyRoute` 클래스와 `penaltyForArticle` 속성을 사용하지 않는다.
- 최신 서비스는 `violatedArticle`, `penaltyArticle`, `violatedNorm`, `hasPenaltyRule` 경로를 기준으로 벌칙을 조회한다.
- SR의 위험 연결은 `sr:addressesFeature`와 구체 관계를 함께 물질화하는 구조로 확장되었다.

---

## 1. 실행 환경

- 디렉토리: `data-team/02-extraction/pipe-A/`
- legalize-kr 소스 커밋: `d8c121b2`

---

## 2. Phase 1 완료 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| Step 0 스크립트 | ✅ 완료 | 1,227조문 추출 (5개 법령) |
| Step 1 스크립트 | ✅ 완료 | 656 벌칙경로 (RULE만 대상) |
| Step 2 배치 준비 | ✅ 완료 | 33개 배치, 656조문 전체 |
| Step 3 NS 생성 (LLM) | ✅ 완료 | 1,229개 NS (653개 조문 커버) |
| Step 4 검증 + DB 적재 | ✅ 완료 | 13개 규칙 검증 (구조적 9 + 의미적 4) |
| JSON Schema 4개 | ✅ 완료 | additionalProperties: false |
| lib 모듈 4개 | ✅ 완료 | article_code, ns_identifier 등 |
| Phase 1 config 파일 3개 | ✅ 완료 | law-sources, delegation-map, penalty-article-map |
| DB 참조성 검증 | ✅ 완료 | PostgreSQL, 9개 규칙 ALL PASS |

**Phase 1 완료.**

---

## 3. 실전 테스트 결과

### Step 0 (조문 추출) — PASS
- 1,227조문 추출 (RULE 674, OSHA 175, SADA 16, DECREE 119, ENFORCE 243)
- `law-sources.json` 경로 `../../../legalize-kr/...`로 수정 후 정상 동작
- 결정론성 확인 (데이터 해시 동일)

### Step 1 (벌칙 경로) — PASS
- 656개 라우트 (형사벌 적용 638, 미적용 18)
- FK 무결성: 656건 모두 article-texts.json에 존재
- 제24조: `delegatedFrom=제38조`, criminal.violation_employer 정확
- 제2조: `hasPenalty=false` 정확

### Step 2 (배치 생성) — PASS
- 33개 배치 생성 완료 (총 656조문, batch-size 20)
- preAssignedIds 자동 생성, hasSanction(criminal/administrative) 자동 복사 확인

### Step 3 (NS 생성, LLM) — PASS
- 33개 배치 × 4병렬 × 9라운드로 처리
- 총 NormStatements: 1,229개 (653개 조문 커버, 3개 조문은 fullText 비어 NS 미생성)
- hasModality 분포: OBLIGATION 917 (74.6%), EXEMPTION 145 (11.8%), PROHIBITION 103 (8.4%), PERMISSION 34 (2.8%), DEFINITION 30 (2.4%)
- 단서 NS (hasModificationLink 있음): ~145개

### Step 4 (NS 검증) — PASS
- 33개 파일, 1,229개 NS, 13규칙 검증
- ERROR: 0건, WARNING: 1,026건
- WARNING 내역: guidanceIssues 986, modalityKeywordMismatches 36, conditionMissing 3, provisoChainIssues 1
- WARNING은 한국어 법률 어미 변형에 의한 false positive. 수동 샘플 확인 완료.

### DB 적재 + 검증 — ALL PASS
- PostgreSQL DB 적재: articles 1,227행, penalty_routes 656행, norm_statements 1,229행 (33개 파일)
- 9개 무결성 규칙 전수 통과, 에러 0건 (V8: NS→articles FK, V9: NS 중복 포함)
- 형사벌 적용: 638조, 과태료 적용: 0조 (법적으로 올바름)

---
## 4. Phase 2 진행 상태

> 계획서: plan_pipea.md (Section 7)
> 재현문서: phase2_step1.md ~ phase2_step6.md

| 항목 | 상태 | 비고 |
|------|------|------|
| Step 1 SR 스키마 + 카테고리 | ✅ 완료 | sr-file.schema.json (`^SR-[A-Z_]+-[0-9]+$`) + sr-section-category-map.json (128개 section exact match) |
| Step 2 SR 배치 준비 | ✅ 완료 | step5_prepare_sr_batch.py, **카테고리 기반 48배치**, 626 SR그룹, 43카테고리 중 42 활성 (GENERAL skipSR) |
| Step 3 SR 에이전트 가이드 | ✅ 완료 | agents/step5-sr-generation.md (categoryContext + addressesHazard 배열 강조) |
| Step 4 SR 생성 (LLM) | ✅ 완료 | 48/48배치, **626/626 SR**, 4라운드 실행 (5+15+15+13) |
| Step 5 SR 검증 | ✅ 완료 | step6_validate_sr.py (14규칙), ERROR 0건, WARNING 14건 (R11 1건 + R13 13건) |
| Step 6 DB 적재 | ✅ 완료 | `import_and_verify.py --clean`, V1~V15 ALL PASS, SR 626행 + sr_ns_mapping 1,020행 + sr_article_mapping 626행 |

**Phase 2 완료.**

---

## 5. Phase 2 실전 테스트 결과

### Step 1 (SR 스키마 + 카테고리 매핑) — PASS
- `sr-file.schema.json`: SR ID 형식 `^SR-[A-Z_]+-[0-9]+$`, 12개 hazard 키워드, 8개 requirementType, Phase 3 예약 필드 5개 (nullable)
- `sr-section-category-map.json`: 128개 고유 section → 43개 카테고리 exact match (`dict.get()`), 커버리지 100%, UNCATEGORIZED 0건
- 편1 총칙 11개 + 편2 안전 18개 + 편3 보건 13개 + 편4 1개 = 43개 카테고리

### Step 2 (SR 배치 준비) — PASS
- OBLIGATION/PROHIBITION NS 1,020개 필터링 (전체 1,229개 중)
- 43개 카테고리 중 42개 활성 (GENERAL은 skipSR), 48개 배치 생성
- SR ID 사전 할당 (`SR-{카테고리}-{3자리순번}`), hasSanction penalty-routes.json에서 자동 복사
- 소규모 카테고리 번들링: PPE-WELFARE, STEELWORK-DEMOLITION, ROBOT-CONVEYOR-SPECIAL, MISC-SMALL
- categoryContext 메타데이터 포함 (LLM 일관성 보장)

### Step 3 (SR 에이전트 가이드) — PASS
- `agents/step5-sr-generation.md`: 10개 생성 규칙 정의
- 핵심 제약: identifier=preAssignedId verbatim, hasSanction 입력 복사, Phase 3 예약=null
- categoryContext + addressesHazard 배열 강조, bindingForce 매핑 (OBLIGATION→MANDATORY, PERMISSION→RECOMMENDED)

### Step 4 (SR 생성, LLM) — PASS
- 48/48 배치, **626/626 SR** 생성, ERROR 0건
- 4라운드 병렬 실행: 파일럿 5배치 → 2차 15배치 → 3차 15배치 → 4차 13배치
- WARNING 14건 (R11 1건 + R13 13건, false positive)
- PATHOGEN 배치: 이전 API 정책 거부 → 재생성 시 정상 통과
- **이슈 해결 — 카테고리 매칭 부분 문자열 충돌**:
  - 발견: `match_category()`의 `kw in section` → "장1"이 "장10"에 매칭, 149개(24%) SR 오분류
  - 수정: `sr-section-category-map.json` (128키 exact match) + `dict.get(section)` 완전 일치로 교체
  - 결과: 159건 카테고리 정정, UNCATEGORIZED 0건 → 48배치 626 SR 전량 재생성 → 검증 PASS → DB 재적재 완료

### Step 5 (SR 검증) — PASS
- `step6_validate_sr.py`: 14개 규칙 (R1~R10 구조적 Hard Error + R11~R14 의미적 Warning)
- 626 SR, **ERROR 0건**, WARNING 14건:
  - R11_QUANT_MISSING 1건: SR-RIGGING-001 (안전계수 값이 법 조문 각호/별표에 있어 NS 텍스트 미포함)
  - R13_TITLE_TEXT_MISMATCH 13건: 한국어 조사 변화에 의한 false positive (예: "국소배기장치의" vs "국소배기장치를")

### Step 6 (DB 적재 + 검증) — ALL PASS
- `python3 db/import_and_verify.py --clean` 실행 (2026-04-12)
- articles 1,227행, penalty_routes 656행, norm_statements 1,229행
- safety_requirements 626행, sr_ns_mapping 1,020행, sr_article_mapping 626행
- V1~V15 무결성 검증 **ALL PASS** (Phase 1 V1~V9 + Phase 2 V10~V15)

---

## 6. Faceted Taxonomy 태깅 결과 (Phase 1)

- **태깅 완료**: SR 626/626 (100%)
- **3축 분류**:
  - `accident_type`: 8개 카테고리
  - `hazardous_agent`: 11개 카테고리
  - `work_context`: 13개 카테고리
- **스크립트**: `step7_faceted_retag.py` (`config/hazard-taxonomy-unified.json` 기반)
- **DB 컬럼**: `accident_types`, `hazardous_agents`, `work_contexts` (JSONB + GIN 인덱스, `safety_requirements` 테이블)

---

*이 문서는 Pipe A의 진행 상태와 테스트 결과를 관리합니다. 계획은 `plan_pipea.md`를 참조하세요.*

## 최종 상태: ✅ 완료 (2026-04-12 확정, 2026-04-25 재확인) + Faceted 태깅 완료

- V1~V15 전부 PASS
- SR 626, NS 1,229, Articles 1,227
- Faceted 3축 태깅: SR 626/626 (100%), accident_type(8)/hazardous_agent(11)/work_context(13)
- Pipe-B/C에서 safety_requirements, sr_ns_mapping, sr_article_mapping 참조 중

## 하류 파이프라인 의존

- Pipe-B: ci_sr_mapping.sr_id → safety_requirements FK
- Pipe-C: sr-registry.json에 Pipe-A SR+NS+Article 데이터 통합
