# arch-bot

`arch-bot` is the top-level planning and coordination repository for the ontology-based KOSHA workplace-risk assistant.

The service goal is:

> When a business owner uploads a workplace photo, the system identifies visible risk factors, recommends corrective actions, and explains possible penalty paths if the risk is not corrected.

## Repository Role

This repository is the root monorepo for the ontology-based KOSHA workplace-risk assistant on `main`.

The project-owned implementation repositories are imported as ordinary root directories:

| Area | Repository |
|---|---|
| Ontology and extraction pipelines | <https://github.com/jinbless/koshaontology> |
| Backend/frontend service | <https://github.com/jinbless/OHS> |
| Legal source dependency | <https://github.com/legalize-kr/legalize-kr> |

`legalize-kr` remains an external local sibling dependency and is not imported or pushed by this project.

## Monorepo Snapshot Baseline

The project has moved to a root-level monorepo operating model on `main`. The original GitHub repositories preserve child history; root `arch-bot` records the imported baseline commits as provenance.

Current decisions:

- `koshaontology` imported baseline: `60d025ee873e071faf9c90cc0b1a89b05c4812bd`.
- `OHS` imported baseline: `7eed7280e1ece9fa7bb32beb182017f5cfa96f5a`.
- `legalize-kr` is an external source dependency and remains ignored by root git.
- `kosha-guides/parsed/**` and `kosha-guides/manifest/**` are tracked as selected data assets.
- `pictures-json/reports/**` remains external/local; root tracks `pictures-json/reports-manifest.json` and `docs/status/evaluation-baseline.md`.

See:

- `MONOREPO_TRANSITION_PLAN.md`
- `DATA_GOVERNANCE.md`
- `repositories.md`
- `docs/architecture/source-provenance.md`

## Data And Provenance Baseline

Data policy is selective tracking plus external/LFS for large artifacts:

- Track root docs, synthetic observation JSONL files, accepted serving artifacts, `kosha-guides/parsed/**`, `kosha-guides/manifest/**`, and lightweight report/provenance manifests.
- Keep raw KOSHA PDFs and `pictures-json/reports/**` report bodies outside normal git history or behind LFS/manifest references.
- Treat manifest data as the operating source for provenance export.

The ontology design now includes a source/provenance and serving-validation layer using W3C PROV-O, DCAT, DCTERMS, and SHACL/SPARQL-style checks. This layer stays separate from the main domain flow and is used for audit/debug/rebuild, not runtime scoring.

Current serving validation snapshot:

- baseline: `ci_unrelated_action_filter1`
- export: `koshaontology/ontology/serving-snapshot-ci_unrelated_action_filter1.ttl`
- policy ontology: `koshaontology/ontology/serving-policy.ttl`
- validation shapes: `koshaontology/ontology/serving-validation-shapes.ttl`
- validation report: `koshaontology/ontology/serving-validation-report-ci_unrelated_action_filter1.*`
- WorkProcess alignment report: `koshaontology/ontology/serving-workprocess-alignment-ci_unrelated_action_filter1.*`

The snapshot is regenerated from OHS serving artifacts and evaluation reports. Do not hand-edit generated TTL to fix data; fix the source JSON/PG/export script, then regenerate.

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
6. `docs/status/evaluation-baseline.md`
7. `WORKPLAN_LLM_DOMAIN_GUARD.md`
8. `온톨로지_통합구조_및_흐름도.md`
9. `OHS/README.md`
10. `koshaontology/pipe-A/status_pipea.md`, `koshaontology/pipe-B/status_pipeb.md`, `koshaontology/pipe-C/status_pipec.md`

## Key Documents

- `NEXT_SESSION_INSTRUCTIONS.md`
- `MONOREPO_TRANSITION_PLAN.md`
- `DATA_GOVERNANCE.md`
- `repositories.md`
- `docs/architecture/source-provenance.md`
- `docs/status/evaluation-baseline.md`
- `kosha-guides/manifest/guides-manifest.json`
- `pictures-json/reports-manifest.json`
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

## Current Evaluation Baseline

Accepted runtime baseline: `ci_unrelated_action_filter1`.

Previous accepted baseline: `ci_preferred_guide_ci1`.

This pass keeps the risk/SHE/SR/status/penalty boundary stable and keeps the top standard-procedure Guide boundary stable. It changes only Stage 5 immediate-action filtering: generic CI rows from unrelated Guides are suppressed when selected top-Guide CI or direct SHE checklist-cue evidence exists. It does not write asserted legal mappings or `ci_sr_mapping`.

