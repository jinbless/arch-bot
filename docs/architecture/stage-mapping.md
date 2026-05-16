# Stage Mapping

9단계 정의 + 각 단계의 현재 코드/파일 위치 매핑.

## Stage 1 — Parsing

법령 + KOSHA Guide PDF → JSON 파싱.

| 입력 | 처리 | 출력 |
|---|---|---|
| `legalize-kr/` (외부 git) | 법령 JSON 로드 | (pipe-A의 step0 입력) |
| `data-team/01-parsing/kosha-guides/{A,B,C,D,E}/*.pdf` (raw PDF, ignored) | `data-team/02-extraction/pipe-B/scripts/step1_parse_pdf_vlm.py` | `data-team/01-parsing/kosha-guides/parsed/*.json` (1,038개, tracked) + `data-team/01-parsing/kosha-guides/manifest/guides-manifest.json` |

핵심 스크립트:
- [data-team/02-extraction/pipe-B/scripts/step0_build_inventory.py](../../data-team/02-extraction/pipe-B/scripts/step0_build_inventory.py)
- [data-team/02-extraction/pipe-B/scripts/step1_parse_pdf_vlm.py](../../data-team/02-extraction/pipe-B/scripts/step1_parse_pdf_vlm.py)

## Stage 2 — Extraction

LLM으로 NS/SR/CI 추출.

| 영역 | 스크립트 | LLM agent |
|---|---|---|
| pipe-A 법령→NS | [data-team/02-extraction/pipe-A/scripts/step3_*](../../data-team/02-extraction/pipe-A/scripts/) | [agents/step3-ns-generation.md](../../data-team/02-extraction/pipe-A/agents/step3-ns-generation.md) |
| pipe-A 법령→SR | [data-team/02-extraction/pipe-A/scripts/step5_*](../../data-team/02-extraction/pipe-A/scripts/) | [agents/step5-sr-generation.md](../../data-team/02-extraction/pipe-A/agents/step5-sr-generation.md) |
| pipe-B Guide→CI/DT/WP/ES/DR | [data-team/02-extraction/pipe-B/scripts/step4_extract_entities.py](../../data-team/02-extraction/pipe-B/scripts/step4_extract_entities.py) | [agents/step4-entity-extraction.md](../../data-team/02-extraction/pipe-B/agents/step4-entity-extraction.md) |

## Stage 3 — Validation

PG 적재 + FK/적합성 검증.

| 영역 | DB schema | 검증 스크립트 |
|---|---|---|
| pipe-A NS/SR/PenaltyRule | [data-team/02-extraction/pipe-A/db/schema_pg.sql](../../data-team/02-extraction/pipe-A/db/schema_pg.sql) | `import_and_verify.py` (V1~V15) |
| pipe-B CI/DT/WP/ES/DR | [data-team/02-extraction/pipe-B/db/schema_pb.sql](../../data-team/02-extraction/pipe-B/db/schema_pb.sql) | `import_pipeb.py --verify-all` (V16~V30) |
| pipe-C 교차검증 | [data-team/03-validation/pipe-C/db/schema_pc.sql](../../data-team/03-validation/pipe-C/db/schema_pc.sql) | `import_pipec.py` (V-C1~V-C10) |

## Stage 4 — Ontology Export

PG 내용을 다시 OWL/TTL로 export. 현재 스크립트는 ontology-team 디렉토리 아래(`ontology-team/06-reasoning/ontology/scripts/export_*`)에 있지만, **본질은 데이터팀 책임**. 향후 [data-team/04-ontology-export/](../../data-team/04-ontology-export/)로 이동 예정.

핵심:
- [ontology-team/06-reasoning/ontology/scripts/export_owl.py](../../ontology-team/06-reasoning/ontology/scripts/export_owl.py)
- [ontology-team/06-reasoning/ontology/scripts/export_serving_snapshot.py](../../ontology-team/06-reasoning/ontology/scripts/export_serving_snapshot.py)
- [ontology-team/06-reasoning/ontology/scripts/sync_fuseki.sh](../../ontology-team/06-reasoning/ontology/scripts/sync_fuseki.sh)

## Stage 5 — Enrichment (임시)

LLM으로 서빙 부족 온톨로지 레이어 보강. **현재 가장 활발한 작업.** 6번 완성 시 폐지.

