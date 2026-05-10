# KOSHA 온톨로지 v2 — Pipe-B 마스터 오케스트레이터

> 현재 기준 참고 (2026-05-10): Pipe-B 산출물은 최신 product에서 `Guide/WorkProcess = 표준 개선 절차`, `ChecklistItem = 즉시 조치/보조 단서/검색 색인`으로 사용한다. Guide JSON은 1,038/1,038개 확보되어 root `kosha-guides/parsed/**`와 manifest로 추적된다. 추천 품질 보강은 manual domain 후보 35 batch와 `usage_profile11` runtime 검증을 기준으로 진행한다.

## 프로젝트 개요

KOSHA 가이드 1,038개 parsed JSON → CI/DT/WP/ES/DR 5종 엔티티 추출 + SR 후보/evidence 레이어 + Guide usage profile 보강.
이 파일은 Pipe B (가이드 → CI) 파이프라인을 관리한다.

> Monorepo 기준(2026-05-10): `koshaontology/`는 root `arch-bot`의 tracked 디렉토리다. raw PDF 원본은 git 직접 추적 대상이 아니며, `../../kosha-guides/parsed/`와 `../../kosha-guides/manifest/`가 root에서 추적되는 Guide 원천이다.

## 작업 시작 가이드

1. `status_pipeb.md`를 먼저 읽어 현재 진행 상태와 남은 작업을 확인한다.
2. `plan_pipeb.md`는 설계 결정의 배경이 필요할 때 참조한다.

## 핵심 설계 원칙

1. **결정론적 출력**: Step 0, 1, 3은 100% 스크립트. 동일 입력 → 동일 출력.
2. **LLM 역할 최소화**: Phase 1 Step 2(PDF 파싱), Phase 2 Step 4(CI 추출)만 LLM 사용. 식별자와 SR 후보는 사전 계산.
3. **사전 스키마 검증**: 모든 출력은 JSON Schema 검증 후 저장. `additionalProperties: false`.
4. **null ≠ 생략**: 선택필드가 없으면 `null`. 필드 자체를 생략하지 않음. `{}`도 금지.
5. **Pipe-A SSOT**: basedOn의 SR은 반드시 Pipe-A DB의 safety_requirements에 존재해야 함.

## 파이프라인 스텝

Pipe B는 Phase 1(Guide Parsing), Phase 2(CI Extraction), Phase 3(DB Integration)으로 구성된다.

### 스크립트 ↔ Phase/Step 매핑

스크립트는 **전체 파이프라인 순번** (step0~step7), 문서는 **Phase 내 순번**을 사용한다.

| 실행순서 | 스크립트 | Phase.Step | 유형 | 입력 → 출력 | 문서 |
|---|---|---|---|---|---|
| 1 | `step0_build_inventory.py` | P1.Step 0 | 스크립트 | PDF 디렉토리 → `guide-inventory.json` | `phase1_step0.md` |
| 2 | (설계) | P1.Step 1 | 수동 | legacy JSON → v2 스키마 확정 | `phase1_step1.md` |
| 3 | `step1_parse_pdf_vlm.py` | P1.Step 2 | LLM | 가이드 PDF → `guide-{shortCode}.json` | `agents/step1-vlm-parse-prompt.md` |
| 4 | `step0_validate_parsing.py` | P1.Step 3 | 스크립트 | guide JSON → `parsing-report.json` | — |
| 5 | `step2_build_sr_index.py` | P2.Step 1 | 스크립트 | Pipe-A DB → `sr-*-index.json` (3종) | `phase2_step1.md` |
| 6 | `step3_prepare_ci_batch.py` | P2.Step 2 | 스크립트 | guide JSON + SR index → batch input | `phase2_step2.md` |
| 7 | `step4_extract_entities.py` | P2.Step 3~4 | LLM | batch input → CI/DT/WP/ES/DR JSON | `agents/step4-entity-extraction.md` |
| 8 | `step6_validate_entities.py` | P2.Step 5 | 스크립트 | ci-output → validation report (B1~B20) | — |
| 9 | `db/schema_pb.sql` + `db/import_pipeb.py` | P3.Step 1~2 | 스크립트 | CI JSON → PostgreSQL (V16~V28) | `db-spec.md` |
| 10 | `step7_fill_sr_phase3.py` | P3.Step 3 | 스크립트 | DB 쿼리 → SR 예약 필드 UPDATE (5개 함수) | — |
| 11 | `db/import_pipeb.py --verify-all` | P3.Step 4 | 스크립트 | DB → V16~V30 + V1~V15 회귀 검증 | — |
| 12 | `step6_faceted_ci_tag.py` | P3.Step 5 | 스크립트 | CI 54,571개 DB baseline faceted 3축 태깅 (SR 상속 + 고아 독립 태깅) | — |
| 13 | `step7_faceted_entity_tag.py` | P3.Step 6 | 스크립트 | DT/ES/WP faceted 태깅 | — |

