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

Accepted runtime baseline: `strict_profile_gate3`.

Previous accepted baseline: `industry_boundary_safe_suppress3`.

This pass keeps the risk/SHE/SR/status/penalty boundary stable and changes only Stage 5 standard-procedure ranking. Broad risk-axis/profile terms such as `화학물질`, `화재`, `폭발`, `고소 작업`, `낙하물`, `피부`, `흡입`, `용제`, and generic domain tags no longer count as strong Guide-specific usage evidence. Strict domain-specific/exclusive Guides now need strong profile evidence or trigger-backed SituationFrame support before they can become top standard procedures.

Report bodies stay local/external under `pictures-json/reports/**`; root git tracks the manifest and summary instead:

- `pictures-json/reports-manifest.json`
- `docs/status/evaluation-baseline.md`

Referenced local report bodies:

- `pictures-json/reports/situation_frame_artifact_build.v2.md`
- `pictures-json/reports/situation_frame_eval_report.v2_child_gate1.md`
- `pictures-json/reports/guide_photo_matchability_audit_v1.md`
- `pictures-json/reports/no_top_guide_support_candidates_v1.md`
- `pictures-json/reports/stage2_no_top_support_candidates_v3.md`
- `pictures-json/reports/stage3_support_alignment_aliases_v2.md`
- `pictures-json/reports/stage2_support_usage_gate_artifacts_v2.md`
- `pictures-json/reports/stage2_taxonomy_gap_support_v15_artifacts_narrow7b.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage2_taxonomy_gap_support_v15_narrow7b.md`
- `pictures-json/reports/actual_response_samples_stage2_taxonomy_gap_support_v15_narrow7b.md`
- `pictures-json/reports/synthetic_observations_v10_stage2_taxonomy_gap_support_v15_narrow7b_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage2_taxonomy_gap_support_v15_narrow7b.md`
- `pictures-json/reports/stage3_remaining_gap_support_v16c_artifacts_narrow8c.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v16c_narrow8c.md`
- `pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v16c_narrow8c.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v16c_narrow8c_report.md`
- `pictures-json/reports/stage3_remaining_gap_support_v17b_artifacts_narrow9b.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v17b_narrow9b.md`
- `pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v17b_narrow9b.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v17b_narrow9b_report.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_safe_cue_negation_fix2.md`
- `pictures-json/reports/actual_response_samples_stage3_safe_cue_negation_fix2.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_safe_cue_negation_fix2_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage3_safe_cue_negation_fix2.md`
- `pictures-json/reports/stage3_remaining_gap_support_v19_artifacts.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v19_dropped_tool.md`
- `pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v19_dropped_tool.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v19_dropped_tool_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v19_dropped_tool.md`
- `pictures-json/reports/stage3_remaining_gap_support_v20_artifacts.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v20_actionable.md`
- `pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v20_actionable.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v20_actionable_report_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v20_actionable.md`
- `pictures-json/reports/stage2_taxonomy_gap_triage_stage3_safe_cue_negation_fix2.md`
- `pictures-json/reports/stage3_remaining_gap_support_v18_artifacts_narrow10.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v18_narrow10.md`
- `pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v18_narrow10.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v18_narrow10_report.md`
- `pictures-json/reports/stage3_sr_gap_support_v14_artifacts_narrow6b.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_sr_gap_support_v14_narrow6b.md`
- `pictures-json/reports/actual_response_samples_stage3_sr_gap_support_v14_narrow6b.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_sr_gap_support_v14_narrow6b_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage3_sr_gap_support_v14_narrow6b.md`
- `pictures-json/reports/stage2_taxonomy_support_v13_artifacts_narrow5.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage2_taxonomy_support_v13_narrow5.md`
- `pictures-json/reports/actual_response_samples_stage2_taxonomy_support_v13_narrow5.md`
- `pictures-json/reports/synthetic_observations_v10_stage2_taxonomy_support_v13_narrow5_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage2_taxonomy_support_v13_narrow5.md`
- `pictures-json/reports/stage3_gap_support_v12_artifacts_narrow4.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_gap_support_v12_narrow4.md`
- `pictures-json/reports/actual_response_samples_stage3_gap_support_v12_narrow4.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_gap_support_v12_narrow4_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage3_gap_support_v12_narrow4.md`
- `pictures-json/reports/stage2_3_support_v11_artifacts_stage2_narrow3.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v11_narrow3.md`
- `pictures-json/reports/actual_response_samples_stage2_3_support_v11_narrow3.md`
- `pictures-json/reports/synthetic_observations_v10_stage2_3_support_v11_narrow3_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v11_narrow3.md`
- `pictures-json/reports/stage2_3_support_v10_artifacts_narrow2.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v10_narrow2.md`
- `pictures-json/reports/actual_response_samples_stage2_3_support_v10_narrow2.md`
- `pictures-json/reports/synthetic_observations_v10_stage2_3_support_v10_narrow2_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v10_narrow2.md`
- `pictures-json/reports/stage2_3_support_v9_artifacts_narrow4.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v9_narrow4.md`
- `pictures-json/reports/actual_response_samples_stage2_3_support_v9_narrow4.md`
- `pictures-json/reports/synthetic_observations_v10_stage2_3_support_v9_narrow4_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v9_narrow4.md`
- `pictures-json/reports/stage2_3_support_v8_artifacts_narrow2.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v8_narrow2.md`
- `pictures-json/reports/actual_response_samples_stage2_3_support_v8_narrow2.md`
- `pictures-json/reports/synthetic_observations_v10_stage2_3_support_v8_narrow2_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v8_narrow2.md`
- `pictures-json/reports/stage2_service_support_v7_artifacts_narrow1.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage2_service_support_v7_narrow1.md`
- `pictures-json/reports/actual_response_samples_stage2_service_support_v7_narrow1.md`
- `pictures-json/reports/synthetic_observations_v10_stage2_service_support_v7_narrow1_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage2_service_support_v7_narrow1.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_domain_support2_confirmation_gate2.md`
- `pictures-json/reports/actual_response_samples_stage3_domain_support2_confirmation_gate2.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_domain_support2_confirmation_gate2_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage3_domain_support2_confirmation_gate2.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_domain_support1_tight1.md`
- `pictures-json/reports/actual_response_samples_stage3_domain_support1_tight1.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_domain_support1_tight1_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage3_domain_support1_tight1.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage2_support_usage_gate2b.md`
- `pictures-json/reports/actual_response_samples_stage2_support_usage_gate2b.md`
- `pictures-json/reports/synthetic_observations_v10_stage2_support_usage_gate2b_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage2_support_usage_gate2b.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage3_support_alias2.md`
- `pictures-json/reports/actual_response_samples_stage3_support_alias2.md`
- `pictures-json/reports/synthetic_observations_v10_stage3_support_alias2_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage3_support_alias2.md`
- `pictures-json/reports/pipeline_quality_v1_v10_stage2_no_top_support3.md`
- `pictures-json/reports/actual_response_samples_stage2_no_top_support3.md`
- `pictures-json/reports/synthetic_observations_v10_stage2_no_top_support3_report.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_stage2_no_top_support3.md`
- `pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile11_20260510_011317.md`
- `pictures-json/reports/synthetic_guide_no_top_queue_usage_profile11_20260510_011333.md`
- `pictures-json/reports/synthetic_observations_v10_usage_profile11_report.md`
- `pictures-json/reports/actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038.md`
- `pictures-json/reports/pipeline_quality_v1_v10_ci_wp_relevance7_profile_tight1.md`
- `pictures-json/reports/stage2_5_no_top_actionability_ci_wp_relevance7_profile_tight1.md`
- `pictures-json/reports/synthetic_observations_v10_ci_wp_relevance7_profile_tight1_report.md`
- `pictures-json/reports/actual_response_samples_ci_wp_relevance7_profile_tight1.md`
- `pictures-json/reports/pipeline_quality_v1_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate.md`
- `pictures-json/reports/synthetic_observations_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate_report.md`
- `pictures-json/reports/actual_response_samples_ci_wp_relevance8d_profile_tight2_ci_safe_gate.md`
- `pictures-json/reports/pipeline_quality_v1_v10_industry_boundary_safe_suppress3.md`
- `pictures-json/reports/industry_boundary_gap_triage_safe_suppress3.md`
- `pictures-json/reports/synthetic_observations_v10_industry_boundary_safe_suppress3_report.md`
- `pictures-json/reports/actual_response_samples_industry_boundary_safe_suppress3.md`
- `pictures-json/reports/pipeline_quality_v1_v10_strict_profile_gate3.md`
- `pictures-json/reports/industry_boundary_gap_triage_strict_profile_gate3.md`
- `pictures-json/reports/synthetic_observations_v10_strict_profile_gate3_report.md`
- `pictures-json/reports/actual_response_samples_strict_profile_gate3.md`

