# KOSHA 온톨로지 Pipe A — 설계 계획서

> 최종 업데이트: 2026-04-25
> 재현문서: phase1_step0.md ~ phase1_step4.md (Phase 1), phase2_step1.md ~ phase2_step6.md (Phase 2)
> 진행상태: status_pipea.md

> 현재 기준 참고 (2026-05-07): 이 문서는 Pipe-A 구축 당시의 설계 계획서다. 최신 product 기준에서는 `PenaltyRoute`/`penaltyForArticle` 모델을 폐기하고 `PenaltyRule` + `violatedArticle` + `penaltyArticle` + `PenaltyPath` 구조를 사용한다. 또한 SR 위험 연결은 `risk:RiskFeature`와 `sr:addressesFeature`를 물질화하는 구조로 확장되었다. 최신 상태는 `status_pipea.md`, 루트 `온톨로지_통합구조_및_흐름도.md`, `OHS/README.md`를 함께 본다.

---

## 1. 설계 동기

이전 파이프라인에서 발견된 **7가지 일관성 문제**:

1. **필드 네이밍 불일치**: 같은 필드를 다른 이름으로 사용
2. **가이드 코드 형식 불일치**: 약칭 규칙 비표준
3. **벌칙(sanction) 중첩 불일치**: LLM이 매번 다른 구조 생성
4. **조문코드 형식 불일치**: 제24조 vs 24조 vs Article 24
5. **NS 식별자 모호성**: LLM이 식별자를 창작하여 충돌
6. **사전 검증 부재**: DB INSERT 시점에서야 오류 발견
7. **선택 필드 처리 불일치**: null vs 생략 vs {} 혼재

**해결 전략**: 결정론적 스크립트 + 사전 계산 식별자/벌칙 + 엄격한 JSON Schema

---

## 2. 법령 소스 (확정, 5개)

| ID | 법령명 | 법령구분 | 조문 수 | 역할 |
|---|---|---|---|---|
| **RULE** | 산업안전보건기준에 관한 규칙 | 고용노동부령 | 674조 (활성 656) | NS 생성 대상, 현장 안전/보건 기술기준 |
| **OSHA** | 산업안전보건법 | 법률 | 175조 | 벌칙 조문 소스 (제167~175조), 위임 근거 |
| **SADA** | 중대재해 처벌 등에 관한 법률 | 법률 | 16조 | 중대재해처벌법 벌칙 소스 (제6조) |
| **DECREE** | 산업안전보건법 시행령 | 대통령령 | 119조 | 적용범위, 대상기준, 별표, 자격요건 |
| **ENFORCE** | 산업안전보건법 시행규칙 | 고용노동부령 | 243조 | 서식, 신고절차, 교육시간, 세부기준 |

**제외된 법령** (폐지/이관된 구버전):
- 산업안전보건법 시행규칙 (구 노동부령, 2010년) — 275조 중 76조 삭제
- 산업안전보건법 시행규칙 환경부령 (2014년) — 297조 중 73조 삭제

### 법령 위임 구조

```
산업안전보건법 (OSHA, 법률)
  ├─ 시행령 (DECREE, 대통령령)      "대통령령으로 정하는 ~"의 대상·범위·자격
  ├─ 시행규칙 (ENFORCE, 고용노동부령) "고용노동부령으로 정하는 ~"의 서식·절차·세부기준
  └─ 산안규칙 (RULE, 고용노동부령)    현장 안전/보건 기술기준 → NS 생성 대상

중대재해처벌법 (SADA, 법률)         중대재해 벌칙
```

### Phase별 활용 계획

**Phase 1 (NS 파이프라인 + DB)**:
- Step 0: 5개 법령 모두 추출 → articles 테이블 적재 (1,227조문)
- Step 1: RULE만 벌칙 경로 생성 → penalty_routes 테이블 적재 (656라우트)
- Step 2: 배치 입력 생성 (preAssignedIds + hasSanction 사전 계산)
- Step 3: RULE 조문에서 NS 생성 (LLM)
- Step 4: NS 검증 (13규칙) → norm_statements 테이블 적재 + DB 무결성 검증 (V1~V9)

