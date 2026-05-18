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
- 백엔드 서비스 구조: `08-app/backend/app/services/` (analysis_pipeline, hazard_normalizer, she_matcher, sr_lookup_service, guide_recommendation_service, penalty_path_service, **shadow_reasoner** 등)
- 프런트 결과 패널: `08-app/frontend/src/components/results/` (RiskOverview / ImmediateActions / GuideProcedure / PenaltyPath / ReasoningTrace)

## 최근 변경 (2026-05-18 저녁, main `b237e78`)

신규 module:
- **`app/services/shadow_reasoner.py`** (T2.A) — Layer 2.5 KB axiom shadow validate. lazy module cache (axioms + industry_ko→en + guide→domain), ~50μs/photo, best-effort never raises. F.3.2 vetted/candidate axiom으로 분석된 candidate guide의 shadow reject 후보 산출.

수정 module:
- **`app/services/analysis_pipeline.py`** (T2.A): `_apply_llm_rerank` happy path + `_log_skipped_analysis` 모두 `shadow_reasoner.shadow_validate` 호출. `_append_analysis_log`에 `reasoner_rejects` kwarg 추가, non-empty 시 analysis_log.jsonl 엔트리에 기록.
- **`app/services/hazard_normalizer.py`** (T1.C): step 4.5 candidate alias match 시 `_log_alias_usage()` 호출 → `alias_candidate_meta.jsonl`에 `used` action append. promote_aliases `--auto` 모드 production-ready.
- **`app/integrations/openai_client.py`** (T3.A): `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text`에 catalog 529 codes enum. `_load_catalog_codes()` lazy module-level load. free-creates 76 → 4 (-94.7%).

수정 ontology:
- **`ontology-team/06-reasoning/ontology/docker/fuseki/.../KoshaFusekiServer.java`** (T2.B): sources array에 `kb-candidates.ttl` 추가. docker image rebuild (`docker-fuseki:latest` sha256 `08837972`). 컨테이너 recreate 후 SPARQL `COUNT(?s a sh:NodeShape)` → **2,216 NodeShapes** (kb-candidates 2,192 + serving 24).

운영 영향:
- Layer 2.5 shadow channel: production analysis_log.jsonl에 `reasoner_rejects` field 누적 (write-only, 실제 reject 안 함)
- T3.A enum: Vision LLM이 catalog 밖 코드 출력 불가. 잔존 4건 (THF/CO/MOBILE_EQUIPMENT/WAREHOUSE)은 OpenAI strict mode edge-case
- Fuseki: kb-candidates.ttl 로드 +17,618 triples (총 981,409). 다음 docker compose는 동일 image 사용 (image tag 고정).

## 향후 repo 분리 계획

[docs/architecture/repo-split-plan.md](../docs/architecture/repo-split-plan.md) 참조.
