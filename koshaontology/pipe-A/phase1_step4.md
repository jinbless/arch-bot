# Phase 1 Step 4: NS 검증 + DB 적재

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 product 기준은 루트 `README.md`, `../../docs/ontology/00-integrated-structure.md`, `OHS/README.md`, 그리고 이 Pipe의 `status_pipea.md`를 우선 확인한다.

> 최종 업데이트: 2026-04-11
> 검증 스크립트: `scripts/step4_validate_ns.py`
> DB 스크립트: `db/import_and_verify.py`

---
## 1. 목적

Step 3에서 LLM이 생성한 NS 파일을 13개 규칙으로 검증하고, PostgreSQL `kosha` DB에 적재한다.

- 13개 검증 규칙: 구조적 9개 (R1~R9) + 의미적 4개 (R10~R13)
- DB: PostgreSQL (`dbname=kosha user=kosha`)
- DB 무결성: 9개 규칙 (V1~V9)

## 2. 전제조건

- Step 3 완료: `data/norm-statements/ns-batch-*.json` 존재
- Step 0/1 출력: `data/article-texts.json`, `data/penalty-routes.json` (참조 데이터)
- PostgreSQL 16+, `kosha` DB 생성 완료
- `pip install psycopg2-binary jsonschema`

## 3. NS 검증 — 13개 규칙

### 3.1 구조적 규칙 (R1~R9) — ERROR 시 FAIL

| 규칙 | 코드 | 설명 |
|------|------|------|
| R1 | R1_SCHEMA | JSON Schema 검증 (`ns-file.schema.json`) |
| R2 | R2_DUPLICATE_ID | 식별자 유일성 (전체 NS 파일 걸쳐) |
| R3 | R3_ID_FORMAT | 식별자 포맷 (`^NS-[A-Z0-9]+-[0-9A-Z]+$`) |
| R4 | R4_FK_ARTICLE | 외래키: (lawId, articleCode) → article-texts.json |
| R5 | R5_SANCTION_MISMATCH | 벌칙 일치: penalty-routes.json과 비교 |
| R6 | R6_MODALITY_SANCTION | DEFINITION → hasSanction null 필수 |
| R7 | R7_OBLIGATION_NO_SANCTION | OBLIGATION + 벌칙 적용 조문 → hasSanction 필수 |
| R8 | R8_EMPTY_TEXT | text 비어있지 않음 |
| R9 | R9_DUPLICATE_PARAGRAPH | 동일 조+항 중복 (단서 제외) |

### 3.2 의미적 규칙 (R10~R13) — WARNING (PASS 판정 영향 없음)

| 규칙  | 코드                    | 설명                                            | 결정론성 |
| --- | --------------------- | --------------------------------------------- | ---- |
| R10 | R10_MODALITY_KEYWORD  | hasModality ↔ text 키워드 일치                     | 90%  |
| R11 | R11_CONDITION_MISSING | 조건 표현 있는데 hasCondition null                   | 70%  |
| R12 | R12_GUIDANCE_*        | roleGuidance 유효성 (DEFINITION null, 길이, 복사 검출) | 70%  |
| R13 | R13_PROVISO_*         | 단서 체인 무결성. NO_LINK·REF_MISSING은 ERROR, CROSS_ARTICLE만 WARNING | 90%  |

### 3.3 R10 키워드 패턴 (참고)

- OBLIGATION: `하여야 한다`, `해야 한다`, `이어야 한다`, `준용한다`, `수행한다` 등
- PROHIBITION: `아니 된다`, `금지`, `해서는` 등
- EXEMPTION: `그러하지 아니하다`, `적용하지 아니한다`, `면제`, `제외` 등
- DEFINITION: `말한다`, `이란`, `뜻은`, `목적으로 한다`
- PERMISSION/POWER: 검사 제외 (둘 다 "할 수 있다")

## 4. 검증 실행

