# Pipe-C: 교차검증 파이프라인

> 현재 기준 참고 (2026-05-07): Pipe-C는 Pipe-A/B 산출물의 품질 검증과 복원용이다. 최신 product에서는 `SR -> Guide/WorkProcess/ChecklistItem` 추천 품질을 높이는 데 Pipe-C 결과를 사용한다. 전체 Guide JSON 추출 완료 후 faceted 교차검증과 Guide 레이어 리빌딩을 다시 수행한다.

Pipe-A(법령→SR)와 Pipe-B(가이드→CI)가 독립적으로 생산한 데이터를 교차 비교·검증·통합한다.

## 현황 (2026-04-25)

- **코드**: ✅ 완성 (스크립트 6개 + lib 1개 + DB 2개)
- **데이터**: Step 0~5 전부 완료, V-C1~V-C10 **10/10 PASS**
- **DB**: guide_inter_links 89건, domain_terms.canonical_id ALTER 완료

## Phase 구조

### Phase 1: DB 기반 교차검증 (결정론적)

| Step | 스크립트 | 내용 | 결과 |
|---|---|---|---|
| 0 | `step0_sr_coverage.py` | SR 커버리지 갭 분석 | 364/626 커버 (58.1%) |
| 1 | `step1_basedon_audit.py` | basedOn 매핑 정확성 감사 | 의심 2,496건 (27.2%) |
| 2 | `step2_dt_dedup.py` | DT 중복 탐지 | 327 그룹 (1,891건) |

### Phase 2: basedOn 복원 + 통합

| Step | 스크립트 | 내용 | 결과 |
|---|---|---|---|
| 3 | `step3_basedon_restore.py` | basedOn null 복원 | 1,123건 DB 적용 (overlap 5+) |
| 4 | `step4_build_sr_registry.py` | sr-registry.json 빌드 | 626 SR (1,270KB) |

### Phase 3: 텍스트 기반 분석

| Step | 스크립트 | 내용 | 결과 |
|---|---|---|---|
| 5 | `step5_guide_interlink.py` | 가이드 상호참조 regex 탐지 | 135건 (DB 89건) |

### Phase 4: Faceted 교차검증 (예정)

| Step | 스크립트 | 내용 | 결과 |
|---|---|---|---|
| 6 | `step3_faceted_mapping.py` *(예정)* | CI-SR faceted 교차 매칭으로 매핑 커버리지 향상 | — |

## 스크립트 목록

- `scripts/step0_sr_coverage.py` — SR별 CI 연결 수 집계 + 도메인별 분석. 함수: `main()`
- `scripts/step1_basedon_audit.py` — CI↔SR 키워드 겹침으로 매핑 품질 검증. 함수: `keyword_overlap(ci_text, sr_text)`, `main()`
- `scripts/step2_dt_dedup.py` — 도메인 내 완전일치 + 유사 용어 탐지. 함수: `main()`
- `scripts/step3_basedon_restore.py` — null basedOn CI를 SR 626개와 재매칭 (`--apply`로 DB 적용). 함수: `keyword_set(text)`, `main()`
- `scripts/step4_build_sr_registry.py` — Pipe-A+B+C 통합 SR 레지스트리. 함수: `main()`
- `scripts/step5_guide_interlink.py` — 파싱 가이드에서 "KOSHA GUIDE" 참조 regex 탐지. 함수: `extract_full_text(doc)`, `normalize_guide_code(raw)`, `main()`
- `scripts/step3_faceted_mapping.py` *(예정)* — CI-SR faceted 3축 교차 매칭으로 매핑 커버리지 향상
- `scripts/lib/paths.py` — 경로 상수
- `db/schema_pc.sql` — guide_inter_links 테이블 DDL
- `db/import_pipec.py` — 적재 + V-C1~V-C10 검증 (`--verify` 옵션으로 검증만 실행). 함수: `apply_schema(conn)`, `import_guide_interlinks(conn)`, `verify(conn)`, `main()`

## DB 스키마

```sql
CREATE TABLE guide_inter_links (
    source_guide VARCHAR(20) NOT NULL,
    referenced_guide VARCHAR(20) NOT NULL,
    reference_type VARCHAR(15) NOT NULL,
    reference_text TEXT,
    raw_match TEXT,
    PRIMARY KEY (source_guide, referenced_guide)
);

ALTER TABLE domain_terms ADD COLUMN canonical_id VARCHAR(30);
```

## 검증 규칙 V-C1~V-C10

- V-C1: guide_inter_links FK 무결
- V-C2: 자기 참조 0건
- V-C3: basedOn 검증 완료 비율
- V-C4: sr-registry SR 수 = DB SR 수
- V-C5: DT canonical_id FK 무결
- V-C6: Pipe-A 회귀 (SR 626 보존)
- V-C7: Pipe-B 회귀 (CI 수 보존)
- V-C8: ci_sr_mapping FK 무결
- V-C9: sr-registry.json 존재
- V-C10: 교차파이프 ID 형식

## 데이터 파일

- `data/sr-coverage-report.json` (108KB)
- `data/basedon-audit-report.json` (48KB)
- `data/dt-dedup-report.json` (444KB)
- `data/basedon-restore-report.json` (116KB)
- `data/sr-registry.json` (1.3MB) — **최종 산출물**
- `data/guide-interlinks.json` (48KB)

## 의존 관계

- Pipe-A: `safety_requirements`, `sr_ns_mapping`, `sr_article_mapping` 읽기 전용
- Pipe-B: `checklist_items`, `ci_sr_mapping`, `domain_terms`, `kosha_guides` 읽기 + 쓰기(복원 시)
