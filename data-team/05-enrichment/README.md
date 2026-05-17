# Stage 5 — LLM Enrichment (Data Team, 임시)

LLM으로 서빙에 부족한 온톨로지 레이어를 보강하는 단계.

**중요**: 5번은 **임시 단계**입니다. 6단계(공리/OWL/SHACL/리즈너)가 안정화되면 자연 폐지됩니다.

**현재 진행 상태 (2026-05-17)**:
- Phase E.2 완료 — Fuseki Java가 v2 ontology + disjoint + SHACL + 172 subClassOf 로드 (commit `3520cab`)
- Phase 3 완료 — catalog v4 (1,914 codes), 498 SHE patterns 생성/검증, reasoning이 LLM 환각 1,902건 차단
- **Phase F.3 first batch 완료** — F.3.0 reject reason 분류 (axiom_missing 36.44%) + F.3.2 mine_missing_axioms (49 verify → 8 accepted) + F.3.3 Gate 3 regression PASS
- 신규 LLM 스크립트: `llm-scripts/{classify_reject_reasons.py, mine_missing_axioms.py, translate_incompat_industries.py}` (이번 sprint 추가)
- Layer 4 (Ontology Learning, cross-cutting) 7-module 정밀 설계 정착 — 상세 [`docs/architecture/ontology-learning-layer.md`](../../docs/architecture/ontology-learning-layer.md)

## 현재 디렉토리 구성

| 하위 | 내용 |
|---|---|
| [eval-data/](eval-data/) | 합성 평가 입력(`synthetic_observations_v1~v10.jsonl`) + `reports-manifest.json` + reports/(11GB ignored) + 51개 generator scripts (`_gen_*.py`, `_fix_*.py`, `_validate_*.py`) |
| [she-scripts/](she-scripts/) | SHE 추출/검증/적재 스크립트 (`invert_sr_to_she.py`, `validate_she_jsonl.py`, `import_she_pg.py`, `load_she_to_fuseki.py`, `llm_provider.py`) |
| [she-data/](she-data/) | SHE 데이터 (jsonl + ttl) |
| [she-db/](she-db/) | SHE PG schema |

## Phase B에서 이동 예정 (현재 다른 위치에 있는 5번 영역)

5번 작업이 활발히 진행 중이라 backend 코드 의존성 때문에 즉시 이동 못 한 부분:

| 현재 위치 | 향후 위치 |
|---|---|
| `serving-team/08-app/backend/scripts/build_*.py`, `analyze_*.py`, `triage_*.py`, `review_*.py`, `bootstrap_*.py`, `backfill_*.py`, `she_shadow_*.py`, `auto_keyword_*.py`, `sync_*_into_profiles.py`, `promote_*.py` | `data-team/05-enrichment/llm-scripts/` |
| `serving-team/08-app/backend/scripts/evaluate_*.py`, `diagnose_*.py`, `generate_test_cases.py`, `run_corner_test.py`, `test_e2e_*.py` | `data-team/05-enrichment/evaluation-scripts/` |
| `serving-team/08-app/backend/app/data/*.json`, `*.jsonl` (runtime artifacts) | `data-team/05-enrichment/runtime-artifacts/` (backend import path 동시 수정) |
| `data-team/02-extraction/pipe-B/data/manual-enrichment-*` (42개) | `data-team/05-enrichment/manual-enrichment/` |

이동 시 backend가 5번 runtime artifacts를 어떻게 받을지(환경변수 path / 빌드 단계 mirror) 동시 결정 필요.

## 6단계 완성 시 폐지 절차

1. 6단계 리즈너가 5번 LLM enrichment를 대체 가능 수준에 도달
2. baseline 안정성 검증
3. 이 디렉토리 전체 archive 또는 삭제
4. cleanup-log에 폐지 entry 추가

## 다른 팀과의 인터페이스

- **← 데이터팀 (1~4단계)**: 파싱·추출·검증·온톨로지화 산출물 입력
- **→ 서빙팀 (8단계, 임시)**: runtime artifacts (`guide_*.json`, `situation_context_taxonomy.*.json`)를 backend가 직접 import
- **→ 온톨로지팀 (6단계)**: 5번이 만든 candidate 데이터를 리즈너가 검증·보정

자세한 단계별 위치 매핑: [docs/architecture/stage-mapping.md](../../docs/architecture/stage-mapping.md)
