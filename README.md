# arch-bot

`arch-bot` is the top-level planning and coordination repository for the ontology-based KOSHA workplace-risk assistant.

The service goal is:

> When a business owner uploads a workplace photo, the system identifies visible risk factors, recommends corrective actions, and explains possible penalty paths if the risk is not corrected.

## Repository Role

This repository is a meta repository. It keeps the current design documents, decision logs, evaluation summaries, and synthetic observation testsets.

The implementation repositories remain separate:

| Area | Repository |
|---|---|
| Ontology and extraction pipelines | <https://github.com/jinbless/koshaontology> |
| Backend/frontend service | <https://github.com/jinbless/OHS> |
| Legal source dependency | <https://github.com/legalize-kr/legalize-kr> |

The local workspace also contains those repositories as child directories. They have their own git histories, so check status separately inside `OHS/`, `koshaontology/`, and `legalize-kr/`.

## Monorepo Transition Baseline

The project is moving toward a root-level monorepo operating model, but physical repository import has not happened yet. The current baseline keeps the sibling layout and records pushed commits before any future snapshot import.

Current decisions:

- `koshaontology` and `OHS` are project-owned and are pushed to their existing GitHub repositories before root documentation is pushed.
- `legalize-kr` is an external source dependency and is not a push target for this project.
- Root `arch-bot` remains the main article and coordination repository until a future snapshot import.
- Future monorepo import should use snapshot import by default; historical traceability remains in the original GitHub repositories.
- `kosha-guides` and `pictures-json` are root-level project data assets, but only selected data should be tracked directly.

See:

- `MONOREPO_TRANSITION_PLAN.md`
- `DATA_GOVERNANCE.md`
- `repositories.md`
- `docs/architecture/source-provenance.md`

## Data And Provenance Baseline

Data policy is selective tracking plus external/LFS for large artifacts:

- Track root docs, synthetic observation JSONL files, selected accepted reports, accepted serving artifacts, future `kosha-guides/parsed/**`, and future `kosha-guides/manifest/**`.
- Keep raw KOSHA PDFs and old `pictures-json/reports/**` outside normal git history or behind LFS/manifest references.
- Treat manifest data as the operating source for provenance export.

The ontology design now includes a planned source/provenance layer using W3C PROV-O, DCAT, DCTERMS, and SHACL. This layer stays separate from the main domain flow and is used for audit/debug/rebuild, not runtime scoring.

## Current Design Baseline

- `risk:` is the shared abstraction layer for risk knowledge.
- `haz:`, `agent:`, and `ctx:` provide concrete risk-feature vocabularies under `risk:RiskFeature`.
- `she:` models reusable situational hazard patterns, not per-photo events.
- `KOSHA Guide / WorkProcess` is the center of standard corrective procedures.
- `ChecklistItem` is used for immediate actions, visual cues, search indexing, and supporting evidence.
- `PenaltyPath` presents three business-facing penalty routes:
  - general violation or general incident
  - death
  - serious accident
- Runtime serving uses materialized triples/search results rather than requiring an OWL reasoner in the request path.
- The LLM extracts visible observations and visual cues. It does not choose laws or penalties directly.
- PostgreSQL materialized tables are the serving path. OWL/RDFS reasoning remains useful for batch enrichment, consistency checks, and operation-side root-cause analysis.

## Current Product Implementation

`OHS` has been refactored toward the current ontology flow:

```text
photo/text input
→ observations and visual cues
→ risk:RiskFeature normalization
→ she:SituationalHazardPattern matching
→ SR / Article / Guide / CI / PenaltyPath lookup
→ business-owner result screen
```

Backend responsibilities are split into smaller services:

- `analysis_service.py`: OpenAI-facing entrypoint and compatibility wrapper
- `analysis_pipeline.py`: analysis orchestration
- `risk_rule_service.py`, `sr_lookup_service.py`, `guide_recommendation_service.py`, `penalty_path_service.py`: domain-specific stages
- `she_matcher.py` + `she_match_models.py`: SHE matching and DTOs

Frontend result panels now follow the product structure:

- risk summary
- immediate actions
- standard guide procedures
- three penalty paths
- reasoning trace

See `OHS/README.md` for product run and verification instructions.

## Next Session

Start with `NEXT_SESSION_INSTRUCTIONS.md`, `README.md`, and the monorepo governance docs. They list the active domain-guard workstream, the current validation baseline, and the repository/data operating rules.

