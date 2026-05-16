# Serving Team

서빙팀은 7~8단계를 담당한다. **향후 private `kosha-ohs` repo로 분리 예정**.

## 단계

| 단계 | 디렉토리 | 역할 |
|---|---|---|
| 7. Materialization | [07-materialization/](07-materialization/) | 보정된 온톨로지 내용을 PG로 재물질화 |
| 8. App | [08-app/](08-app/) | OHS backend(FastAPI) + frontend(React+Vite) PG 기반 서비스 |

## 원칙

- **온톨로지는 서빙 경로에 직접 관여하지 않는다.** OWL 리즈너는 요청 경로 밖에서만 사용.
- 서빙 = PG materialized table 조회. 빠르고 deterministic.
- LLM은 사진/텍스트 관찰사실 + 시각단서만 추출. 법령/벌칙은 PG에서 조회.

## 다른 팀과의 인터페이스

- **← 온톨로지팀 (6단계)**: [ontology-team/06-reasoning/](../ontology-team/06-reasoning/)이 보정한 TBox/ABox TTL을 7단계가 PG로 재물질화
- **← 데이터팀 (5단계)**: 현재 5단계 LLM enrichment의 runtime artifacts (`serving-team/08-app/backend/app/data/*.json`)를 직접 import. 6단계 완성 시 이 경로 폐지.

## 운영 가이드

- 서비스 실행/검증: [08-app/README.md](08-app/README.md)
- 백엔드 서비스 구조: `08-app/backend/app/services/` (analysis_pipeline, hazard_normalizer, she_matcher, sr_lookup_service, guide_recommendation_service, penalty_path_service 등)
- 프런트 결과 패널: `08-app/frontend/src/components/results/` (RiskOverview / ImmediateActions / GuideProcedure / PenaltyPath / ReasoningTrace)

## 향후 repo 분리 계획

[docs/architecture/repo-split-plan.md](../docs/architecture/repo-split-plan.md) 참조.
