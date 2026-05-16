# Data Team

데이터팀은 1~5단계를 담당한다. **향후 private `kosha-data-pipeline` repo로 분리 예정**.

## 단계

| 단계 | 디렉토리 | 역할 |
|---|---|---|
| 1. Parsing | [01-parsing/](01-parsing/) | 법령(legalize-kr) + KOSHA Guide PDF → JSON 파싱 |
| 2. Extraction | [02-extraction/](02-extraction/) | LLM으로 NS/SR/CI 추출 (pipe-A, pipe-B) |
| 3. Validation | [03-validation/](03-validation/) | PG 적재로 적합성/FK 규칙 검증 (pipe-C) |
| 4. Ontology Export | [04-ontology-export/](04-ontology-export/) | PG → 온톨로지 export |
| 5. Enrichment (임시) | [05-enrichment/](05-enrichment/) | LLM으로 서빙 부족 온톨로지 레이어 보강 — 6번 완성 시 폐지 |

## 주기성

- 1~4번은 **1회성** (새 데이터/Guide 추가 시에만 재실행)
- 5번은 **현재 집중 작업** — 6번(온톨로지 리즈너 기반 보정)이 안정화되면 자연 폐지

## 다음 팀과의 인터페이스

- **→ 온톨로지팀 (6단계)**: 4단계가 만든 TBox/ABox TTL을 [ontology-team/06-reasoning/](../ontology-team/06-reasoning/)에서 읽어 추론·SHACL 검증
- **→ 서빙팀 (7~8단계)**: 5단계의 runtime artifacts (`05-enrichment/runtime-artifacts/` 또는 현재는 `serving-team/08-app/backend/app/data/`)를 [serving-team/08-app/backend](../serving-team/08-app/backend)가 직접 import

## 공통 reference

- [shared/reference/hazard-taxonomy-unified.json](../shared/reference/hazard-taxonomy-unified.json) — 위험 분류 통합 데이터

## 향후 repo 분리 계획

[docs/architecture/repo-split-plan.md](../docs/architecture/repo-split-plan.md) 참조.
