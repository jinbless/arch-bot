# OHS product

`OHS`는 온톨로지 기반 KOSHA 위험요소 분석 product의 백엔드/프론트 구현 프로젝트다.

현재 목표는 사업주가 사진이나 텍스트를 입력하면 위험요약, 즉시 조치, 표준 개선 절차, 벌칙 3경로, 근거 보기를 제공하는 것이다.

## Repository Boundary

현재 기준은 root `arch-bot`의 `main` 단일 monorepo다. `OHS`는 더 이상 별도 Git repo로 운영하지 않고, root에서 추적되는 product 디렉토리로 관리한다.

```text
arch-bot/
  OHS/              root-tracked product code and docs
  koshaontology/    root-tracked ontology pipeline code and docs
  legalize-kr/      external ignored dependency, not part of the root repo
  pictures-json/    tracked synthetic inputs plus local/external report bodies
```

과거 독립 `OHS` repo와 `codex/monorepo-snapshot-import` 브랜치 언급은 historical migration context로만 해석한다. 현재 작업, 검증, push 기준은 root `arch-bot/main`이다.

## Current Flow

```text
photo/text input
→ observations and visual cues
→ risk:RiskFeature normalization
→ she:SituationalHazardPattern matching
→ SR / Article / WorkProcess / Guide / CI / PenaltyPath lookup
→ business-owner result screen
```

LLM은 법령 판단자가 아니라 관찰 사실과 시각 단서를 추출하는 역할이다. 법령/SR/가이드/벌칙 연결은 물질화된 온톨로지 데이터와 Python/PostgreSQL 조회 로직이 담당한다.

Guide 추천은 단순 Guide title 랭킹이 아니라 `SHE/SR → WorkProcess/Guide → ChecklistItem` 순서로 구성한다. 중신뢰 후보는 추천 점수에는 쓰지만 법적 확정 근거처럼 표시하지 않는다.

## Backend Structure

핵심 서비스 파일:

```text
backend/app/services/analysis_service.py
  OpenAI 호출 진입점과 기존 API 호환 래퍼

backend/app/services/analysis_pipeline.py
  전체 분석 오케스트레이션

backend/app/services/hazard_normalizer.py
  LLM 단서와 텍스트를 risk feature 후보로 정규화

backend/app/services/risk_rule_service.py
  정규화 feature 보정과 규칙 기반 feature 확장

backend/app/services/she_matcher.py
backend/app/services/she_match_models.py
  SHE pattern 매칭, 상태 판정, DTO

backend/app/services/sr_lookup_service.py
  SR 후보 조회

backend/app/services/guide_recommendation_service.py
  ChecklistItem 즉시 조치와 Guide/WorkProcess 표준 절차 추천
  risk feature, SHE match, visual cue, industry context를 함께 사용

backend/app/services/guide_domain_profile.py
  Guide 고유 업종/작업장 문맥과 사진 문맥의 불일치 평가
  exclusive mismatch는 제외, domain_specific mismatch는 감점

backend/app/services/guide_photo_matchability.py
  1,038개 Guide가 사진 기반 top 표준절차로 적합한지 평가
  측정·분석/시험/검진/문서/방법론 Guide는 photo top에서 제외

backend/app/services/situation_frame_service.py
  Stage 2와 Stage 3 사이의 세부 상황 표현 계층
  child context는 Guide 보조 점수에만 사용하고 status/penalty에는 직접 쓰지 않음

backend/app/services/penalty_path_service.py
  PenaltyRule 후보를 PenaltyPath 3경로로 그룹화
```

중요 데이터 파일:

```text
backend/app/data/risk_feature_aliases.json
backend/app/data/risk_feature_catalog.json
backend/app/data/guide_domain_profiles.json
backend/app/data/guide_photo_matchability.v1.json
backend/app/data/broad_sr_policy.json
backend/app/data/situation_context_taxonomy.v21.json
backend/app/data/guide_support_candidates.v21.jsonl
```

PostgreSQL의 Guide 보강 후보 테이블:

```text
guide_usage_profiles
guide_entity_feature_candidates
guide_sr_link_candidates
guide_visual_trigger_candidates
```

`guide_domain_profiles.json`은 Pipe-B의 1,038개 manual Guide usage profile export를 OHS serving용으로 복사한 파일이다. 현재 Guide profile 자체는 `ci_broad_sr_guard4` 기준으로 `guide_usage_profiles` PostgreSQL 테이블에도 1,038행 동기화되어 있고, 최신 서빙 기준 `ci_candidate_promotion_v1`은 그 위에서 review-only CI/SR 후보 17행만 serving `candidate`로 승격한 상태다. 런타임은 JSON artifact와 PG 후보 테이블을 읽고, PG 동기화본은 감사/ontology export 정합성 확인에 쓴다. `broad_sr_policy.json`은 broad SR이 단독으로 표준절차를 만들지 못하도록 제한하는 serving policy다.