```bash
cd koshaontology/pipe-A
python3 scripts/step4_validate_ns.py
```

- `ns-batch-*.json` glob으로 자동 수집
- PASS 기준: **ERROR 0건** (WARNING은 허용)
- 출력: `data/validation/ns-validation-report.json`

## 5. DB 적재 — PostgreSQL

### 5.1 스키마

> `db/schema_pg.sql`

3개 테이블: `articles`, `penalty_routes`, `norm_statements`
- `norm_statements`의 JSONB 컬럼: `has_condition`, `has_sanction`, `has_modification_link`, `role_guidance`
- FK: `norm_statements(law_id, article_code)` → `articles(law_type, article_code)`

### 5.2 적재 + 검증 스크립트

> `db/import_and_verify.py`

```bash
python3 db/import_and_verify.py --clean
```

- `--clean`: 테이블 DROP CASCADE + 재생성 후 적재
- JSON → PostgreSQL 직접 적재 (psycopg2)
- JSONB 컬럼: `psycopg2.extras.Json()` 래핑

함수:
- `create_db(clean)`: PostgreSQL 접속 및 스키마 적용
- `import_articles(conn)`: article-texts.json → articles 테이블
- `import_penalty_routes(conn)`: penalty-routes.json → penalty_routes 테이블
- `import_norm_statements(conn)`: ns-batch-*.json → norm_statements 테이블
- `import_safety_requirements(conn)`: sr-batch-*.json → safety_requirements + 매핑 테이블 (Phase 2)
- `verify(conn)`: V1~V9 참조 무결성 검증
- `verify_sr(conn)`: V10~V15 SR 참조 무결성 검증 (Phase 2)
- `print_summary(conn, errors)`: 검증 결과 요약 출력
- `main()`: CLI 파싱 및 전체 실행

### 5.3 DB 무결성 규칙 (V1~V9)

| 규칙 | 코드 | 설명 |
|------|------|------|
| V1 | V1_FK_PENALTY_TO_ARTICLE | penalty_routes → articles(RULE) FK |
| V2 | V2_FK_DELEGATION_TO_OSHA | delegatedFrom → articles(OSHA) FK |
| V3 | V3_DUPLICATE_ARTICLE | articles PK 유일성 |
| V4 | V4_DUPLICATE_PENALTY | penalty_routes PK 유일성 |
| V5 | V5_DELETED_IN_PENALTY | 삭제 조문이 penalty에 미포함 |
| V6 | V6_PENALTY_WITHOUT_CRIMINAL | hasPenalty=true → criminal 필수 |
| V7 | V7_ADMIN_FINE_WITHOUT_LAW | hasAdminFine=true → admin_law 필수 |
| V8 | V8_FK_NS_TO_ARTICLE | norm_statements → articles FK |
| V9 | V9_DUPLICATE_NS | norm_statements PK 유일성 |

## 6. 실행 결과 (656조문 전체)

### NS 검증

```
[PASS] NS 검증 완료 (13규칙)
  파일: 33개, NS: 1229개, ERROR: 0건, WARNING: 1026건
  conditionMissing: 3
  guidanceIssues: 986
  modalityKeywordMismatches: 36
  provisoChainIssues: 1
```

WARNING 1,026건은 검증 규칙의 false positive (한국어 법률 어미 변형, 법률용어 중복에 의한 유사도 등). 수동 샘플 확인 완료.

### DB 적재 + 검증

```
[OK] PostgreSQL DB 초기화 완료: kosha
[OK] articles 적재: 1227행
[OK] penalty_routes 적재: 656행
[OK] norm_statements 적재: 1229행 (33개 파일)

[검증 결과] ALL PASS (9개 규칙, 에러 0건)
```

---

*이 문서는 Step 4(NS 검증 + DB 적재)만 다룹니다. NS 생성은 `phase1_step3.md`, 배치 준비는 `phase1_step2.md`를 참조하세요.*
