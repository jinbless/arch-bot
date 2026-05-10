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

Accepted runtime baseline: `usage_profile11`.

This pass keeps the risk/SHE status boundary stable and moves the extra guard to Guide recommendation. Standard procedures and immediate checklist items now use actionable SHE matches as direct recommendation evidence; context-only/non-actionable SHE matches no longer create Guide procedures by themselves.

Report bodies stay local/external under `pictures-json/reports/**`; root git tracks the manifest and summary instead:

- `pictures-json/reports-manifest.json`
- `docs/status/evaluation-baseline.md`

Referenced local report bodies:

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

Earlier `v10fix6`, `domain_guard2`, and `usage_profile1/2/5` results are historical milestones. Treat `usage_profile11` as the only current product baseline unless a newer accepted evaluation is recorded in `docs/status/evaluation-baseline.md`.
