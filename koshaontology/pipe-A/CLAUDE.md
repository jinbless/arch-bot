# KOSHA 온톨로지 v2 — 마스터 오케스트레이터

> 현재 기준 참고 (2026-05-07): Pipe-A 산출물은 `law:Article`, `law:NormStatement`, `sr:SafetyRequirement`, `PenaltyRule`의 원천이다. 현재 product serving에서는 reasoner를 요청 경로에 두지 않고, Pipe-A 산출물을 PostgreSQL/TTL로 물질화해 `SHE Pattern -> SR -> Article -> PenaltyPath` 조회에 사용한다. 과거 문서의 `penalty_routes`는 추출 중간 산출물명이며, 최신 온톨로지 모델에서는 `PenaltyRoute` 클래스와 `penaltyForArticle` 속성을 사용하지 않는다.

## 프로젝트 개요

산업안전보건기준에관한규칙(RULE) + KOSHA 가이드 → 온톨로지 기반 그래프DB.
이 파일은 Pipe A (법령 → NS → SR) 파이프라인을 관리한다.

## 작업 시작 가이드

1. `status_pipea.md`를 먼저 읽어 현재 진행 상태와 남은 작업을 확인한다.
2. `plan_pipea.md`는 설계 결정의 배경이 필요할 때 참조한다.

## 핵심 설계 원칙

1. **결정론적 출력**: Step 0, 1, 2, 4는 100% 스크립트. 동일 입력 → 동일 출력.
2. **LLM 역할 최소화**: Step 3만 LLM 사용. 식별자와 벌칙은 사전 계산.
3. **사전 스키마 검증**: 모든 출력은 JSON Schema 검증 후 저장. `additionalProperties: false`.
4. **null ≠ 생략**: 선택필드가 없으면 `null`. 필드 자체를 생략하지 않음. `{}`도 금지.

## 파이프라인 스텝

Pipe A는 Phase 1(NS 파이프라인)과 Phase 2(SR 파이프라인)로 구성되며, 각 Phase는 독립적인 Step 번호 체계를 가진다.

> 참고: 스크립트 파일명(step0~step6)은 Phase 1~2를 통합한 전체 순번이므로 Phase 내 Step 번호와 일치하지 않는다.

### Phase 1: NS 파이프라인 (Step 0~4)

| Step | 유형 | 스크립트/에이전트 | 입력 | 출력 | 재현 문서 |
|------|------|-------------------|------|------|----------|
| 0 | 스크립트 | `step0_extract_articles.py` | legalize-kr JSON | `article-texts.json` | `phase1_step0.md` |
| 1 | 스크립트 | `step1_extract_penalties.py` | article-texts + config | `penalty-routes.json` | `phase1_step1.md` |
| 2 | 스크립트 | `step2_prepare_batch.py` | article-texts + penalty-routes | `batch-*-input.json` | `phase1_step2.md` |
| 3 | LLM | `agents/step3-ns-generation.md` | batch input JSON | `ns-batch-*.json` | `phase1_step3.md` |
| 4 | 스크립트 | `step4_validate_ns.py` + `db/import_and_verify.py` | NS files + article-texts + penalty-routes | validation report + PostgreSQL | `phase1_step4.md` |

### Phase 2: SR 파이프라인 (Step 1~6)

| Step | 유형 | 스크립트/에이전트 | 입력 | 출력 | 재현 문서 |
|------|------|-------------------|------|------|----------|
| 1 | 설계 | 수동 | RULE 편/장/절 구조 | `sr-file.schema.json` + `sr-section-category-map.json` (128키) | `phase2_step1.md` |
| 2 | 스크립트 | `step5_prepare_sr_batch.py` | NS + penalty-routes + category-map | `sr-batch-*-input.json` | `phase2_step2.md` |
| 3 | LLM 가이드 | `agents/step5-sr-generation.md` | 에이전트 프롬프트 설계 | SR 생성 에이전트 가이드 | `phase2_step3.md` |
| 4 | LLM | `agents/step5-sr-generation.md` | SR batch input JSON | `sr-batch-*.json` | `phase2_step4.md` |
| 5 | 스크립트 | `step6_validate_sr.py` | SR files + NS + articles | SR validation report | `phase2_step5.md` |
| 6 | 스크립트 | `db/schema_pg.sql` + `db/import_and_verify.py` | SR files | PostgreSQL 적재 완료 (V1~V15 PASS) | `phase2_step6.md` |
| 7 | 스크립트 | `step7_faceted_retag.py` | SR 626개 + hazard-taxonomy-unified.json | SR 626개 faceted 3축 태깅 (accident_types, hazardous_agents, work_contexts JSONB) | — |

계획서: `plan_pipea.md` 참조. Phase 2 재현 문서는 `phase2_step1.md` ~ `phase2_step6.md`.

### 유틸리티 스크립트

- `scripts/extract_sections.py` — RULE 조문의 편/장/절 구조를 분석하는 보조 스크립트. 카테고리 매핑 설계 시 참고용으로 사용. 함수: `_parse_levels()`, `classify_section()`, `load_articles()`, `extract_unique_sections()`, `main()`.
- `scripts/step7_faceted_retag.py` — SR 626개에 faceted 3축 태깅 (accident_type, hazardous_agent, work_context). `config/hazard-taxonomy-unified.json` 기반, JSONB + GIN 인덱스 적용.

