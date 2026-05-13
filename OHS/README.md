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
backend/app/data/situation_context_taxonomy.v20.json
backend/app/data/guide_support_candidates.v20.jsonl
```

PostgreSQL의 Guide 보강 후보 테이블:

```text
guide_entity_feature_candidates
guide_sr_link_candidates
guide_visual_trigger_candidates
```

`guide_domain_profiles.json`은 Pipe-B의 1,038개 manual Guide usage profile export를 OHS serving용으로 복사한 파일이다. `broad_sr_policy.json`은 broad SR이 단독으로 표준절차를 만들지 못하도록 제한하는 serving policy다.

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
python scripts/evaluate_synthetic_observations.py --input ../../pictures-json/synthetic_observations_v10.jsonl --report-prefix synthetic_observations_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate --use-declared-industry --penalty-sr-scope she
```

Actual response 240 replay:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python scripts/evaluate_actual_response_samples.py --report-prefix actual_response_samples_ci_wp_relevance8d_profile_tight2_ci_safe_gate --database-note "ci_wp_relevance8d_profile_tight2_ci_safe_gate / no asserted mapping changes"
```

Guide recommendation evaluation:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python scripts/evaluate_synthetic_guide_recommendations.py --report-prefix synthetic_guide_recommendations_v1_v10_usage_profile11
```

Stage 2~5 integrated pipeline quality evaluation:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/evaluate_stage2_5_pipeline_quality.py --report-prefix pipeline_quality_v1_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate --progress-every 250 --photo-baseline-report pictures-json/reports/pipeline_quality_v1_v10_ci_wp_relevance7_profile_tight1.json
```

Current support baseline replay:

```bash
cd /mnt/c/project/arch-bot
OHS/backend/.venv/bin/python OHS/backend/scripts/evaluate_stage2_5_pipeline_quality.py --report-prefix pipeline_quality_v1_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate --progress-every 250 --photo-baseline-report pictures-json/reports/pipeline_quality_v1_v10_ci_wp_relevance7_profile_tight1.json
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

1. `ci_wp_relevance8d_profile_tight2_ci_safe_gate` 기준 NO_TOP 26건은 broad alias/support로 억지 축소하지 말고, exact source Guide가 생기거나 별도 public/customer/animal-safety taxonomy를 만들 때만 재검토한다.
2. 다음 Guide 품질 작업은 `industry_boundary_gap 70`, `CI no_action 438`, `CI guide_boundary_mismatch 48`, `workprocess_mismatch 16`을 기준으로 처리한다.
3. `MACHINE`, `MATERIAL_HANDLING`, `CONSTRUCTION_EQUIP`, `EXCAVATION` 붕괴 케이스는 runtime status가 아니라 Guide support/WorkProcess relevance 후보로만 확장한다.
4. `guide_sr_link_candidates` unique key 충돌 후보를 evidence merge/pre-aggregate한 뒤 candidate table import를 dry-run한다.
5. asserted mapping update는 0으로 유지하고, 중신뢰 후보는 법적 확정 근거처럼 표시하지 않는다.
6. WorkProcess step 품질 점수와 industry alignment 점수를 더 세분화한다.

## Notes

- `OHS`는 root `arch-bot/main` monorepo에서 추적되는 일반 디렉토리다.
- `frontend/node_modules/**`는 vendor 영역이므로 문서 최신화 대상에서 제외한다.
- 현재 product는 PostgreSQL 물질화 조회를 serving path로 사용한다. OWL reasoner는 런타임 필수 의존성이 아니라 배치 검증/운영 분석 도구로 본다.

## Runtime Guide Guard Summary

Runtime reads local OHS serving artifacts instead of koshaontology working files:

```text
OHS/backend/app/data/guide_domain_profiles.json
OHS/backend/app/data/broad_sr_policy.json
OHS/backend/app/data/guide_photo_matchability.v1.json
OHS/backend/app/data/situation_context_taxonomy.v20.json
OHS/backend/app/data/guide_support_candidates.v20.jsonl
```

Serving candidate gates:

```text
confidence >= 0.65
review_status in ('candidate', 'asserted')
broad SRs are secondary-only and cannot create standard procedures or legacy fallback results by themselves
needs_review/rejected candidates are excluded from serving
```

Guide recommendations consume the 1,038 manual Guide usage profiles exported from Pipe-B. Standard procedure scoring is guarded so broad SRs, broad/generic features, and industry alignment cannot create top Guide procedures alone.