legacy resource/video/category 기반 파일은 product 런타임에서 제거했다.

## Frontend Structure

결과 화면은 다음 패널 중심이다.

```text
frontend/src/components/results/RiskOverviewPanel.tsx
frontend/src/components/results/ImmediateActionsPanel.tsx
frontend/src/components/results/GuideProcedurePanel.tsx
frontend/src/components/results/PenaltyPathPanel.tsx
frontend/src/components/results/ReasoningTracePanel.tsx
```

분석 실행 중복은 `frontend/src/hooks/useRunAnalysis.ts`로 묶었다.

`standard_procedures`는 기존 카드 호환 필드(`title`, `description`, `guide_code`, `confidence`)를 유지하면서, `steps`가 있으면 WorkProcess 절차형 목록으로 표시한다.

## Run Locally

백엔드:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

프론트:

```bash
cd /mnt/c/project/arch-bot/OHS/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

브라우저:

```text
http://127.0.0.1:5173/ohs/
```

## Environment

백엔드 기본값:

```text
DATABASE_URL=postgresql://kosha:1229@localhost/kosha
FUSEKI_ENDPOINT=http://localhost:3030/kosha/sparql
FUSEKI_ENABLED=true
```

프론트 개발 fallback:

```text
http://localhost:8001/api/v1
```

실제 OpenAI 이미지/텍스트 분석에는 `OPENAI_API_KEY`가 필요하다. 없으면 분석 API가 503을 반환할 수 있다.

## Validation

Python compile:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python -c "import pathlib; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in pathlib.Path('.').rglob('*.py') if '__pycache__' not in p.parts]; print('compile ok')"
```

Frontend build:

```bash
cd /mnt/c/project/arch-bot/OHS/frontend
npm run build
```

Synthetic smoke:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
.venv/bin/python scripts/evaluate_synthetic_observations.py --input ../../pictures-json/synthetic_observations_v10.jsonl --report-prefix synthetic_observations_v10_ci_candidate_promotion_v1_report
```

Actual response 240 replay:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
.venv/bin/python scripts/evaluate_actual_response_samples.py --report-prefix actual_response_samples_ci_candidate_promotion_v1 --database-note "ci_candidate_promotion_v1"
```

Guide recommendation evaluation:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
.venv/bin/python scripts/evaluate_synthetic_guide_recommendations.py --report-prefix synthetic_guide_recommendations_v1_v10_ci_broad_sr_guard4
```

Stage 2~5 integrated pipeline quality evaluation:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/evaluate_stage2_5_pipeline_quality.py --report-prefix pipeline_quality_v1_v10_ci_candidate_promotion_v1 --progress-every 500 --photo-baseline-report pictures-json/reports/pipeline_quality_v1_v10_ci_broad_sr_guard4.json
```

Serving ontology snapshot export and validation:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python koshaontology/ontology/scripts/export_serving_snapshot.py
OHS/backend/.venv/bin/python koshaontology/ontology/scripts/validate_serving_snapshot.py
```

Guide usage profile PG sync:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
.venv/bin/python scripts/import_guide_usage_profiles_to_pg.py --report-prefix pg_guide_usage_profiles_sync_ci_broad_sr_guard4
```

Stage 3 remaining-gap support artifact:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/build_stage3_remaining_gap_support_v20_artifacts.py
```

Stage 2 support usage-gate artifact:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/build_stage2_support_usage_gate_artifacts.py --report-prefix stage2_support_usage_gate_artifacts_v2
```

Stage 3 domain support v6 artifact:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/build_stage3_domain_support_v6_artifacts.py --report-prefix stage3_domain_support_v6_artifacts_tight1
```

Guide photo matchability artifact:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/build_guide_photo_matchability.py
```

NO_TOP Guide support artifact:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/build_no_top_guide_support_candidates.py --support-output OHS/backend/app/data/guide_support_candidates.v3.jsonl
```

Stage 3 SHE gap candidate diagnosis:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/analyze_stage3_she_gap_candidates.py --input pictures-json/reports/pipeline_quality_v1_v10_ci_reference_guard1.json --report-prefix stage3_she_gap_candidates_reference_guard1
```