## 실행 방법

### Phase 1: NS 파이프라인

```bash
cd koshaontology/pipe-A

# Step 0: 조문 추출
python3 scripts/step0_extract_articles.py

# Step 1: 벌칙 경로
python3 scripts/step1_extract_penalties.py

# Step 2: 배치 입력 생성
python3 scripts/step2_prepare_batch.py --articles 제24조,제42조 --batch-id batch-001
# 또는 전체: python3 scripts/step2_prepare_batch.py --law-id RULE --all --batch-size 20
# 옵션: --range 3-50 (조문 번호 범위), --skip-deleted (삭제 조문 건너뜀, 기본 True)

# Step 3: NS 생성 (LLM — agents/step3-ns-generation.md 참조)
# batch-*-input.json을 LLM 에이전트에 입력 → ns-batch-*.json 출력

# Step 4: NS 검증 + DB 적재
python3 scripts/step4_validate_ns.py
python3 db/import_and_verify.py --clean
```

### Phase 2: SR 파이프라인

```bash
cd koshaontology/pipe-A

# Step 1: SR 스키마 + 카테고리 매핑 (수동 설계 — phase2_step1.md 참조)

# Step 2: SR 배치 입력 생성
python3 scripts/step5_prepare_sr_batch.py --all --batch-size 20
# 옵션: --dry-run (파일 미생성), --small-threshold 5 (소규모 카테고리 병합 기준)

# Step 3~4: SR 생성 (LLM — agents/step5-sr-generation.md 참조)
# sr-batch-*-input.json을 LLM 에이전트에 입력 → sr-batch-*.json 출력

# Step 5: SR 검증 (14규칙)
python3 scripts/step6_validate_sr.py

# Step 6: DB 확장 + SR 적재
python3 db/import_and_verify.py --clean
```

## 정규 식별자 형식

```
조문코드:  ^제\d+조(의\d+)?$          예: 제24조, 제332조의2
NS ID:    ^NS-[A-Z0-9]+-[0-9A-Z]+$  예: NS-RULE24-0, NS-RULE332B-1
SR ID:    ^SR-[A-Z_]+-[0-9]+$        예: SR-FALL-001, SR-FIRE_EXPLOSION-001
CI ID:    ^CI-[A-Z0-9]+-[0-9]+$      예: CI-DC13-001
```

## 조의N → 식별자 매핑 (참고)

```
제332조의2 → NS-RULE332B-{seq}   (의2 → B)
제619조의3 → NS-RULE619C-{seq}   (의3 → C)
```

## 제재 구조 (criminal/administrative 분리)

penalty-routes.json과 NS의 hasSanction은 형사벌과 과태료를 구분한다.

**criminal (형사벌)** — 제167~172조:
- `violation_employer`: 산안법 제168조 — "5년 이하의 징역 또는 5천만원 이하의 벌금"
- `violation_contractor`: 산안법 제169조 — "3년 이하의 징역 또는 3천만원 이하의 벌금"
- `death`: 산안법 제167조 — "7년 이하의 징역 또는 1억원 이하의 벌금"
- `seriousAccident`: 중대재해처벌법 제6조

**administrative (과태료)** — 제175조 (6단계: 5천만원~300만원):
- `law`: 제175조 항·호 참조
- `maxFine`: 법정 상한
- `fineTableRef`: 시행령 별표35 (세부금액 참조)
- `oshaArticleRef`: 과태료 근거 OSHA 조+항

참고: RULE 조문은 제38조/제39조를 통해 위임되며, 이 두 조문은 과태료 대상이 아니므로 대부분의 RULE 조문에는 형사벌만 적용된다.

## 금지 패턴

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

## 법령 소스

| ID | 법령명 | 경로 |
|----|--------|------|
| RULE | 산업안전보건기준에 관한 규칙 | `../../legalize-kr/kr/산업안전보건기준에관한규칙/고용노동부령.json` |
| OSHA | 산업안전보건법 | `../../legalize-kr/kr/산업안전보건법/법률.json` |
| SADA | 중대재해 처벌 등에 관한 법률 | `../../legalize-kr/kr/중대재해처벌등에관한법률/법률.json` |
| DECREE | 산업안전보건법 시행령 | `../../legalize-kr/kr/산업안전보건법/시행령.json` |
| ENFORCE | 산업안전보건법 시행규칙 | `../../legalize-kr/kr/산업안전보건법/시행규칙(고용노동부령).json` |

## 하류 파이프라인 의존 (2026-04-17 추가)

- **Pipe-B**: `safety_requirements` 테이블 참조 (`ci_sr_mapping.sr_id` FK)
- **Pipe-B faceted**: `step6_faceted_ci_tag.py`, `step7_faceted_entity_tag.py` — Pipe-A SR faceted 태깅 결과를 기반으로 CI/DT/ES/WP 하류 태깅 수행
- **Pipe-C**: `sr_article_mapping`, `sr_ns_mapping` 참조 → `sr-registry.json` 통합
- Pipe-A 데이터 변경 시 Pipe-B/C 회귀 검증 필수 (V-C6, V-C7)