Recommended first read order:

1. `NEXT_SESSION_INSTRUCTIONS.md`
2. `README.md`
3. `MONOREPO_TRANSITION_PLAN.md`
4. `DATA_GOVERNANCE.md`
5. `repositories.md`
6. `WORKPLAN_LLM_DOMAIN_GUARD.md`
7. `온톨로지_통합구조_및_흐름도.md`
8. `OHS/README.md`
9. `koshaontology/pipe-A/status_pipea.md`, `koshaontology/pipe-B/status_pipeb.md`, `koshaontology/pipe-C/status_pipec.md`

## Key Documents

- `NEXT_SESSION_INSTRUCTIONS.md`
- `MONOREPO_TRANSITION_PLAN.md`
- `DATA_GOVERNANCE.md`
- `repositories.md`
- `docs/architecture/source-provenance.md`
- `WORKPLAN_LLM_DOMAIN_GUARD.md`
- `온톨로지_통합구조_및_흐름도.md`
- `온톨로지_법령레이어_상세도.md`
- `온톨로지_SR레이어_상세도.md`
- `온톨로지_위험상황레이어_상세도.md`
- `온톨로지_가이드레이어_상세도.md`
- `온톨로지_벌칙레이어_상세도.md`
- `needToChangeCode.md`
- `PROJECT_CLEANUP_LOG.md`
- `최종보고서_온톨로지_AI시스템_핵심요약.md`
- `OHS/README.md`
- `koshaontology/pipe-A/status_pipea.md`
- `koshaontology/pipe-B/status_pipeb.md`
- `koshaontology/pipe-C/status_pipec.md`

## Latest Synthetic Evaluation

Latest aggregate report before the OHS product refactor:

- `pictures-json/reports/synthetic_observations_v1_v10_v10fix6_confusion_matrix.md`

Summary:

```text
v1~v10 total cases: 2360
SHE TP/FN/FP/TN: 2016/0/67/277
SHE recall: 100.0%
SHE precision: 96.8%
SHE specificity: 80.5%
normal suppression: 276/276 (100.0%)
```

The remaining priority is not SHE recall. It is the boundary between confirmed risk and confirmation-needed candidate results.

Latest domain-guard smoke reports:

- `pictures-json/reports/synthetic_observations_v10_domain_guard2_report.md`
- `pictures-json/reports/actual_response_samples_v1_v10_domain_guard2_vs_pipeb1038.md`

Summary:

```text
v10 cases: 330
SHE recall: 100.0%
SHE false negative: 0
SHE false positive: 0
normal suppression: 100.0%
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
A-G-18 top procedure: 51 -> 3
G-116 top procedure: 5 -> 0
A-G-10 top procedure: 14 -> 3
```

The current product task is therefore not raw SHE recall. The priority is improving Guide/WorkProcess domain alignment while preserving status and penalty boundaries.

## Latest Broad SR / Manual Domain Guard Runtime

The 1,038 manual Guide domain profiles are now exported as OHS serving artifacts, while asserted mapping tables remain untouched. OHS serving uses `confidence >= 0.65` plus `review_status in ('candidate', 'asserted')`; broad SRs are secondary-only.

Latest reports:

- `koshaontology/pipe-B/data/manual-enrichment-domain-guard-import-preview.md`
- `koshaontology/pipe-B/data/manual-enrichment-domain-guard-review-queues.md`
- `pictures-json/reports/synthetic_observations_v10_domain_guard_broad_sr_policy_report.md`
- `pictures-json/reports/actual_response_samples_v1_v10_domain_guard1_vs_pipeb1038_broad_sr_policy.md`
- `pictures-json/reports/actual_response_samples_v1_v10_domain_guard1_vs_pipeb1038_broad_sr_policy_watch_summary.md`

Validation summary: v10 SHE recall 100%, FN 0, FP 0; actual response 240 status changed 0; A-G-18 top procedure 33 -> 3 and remaining cases are all 항만 하역업.

## Latest Synthetic Guide Recommendation Evaluation

New Guide-specific evaluator:

- `OHS/backend/scripts/evaluate_synthetic_guide_recommendations.py`

Latest reports:

- `pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile1_20260509_230048.md`
- `pictures-json/reports/synthetic_observations_v10_usage_profile1_report.md`
- `pictures-json/reports/actual_response_samples_v1_v10_usage_profile1_vs_pipeb1038.md`

Summary:

```text
synthetic Guide v1~v10 total: 2,360
legacy obvious top Guide mismatch: 1,149
current obvious top Guide mismatch: 533
reduction: 53.61%
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
v10 SHE recall: 100.0%, FN 0, FP 0
```

The main remaining work is structural Guide usage-profile repair, not keyword expansion: `industry_boundary_gap`, `missing_usage_profile`, and `workprocess_mismatch` queues now identify the next data corrections.

### Usage Profile Attention Correction v2

First structural repair pass completed for 8 overexposed Guides: `B-E-3`, `C-C-16`, `A-G-1`, `B-M-32`, `G-32`, `A-G-15`, `C-C-92`, `C-18`. Runtime now prefers manual 1,038 Guide profiles before legacy hardcoded rules, blocks exclusive Guide feature-only promotion, treats `ELECTRICAL_WORK` as broad/generic for domain matching, and requires explicit context for `management_program` Guides.

Latest reports:

- `pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile2_20260509_233015.md`
- `pictures-json/reports/synthetic_observations_v10_usage_profile2_report.md`
- `pictures-json/reports/actual_response_samples_v1_v10_usage_profile2_vs_pipeb1038.md`

Summary:

```text
synthetic Guide v1~v10 total: 2,360
legacy obvious top Guide mismatch: 1,150
current obvious top Guide mismatch: 361
reduction: 68.61%
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
v10 SHE recall: 100.0%, FN 0, FP 0
backend compileall: OK
frontend build: OK
```

Next structural queues: `NO_TOP`/`missing_usage_profile` 367 separation, remaining overexposed Guides (`A-G-12`, `A-G-9`, `C-70`, `H-100`, `A-R-2`, `H-187`, `A-G-14`, `E-M-4`), and WorkProcess mismatch (`D-C-7`, `E-G-22`, `H-116`, `M-62`).

### Usage Profile Correction v3/v5

Second structural repair pass completed. OHS now treats industry alignment as a supplemental signal only; `exclusive` and `domain_specific` Guide profiles need Guide-specific term/context evidence before they can become top standard procedures. The manual batch profiles were tightened for the previous overexposure set: `A-G-12`, `A-G-9`, `C-70`, `H-100`, `A-R-2`, `H-187`, `A-G-14`, `E-G-22`, `H-116`, `M-62`, `D-C-7`.

Latest reports:

- `pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile5_20260510_000306.md`
- `pictures-json/reports/synthetic_guide_no_top_queue_usage_profile5_20260510_000435.md`
- `pictures-json/reports/synthetic_observations_v10_usage_profile5_report.md`
- `pictures-json/reports/actual_response_samples_v1_v10_usage_profile5_vs_pipeb1038.md`

Summary:

```text
synthetic Guide v1~v10 total: 2,360
legacy obvious top Guide mismatch: 1,151
current obvious top Guide mismatch: 220
reduction: 80.89%
v10 SHE recall: 100.0%, FN 0, FP 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
backend compileall: OK
frontend build: OK
```

Remaining work is coverage recovery, not keyword stuffing: `NO_TOP` 404 has been split into taxonomy/profile gaps and `synthetic_fixture_gap` 72.

### Usage Profile v11: Actionable SHE Guide Gate

Latest accepted baseline: `usage_profile11`.

This pass keeps the risk/SHE status boundary stable and moves the extra guard to Guide recommendation. Standard procedures and immediate checklist items now use actionable SHE matches as direct recommendation evidence; context-only/non-actionable SHE matches no longer create Guide procedures by themselves.

Latest reports:

- `pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile11_20260510_011317.md`
- `pictures-json/reports/synthetic_guide_no_top_queue_usage_profile11_20260510_011333.md`
- `pictures-json/reports/synthetic_observations_v10_usage_profile11_report.md`
- `pictures-json/reports/actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038.md`

Summary:

```text
synthetic Guide v1~v10 total: 2,360
legacy obvious top Guide mismatch: 1,145
current obvious top Guide mismatch: 165
reduction: 85.59%
NO_TOP: 395
v10 SHE recall: 100.0%, FN 0, FP 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
backend compileall: OK
frontend build: OK
```

Important implementation note: broadening `hazard_normalizer`/`hazard_rule_engine` with extra text aliases improved some NO_TOP coverage but changed actual 240 status counts, so that approach was rejected. Remaining coverage work should update Guide usage profiles and WorkProcess relevance, not status-level risk inference.
