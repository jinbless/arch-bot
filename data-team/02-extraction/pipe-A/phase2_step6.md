# Phase 2 Step 6: DB 스키마 확장

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 serving path는 PostgreSQL 물질화 조회를 기준으로 하며, OWL reasoner는 배치 검증/운영 분석 용도로 본다.

> 최종 업데이트: 2026-04-12
> 산출물: `db/schema_pg.sql` (3테이블 추가), PostgreSQL 적재 완료
> 선행: phase2_step5 (SR 검증 PASS)

---

## 1. 목적

Phase 1의 PostgreSQL 스키마(articles, penalty_routes, norm_statements)에 SR 관련 3개 테이블을 추가하고, DB 무결성 검증 규칙 V10~V15를 정의한다.

## 2. 전제조건

- phase2_step5 완료: SR 검증 PASS (626개 SR, ERROR 0)
- Phase 1 DB 적재 완료: articles 1,227행, penalty_routes 656행, norm_statements 1,229행

## 3. 추가 테이블 (3개)

### 3.1 safety_requirements (Layer 4 허브)

```sql
CREATE TABLE safety_requirements (
    identifier              VARCHAR(30) NOT NULL PRIMARY KEY
                            CHECK(identifier ~ '^SR-[A-Z_]+-[0-9]+$'),
    title                   TEXT NOT NULL,
    text                    TEXT NOT NULL CHECK(length(text) > 0),
    requirement_type        VARCHAR(25) NOT NULL CHECK(requirement_type IN (
        'PHYSICAL_PROTECTION','PPE_REQUIREMENT','PROCEDURAL','TRAINING',
        'EQUIPMENT_STANDARD','ENVIRONMENTAL','MANAGEMENT_SYSTEM','EMERGENCY_RESPONSE'
    )),
    binding_force           VARCHAR(15) NOT NULL DEFAULT 'MANDATORY'
                            CHECK(binding_force IN ('MANDATORY','RECOMMENDED')),
    addresses_hazard        JSONB,
    structural_requirements JSONB,
    has_sanction            JSONB,
    has_modification_link   JSONB,
    -- Phase 3 예약 (Layer 4 전방 호환, 모두 nullable)
    requires_ppe            JSONB,
    has_corrective_action   JSONB,
    has_incident_response   JSONB,
    applicable_industry     JSONB,
    hazard_assessment       JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 3.2 sr_ns_mapping (L3→L4: mandatedBy N:N)

```sql
CREATE TABLE sr_ns_mapping (
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    ns_id   VARCHAR(30) NOT NULL REFERENCES norm_statements(identifier),
    PRIMARY KEY (sr_id, ns_id)
);
```

### 3.3 sr_article_mapping (L4→L2: referencesArticle N:N)

```sql
CREATE TABLE sr_article_mapping (
    sr_id        VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    law_type     VARCHAR(10) NOT NULL,
    article_code VARCHAR(20) NOT NULL,
    PRIMARY KEY (sr_id, law_type, article_code),
    FOREIGN KEY (law_type, article_code) REFERENCES articles(law_type, article_code)
);
```

## 4. 핵심 설계 결정

### 4.1 identifier 정규식

`^SR-[A-Z_]+-[0-9]+$` — FIRE_EXPLOSION, CONSTRUCTION_EQUIP 등 언더스코어 포함 카테고리 지원.
sr-file.schema.json, step6_validate_sr.py와 동일 패턴.

### 4.2 Phase 3 예약 컬럼 (5개, 모두 nullable JSONB)

| 컬럼 | Phase 3 용도 | 온톨로지 Layer 4 클래스 |
|------|-------------|----------------------|
| requires_ppe | PPE 규격·착용조건 | PPERequirement |
| has_corrective_action | 시정조치·비용·난이도 | CorrectiveAction |
| has_incident_response | 비상대응·기한·책임자 | IncidentResponse |
| applicable_industry | 적용 업종 | IndustryType |
| hazard_assessment | 위험도 평가 (severity/likelihood/riskScore) | HazardFactor |

Phase 2에서는 모두 NULL. Phase 3에서 `UPDATE ... SET requires_ppe = '{...}'`로 채움 (스키마 변경 불필요).

### 4.3 N:N 매핑 테이블

SR은 여러 NS에 근거하고(mandatedBy), 여러 조문을 참조한다(referencesArticle). 1:N 관계를 별도 매핑 테이블로 분리하여 양방향 조회를 지원:
- "NS-RULE42-0이 근거인 SR은?" → `sr_ns_mapping WHERE ns_id='NS-RULE42-0'`
- "SR-FALL-001의 근거 NS는?" → `sr_ns_mapping WHERE sr_id='SR-FALL-001'`

## 5. DB 무결성 검증 규칙 (V10~V15)

| 규칙 | 검증 내용 |
|------|----------|
| V10 | safety_requirements 적재 확인 (0행이면 SR 검증 건너뜀) |
| V11 | sr_ns_mapping의 모든 ns_id가 norm_statements에 존재 |
| V12 | sr_ns_mapping의 모든 sr_id가 safety_requirements에 존재 |
| V13 | sr_article_mapping의 모든 (law_type, article_code)가 articles에 존재 |
| V14 | RULE의 OBLIGATION/PROHIBITION NS 중 SR에 연결되지 않은 NS 없음 (커버리지) |
| V15 | SR identifier 중복 없음 |

V10~V15는 적재·검증 스크립트 import_and_verify.py의 verify_sr() 함수로 검증.

## 6. 인덱스

```sql
CREATE INDEX idx_sr_type ON safety_requirements(requirement_type);
CREATE INDEX idx_sr_ns_ns ON sr_ns_mapping(ns_id);
CREATE INDEX idx_sr_art_art ON sr_article_mapping(law_type, article_code);
```

## 7. 적재 결과 (2026-04-12)

```bash
cd koshaontology/pipe-A
python3 db/import_and_verify.py --clean
```

**적재 수치:**

| 테이블 | 행 수 |
|--------|-------|
| articles | 1,227 |
| penalty_routes | 656 |
| norm_statements | 1,229 |
| safety_requirements | 626 |
| sr_ns_mapping | 1,020 |
| sr_article_mapping | 626 |

**무결성 검증: V1~V15 ALL PASS (에러 0건)**

---

## 8. 재현 방법

```bash
cd koshaontology/pipe-A

# 전체 적재 (Phase 1 + Phase 2, 기존 테이블 DROP 후 재생성)
python3 db/import_and_verify.py --clean

# 결과 확인
cat data/validation/db-verification-report.json | python3 -m json.tool | head -20
```

---

*Phase 2 Step 1~6 재현 문서 완료.*