Stage 3 review-only SHE candidate preview:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/build_stage3_she_candidate_preview.py
```

SituationFrame artifacts and evaluation:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/build_situation_frame_artifacts.py
OHS/backend/.venv/bin/python OHS/backend/scripts/evaluate_situation_frame_quality.py --report-prefix situation_frame_eval_report.v2_child_gate1
OHS/backend/.venv/bin/python OHS/backend/scripts/evaluate_stage2_5_pipeline_quality.py --report-prefix pipeline_quality_v1_v10_situation_frame_support7
OHS/backend/.venv/bin/python OHS/backend/scripts/evaluate_actual_response_samples.py --report-prefix actual_response_samples_situation_frame_support7 --database-note "SituationFrame v2 child-gated support / support7 accepted candidate"
cd /mnt/c/project/arch-bot/OHS/backend
.venv/bin/python scripts/evaluate_synthetic_observations.py --input ../../pictures-json/synthetic_observations_v10.jsonl --report-prefix synthetic_observations_v10_situation_frame_support7
```

Latest Stage 3 candidate preview, generated from `pipeline_quality_v1_v10_ci_reference_guard1`:

```text
source gap rows: 250
review-only SHE draft candidates: 230
candidate with source SR evidence: 229
candidate without source SR evidence: 1
review priority: high 132 / medium 73 / blocked 25
source SR evidence: medium 144 / weak 85 / missing 1
runtime import: not applied
asserted mapping update: 0
```

Stage 3 shadow import experiments, run 2026-05-11:

```text
baseline pipeline_quality_v1_v10_ci_reference_guard1:
  SHE TP/FN/FP 1107/909/82
  Guide mismatch 162, NO_TOP 312, industry_boundary_gap 90, workprocess_mismatch 71
  CI no_action 497, broad_sr_only 16, boundary_mismatch 65

shadow high exact features:
  SHE TP/FN/FP 1109/907/82
  Guide mismatch 161, industry_boundary_gap 89
  CI no_action regressed to 509

shadow high runtime_match_features:
  SHE TP/FN/FP 1108/908/82
  Guide mismatch 158, industry_boundary_gap 85
  CI no_action regressed to 518
  actual 240 failed: status changed 7, ambiguous_over_promoted 7

shadow high runtime_match_features + visual trigger gate:
  SHE TP/FN/FP 1108/908/82
  Guide mismatch 159, industry_boundary_gap 86
  CI no_action 518
  actual 240 failed: status changed 7, ambiguous_over_promoted 7
```

Conclusion: the 230 Stage 3 candidates are useful as ontology/review candidates, but they must not be promoted into runtime `approved_*` SHE patterns yet. Broad runtime parent features such as `MACHINE`, `CHEMICAL_WORK`, and `SCAFFOLD` can change status/penalty decisions. Next work should use these candidates as Guide/CI support signals or taxonomy review queues, not as direct finding-status drivers.

SituationFrame support-only v2, accepted 2026-05-11:

```text
baseline: situation_frame_support7
Python compile: OK
frontend npm run build: OK
synthetic Stage 2~5 v1~v10:
  total samples 2,360
  SHE TP/FN/FP 1107/909/82
  SR TP/FN/FP 1414/270/211
  Guide mismatch 145
  Stage 2~5 NO_TOP 308
  industry_boundary_gap 74
  workprocess_mismatch 70
  broad_sr_overreach 1
  CI no_action 497
  CI context_mismatch 17
  CI broad_sr_only 16
  CI needs_review_used 0
  CI guide_boundary_mismatch 63
v10 smoke:
  SHE recall 100.0%
  SHE false negative 0
  SHE false positive 0
  normal suppression 100.0%
actual response 240:
  status changed 0
  negative_false_positive 10
  positive_missed 2
  ambiguous_over_promoted 5
```

SituationFrame artifact summary:

```text
classified Stage 3 candidates: 230
runtime SHE approved update: 0
asserted mapping update: 0
child contexts: 86
Guide support candidates: 1
support Guide review:
  accept 1
  reject 190
support Guide reject reasons:
  manual_child_guide_boundary 187
  domain_excluded 2
  domain_mismatch 1
classification labels:
  taxonomy_gap 230
  guide_support_only 112
  ambiguous_confirmation 117
  true_new_she 60
  sr_review_needed 98
frame extraction on synthetic v1~v10:
  child_context_available 528
  broad_parent_without_child 241
  guide support hit samples 8
```

`situation_frame_support7` is a conservative runtime layer. It keeps child contexts for Guide/CI support only. Parent contexts such as `MACHINE` and `MATERIAL_HANDLING` remain search expansion signals and cannot create confirmed status, penalty exposure, direct SR evidence, or broad-only Guide/CI results.