**Phase 2 (SR 파이프라인)**:
- Step 1: RULE 편/장/절 구조 기반 43카테고리 매핑 (GENERAL 제외 42카테고리 활성)
- Step 2: OBLIGATION/PROHIBITION NS 1,020개 → 626 SR그룹, 48배치 생성
- Step 3~4: SR 생성 (LLM)
- Step 5: SR 검증 (14규칙, ERROR 0)
- Step 6: DB 확장 + 적재 (V10~V15 추가, 총 V1~V15 ALL PASS)

**Phase 3 이후 (미착수)**:
- DECREE: SR의 `hasCondition`에 시행령 별표 기준 반영 예정
  - 예: "전기 계약용량 300kW 이상" (시행령 제42조) → SR 적용 조건
- ENFORCE: CI의 교육/서식 요구사항 반영 예정
  - 예: "안전교육 시간 및 내용" (시행규칙 제26조) → CI 교육 항목

---

## 3. 핵심 설계 원칙

1. **결정론적 출력**: Step 0, 1, 2, 4는 100% 스크립트. 동일 입력 → 동일 출력.
2. **LLM 역할 최소화**: Step 3만 LLM 사용. 식별자와 벌칙은 사전 계산.
3. **사전 스키마 검증**: 모든 출력은 JSON Schema 검증 후 저장. `additionalProperties: false`.
4. **null ≠ 생략**: 선택필드가 없으면 `null`. 필드 자체를 생략하지 않음. `{}`도 금지.

### 정규 식별자 형식

```
조문코드:  ^제\d+조(의\d+)?$          예: 제24조, 제332조의2
NS ID:    ^NS-[A-Z0-9]+-[0-9A-Z]+$  예: NS-RULE24-0, NS-RULE332B-1
SR ID:    ^SR-[A-Z_]+-[0-9]+$        예: SR-FALL-001, SR-FIRE_EXPLOSION-001
CI ID:    ^CI-[A-Z0-9]+-[0-9]+$      예: CI-DC13-001
```

### 조의N → 식별자 매핑

```
제332조의2 → NS-RULE332B-{seq}   (의2 → B)
제619조의3 → NS-RULE619C-{seq}   (의3 → C)
```

### 제재 구조 (criminal/administrative 분리)

penalty-routes.json과 NS의 hasSanction은 형사벌과 과태료를 구분한다.

**criminal (형사벌)** — 제167~172조:
- `violation_employer`: 산안법 제168조 — "5년 이하의 징역 또는 5천만원 이하의 벌금"
- `violation_contractor`: 산안법 제169조 — "3년 이하의 징역 또는 3천만원 이하의 벌금"
- `death`: 산안법 제167조 — "7년 이하의 징역 또는 1억원 이하의 벌금"
- `seriousAccident`: 중대재해처벌법 제6조 — 사망 "1년 이상 징역/10억 벌금", 부상 "7년 이하 징역/1억 벌금"

**administrative (과태료)** — 제175조 (6단계: 5천만원~300만원):
- `law`: 제175조 항·호 참조
- `maxFine`: 법정 상한
- `fineTableRef`: 시행령 별표35 (세부금액 참조)
- `oshaArticleRef`: 과태료 근거 OSHA 조+항

참고: RULE 조문은 제38조/제39조를 통해 위임되며, 이 두 조문은 과태료 대상이 아니므로 대부분의 RULE 조문에는 형사벌만 적용된다.

### 금지 패턴

```
절대 하지 마라:
- NS 식별자를 LLM이 창작
- hasSanction을 LLM이 작성 (penalty-routes.json에서 복사)
- additionalProperties 없는 스키마
- {} 빈 객체 (null 사용)
- "" 빈 문자열 (minLength: 1 위반)
- guideCode를 NS 메타데이터에 포함 (NS는 가이드 독립)
- 약식 형량 표기 (예: "5년/5천만원" → 정식만 허용)
```