Summary:

```text
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
previous accepted Guide mismatch: 73
Guide mismatch after strict_profile_gate3: 43
Stage 2~5 NO_TOP: 67
industry_boundary_gap: 21
workprocess_mismatch: 21
broad_sr_overreach: 1
photo_unmatchable_top_count: 0
photo_unmatchable_suppressed_count: 0
followup_only_retained_count: 16
top_replaced_by_photo_actionable_count: 0
CI no_action: 480
CI context_mismatch: 14
CI broad_sr_only: 13
CI needs_review_used: 0
CI guide_boundary_mismatch: 31
v10 SHE recall: 100.0%, FN 0, FP 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
SituationFrame classified candidates: 230
SituationFrame child contexts: 178
Guide support candidates v20: 227
NO_TOP support covered cases: Stage3 support 136, curated Stage2 support 20
Stage3 profile-alignment aliases: 18 aliases / 7 child contexts / 15 affected support rows
Stage2 support usage gate: 6 context updates / 2 new support rows / 5 trigger-only rows
Stage3 domain support v6: 3 new support rows for spray painting / dry-cleaning solvent / pesticide application
Stage2 service support v7 narrow1: 2 new support-only contexts for display electrical maintenance and floor cleaning machines
Stage2/3 support v8 narrow2: 6 new support-only contexts for X-ray, blasting, hot-work permit deviation, shipyard/internal welding, soldering, and solvent-waste fire
Stage2/3 support v9 narrow4: 5 new support-only contexts for sports-facility slip/trip, powered cardio-equipment maintenance, needlestick/sharps disposal, blood-contaminated waste handling, and flammable-chemical smoking
Stage2/3 support v10 narrow2: 6 new support-only contexts for powered food-slicer cleaning, bakery oven/hot-tray burn, small-server electrical overload, elevated welding fall control, automotive tire-wheel service, and silica-dust blasting
Stage2/3 support v11 narrow3: 5 new support-only contexts for sharp glass manual handling, lead-paint grinding dust, ice-pick fragment eye exposure, climbing-wall fall surface, and chair-stack manual carry
Stage3 gap support v12 narrow4: 13 new support-only contexts for laser PPE gap, high-pressure wash/electrical panel, process dust respirator gap, underground live cable excavation, acid etching, cold-storage electrical panel moisture, air-impact fragment eye exposure, heat stress, compressed-air hose whip, icy cold-storage floor, box carrying on stairs, high-temperature dyeing, and steam iron burn/trip
Stage2 taxonomy support v13 narrow5: 7 new support-only contexts for high-pressure waterjet PPE, UV lamp eye PPE, UV coating ozone respirator, formalin contact PPE, cold-room PPE, crematorium hot-surface PPE, and sharp-fragment hand PPE
Stage3 SR gap support v14 narrow6b: 13 new support-only contexts for welding fume PPE, sharp metal edge handling, reflow oven residual heat, FOUP stair carrying, excavator slope/signal, confined tank attendant, ship heavy-lift sling inspection, vehicle exposed wiring, scalding tank fall/burn, binding machine jam/hotmelt, and plate-making chemical/UV PPE
remaining NO_TOP root cause: stage2_taxonomy 14 / situation_frame_child_context_gap 5 / stage3_she_to_sr_gap 2 / stage3_she_gap_but_sr_available 1 / fixture_or_safe_controlled_positive 2
NO_TOP actionability: runtime repair candidates 0 / outside scope 10 / safe-controlled 7 / corpus gap 3 / reject stale support 2 / follow-up only 2
Guide photo_matchability: 637 actionable / 36 follow-up / 365 unmatchable
backend compileall: OK
frontend build: OK
```

