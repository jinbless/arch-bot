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
- 백엔드 서비스 구조: `08-app/backend/app/services/` (analysis_pipeline, hazard_normalizer, **hazard_to_guide_service**, she_matcher, sr_lookup_service, **sr_inferred_service**, guide_recommendation_service, penalty_path_service, shadow_reasoner 등)
- 프런트 결과 패널: `08-app/frontend/src/components/results/` (RiskOverview / **HazardGuideRelations** / ImmediateActions / GuideProcedure / PenaltyPath / ReasoningTrace)

## 최근 변경 (2026-06-14) — Track A ② 추론 수직 슬라이스

리즈너 도출 관계를 PG로 물질화하고 서빙이 Fuseki 대신 PG를 읽도록 전환 (commit `87d9e63`/`7c50304`/`e6140bb`, main push 완료).

**PG schema (신규 2 table)**:
- `sr_inferred_relations` — 총 **103,295 row**. rule_id별: R-1 exemptedBy **107** + K-R2 coApplicable **32,858**(16,429 distinct pair × 양방향) + K-R4 dependsOn **70,330**(35,165 distinct pair × 양방향). R-2 strict coApplicable=0(SR↔Article 1:1). R-3 HighSeverityPenalty(3,579)는 본 table에 저장 안 함 — `penalty_rule_index.severity_score>=5` SQL 재현.
- `materialization_runs` — PROV run-tracking (run_id, rule_set, ontology_commit=git rev, source_ttl_sha256=content-hash, triple_count, status).

**신규/수정 service**:
- `app/services/sr_inferred_service.py` 신규 — `sr_inferred_relations` PG 조회.
- `hazard_rule_engine.py`: dead `enrich_sr_with_sparql` → PG 기반 `enrich_sr_with_pg`로 교체.

**`/sparql` endpoint (4)**:
- `/api/v1/sparql/sr/{id}/exemptions`, `/co-applicable`, `/article/{code}/inferred-graph` — Fuseki→PG SELECT 전환
- `/api/v1/sparql/sr/{id}/depends-on` — 신규

**신규 스크립트**: `serving-team/07-materialization/pg-sync-scripts/import_sr_inferred_relations_to_pg.py`, `serving-team/08-app/backend/scripts/verify_inferred_relations.py`.

**Gate**: f1-regression all-metric delta **0.0000**(analysis hot-path 불변, 3 slice 전부), latency PASS, verify-baseline PASS, phase-g5/g5b/g5c-verify PASS.

## 최근 변경 (2026-05-28, origin/main `4aa3cca`) — guide-accuracy Sprint

CI 추천은 정확하나 Guide가 엉뚱하게 추천되는 문제(boilerplate CI fan-out + CI 개수 단독 랭킹) 근본 해결.

**수정/신규 service** (`app/services/hazard_rule_engine.py`):
- `get_guides_from_srs()` — CI **개수** 랭킹 → **Σ(ci_weight) 변별력 가중합**. `ci_weight = 1/log2(1+guide_frequency)` (boilerplate 자동 억제). score = 0.55 + 0.30·norm_weighted + industry_adjustment.
- `get_guides_by_hazard_features()` ⭐ 신규 — `guide_entity_feature_candidates(entity_type='GUIDE')` 직접 조회 (CI 경유 없음). score = 0.60 + 0.20·conf + 0.05·(n_feat−1) + industry.
- `app/services/hazard_to_guide_service.py:_merge_guide_paths()` — 직접 매핑 우선 + CI 경유 union (교집합 bonus +0.15).

**PG schema**:
- `checklist_items.guide_frequency` (Integer, 신규 컬럼) — backfill **3,953 CI, max 130**.
- `guide_entity_feature_candidates(entity_type='GUIDE', method='guide_hazard_weighted_majority')` **2,115행 / 659 Guide**.

**데이터 도출 스크립트** (`data-team/05-enrichment/llm-scripts/`): `compute_ci_guide_frequency.py`, `derive_guide_hazard_features.py`, `export_guide_hazard_to_abox.py`.

**검증**: 8-photo Guide mapping 80%→100%, guide_hazard_direct 85%, boilerplate 0. Gate 3 regression PASS. Runbook: `docs/dev-notes/guide-recommendation-accuracy.md`.