---

## 4. Phase 1 파이프라인 스텝

| Step | 유형 | 스크립트/에이전트 | 입력 | 출력 |
|------|------|-------------------|------|------|
| 0 | 스크립트 | `scripts/step0_extract_articles.py` | legalize-kr JSON | `data/article-texts.json` |
| 1 | 스크립트 | `scripts/step1_extract_penalties.py` | article-texts + config | `data/penalty-routes.json` |
| 2 | 스크립트 | `scripts/step2_prepare_batch.py` | article-texts + penalty-routes | `data/norm-statements/batch-*-input.json` |
| 3 | LLM | `agents/step3-ns-generation.md` | batch input JSON | `data/norm-statements/ns-batch-*.json` |
| 4 | 스크립트 | `step4_validate_ns.py` + `db/import_and_verify.py` | NS files + article-texts + penalty-routes | validation report + PostgreSQL 적재 |

### 실행 방법

```bash
cd koshaontology/pipe-A

# Step 0: 조문 추출 (5개 법령, 1,227조문)
python3 scripts/step0_extract_articles.py

# Step 1: 벌칙 경로 (RULE만 대상, 656라우트)
python3 scripts/step1_extract_penalties.py

# Step 2: 배치 입력 생성
python3 scripts/step2_prepare_batch.py --articles 제24조,제42조 --batch-id batch-001
# 또는 전체: python3 scripts/step2_prepare_batch.py --law-id RULE --all --batch-size 20

# Step 3: NS 생성 (LLM — agents/step3-ns-generation.md 참조)
# batch-*-input.json을 LLM 에이전트에 입력 → ns-batch-*.json 출력

# Step 4: NS 검증 (13규칙) + DB 적재
python3 scripts/step4_validate_ns.py
python3 db/import_and_verify.py --clean

# --- Phase 2: SR 파이프라인 ---

# Step 1: SR 스키마 + 카테고리 매핑 (수동 설계 — phase2_step1.md 참조)

# Step 2: SR 배치 입력 생성
python3 scripts/step5_prepare_sr_batch.py --all --batch-size 20

# Step 3~4: SR 생성 (LLM — agents/step5-sr-generation.md 참조)
# sr-batch-*-input.json을 LLM 에이전트에 입력 → sr-batch-*.json 출력

# Step 5: SR 검증 (14규칙)
python3 scripts/step6_validate_sr.py

# Step 6: DB 확장 + SR 적재
python3 db/import_and_verify.py --clean
```

---

## 5. 설계 결정 이력 (10건)

### 결정 1: `step2_prepare_batch.py` 신규 추가 ✅

LLM 배치 입력을 자동 생성하는 스크립트가 없어 신규 작성.
- `--articles`, `--range`, `--all --batch-size` 3가지 모드 지원
- preAssignedIds 자동 생성, hasSanction 자동 복사

### 결정 2: `expressedInUnit` 필드 — 추가 안 함 ✅

`articleCode + lawId + paragraphRef`로 완전히 재구성 가능. 스키마 단순성 유지.

### 결정 3: `criminal.death` 조건 필드 — 보류 ⏳ (Phase 3)

`death` 키 자체가 "사망" 조건을 의미하므로 중복. Phase 3에서 검토.

### 결정 4: 위임 분류 근사치 — 수용 ✅ (Phase 3 이후 정밀화)

Step 1이 section 키워드로 제38조/제39조 분류. 벌칙 미적용 18조가 모두 정의/목적/적용 조문으로 정확. Phase 3 이후 `rule-to-delegation.json` 작성 예정.

### 결정 5: SR 파이프라인 — Phase 2 완료 ✅

Step 1~6 완료. 626 SR (48배치, 43카테고리 중 42 활성—GENERAL skipSR), sr-section-category-map.json (128키 exact match), DB 적재 + V1~V15 ALL PASS.