Report bodies stay local/external under `pictures-json/reports/**`; root git tracks the manifest and summary instead:

- `pictures-json/reports-manifest.json`
- `docs/status/evaluation-baseline.md`

Referenced current local report bodies:

- `pictures-json/reports/pipeline_quality_v1_v10_ci_unrelated_action_filter1.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_ci_broad_sr_guard4.md`
- `pictures-json/reports/stage2_5_no_top_actionability_ci_broad_sr_guard4.md`
- `pictures-json/reports/synthetic_observations_v10_ci_unrelated_action_filter1_report_report.md`
- `pictures-json/reports/actual_response_samples_ci_unrelated_action_filter1.md`
- `pictures-json/reports/ci_boundary_mismatch_triage_ci_unrelated_action_filter1.md`
- `pictures-json/reports/pg_guide_usage_profiles_sync_ci_broad_sr_guard4.md`
- `pictures-json/reports/ci_sr_candidate_promotion_ci_broad_sr_guard4.md`
- `pictures-json/reports/ci_no_action_triage_ci_unrelated_action_filter1_current.md`
- `pictures-json/reports/ci_sr_mapping_candidate_review_ci_unrelated_action_filter1_current.md`
- `pictures-json/reports/pg_ci_sr_link_candidates_ci_unrelated_action_filter1_current_apply.md`
- `pictures-json/reports/ci_sr_candidate_promotion_ci_unrelated_action_filter1_current.md`
- `pictures-json/reports/pipeline_quality_v1_v10_ci_candidate_review_current_pg.md`
- `koshaontology/ontology/serving-validation-report-ci_unrelated_action_filter1.*`
- `koshaontology/ontology/serving-workprocess-alignment-ci_unrelated_action_filter1.*`

Summary:

```text
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5
Stage 2~5 NO_TOP: 88
NO_TOP actionability: accepted empty top 31 / source-taxonomy review 57 / runtime repair candidates 0
industry_boundary_gap: 0
workprocess_mismatch: 5
broad_sr_overreach: 0
photo_unmatchable_top_count: 0
followup_only_retained_count: 16
CI no_action: 494
CI context_mismatch: 0
CI broad_sr_only: 0
CI needs_review_used: 0
CI guide_boundary_mismatch: 2
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
serving ontology validation: PASS, hard violations 0, warnings 0
accepted photo-actionable role overrides: 10
```

Serving validation snapshot:

```text
snapshot: koshaontology/ontology/serving-snapshot-ci_unrelated_action_filter1.ttl
validation report: koshaontology/ontology/serving-validation-report-ci_unrelated_action_filter1.*
WorkProcess alignment report: koshaontology/ontology/serving-workprocess-alignment-ci_unrelated_action_filter1.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
PG guide_usage_profiles sync: PASS, 1,038 rows
PG primary WorkProcess check: missing 0 / cross-guide 0
```

Implementation note: `ci_unrelated_action_filter1` keeps the `ci_preferred_guide_ci1` status/penalty/SHE/SR, Guide/WorkProcess, and top standard-procedure boundary. It changes only final immediate-action filtering after preferred top-Guide CI ordering: direct SHE checklist cues remain eligible, selected top-Guide CIs remain eligible, and generic CIs from unrelated Guides are suppressed. CI guide-boundary mismatch improves `8 -> 2`; CI no_action changes `491 -> 494`; CI broad_sr_only and needs_review leaks remain `0`. A stricter primary-Guide-only trial was rejected because it reduced mismatch to `0` but regressed CI no_action to `551`.

NO_TOP interpretation: `NO_TOP` is not automatically a defect. Current audit splits 88 cases into 31 accepted empty-top cases and 57 source/taxonomy review cases. Runtime repair candidates are 0; do not reduce the remaining 88 with broad aliases or generic Guide fallback. The remaining CI guide-boundary mismatch tail is now 2 cases and should be handled as source/profile/taxonomy review, not broad action fallback.

PG candidate review refresh on 2026-05-16: `ci_candidate_review_v1` now has 50 review rows in `guide_sr_link_candidates`; 17 are serving `candidate`, 33 remain `needs_review`, all are `asserted=false`, and `ci_sr_mapping` inserts remain 0. Verification report `pipeline_quality_v1_v10_ci_candidate_review_current_pg` preserves the accepted metrics exactly: Guide mismatch 5, NO_TOP 88, CI no_action 494, CI guide-boundary mismatch 2, CI needs_review_used 0.