The current accepted OHS runtime baseline is `ci_wp_relevance8d_profile_tight2_ci_safe_gate`. Guide recommendations require actionable SHE evidence or conservative SituationFrame child-context support before creating standard procedures/checklist items. Context-only SHE still informs reasoning and status, but it no longer creates top Guide procedures by itself. Photo-top standard procedures are gated by `guide_photo_matchability.v1.json`; measurement/analysis, test, health-screening, risk-method, and document-reference Guides cannot appear as photo-based top procedures. `guide_support_candidates.v20.jsonl` keeps the previously accepted support rows through v19 and adds two narrow support rows for greenhouse-frame fall risk and dry-cleaning exposed steam-pipe burn risk. CI/WP relevance now also tightens selected feature-only overpromotion Guides, reorders primary WorkProcess IDs for concrete photo-actionable Guides, and permits same-top-Guide local CI fallback only when observable violation context is present and non-negated safe-control wording is absent. The safe-cue negation fix remains active, so `LOTO 미적용`, `밀착 미흡`, and `동료 정상 착용과 대비` do not become `status_safe`, while safe procedure contexts such as `압력 게이지 0`, `잔압 완전 방출`, and `방열 장갑 착용` block trigger-only Guide support. `confirmation_required` support may satisfy Guide usage/domain gates only when it is trigger-backed, backed by a non-broad SR, and child-context/profile-aligned. `situation_context_taxonomy.v20.json` has 178 child contexts. This does not change status, penalty, SHE approval, asserted mapping, legal SR evidence, or public API shape.

Latest validation:

```text
baseline: ci_wp_relevance8d_profile_tight2_ci_safe_gate
synthetic Stage 2~5 v1~v10: 2,360 samples
Guide mismatch: 87
Stage 2~5 NO_TOP: 26
industry_boundary_gap: 70
workprocess_mismatch: 16
broad_sr_overreach: 1
photo_unmatchable_top_count: 0
photo_unmatchable_suppressed_count: 13
followup_only_retained_count: 24
top_replaced_by_photo_actionable_count: 17
CI no_action: 438
CI context_mismatch: 16
CI broad_sr_only: 14
CI needs_review_used: 0
CI guide_boundary_mismatch: 48
NO_TOP actionability: runtime repair candidates 0 / outside scope 10 / safe-controlled 7 / corpus gap 3 / reject stale support 2 / follow-up only 2
v10 synthetic SHE recall 100.0%, FN 0, FP 0
actual response 240 status changed 0
negative_false_positive 10
positive_missed 2
ambiguous_over_promoted 5
backend compileall OK
frontend npm run build OK
```

Latest reports:

```text
docs/status/evaluation-baseline.md
pictures-json/reports-manifest.json
```

Local/external report bodies referenced by the manifest include the `usage_profile11` historical baseline, the `situation_frame_support7` artifact set, the `photo_matchability1` audit, previous accepted support reports through `stage3_remaining_gap_support_v20_actionable`, and the current `ci_wp_relevance8d_profile_tight2_ci_safe_gate` Stage 2~5, v10 smoke, and actual 240 replay reports.

Rejected approaches: widening hazard/risk text alias inference at status level changed actual 240 status behavior. Broadly widening `UNSAFE_TERMS` reduced NO_TOP only slightly but regressed Guide mismatch and industry boundary quality. Trigger-only domain override reduced NO_TOP but reintroduced broad SR overreach. Broad Stage 2/3 support builds reduced NO_TOP further but overmatched electrical/cleaning/painting/radiation/permit/welding/solvent contexts; accepted rows keep only narrow support-only trigger evidence and block safe checklist-style contexts. The accepted v8 narrow2 pass removed broad `방사선`, `허가서`, `용접 흄`, and `용제` triggers from the rejected v8 trial. Early v9 trials removed generic `전원을 끄지 않고`, generic medical-waste wording, and `담배꽁초` after semantic review. The first v10 trial removed high-pressure washing/electrical-panel support and tightened food-slicer, elevated-welding, and silica triggers after semantic review. Early v11 trials overmatched PPE-only, generic fall-risk, and generic blocked-visibility wording, so accepted narrow3 requires object-specific triggers. The first v12 trial overmatched safe PPE, high-heat, stair, and electrical-control scenes; accepted narrow4 keeps only unsafe/object-specific trigger terms and drops the EV battery seed that moved one case from CI no-action to CI boundary mismatch. Early v13 trials overmatched broad cold-room wording or over-tightened short-token matching; accepted narrow5 keeps object-specific PPE/control triggers and only blocks the confirmed `P-55-2012` single-character `황` false match. The first v14 trial overmatched `발판 없이`, generic `슬링/인양`, generic `용접 흄`, and generic `보호 장갑 미착용`; accepted narrow6b keeps compound/object-specific triggers. Stage 3 support aliases are accepted only as profile-alignment hints, not extraction aliases. Remaining Guide coverage should be handled through SituationFrame child contexts, usage profiles, visual triggers, review-only SHE/SR support candidates, and WorkProcess relevance.