### 결정 6: DB 스키마 — Phase 1 + Phase 2 완료 ✅

Phase 1: V1~V9 (9규칙) + Phase 2: V10~V15 (6규칙) = **15규칙 ALL PASS**. safety_requirements, sr_ns_mapping, sr_article_mapping 3테이블 추가.

### 결정 7: 식별자 0-based ✅

`NS-RULE24-0` (0-based). 단서 NS도 순번으로 통일 (`NS-RULE24-2`). `hasModificationLink`로 단서 관계 표현.

### 결정 8: hasSubjectRole string 간소화 ✅

`"사업주"` (string). object wrapper `{title: "사업주"}`는 정보 추가 없이 복잡성만 증가.

### 결정 9: 법령 소스 3개 → 5개 확장 ✅

DECREE(시행령) + ENFORCE(시행규칙) 추가. SR/CI 단계에서 활용.

### 결정 10: 과태료 통합 (criminal/administrative 분리) ✅

형사벌(벌칙)만 다루던 구조를 `criminal`/`administrative` 분리로 재설계.
- 변경 파일 9개 (penalty-article-map, penalty-routes schema, step1~3, DB schema/verify, CLAUDE.md 등)
- RULE 과태료 0건은 법적으로 올바름 (제38조/제39조는 과태료 대상 아님)
- Phase 2에서 OSHA 조문 NS 생성 시 활용 가능

---

## 6. 디렉토리 구조

```
koshaontology/
├── CLAUDE.md                           프로젝트 허브 (각 pipe CLAUDE.md로 안내)
├── plan_pipeb.md                       Pipe-B 설계 계획서
├── pipe-A/
│   ├── CLAUDE.md                       Pipe-A 오케스트레이터
│   ├── plan_pipea.md                   이 문서 (설계 계획서)
│   ├── status_pipea.md                 진행 상태
│   ├── phase1_step0.md ~ phase1_step4.md  Phase 1 재현 문서
│   ├── phase2_step1.md ~ phase2_step6.md  Phase 2 재현 문서
│   ├── scripts/
│   │   ├── step0_extract_articles.py
│   │   ├── step1_extract_penalties.py
│   │   ├── step2_prepare_batch.py
│   │   ├── step4_validate_ns.py
│   │   ├── step5_prepare_sr_batch.py       Phase 2 SR 배치 준비
│   │   ├── step6_validate_sr.py            Phase 2 SR 검증 (14규칙)
│   │   ├── extract_sections.py             128개 section 추출 헬퍼
│   │   └── lib/
│   │       ├── __init__.py
│   │       ├── article_code.py
│   │       ├── legalize_reader.py
│   │       ├── ns_identifier.py
│   │       └── schema_validator.py
│   ├── agents/
│   │   ├── step3-ns-generation.md
│   │   └── step5-sr-generation.md          Phase 2 SR 생성 에이전트 가이드
│   ├── schemas/
│   │   ├── article-texts.schema.json
│   │   ├── penalty-routes.schema.json
│   │   ├── ns-file.schema.json
│   │   ├── sr-file.schema.json             Phase 2 SR 스키마
│   │   └── validation-report.schema.json
│   ├── config/
│   │   ├── law-sources.json             (5개 법령)
│   │   ├── delegation-map.json
│   │   ├── penalty-article-map.json     (과태료 제175조 포함)
│   │   ├── sr-section-category-map-template.json  Phase 2 초기 (참고용)
│   │   └── sr-section-category-map.json Phase 2 최종 (128키, exact match)
│   ├── data/
│   │   ├── article-texts.json
│   │   ├── penalty-routes.json
│   │   ├── norm-statements/
│   │   │   ├── batch-*-input.json
│   │   │   └── ns-batch-*.json
│   │   ├── safety-requirements/            Phase 2
│   │   │   ├── sr-batch-*-input.json       48개 배치 입력
│   │   │   └── sr-batch-*.json             48개 SR 출력 (626 SR)
│   │   └── validation/
│   │       ├── ns-validation-report.json
│   │       ├── sr-validation-report.json   Phase 2
│   │       └── db-verification-report.json
│   └── db/
│       ├── schema_pg.sql                PostgreSQL DDL
│       └── import_and_verify.py         JSON→PostgreSQL 적재 + 무결성 검증
├── pipe-B/                              가이드 → CI/DT/WP/ES/DR (완료)
└── pipe-C/                              교차검증 (완료)
```

