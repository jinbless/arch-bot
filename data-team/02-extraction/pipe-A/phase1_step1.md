# Phase 1 Step 1: 벌칙 경로 추출 + DB 검증

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 온톨로지 모델은 `PenaltyRoute` 클래스가 아니라 `PenaltyRule`, `violatedArticle`, `penaltyArticle`, `PenaltyPath` 구조를 사용한다. 최신 기준은 `status_pipea.md`와 루트 통합 구조도를 확인한다.

> 최종 업데이트: 2026-04-11
> 스크립트: `scripts/step1_extract_penalties.py`

---
## 1. 목적

- **Step 1**: RULE 조문별 벌칙(형사벌) + 과태료(행정벌) 경로 매핑
  - criminal (형사벌): 제167~172조 -- 위반, 사망가중, 중대재해
  - administrative (과태료): 제175조 -- 6단계 과태료
- **DB 검증**: PostgreSQL로 참조 무결성 검증 (9개 규칙)

---

## 2. 전제조건

- Step 0 완료 (`data/article-texts.json` 존재, 1,227 조문)
- Python 3.12+
- `lib/schema_validator.py` 존재 (Step 0 문서에서 생성)

---

## 3. 파일 생성 순서

### 3.1. `config/delegation-map.json`
- 산안법→산안규칙 위임 체인 (21개 OSHA 조문, 벌칙조문 매핑)
### 3.2. `config/penalty-article-map.json`
- 형사벌(제167~172조) + 과태료(제175조) 대상 조문 정적 매핑
### 3.3. `schemas/penalty-routes.schema.json`
- criminal/administrative 분리 구조 출력 스키마
### 3.4. `scripts/step1_extract_penalties.py`
- 메인 (→ schema_validator 의존, article-texts.json + config 2개 읽어 penalty-routes.json 생성)
- 함수: `build_admin_fine_map(penalty_map)`, `main()`

---

## 4. 실행 방법

```bash
cd data-team/02-extraction/pipe-A
python3 scripts/step1_extract_penalties.py
```

---

## 5. 예상 출력

```
[OK] 저장 완료: .../data/penalty-routes.json (xxx bytes)

[DONE] penalty-routes.json 생성 완료
  형사벌 적용: 638조, 미적용: 18조
  과태료 적용: 0조, 미적용: 656조
  [참고] 제38조/제39조는 과태료 대상이 아님 — RULE 조문 대부분은 형사벌만 적용
```

- 총 656 라우트 (형사벌 638, 과태료 0)
- **과태료가 0인 이유**: RULE 조문은 제38조/제39조를 통해 위임되며, 이 두 조문은 제175조(과태료) 대상이 아니다. 형사벌(제167~172조)만 적용된다. delegation-map의 다른 OSHA 조문(제64조 등)이 과태료 대상일 수 있으나, 현재 RULE 조문의 위임 경로는 모두 제38조/제39조를 경유하므로 과태료 적용 건수는 0이다.

---

## 6. DB 검증

### 6.1 DB 스키마

> 전문: `db/schema_pg.sql`

PostgreSQL 3개 테이블:
- `articles` — 조문 원문 (PK: law_type + article_code)
- `penalty_routes` — 벌칙 경로 (PK: article_code, FK → articles(RULE), criminal/administrative 분리)
- `norm_statements` — 규범문장 (PK: identifier, FK → articles)

### 6.2 적재 + 검증 스크립트

> 전문: `db/import_and_verify.py` (PostgreSQL 전용)

- `--clean`: 테이블 DROP CASCADE + 재생성 후 적재
- JSON → PostgreSQL 직접 적재 (psycopg2, JSONB는 `psycopg2.extras.Json()` 래핑)
- 9개 무결성 규칙 검증 (V1~V9)

### 6.3 실행 방법
```bash
cd data-team/02-extraction/pipe-A
python3 db/import_and_verify.py --clean
```

### 6.4 예상 출력 (legalize-kr 커밋 d8c121b2 기준)
```
[OK] PostgreSQL DB 초기화 완료: kosha
[OK] articles 적재: 1227행
[OK] penalty_routes 적재: 656행
[검증 결과] ALL PASS (9개 규칙, 에러 0건)
```

## 7. 검증 규칙 (9개)

| 규칙 | 코드 | 설명 |
|------|------|------|
| V1 | `V1_FK_PENALTY_TO_ARTICLE` | penalty_routes의 모든 article_code가 articles(RULE)에 존재 |
| V2 | `V2_FK_DELEGATION_TO_OSHA` | delegatedFrom 조문이 articles(OSHA)에 존재 |
| V3 | `V3_DUPLICATE_ARTICLE` | articles 복합 PK (law_type, article_code) 유일성 |
| V4 | `V4_DUPLICATE_PENALTY` | penalty_routes PK (article_code) 유일성 |
| V5 | `V5_DELETED_IN_PENALTY` | 삭제 조문이 penalty_routes에 미포함 |
| V6 | `V6_PENALTY_WITHOUT_CRIMINAL` | hasPenalty=true이면 criminal_employer NOT NULL |
| V7 | `V7_ADMIN_FINE_WITHOUT_LAW` | hasAdministrativeFine=true이면 admin_law NOT NULL (과태료 무결성) |
| V8 | `V8_FK_NS_TO_ARTICLE` | norm_statements → articles FK |
| V9 | `V9_DUPLICATE_NS` | norm_statements PK 유일성 |