Important implementation note: broadening `hazard_normalizer`/`hazard_rule_engine` with extra text aliases improved some NO_TOP coverage but changed actual 240 status counts, so that approach was rejected. A separate broad `UNSAFE_TERMS` widening experiment reduced NO_TOP only slightly while regressing Guide mismatch. Broad Stage 2/3 support attempts reduced NO_TOP more aggressively but caused Guide overreach; accepted support rows still require specific trigger hits. The rejected v8 trial overmatched broad `방사선`, `허가서`, `용접 흄`, and `용제` wording, while accepted `narrow2` keeps only specific unsafe/context phrases. Early v9 trials overmatched generic `전원을 끄지 않고`, generic medical-waste wording, and `담배꽁초`; accepted `narrow4` keeps only child-context plus unsafe/observable trigger matches. The first v10 trial overmatched high-pressure washing/electrical-panel and safe elevated-welding scenes, so accepted `narrow2` removes that seed and tightens food-slicer, elevated-welding, and silica triggers. Early v11 trials overmatched PPE-only, generic fall-risk, and generic blocked-visibility wording, so accepted `narrow3` requires object-specific triggers. The first v12 trial overmatched safe PPE, high-heat, stair, and electrical-control scenes, so accepted `narrow4` keeps only unsafe/object-specific trigger terms and drops the EV battery seed that moved one case from CI no-action to CI boundary mismatch. Early v13 trials overmatched broad cold-room wording or over-tightened short-token matching; accepted `narrow5` keeps object-specific PPE triggers and only blocks the confirmed `P-55-2012` single-character `황` false match. The first v14 trial overmatched short terms such as `발판 없이`, generic `슬링/인양`, generic `용접 흄`, and generic `보호 장갑 미착용`; accepted `narrow6b` keeps compound/object-specific triggers and rejects stale reflow support rows. Remaining coverage work should update SituationFrame child contexts, Guide usage profiles, visual triggers, SHE/SR review candidates, and WorkProcess relevance, not status-level risk inference.