---

## 7. Phase 2 완료 결과 (SR 파이프라인)

### 7.1 Phase 2 스텝 (독립 번호 체계 Step 1~6) — 전체 완료

재현 문서는 `phase2_step1.md` ~ `phase2_step6.md` 참조.

- **Step 1**: ✅ SR 스키마 설계 + 카테고리 매핑 (`sr-section-category-map.json`, 128키 exact match, 43카테고리 중 42 활성)
- **Step 2**: ✅ SR 배치 준비 (`step5_prepare_sr_batch.py`, 48배치, 626 SR그룹)
- **Step 3**: ✅ SR 생성 LLM 에이전트 가이드 (`agents/step5-sr-generation.md`)
- **Step 4**: ✅ SR 생성 실행 (4라운드: 5+15+15+13, 626/626 SR)
- **Step 5**: ✅ SR 검증 (`step6_validate_sr.py`, 14규칙, ERROR 0, WARNING 14)
- **Step 6**: ✅ DB 적재 (`import_and_verify.py --clean`, V1~V15 ALL PASS)

### 7.2 SR 스키마 실제 결과

- `additionalProperties: false`
- SR 식별자: `^SR-[A-Z_]+-[0-9]+$` (알고리즘 생성, 언더스코어 포함)
- `mandatedBy`: NS 식별자 배열 (FK) — 1,020개 매핑
- `referencesArticle`: 조문코드 배열 (FK) — 626개 매핑
- `addressesHazard`: 12개 표준 키워드 enum (배열)
- `requirementType` enum: 8개 타입
- guideCode 의존성 제거
- 카테고리 매핑: `sr-section-category-map.json` (128개 section → 43카테고리, GENERAL skipSR → 42 활성, `dict.get()` exact match)

### 7.3 DB 적재 결과 (2026-04-12)

| 테이블 | 행 수 | Phase |
|--------|-------|-------|
| articles | 1,227 | 1 |
| penalty_routes | 656 | 1 |
| norm_statements | 1,229 | 1 |
| safety_requirements | 626 | 2 |
| sr_ns_mapping | 1,020 | 2 |
| sr_article_mapping | 626 | 2 |

무결성 검증: V1~V15 (15규칙) **ALL PASS**

참고: `penalty_routes`는 `law_type` 컬럼(`DEFAULT 'RULE'`, `CHECK 'RULE'`)과 복합 FK `(law_type, article_code) REFERENCES articles(law_type, article_code)`로 `articles` 테이블과 연결된다 (2026-04-12 추가).

### 7.4 향후 작업

- ✅ Phase 2 (SR 파이프라인) — 완료
- ✅ Pipe B (가이드 → CI/WP/ES/DR/DT) — 1,038/1,038 Guide JSON 추출·적재 완료, manual domain 후보 35 batch 생성 완료
- ✅ Pipe C (교차검증) — 1,038 Guide 기준 후보/evidence audit 추가, legacy 796 기준 basedOn 복원 이력은 historical로만 유지
- ✅ Phase 3 (SR 예약 필드 채움) — legacy 796 기준 완료 이력 이후 1,038 Guide 기준 재빌드/검증 완료. 현재 추천 기준은 `usage_profile11`

### 7.5 보류 항목 (Phase 3 이후)

- criminal.death 조건 필드 추가 검토
- 위임 분류 정밀화 (`rule-to-delegation.json`)

---

*이 문서는 KOSHA 온톨로지 Pipe A의 설계 계획서입니다. 진행 상태는 `status_pipea.md`를 참조하세요.*