> 스크립트 step5는 존재하지 않음 (step4→step6 사이 결번). `step0_validate_parsing.py`는 이름이 step0이지만 P1.Step 3에 해당.

계획서: `plan_pipeb.md` 참조.

## 실행 방법

### Phase 1: Guide Parsing

```bash
cd koshaontology/pipe-B

# Step 0: 가이드 인벤토리 생성
python3 scripts/step0_build_inventory.py

# Step 1: v2 스키마 설계 + legacy 호환성 검증 (phase1_step1.md 참조)

# Step 2: 가이드 PDF → 텍스트 JSON (VLM — step1_parse_pdf_vlm.py)
python3 scripts/step1_parse_pdf_vlm.py --domain D --model sonnet
# 옵션: --guide AG4 (단일 가이드), --dry-run, --force, --max-guides 10

# Step 3: 파싱 품질 검증
python3 scripts/step0_validate_parsing.py
```

### Phase 2: CI Extraction

```bash
cd koshaontology/pipe-B

# Step 1: SR 조회 인덱스 생성
python3 scripts/step2_build_sr_index.py

# Step 2: CI 배치 입력 생성
python3 scripts/step3_prepare_ci_batch.py --domain D --batch-size 5
# 옵션: --guides-file pilot-guides.json, --batch-prefix pipeb-batch

# Step 3~4: CI 추출 (LLM — agents/step4-entity-extraction.md 참조)
python3 scripts/step4_extract_entities.py --batch data/ci-batches/pipeb-batch-001-input.json
# 옵션: --guide AG4 (단일), --skip-existing (기본 True), --force, --skip-guides "XX1,XX2", --dry-run, --model opus

# Step 5: 추출 결과 검증 (20규칙)
python3 scripts/step6_validate_entities.py
```

### Phase 3: DB Integration

```bash
cd koshaontology/pipe-B

# Step 1: DB 스키마 확장
psql -f db/schema_pb.sql

# Step 2: 데이터 적재 + V16~V28 검증
python3 db/import_pipeb.py --clean
# 옵션: --input-dir data/ci-output, --verify (V16~V28만), --verify-all (V16~V30 전체)

# Step 3: SR Phase 3 필드 채우기
python3 scripts/step7_fill_sr_phase3.py

# Step 4: 전체 무결성 검증 + 회귀
python3 db/import_pipeb.py --verify-all

# Step 5: CI faceted 3축 태깅 (SR 상속 + 고아 독립 태깅)
python3 scripts/step6_faceted_ci_tag.py

# Step 6: DT/ES/WP faceted 태깅
python3 scripts/step7_faceted_entity_tag.py
```

## 정규 식별자 형식

```
CI ID:    ^CI-[A-Z0-9]+-[0-9]+$      예: CI-DC13-001, CI-AG4-015
DT ID:    ^DT-[A-Z0-9]+-[0-9]+$      예: DT-AG4-001
WP ID:    ^WP-[A-Z0-9]+-[0-9]+$      예: WP-AG4-01
ES ID:    ^ES-[A-Z0-9]+-[0-9]+$      예: ES-AG4-001
DR ID:    ^DR-[A-Z0-9]+-[0-9]+$      예: DR-DC13-001
```

## shortCode 생성 규칙

```
가이드코드에서 하이픈과 연도를 제거:
  A-G-4-2025   → AG4
  D-C-13-2026  → DC13
  C-103-2014   → C103
  G-1-2023     → G1
  M-149-2023   → M149
```

## 금지 패턴

```
절대 하지 마라:
- CI 식별자를 LLM이 창작 (preAssignedId 범위 내에서만 사용)
- candidateSR 목록 밖의 SR을 basedOn에 참조
- additionalProperties 없는 스키마
- {} 빈 객체 (null 사용)
- "" 빈 문자열 (minLength: 1 위반)
- text 축약/의역 (원문 그대로)
- 5개 엔티티 배열 키 생략 (0건이어도 [] 명시)
```

## 참조

- Pipe-A: `../pipe-A/CLAUDE.md` (NS/SR 파이프라인)
- 법령 소스: `../../legalize-kr/` (legalize-kr)
- KOSHA Guide parsed/manifest: `../../kosha-guides/parsed/`, `../../kosha-guides/manifest/`
- KOSHA 원본 PDF: 외부/local artifact. root git 직접 추적 대상이 아님
- Pipe-A DB: `../pipe-A/db/schema_pg.sql` (FK 대상: safety_requirements, articles)