## Current Open Work

1. `ci_candidate_promotion_v1` 기준 ontology hard violation/warning은 0건이다. 다음 작업은 consistency repair가 아니라 품질 개선이다.
2. 현장 사진에 맞는 KOSHA Guide가 없을 수 있다는 전제를 유지한다. `NO_TOP 88`은 전부 나쁜 것이 아니며, broad/hot-work Guide로 빈칸을 메우지 않는다.
3. NO_TOP actionability는 `accepted empty top 31`, `source/taxonomy review 57`, `runtime repair candidate 0`으로 분리됐다. 즉시 보정 대상은 소진됐다.
4. 다음 구조적 보강 대상은 `CI no_action 491`, `CI guide_boundary_mismatch 20`이다. `CI broad_sr_only`는 13건에서 0건으로 해소했다.
5. UI/UX와 개발서버 확인은 알고리즘 artifact, ontology TTL, evaluation baseline, reports manifest를 건드리지 않는 범위에서 진행한다.

## Notes

`OHS` is now tracked inside the root `arch-bot` monorepo. Keep using `/mnt/c/project/arch-bot/OHS` as the working path. Do not edit `frontend/node_modules/**` or historical `pictures-json/reports/**` bodies.

## Runtime Guide Guard Summary

Runtime reads local OHS serving artifacts instead of koshaontology working files:

```text
OHS/backend/app/data/guide_domain_profiles.json
OHS/backend/app/data/broad_sr_policy.json
OHS/backend/app/data/guide_photo_matchability.v1.json
OHS/backend/app/data/situation_context_taxonomy.v21.json
OHS/backend/app/data/guide_support_candidates.v21.jsonl
```

The same serving baseline is exported to `koshaontology/ontology/serving-snapshot-ci_candidate_promotion_v1.ttl` only for validation and anomaly discovery. OHS does not query that TTL in the request path; fixes should be made in OHS artifacts, PG/export scripts, or Pipe-B profile generation and then regenerated.

Serving candidate gates:

```text
confidence >= 0.65
review_status in ('candidate', 'asserted')
broad SRs are secondary-only and cannot create standard procedures or legacy fallback results by themselves
needs_review/rejected candidates are excluded from serving
photo_unmatchable Guides cannot be photo-based top standard procedures
scene-specific Guide families require their own required context terms; missing Guide coverage may remain NO_TOP
```

The current accepted OHS runtime baseline is `ci_candidate_promotion_v1`. It keeps `ci_broad_sr_guard4` status/penalty/SHE/SR and Guide/WorkProcess behavior, then changes only a narrow immediate-action CI candidate subset. `ci_candidate_review_v1` has 42 review rows; 17 direct CI/SR pairs are serving `candidate`, 25 remain `needs_review`, `asserted=false` stays fixed, and `ci_sr_mapping` is unchanged. This does not change public API shape, SHE approval, asserted mappings, legal SR evidence, status, or penalty behavior.

Latest validation:

```text
baseline: ci_candidate_promotion_v1
synthetic Stage 2~5 v1~v10: 2,360 samples
Guide mismatch: 5
Stage 2~5 NO_TOP: 88
NO_TOP actionability accepted empty top 31 / source-taxonomy review 57 / runtime repair candidates 0
industry_boundary_gap: 0
workprocess_mismatch: 5
broad_sr_overreach: 0
photo_unmatchable_top_count: 0
followup_only_retained_count: 16
CI no_action: 491
CI context_mismatch: 0
CI broad_sr_only: 0
CI needs_review_used: 0
CI guide_boundary_mismatch: 20
v10 synthetic SHE recall 100.0%, FN 0, FP 0
v1~v10 synthetic SHE smoke recall 100.0%, FN 0, FP 67
actual response 240 status changed 0
negative_false_positive 10
positive_missed 2
ambiguous_over_promoted 5
serving ontology validation PASS
serving ontology hard violations 0
serving ontology warnings 0
accepted photo-actionable role overrides 10
PG guide_usage_profiles sync PASS
PG guide_usage_profiles rows 1,038
PG primary WorkProcess check missing 0 / cross-guide 0
```

Latest tracked summaries and local report references:

```text
docs/status/evaluation-baseline.md
pictures-json/reports-manifest.json
pictures-json/reports/stage2_5_no_top_root_cause_ci_broad_sr_guard4.*
pictures-json/reports/stage2_5_no_top_actionability_ci_broad_sr_guard4.*
pictures-json/reports/pg_guide_usage_profiles_sync_ci_broad_sr_guard4.*
pictures-json/reports/ci_no_action_triage_ci_broad_sr_guard4.*
pictures-json/reports/ci_mapping_review_semantic_ci_broad_sr_guard4.*
pictures-json/reports/ci_sr_mapping_candidate_review_ci_broad_sr_guard4.*
pictures-json/reports/pg_ci_sr_link_candidates_ci_broad_sr_guard4.*
pictures-json/reports/pipeline_quality_v1_v10_ci_candidate_review_v1.*
pictures-json/reports/ci_sr_candidate_promotion_ci_broad_sr_guard4.*
pictures-json/reports/pipeline_quality_v1_v10_ci_candidate_promotion_v1.*
pictures-json/reports/synthetic_observations_v10_ci_candidate_promotion_v1_report_report.*
pictures-json/reports/actual_response_samples_ci_candidate_promotion_v1.*
koshaontology/ontology/serving-validation-report-ci_candidate_promotion_v1.*
koshaontology/ontology/serving-workprocess-alignment-ci_candidate_promotion_v1.*
```

Local/external report bodies referenced by the manifest include the historical `usage_profile11` and support-pass reports, plus the current `ci_candidate_promotion_v1` Stage 2~5, v10 smoke, actual 240 replay, ontology validation, WorkProcess alignment, and the preceding `ci_broad_sr_guard4` CI no-action triage / mapping review / review-only import reports.

CI no-action triage (`ci_no_action_triage_ci_broad_sr_guard4`) splits the 492 no-action cases as follows:

```text
upstream_stage2_3_review 357
ci_mapping_review 63
source_or_taxonomy_review 45
accepted_empty_top 24
runtime_repair_candidate 3
```

Semantic review of the 63 `ci_mapping_review` cases (`ci_mapping_review_semantic_ci_broad_sr_guard4`) shows that only 16 are safe CI-SR/candidate mapping candidates:

```text
guide_selection_mismatch 21
corpus_gap_or_near_analogy 21
true_ci_mapping_candidate 16
safe_or_followup_no_immediate 5
```

The direct runtime tail is small. The next CI work should start with the 16 true CI mapping candidates, while the 42 Guide/corpus-gap rows should be handled through Guide profile/scoring, source/taxonomy review, or accepted no-action policy instead of adding broad CI mappings.

The 16 true candidates were also converted into a CI/SR mapping review table (`ci_sr_mapping_candidate_review_ci_broad_sr_guard4`). This table seeds plausible ChecklistItems such as `CI-AG6-006` for knife/cutting, `CI-BM37-140` for conveyor guarding/emergency stop, `CI-C113-130` for icy walking surfaces, and `CI-P22-027` for dry-cleaning ventilation. It is still review material only; no `ci_sr_mapping` rows were inserted.

The review seeds were imported into `guide_sr_link_candidates` as method `ci_candidate_review_v1`: 42 rows, 19 distinct CI, 19 distinct SR, all `review_status=needs_review` and `asserted=false`. Serving-eligible rows from this method are 0 because `needs_review` candidates are excluded from OHS runtime gates.

Post-import Stage 2~5 validation (`pipeline_quality_v1_v10_ci_candidate_review_v1`) confirmed no serving contamination: total 2,360, Guide mismatch 5, NO_TOP 88, industry boundary gap 0, WorkProcess mismatch 5, CI no_action 492, CI broad_sr_only 0, CI needs_review_used 0, and CI guide_boundary_mismatch 21.

Candidate promotion validation (`ci_candidate_promotion_v1`) promoted only 17 of the 42 review rows to serving `candidate` and kept 25 as `needs_review`. Stage 2~5 v1~v10 stayed stable: Guide mismatch 5, NO_TOP 88, industry boundary gap 0, WorkProcess mismatch 5, CI broad_sr_only 0, CI needs_review_used 0. CI no_action improved 492→491 and CI guide_boundary_mismatch improved 21→20. Actual response 240 stayed status changed 0 with negative_false_positive 10, positive_missed 2, ambiguous_over_promoted 5. v10 SHE smoke stayed recall 100%, FN 0, FP 0. The new ontology snapshot `serving-snapshot-ci_candidate_promotion_v1.ttl` validates with hard 0 / warning 0.

Rejected approaches remain the same: do not broaden status-level hazard/risk text aliases or generic `UNSAFE_TERMS` to chase NO_TOP. Use SituationFrame child contexts, Guide usage profiles, visual triggers, review-only SHE/SR support candidates, and WorkProcess/CI relevance instead.