| 영역 | 현재 위치 |
|---|---|
| manual-enrichment 보고서 (42개) | [data-team/02-extraction/pipe-B/data/manual-enrichment-*](../../data-team/02-extraction/pipe-B/data/) |
| LLM enrichment build/analyze/triage/promote 스크립트 | [serving-team/08-app/backend/scripts/build_*.py](../../serving-team/08-app/backend/scripts/) (분류: `build_*`, `analyze_*`, `triage_*`, `review_*`, `bootstrap_*`, `backfill_*`, `she_shadow_*`, `auto_keyword_*`, `sync_*_into_profiles`, `promote_*`) |
| evaluation 스크립트 | [serving-team/08-app/backend/scripts/evaluate_*.py](../../serving-team/08-app/backend/scripts/) (분류: `evaluate_*`, `diagnose_*`, `generate_test_cases.py`, `run_corner_test.py`, `test_e2e_*`) |
| runtime artifacts (보강된 결과) | [serving-team/08-app/backend/app/data/*.json, *.jsonl](../../serving-team/08-app/backend/app/data/) |
| 합성 평가 입력 | [data-team/05-enrichment/eval-data/synthetic_observations_v*.jsonl](../../data-team/05-enrichment/eval-data/) |
| 평가 보고서 (ignored, 11GB) | `data-team/05-enrichment/eval-data/reports/` |
| SHE enrichment 스크립트 | [data-team/05-enrichment/she-scripts/](../../data-team/05-enrichment/she-scripts/) |
| SHE 데이터 | [data-team/05-enrichment/she-data/](../../data-team/05-enrichment/she-data/) |
| SHE PG schema | [data-team/05-enrichment/she-db/](../../data-team/05-enrichment/she-db/) |

**향후 분리 작업 (별도 PR)**: 위의 backend/scripts/* 와 backend/app/data/* 를 [data-team/05-enrichment/](../../data-team/05-enrichment/) 하위로 이동. 단 backend가 app/data/*.json을 직접 import하는 부분의 path 재설계가 필요해서 5번 작업 안정화 후 진행.

## Stage 6 — Reasoning (오픈소스 공개 대상)

공리/OWL/SHACL → 리즈너로 문제 발견·수정.

| 영역 | 위치 |
|---|---|
| TBox (OWL DL 정의) | [ontology-team/06-reasoning/ontology/kosha-ontology.owl](../../ontology-team/06-reasoning/ontology/kosha-ontology.owl) |
| ABox (인스턴스) | [ontology-team/06-reasoning/ontology/kosha-instances.ttl](../../ontology-team/06-reasoning/ontology/kosha-instances.ttl) |
| SWRL rules | [ontology-team/06-reasoning/ontology/kosha-rules.swrl](../../ontology-team/06-reasoning/ontology/kosha-rules.swrl) |
| SHACL shapes | [ontology-team/06-reasoning/ontology/serving-validation-shapes.ttl](../../ontology-team/06-reasoning/ontology/serving-validation-shapes.ttl) |
| 정책 TTL | [ontology-team/06-reasoning/ontology/serving-policy.ttl](../../ontology-team/06-reasoning/ontology/serving-policy.ttl) |
| Reasoner runner | [ontology-team/06-reasoning/ontology/scripts/run_inference.py](../../ontology-team/06-reasoning/ontology/scripts/run_inference.py), [validate_ontology.py](../../ontology-team/06-reasoning/ontology/scripts/validate_ontology.py), [verify_fuseki_inference.sh](../../ontology-team/06-reasoning/ontology/scripts/verify_fuseki_inference.sh) |
| Fuseki infra | [ontology-team/06-reasoning/ontology/docker/](../../ontology-team/06-reasoning/ontology/docker/) |
| 시각화 | [ontology-team/06-reasoning/visualization/](../../ontology-team/06-reasoning/visualization/) |
| 자동 생성 검증 리포트 | `ontology-team/06-reasoning/ontology/serving-validation-report-*.{md,csv,json}`, `serving-workprocess-alignment-*` (수동 편집 금지) |

## Stage 7 — Materialization

보정된 내용을 PG로 재물질화. ontology-team 산출물을 받아 PG schema에 적재.

핵심:
- [serving-team/08-app/backend/scripts/import_guide_usage_profiles_to_pg.py](../../serving-team/08-app/backend/scripts/import_guide_usage_profiles_to_pg.py)
- [serving-team/08-app/backend/scripts/import_ci_sr_link_candidates.py](../../serving-team/08-app/backend/scripts/import_ci_sr_link_candidates.py)
- [serving-team/08-app/backend/scripts/reindex_articles.py](../../serving-team/08-app/backend/scripts/reindex_articles.py)
- [ontology-team/06-reasoning/ontology/scripts/validate_serving_snapshot.py](../../ontology-team/06-reasoning/ontology/scripts/validate_serving_snapshot.py)
- [ontology-team/06-reasoning/ontology/scripts/audit_serving_workprocess_alignment.py](../../ontology-team/06-reasoning/ontology/scripts/audit_serving_workprocess_alignment.py)

**향후 분리 작업**: 위의 import_* 스크립트를 [serving-team/07-materialization/pg-sync-scripts/](../../serving-team/07-materialization/)로, validate/audit를 [07-materialization/validation-scripts/](../../serving-team/07-materialization/)로 이동.

## Stage 8 — App

OHS backend + frontend PG 기반 서비스.

| 영역 | 위치 |
|---|---|
| 백엔드 FastAPI | [serving-team/08-app/backend/app/main.py](../../serving-team/08-app/backend/app/main.py) |
| 분석 오케스트레이션 | [serving-team/08-app/backend/app/services/analysis_pipeline.py](../../serving-team/08-app/backend/app/services/analysis_pipeline.py) |
| 도메인 서비스들 | [serving-team/08-app/backend/app/services/](../../serving-team/08-app/backend/app/services/) (hazard_normalizer, she_matcher, sr_lookup_service, guide_recommendation_service, penalty_path_service 등) |
| 프런트 페이지 | [serving-team/08-app/frontend/src/pages/](../../serving-team/08-app/frontend/src/pages/) |
| 결과 패널 | [serving-team/08-app/frontend/src/components/results/](../../serving-team/08-app/frontend/src/components/results/) (RiskOverview / ImmediateActions / GuideProcedure / PenaltyPath / ReasoningTrace) |
