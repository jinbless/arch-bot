# Team Structure

3팀 분담 + 9단계 매핑 + 책임 영역.

## 9단계 작업 모델

1. **Parsing** — 법령(legalize-kr) + KOSHA Guide PDF → JSON
2. **Extraction** — LLM으로 NS/SR/CI 추출
3. **Validation** — PG 적재로 적합성/FK 규칙 검증
4. **Ontology Export** — PG 적재 내용을 다시 온톨로지화
5. **Enrichment (임시)** — LLM으로 서빙 부족 온톨로지 레이어 채우기
6. **Reasoning (오픈소스)** — 공리/OWL/SHACL → 리즈너로 문제 발견·수정 (LLM 활용 최소화)
7. **Materialization** — 보정된 내용을 PG로 재물질화
8. **App** — OHS에서 PG 기반 서비스
9. **(원칙)** 온톨로지는 데이터 관리/확장 표준 DB 역할이며 서빙에 직접 관여하지 않는다

## 팀 분담

| 팀 | 단계 | 디렉토리 | 향후 repo | 공개 |
|---|---|---|---|---|
| **데이터팀** | 1, 2, 3, 4, 5 | [data-team/](../../data-team/) | `kosha-data-pipeline` | private |
| **온톨로지팀** | 6 | [ontology-team/](../../ontology-team/) | `kosha-ontology-reasoning` | **public (오픈소스)** |
| **서빙팀** | 7, 8 | [serving-team/](../../serving-team/) | `kosha-ohs` | private |

## 5번 영역 — 데이터팀 소속의 임시 단계

5번(LLM enrichment)은 현재 가장 활발한 작업 영역이다. **본질은 데이터 보정**이므로 데이터팀 소속. 단 6번이 완성되어 공리/리즈너로 자동 보정이 가능해지면 자연 폐지된다.

5번 영역 위치:
- 스크립트 / artifact는 현재 [serving-team/08-app/backend/scripts/](../../serving-team/08-app/backend/scripts/) 및 [serving-team/08-app/backend/app/data/](../../serving-team/08-app/backend/app/data/)에 남아 있음 (Phase 2 commit 1 한정. 향후 별도 PR로 [data-team/05-enrichment/](../../data-team/05-enrichment/) 하위로 옮길 예정).
- manual enrichment 보고서는 [data-team/02-extraction/pipe-B/data/manual-enrichment-*](../../data-team/02-extraction/pipe-B/data/) (현재). 향후 [data-team/05-enrichment/manual-enrichment/](../../data-team/05-enrichment/) 하위로 분리 예정.
- eval-data는 이미 [data-team/05-enrichment/eval-data/](../../data-team/05-enrichment/eval-data/)에 위치.

## 책임 경계

- **데이터팀**: 원천 데이터의 파싱·추출·검증·물질화·LLM 보강. PG schema 1차 소유.
- **온톨로지팀**: 데이터팀이 만든 TBox/ABox를 받아 공리 적용·리즈너 운영·SHACL 검증. 부정확한 매핑 발견 → 데이터팀과 협의하여 수정.
- **서빙팀**: 온톨로지팀이 보정한 내용을 PG로 재물질화 + OHS API/UI 운영. 온톨로지 직접 호출 안 함.

## 공통 reference 데이터

[shared/](../../shared/) — 위험 분류 통합 데이터 등 3팀 공통 reference.

## 협업 정책

- 단계 간 인터페이스는 [inter-stage-interfaces.md](inter-stage-interfaces.md) 명세에 따른다. 임의 변경 금지.
- 한 팀이 다른 팀의 디렉토리를 직접 수정하지 않는다. 변경 필요 시 PR.
- baseline 갱신은 [docs/status/evaluation-baseline.md](../status/evaluation-baseline.md) 정본 단일 진실.