Earlier `v10fix6`, `domain_guard2`, `usage_profile1/2/5/11`, `situation_frame_support3`, `situation_frame_support7`, `photo_matchability1`, `no_top_support1`, `no_top_support_signal1`, `no_top_support_signal3`, `stage2_no_top_support3`, `stage3_support_alias2`, `stage2_support_usage_gate2b`, `stage2_support_usage_gate3_safe_lock1`, `stage3_domain_support1_tight1`, `stage3_domain_support2_confirmation_gate2`, `stage2_service_support_v7_narrow1`, `stage2_3_support_v8_narrow2`, `stage2_3_support_v9_narrow4`, `stage2_3_support_v10_narrow2`, `stage2_3_support_v11_narrow3`, `stage3_gap_support_v12_narrow4`, `stage2_taxonomy_support_v13_narrow5`, `stage3_sr_gap_support_v14_narrow6b`, `stage2_taxonomy_gap_support_v15_narrow7b`, `stage3_remaining_gap_support_v16c_narrow8c`, `stage3_remaining_gap_support_v17b_narrow9b`, `stage3_remaining_gap_support_v18_narrow10`, `stage3_safe_cue_negation_fix2`, `stage3_remaining_gap_support_v19_dropped_tool`, `stage3_remaining_gap_support_v20_actionable`, `ci_wp_relevance6_x41_profile`, `ci_wp_relevance7_profile_tight1`, and `ci_wp_relevance8d_profile_tight2_ci_safe_gate`, `industry_boundary_safe_suppress3` results are historical milestones. Treat `strict_profile_gate3` as the current product baseline unless a newer accepted evaluation is recorded in `docs/status/evaluation-baseline.md`.
