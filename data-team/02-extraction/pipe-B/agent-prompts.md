# Pipe-B 단계별 에이전트 프롬프트

> 현재 기준 참고 (2026-05-07): 이 문서는 Pipe-B 추출 프롬프트 모음이다. 최신 product 기준에서는 `Guide/WorkProcess`를 표준 개선 절차 중심으로, `ChecklistItem`을 즉시 조치/보조 단서/검색 색인으로 사용한다.

> 각 단계를 독립 에이전트 세션에서 실행할 때 사용하는 프롬프트.
> 순서: Step 1 → 10 (Step 2는 수동 설계, 생략)

---

## Step 1: 가이드 인벤토리 생성

```
data-team/02-extraction/pipe-B/CLAUDE.md를 읽고, 가이드 인벤토리를 생성해.

실행:
cd data-team/02-extraction/pipe-B
python3 scripts/step0_build_inventory.py

완료 후 data/guide-inventory.json이 생성되었는지 확인하고, 도메인별 가이드 수를 보고해.
```

---

## Step 3: PDF 파싱 (VLM)

```
data-team/02-extraction/pipe-B/CLAUDE.md를 읽고, 가이드 PDF를 텍스트 JSON으로 파싱해.

실행:
cd data-team/02-extraction/pipe-B
python3 scripts/step1_parse_pdf_vlm.py --domain {도메인} --model sonnet

도메인은 A/B/C/D/E 중 하나. 전체 도메인을 순차 실행하려면 A부터 E까지 반복해.
옵션: --guide {shortCode} (단일 가이드), --max-guides 10, --force (기존 덮어쓰기)

완료 후 ../../01-parsing/data-team/01-parsing/kosha-guides/parsed/ 디렉토리에 guide-{shortCode}.json 파일이 생성되었는지 확인해.
```

---

## Step 4: 파싱 품질 검증

```
data-team/02-extraction/pipe-B/CLAUDE.md를 읽고, 파싱된 가이드 JSON의 품질을 검증해.

실행:
cd data-team/02-extraction/pipe-B
python3 scripts/step0_validate_parsing.py

PASS/FAIL 건수를 보고해.
```

---

## Step 5: SR 조회 인덱스 생성

```
data-team/02-extraction/pipe-B/CLAUDE.md를 읽고, Pipe-A DB의 SR 데이터로 조회 인덱스를 생성해.

전제: Pipe-A DB 적재 완료 (safety_requirements 626건 존재)

실행:
cd data-team/02-extraction/pipe-B
python3 scripts/step2_build_sr_index.py

완료 후 data/ 디렉토리에 sr-*-index.json 3종이 생성되었는지 확인해.
```

---

## Step 6: CI 배치 입력 생성

```
data-team/02-extraction/pipe-B/CLAUDE.md를 읽고, CI 추출용 배치 입력 파일을 생성해.

전제: Step 5 완료 (SR 인덱스 존재), 파싱된 가이드 JSON 존재

실행:
cd data-team/02-extraction/pipe-B
python3 scripts/step3_prepare_ci_batch.py --domain {도메인} --batch-size 5

전체 도메인을 처리하려면 A~E 순차 실행.
완료 후 data/ci-batches/ 에 pipeb-batch-{domain}-*-input.json 파일들이 생성되었는지 확인해.
```

---

## Step 7: CI/DT/WP/ES/DR 추출 (LLM)

```
data-team/02-extraction/pipe-B/CLAUDE.md를 읽고, 배치 입력으로부터 5종 엔티티를 추출해.
추출 에이전트 프롬프트는 agents/step4-entity-extraction.md를 반드시 읽어.

전제: Step 6 완료 (배치 입력 존재)

실행:
cd data-team/02-extraction/pipe-B
python3 scripts/step4_extract_entities.py --batch data/ci-batches/pipeb-batch-{domain}-001-input.json

전체 실행: 도메인별 배치를 순차 처리하거나 --guide {shortCode}로 단일 가이드 처리.
옵션: --skip-existing (기본 True), --force (기존 덮어쓰기), --skip-guides "XX1,XX2" (특정 가이드 제외)

완료 후 data/ci-output/ 에 ci-{shortCode}.json 파일들이 생성되었는지 확인해.
```

---

## Step 8: 추출 결과 검증

```
data-team/02-extraction/pipe-B/CLAUDE.md를 읽고, 추출된 CI/DT/WP/ES/DR의 품질을 검증해.

전제: Step 7 완료 (ci-output/ 에 추출 결과 존재)

실행:
cd data-team/02-extraction/pipe-B
python3 scripts/step6_validate_entities.py

검증 규칙 B1~B20 결과를 보고해. B1~B14 Hard Error는 0건이어야 한다.
```

---

## Step 9: DB 스키마 + 적재

```
data-team/02-extraction/pipe-B/CLAUDE.md를 읽고, DB 스키마를 생성한 뒤 추출 데이터를 적재해.

전제: Step 8 완료, Pipe-A DB 적재 완료 (safety_requirements FK 의존)

실행:
cd data-team/02-extraction/pipe-B

# DDL 실행
psql "dbname=kosha user=kosha password=1229 host=localhost" -f db/schema_pb.sql

# 데이터 적재 + 검증
python3 db/import_pipeb.py --clean

--clean은 기존 Pipe-B 데이터를 지우고 재적재. V16~V28 검증 포함.
적재 후 13개 테이블의 행수를 보고해.
```

---

## Step 10: SR Phase 3 + 최종 검증

```
data-team/02-extraction/pipe-B/CLAUDE.md를 읽고, SR Phase 3 필드를 채운 뒤 전체 검증을 실행해.

전제: Step 9 완료 (DB 적재 완료)

실행:
cd data-team/02-extraction/pipe-B

# SR Phase 3 필드 채우기 (requires_ppe, has_corrective_action, has_incident_response, applicable_industry, hazard_assessment)
python3 scripts/step7_fill_sr_phase3.py

# 전체 검증 V16~V30 (V29~V30은 Pipe-A 교차검증)
python3 db/import_pipeb.py --verify-all

5개 Phase 3 필드의 채움 건수와 V16~V30 검증 결과를 보고해.
```