## 이전 변경 (2026-05-19, origin/main `164de5a`) — Hazard-Direct Architecture Pivot

Vision LLM이 `hazards[]`를 자연어로 직접 출력 → catalog code 매핑 → ontology Guide 추천하는 신규 path. SHE matcher chain 우회, 기존 SHE-based path는 fallback 병행 (`HAZARD_DIRECT_MODE=off|parallel|primary`).

**신규 service**:
- `app/services/hazard_to_guide_service.py` — `match_hazards_to_guides()`: hazard별 SR → Guide grouping (hazard_rule_engine 재사용)

**수정 service/model**:
- `app/services/hazard_normalizer.py` — `normalize_hazards_array()` 신규 함수 (`hazards[].name` → canonical 3축)
- `app/services/analysis_pipeline.py` — `HAZARD_DIRECT_MODE` 분기 + hazards/hazard_guide_relations 응답 조립
- `app/models/analysis.py` — `HazardItem` / `GuideRef` / `HazardGuideRelation` Pydantic + `AnalysisResponse` 확장
- `app/integrations/openai_client.py` — `ONTOLOGY_OBSERVATION_SCHEMA`에 `hazards[]` 필드 + 14 표준 라벨 prompt

**검증**: 8 real-test-photo 실호출 → **25/25 (100%) catalog 매핑 PASS** (AC-2 ≥85%), 25 hazard_guide_relations, 14 penalty paths. Runbook: `docs/workplans/hazard-direct-architecture-pivot.md`.

## 이전 변경 (2026-05-19, main `448a8d0`) — Phase G PG materialization

**Phase G PG materialization 본격 적용** — 사용자 구조 step 4 "온톨로지화된 KB → PG 적재 → 실 서비스 자동 반영" 입증.

**Backend services PG primary 전환** (3 services + 1 신규):
- `app/services/shadow_reasoner.py` (Phase G.1, `d6b4589`): `guide_domain_incompatibilities` PG primary + JSON fallback (lazy module cache 유지)
- `app/services/guide_domain_profile.py` (Phase G.2, `2f7ef92`): `guide_usage_profiles` PG primary + JSON fallback
- `app/services/hazard_rule_engine.py:_load_penalty_index` (Phase G.3, `8ddc2c7`): TTL parse 우회 → PG `penalty_rule_index` (4,076 rules). **penalty_accuracy +27.16%p, overall +18.81%p**
- `app/services/openai_client.py` (이전 Tier 3.A): catalog 529 codes enum

**Backend ORM 신규** (`app/db/models.py`): `PgGuideDomainIncompatibility`, `PgPenaltyRoute`, `PgPenaltyRuleIndex`.

**Fuseki + Ontology 변경**:
- Fuseki container 신규 image (kb-candidates.ttl + kosha-rules-r1-r3-swrl.ttl 추가, 총 981,485 triples)
- ~~SWRL Pellet 실행기 검증: R-1 exemptedBy 107 inferred + R-3 HighSeverityPenalty 3,579 inferred ⭐~~ → **2026-06-14 정정**: R-1/R-3는 더 이상 Fuseki Pellet 요청 경로가 아니다. R-1은 `sr_inferred_relations`(107 row) PG-served, R-3는 `penalty_rule_index.severity_score>=5` SQL 재현. (상단 2026-06-14 절 참조)

**PG materialization 현황**:

| PG table | rows | Phase G sprint | Backend service |
|---|---|---|---|
| `guide_domain_incompatibilities` | 2,016 | G.1 (`d6b4589`) | shadow_reasoner |
| `guide_usage_profiles` | 1,038 (기존) | G.2 (`2f7ef92`) | guide_domain_profile |
| `penalty_rule_index` | 4,076 | G.3 (`8ddc2c7`) | hazard_rule_engine._load_penalty_index |
| `she_patterns_reasoner_derived` (view) | 77 | G.4 (`434f35f`) | (Future matcher integration) |
| `sr_inferred_relations` | 103,295 | G5/G5b/G5c (2026-06-14) | sr_inferred_service (R-1 107 + K-R2 32,858 + K-R4 70,330) |
| `materialization_runs` | run-tracking | G5 (2026-06-14) | (PROV: git rev + ttl sha256) |

## 이전 변경 (2026-05-18 저녁, main `b237e78`)

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
