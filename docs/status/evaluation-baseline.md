# Evaluation Baseline

Latest updated: 2026-05-15

Accepted runtime baseline: `ci_unrelated_action_filter1`

Previous accepted baseline: `ci_preferred_guide_ci1`

The full report bodies under `pictures-json/reports/**` are local/external artifacts. Root git tracks `pictures-json/reports-manifest.json` and this summary instead of adding historical report files to repository history.

## CI Unrelated Action Filter 1

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_ci_unrelated_action_filter1.*
pictures-json/reports/synthetic_observations_v10_ci_unrelated_action_filter1_report_report.*
pictures-json/reports/actual_response_samples_ci_unrelated_action_filter1.*
pictures-json/reports/ci_boundary_mismatch_triage_ci_unrelated_action_filter1.*
koshaontology/ontology/serving-snapshot-ci_unrelated_action_filter1.ttl
koshaontology/ontology/serving-validation-report-ci_unrelated_action_filter1.*
koshaontology/ontology/serving-workprocess-alignment-ci_unrelated_action_filter1.*
```

Summary:

```text
previous accepted baseline: ci_preferred_guide_ci1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5 -> 5
NO_TOP: 88 -> 88
industry_boundary_gap: 0 -> 0
workprocess_mismatch: 5 -> 5
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 16
CI no_action: 491 -> 494
CI context_mismatch: 0 -> 0
CI broad_sr_only: 0 -> 0
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 8 -> 2
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: this pass keeps status/penalty/SHE/SR, Guide top selection, NO_TOP, WorkProcess, photo policy, and ontology validation stable. It only changes immediate-action filtering after preferred top-Guide CI ordering: direct SHE checklist cues stay eligible, selected top-Guide CIs stay eligible, and generic CIs from unrelated Guides are suppressed. This reduces `CI guide_boundary_mismatch` from 8 to 2, with a small `CI no_action` increase from 491 to 494. The stricter primary-Guide-only trial was rejected because it reduced mismatch to 0 but regressed CI no_action to 551.

Residual `CI guide_boundary_mismatch` triage:

```text
total: 2
top Guide source_ci_ids present: 0
top Guide source_ci_ids absent: 2
top_guide_local_ci_gap: 1
guide_or_source_gap: 1
remaining top Guides: E-13, C-54
remaining top action source Guides: H-115, H-117
```

Interpretation: the remaining 2 cases are source/profile/taxonomy review tails, not broad alias candidates. Do not solve them by allowing unrelated generic CI fallback.

## CI Preferred Guide CI1

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_ci_preferred_guide_ci1.*
pictures-json/reports/synthetic_observations_v10_ci_preferred_guide_ci1_report_report.*
pictures-json/reports/actual_response_samples_ci_preferred_guide_ci1.*
pictures-json/reports/ci_boundary_mismatch_triage_ci_candidate_promotion_v1.*
koshaontology/ontology/serving-snapshot-ci_preferred_guide_ci1.ttl
koshaontology/ontology/serving-validation-report-ci_preferred_guide_ci1.*
koshaontology/ontology/serving-workprocess-alignment-ci_preferred_guide_ci1.*
```

Summary:

```text
previous accepted baseline: ci_candidate_promotion_v1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5 -> 5
NO_TOP: 88 -> 88
industry_boundary_gap: 0 -> 0
workprocess_mismatch: 5 -> 5
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 16
CI no_action: 491 -> 491
CI context_mismatch: 0 -> 0
CI broad_sr_only: 0 -> 0
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 20 -> 8
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: this pass keeps status/penalty/SHE/SR, Guide top selection, NO_TOP, WorkProcess, photo policy, and ontology validation stable. It only changes immediate-action ordering: when the top standard-procedure Guide already has context-matched local CI candidates, those CIs are preferred over generic CI rows from unrelated Guides. This reduces `CI guide_boundary_mismatch` from 20 to 8 without increasing `CI no_action` or allowing broad-SR/needs-review leaks.

## CI Candidate Promotion v1

Source reports:

```text
pictures-json/reports/ci_sr_candidate_promotion_ci_broad_sr_guard4.*
pictures-json/reports/pipeline_quality_v1_v10_ci_candidate_promotion_v1.*
pictures-json/reports/synthetic_observations_v10_ci_candidate_promotion_v1_report_report.*
pictures-json/reports/actual_response_samples_ci_candidate_promotion_v1.*
pictures-json/reports/ci_boundary_mismatch_triage_ci_candidate_promotion_v1.*
koshaontology/ontology/serving-snapshot-ci_candidate_promotion_v1.ttl
koshaontology/ontology/serving-validation-report-ci_candidate_promotion_v1.*
koshaontology/ontology/serving-workprocess-alignment-ci_candidate_promotion_v1.*
```

Summary:

```text
previous accepted baseline: ci_broad_sr_guard4
candidate review method: ci_candidate_review_v1
review rows: 42
serving candidate rows: 17
kept needs_review rows: 25
asserted mapping update: 0
ci_sr_mapping update: 0
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5 -> 5
NO_TOP: 88 -> 88
industry_boundary_gap: 0 -> 0
workprocess_mismatch: 5 -> 5
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 16
CI no_action: 492 -> 491
CI context_mismatch: 0 -> 0
CI broad_sr_only: 0 -> 0
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 21 -> 20
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: this pass accepts the smallest safe part of the CI no-action mapping review queue. It promotes only direct, reviewed CI/SR pairs such as conveyor guarding, hot-work fire prevention, winter ice slip control, dry-cleaning ventilation, and ergonomic standing-work controls. Broad/generic PPE, near-analogy SRs, and weak corpus-gap rows remain `needs_review`. The runtime still blocks `needs_review/rejected` candidates, broad SR-only top actions, and asserted legal mapping changes.

Residual `CI guide_boundary_mismatch` triage:

```text
total: 20
top Guide source_ci_ids present: 6
top Guide source_ci_ids absent: 14
top_guide_local_ci_gap: 6
preferred_guide_ci_rank_gap: 5
source_or_taxonomy_gap: 4
ambiguous_or_source_gap: 3
guide_or_source_gap: 2
top action source Guide category: industry_boundary_gap 19, broad_sr_overreach 1
```

Interpretation: the remaining 20 cases are not broad alias candidates. In all 20, the top standard-procedure Guide is currently evaluated as acceptable, but the first immediate-action CI comes from a different Guide. The next safe repair is therefore CI/WorkProcess relevance, not risk-feature alias expansion: first prefer existing top-Guide `source_ci_ids` where they already exist, then review local CI support for Guides such as `B-M-36`, `D-C-7`, `G-11`, `A-G-18`, `G-67`, `E-13`, and `P-76`.

## CI Broad SR Guard v4

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_ci_broad_sr_guard4.*
pictures-json/reports/stage2_5_no_top_root_cause_ci_broad_sr_guard4.*
pictures-json/reports/stage2_5_no_top_actionability_ci_broad_sr_guard4.*
pictures-json/reports/synthetic_observations_v10_ci_broad_sr_guard4_report.*
pictures-json/reports/actual_response_samples_ci_broad_sr_guard4.*
pictures-json/reports/pg_guide_usage_profiles_sync_ci_broad_sr_guard4.*
pictures-json/reports/ci_no_action_triage_ci_broad_sr_guard4.*
pictures-json/reports/ci_mapping_review_semantic_ci_broad_sr_guard4.*
pictures-json/reports/ci_sr_mapping_candidate_review_ci_broad_sr_guard4.*
pictures-json/reports/pg_ci_sr_link_candidates_ci_broad_sr_guard4.*
pictures-json/reports/pipeline_quality_v1_v10_ci_candidate_review_v1.*
koshaontology/ontology/serving-validation-report-ci_broad_sr_guard4.*
koshaontology/ontology/serving-workprocess-alignment-ci_broad_sr_guard4.*
```

Summary:

```text
previous accepted baseline: ci_wp_relevance_guard1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5 -> 5
NO_TOP: 88 -> 88
industry_boundary_gap: 0 -> 0
workprocess_mismatch: 5 -> 5
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 16
CI no_action: 497 -> 492
CI context_mismatch: 0 -> 0
CI broad_sr_only: 13 -> 0
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 23 -> 22
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
accepted photo-actionable role overrides: 10
PG guide_usage_profiles sync: PASS, 1,038 rows
PG primary WorkProcess check: missing 0 / cross-guide 0
```

Policy change:

```text
active artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v21.json
  OHS/backend/app/data/guide_support_candidates.v21.jsonl
runtime gate:
  immediate-action CI is suppressed for explicit normal/completed/stored/education scenes
  broad SRs and needs_review candidates remain blocked from serving
profile boundary tightened:
  G-91 patient-transfer hoist is exclusive and no longer matches general lifting/crane scenes
  C-C-85 inert-gas purging excludes public indoor CO2 ventilation scenes
  G-44 hand-tool and M-51 noise-control require their own usage terms
status/penalty/SHE/SR/legal asserted mapping/public API impact: none
```

NO_TOP actionability:

```text
total NO_TOP: 88
accepted empty top: 31
source/taxonomy review: 57
runtime repair candidate: 0
manual review: 0
```

Ontology validation result:

```text
snapshot: koshaontology/ontology/serving-snapshot-ci_broad_sr_guard4.ttl
validation report: koshaontology/ontology/serving-validation-report-ci_broad_sr_guard4.*
WorkProcess alignment report: koshaontology/ontology/serving-workprocess-alignment-ci_broad_sr_guard4.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
PG guide_usage_profiles sync: PASS, 1,038 rows
PG photo_actionable / conditional / unmatchable: 631 / 39 / 368
PG primary WorkProcess check: missing 0 / cross-guide 0
```

Interpretation: this pass accepts that some photos still have no scene-relevant KOSHA top Guide. NO_TOP stays at 88 and runtime repair candidates remain 0. Guide mismatch, industry boundary, WorkProcess mismatch, and ontology validation stay stable; CI broad-only, no_action, and boundary queues improve while v10 smoke and actual 240 status behavior remain stable. The next quality target is remaining CI no_action, CI guide-boundary mismatch, and generic CI overreach.

CI no-action triage:

```text
source report: pictures-json/reports/ci_no_action_triage_ci_broad_sr_guard4.*
total CI no_action: 492
upstream_stage2_3_review: 357
ci_mapping_review: 63
source_or_taxonomy_review: 45
accepted_empty_top: 24
runtime_repair_candidate: 3

triage categories:
  upstream_she_not_actionable_no_sr: 194
  upstream_she_not_actionable_with_sr: 163
  no_top_source_or_taxonomy_review: 45
  top_guide_ci_sr_mapping_gap: 36
  top_guide_ci_has_no_sr_mapping: 27
  no_top_accepted_empty_top: 24
  top_guide_ci_relevance_gate_gap: 3
```

Semantic review of the 63 `ci_mapping_review` rows:

```text
source report: pictures-json/reports/ci_mapping_review_semantic_ci_broad_sr_guard4.*
guide_selection_mismatch: 21
corpus_gap_or_near_analogy: 21
true_ci_mapping_candidate: 16
safe_or_followup_no_immediate: 5
```

Interpretation: `CI no_action 492` is mostly not a direct CI ranking bug. The immediate runtime repair tail is only 3 cases (`E-31`, `A-G-18`), while the apparent 63-case CI mapping queue shrinks to 16 true CI-SR/candidate mapping candidates after semantic review. The other 47 should be handled as Guide selection/profile issues, source/taxonomy gaps, or accepted safe/follow-up no-action scenes. The largest bucket, 357 cases, still belongs upstream in Stage 2/3 because SHE is not actionable enough to create immediate actions.

CI/SR mapping candidate review for the 16 true candidates:

```text
source report: pictures-json/reports/ci_sr_mapping_candidate_review_ci_broad_sr_guard4.*
review cases: 16
manual-seeded CI candidates: 16
best candidate still needs mapping review: 16
top Guides: A-G-12 7, B-M-37 2, A-G-11/A-G-6/C-113/D-28/E-G-1/G-11/P-22 1 each
```

Interpretation: the 16 rows now have concrete ChecklistItem review seeds, but they are not asserted PG mappings. Examples include `CI-AG6-006` for knife/cutting, `CI-BM37-140` for conveyor guarding/emergency stop, `CI-C113-130` for icy surfaces, and `CI-P22-027` for dry-cleaning ventilation. Any PG update should import these as candidate/review rows first or apply a tightly reviewed `ci_sr_mapping` patch, then rerun v1~v10 and actual 240.

PG review-only candidate import:

```text
source report: pictures-json/reports/pg_ci_sr_link_candidates_ci_broad_sr_guard4.*
table: guide_sr_link_candidates
method: ci_candidate_review_v1
mode: apply
raw candidate rows: 62
pre-aggregated rows inserted: 42
distinct CI / SR: 19 / 19
review_status: needs_review
asserted: false
serving-eligible rows: 0
missing Guide/CI/SR refs: 0
ci_sr_mapping inserts: 0
```

Interpretation: the review candidates now exist in PostgreSQL for ontology/audit review, but they cannot affect OHS runtime because `needs_review` is excluded from serving gates. The next step is not to rerank immediately; it is to review these 42 candidate rows, promote only validated rows to a serving-eligible candidate or asserted mapping policy if justified, and then rerun synthetic v1~v10 plus actual 240.

Post-import Stage 2~5 validation:

```text
source report: pictures-json/reports/pipeline_quality_v1_v10_ci_candidate_review_v1.*
total: 2,360
SHE: TP 1,107 / FN 909 / FP 82
SR: TP 1,414 / FN 270 / FP 211
Guide mismatch: 5
NO_TOP: 88
industry boundary gap: 0
WorkProcess mismatch: 5
CI no_action: 492
CI broad_sr_only: 0
CI needs_review_used: 0
CI guide_boundary_mismatch: 21
```

Interpretation: PG now contains review-only CI/SR candidates, but the runtime-facing evaluation remains stable. The candidate import did not create `ci_needs_review_used` leakage.

## NO TOP Serving Bridge v4

Historical accepted baseline before `ci_wp_relevance_guard1`.

## No Forced Hotwork Gate v1

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_no_forced_hotwork_gate1.*
pictures-json/reports/synthetic_observations_v10_no_forced_hotwork_gate1_report.*
pictures-json/reports/actual_response_samples_no_forced_hotwork_gate1.*
koshaontology/ontology/serving-validation-report-no_forced_hotwork_gate1.*
koshaontology/ontology/serving-workprocess-alignment-no_forced_hotwork_gate1.*
```

Summary:

```text
previous accepted baseline: context_safe_gate1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 15 -> 8
NO_TOP: 85 -> 90
industry_boundary_gap: 1 -> 1
workprocess_mismatch: 14 -> 7
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 15
CI no_action: 482 -> 482
CI context_mismatch: 12 -> 12
CI broad_sr_only: 14 -> 14
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 26 -> 26
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
accepted photo-actionable role overrides: 10
```

Policy change:

```text
context-required Guide families added on top of context_safe_gate1:
  air_jacket_gas_manifold_welding_support
  small_tank_drum_hot_work
principle:
  현장 사진에 맞는 Guide가 없으면 broad hot-work Guide를 억지로 올리지 않고 NO_TOP으로 남길 수 있다.
status/penalty/SHE/SR/legal asserted mapping/public API impact: none
```

Ontology validation result:

```text
snapshot: koshaontology/ontology/serving-snapshot-no_forced_hotwork_gate1.ttl
validation report: koshaontology/ontology/serving-validation-report-no_forced_hotwork_gate1.*
WorkProcess alignment report: koshaontology/ontology/serving-workprocess-alignment-no_forced_hotwork_gate1.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: `G-76-2011` no longer appears as a repeated WorkProcess mismatch warning. Some chemical/lab cases now correctly remain `NO_TOP` when the current Guide corpus lacks a scene-specific procedure.

## Context Safe Gate v1

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_context_safe_gate1.*
pictures-json/reports/synthetic_observations_v10_context_safe_gate1_report.*
pictures-json/reports/actual_response_samples_context_safe_gate1.*
koshaontology/ontology/serving-validation-report-context_safe_gate1.*
koshaontology/ontology/serving-workprocess-alignment-context_safe_gate1.*
```

Summary:

```text
previous accepted baseline: corpus_gap_guard1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 22 -> 15
NO_TOP: 85 -> 85
industry_boundary_gap: 1 -> 1
workprocess_mismatch: 20 -> 14
broad_sr_overreach: 1 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 15
CI no_action: 482 -> 482
CI context_mismatch: 11 -> 12
CI broad_sr_only: 14 -> 14
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 26 -> 26
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 1
accepted photo-actionable role overrides: 10
```

Policy change:

```text
context-required Guide families added:
  pipe_support_installation_welding
  airborne_infectious_disease_workplace_prevention
safe welding block phrases added:
  착용 완비 / 차광 커튼 / 차광막 / 국소 배기 가동 / 국소 배기 장치가 가동 / 자동 차광 헬멧
status/penalty/SHE/SR/legal asserted mapping/public API impact: none
```

Ontology validation result:

```text
snapshot: koshaontology/ontology/serving-snapshot-context_safe_gate1.ttl
validation report: koshaontology/ontology/serving-validation-report-context_safe_gate1.*
WorkProcess alignment report: koshaontology/ontology/serving-workprocess-alignment-context_safe_gate1.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 1
remaining warning: G-76-2011 repeated workprocess_mismatch 7 cases
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: `B-M-20-2026`, `H-186-2016`, and `A-G-14-2026` warning queues were resolved without broadening status-level inference. The remaining issue is a narrower `G-76-2011` WorkProcess relevance queue, so the next work should refine Guide/WorkProcess matching rather than add broad aliases.

## SituationFrame Support v2

Source reports:

```text
pictures-json/reports/situation_frame_artifact_build.v2.*
pictures-json/reports/situation_frame_eval_report.v2_child_gate1.*
pictures-json/reports/pipeline_quality_v1_v10_situation_frame_support7.*
pictures-json/reports/actual_response_samples_situation_frame_support7.*
pictures-json/reports/synthetic_observations_v10_situation_frame_support7_report.*
```

Artifact build summary:

```text
Stage 3 candidate input: 230
classified candidates: 230
runtime SHE approved update: 0
asserted mapping update: 0
child contexts: 86
Guide support candidates v2 historical: 1
support Guide review:
  accept: 1
  reject: 190
reject reasons:
  manual_child_guide_boundary: 187
  domain_excluded: 2
  domain_mismatch: 1
classification labels:
  taxonomy_gap: 230
  guide_support_only: 112
  ambiguous_confirmation: 117
  true_new_she: 60
  sr_review_needed: 98
```

Frame extraction summary on synthetic v1~v10:

```text
total samples: 2,360
match policy:
  confirmation_required: 880
  guide_support_only: 1,351
  status_safe: 129
collapse queues:
  child_context_available: 528
  broad_parent_without_child: 241
  no_broad_parent: 1,591
Guide support hit samples: 8
```

## Guide Photo Matchability v1

Source reports:

```text
pictures-json/reports/guide_photo_matchability_audit_v1.*
pictures-json/reports/pipeline_quality_v1_v10_photo_matchability1.*
pictures-json/reports/actual_response_samples_photo_matchability1.*
pictures-json/reports/synthetic_observations_v10_photo_matchability1_report.*
```

Artifact:

```text
OHS/backend/app/data/guide_photo_matchability.v1.json
OHS/backend/app/data/guide_domain_profiles.json
```

Classification summary:

```text
Guide profiles: 1,038
photo_actionable: 631
photo_conditional_followup: 39
photo_unmatchable: 368
non-field role overrides: 10 field-action Guides retained as photo_actionable
asserted mapping update: 0
SHE/SR/status/penalty impact: none
```

Serving policy:

```text
photo_actionable: can appear as photo-based top standard procedure
photo_conditional_followup: cannot be top; allowed as at most one lower follow-up with explicit management/document context
photo_unmatchable: cannot be photo top; explicit document/measurement/test/health/method context is required for any follow-up
scope: standard_procedures top lane only
not applied to: immediate_actions, SHE status, SR evidence, penalty path
```

## Stage 2~5 Integrated Quality

Source report:

```text
pictures-json/reports/pipeline_quality_v1_v10_no_forced_hotwork_gate1.*
pictures-json/reports/stage2_5_no_top_root_cause_no_forced_hotwork_gate1.*
pictures-json/reports/stage2_5_no_top_actionability_no_forced_hotwork_gate1.*
```

Summary:

```text
total samples: 2,360
Stage failure counts:
  stage2: 775
  stage3: 1,288
  stage4: 612
  stage5: 564
SHE TP/FN/FP: 1,107 / 909 / 82
SHE recall: 54.9%
SR TP/FN/FP: 1,414 / 270 / 211
SR recall: 84.0%
Guide mismatch: 8
Stage 2~5 NO_TOP: 90
industry_boundary_gap: 1
workprocess_mismatch: 7
broad_sr_overreach: 0
photo_unmatchable_top_count: 0
followup_only_retained_count: 15
CI no_action: 482
CI context_mismatch: 12
CI broad_sr_only: 14
CI needs_review_used: 0
CI guide_boundary_mismatch: 26
```

NO_TOP actionability audit:

```text
total NO_TOP reviewed: 90
accepted empty top: 29
source/taxonomy review: 54
runtime repair candidates: 7
manual review required: 0

actionability groups:
  source_or_taxonomy_review 54
  accepted_empty_top 29
  runtime_repair_candidate 7

runtime repair candidate types:
  situation_frame_support_repair_candidate 5
  guide_usage_profile_repair_candidate 2
runtime repair candidate case ids:
  SYN-V10-0023, SYN-V2-0073, SYN-V3-0061, SYN-V5-0001, SYN-V9-0128, SYN-V9-0181, SYN-V9-0216
```

Interpretation: `NO_TOP` is not automatically a failure. For 29 cases, the safer product behavior is to leave `standard_procedures` empty because the scene is safe-controlled, outside the KOSHA photo-top scope, follow-up/document-only, or known wrong-support territory. For 54 cases, the next step is source/taxonomy review rather than a scoring tweak. Only 7 cases are immediate runtime repair candidates, and those must be handled through Guide usage profile or SituationFrame support evidence.

Synthetic SHE smoke by version:

| Version | Samples | positive / ambiguous / negative | SHE recall | SHE FN | SHE FP | negative specificity | confirmed-risk recall | ambiguous over-promoted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v1 | 120 | 60 / 40 / 20 | 100.0% | 0 | 28 | 42.9% | 48.3% | 6 |
| v2 | 100 | 55 / 25 / 20 | 100.0% | 0 | 10 | 66.7% | 60.0% | 5 |
| v3 | 200 | 120 / 60 / 20 | 100.0% | 0 | 25 | 44.4% | 55.0% | 2 |
| v4 | 80 | 48 / 24 / 8 | 100.0% | 0 | 0 | 100.0% | 52.1% | 1 |
| v5 | 210 | 126 / 63 / 21 | 100.0% | 0 | 0 | 100.0% | 66.7% | 1 |
| v6 | 330 | 198 / 99 / 33 | 100.0% | 0 | 0 | 100.0% | 70.2% | 37 |
| v7 | 330 | 198 / 99 / 33 | 100.0% | 0 | 1 | 97.1% | 68.7% | 7 |
| v8 | 330 | 198 / 99 / 33 | 100.0% | 0 | 3 | 91.7% | 68.7% | 17 |
| v9 | 330 | 187 / 99 / 44 | 100.0% | 0 | 0 | 100.0% | 65.8% | 7 |
| v10 | 330 | 187 / 99 / 44 | 100.0% | 0 | 0 | 100.0% | 42.8% | 0 |
| v1~v9 | 2,030 | 1,190 / 608 / 232 | 100.0% | 0 | 67 | 71.1% | 64.8% | 83 |
| v1~v10 | 2,360 | 1,377 / 707 / 276 | 100.0% | 0 | 67 | 75.7% | 61.8% | 83 |

## Serving Ontology Validation Snapshot

Source artifacts:

```text
OHS/backend/app/data/guide_domain_profiles.json
OHS/backend/app/data/guide_photo_matchability.v1.json
OHS/backend/app/data/broad_sr_policy.json
OHS/backend/app/data/situation_context_taxonomy.v21.json
OHS/backend/app/data/guide_support_candidates.v21.jsonl
pictures-json/reports/pipeline_quality_v1_v10_ci_broad_sr_guard4.json
pictures-json/reports/pg_guide_usage_profiles_sync_ci_broad_sr_guard4.json
```

Generated ontology files:

```text
koshaontology/ontology/serving-policy.ttl
koshaontology/ontology/serving-snapshot-ci_broad_sr_guard4.ttl
koshaontology/ontology/serving-validation-shapes.ttl
koshaontology/ontology/serving-validation-report-ci_broad_sr_guard4.*
koshaontology/ontology/serving-workprocess-alignment-ci_broad_sr_guard4.*
```

Validation summary:

```text
GuideUsageProfile: 1,038
photo_actionable: 631
photo_conditional_followup: 39
photo_unmatchable: 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 0
accepted photo-actionable role overrides: 10
```

Warning queue:

```text
none
```

Core A-Box sync:

```text
kosha-instances.ttl regenerated from PostgreSQL on 2026-05-14
KoshaGuide: 1,038
ChecklistItem: 54,631
DomainTerm: 7,726
WorkProcess: 9,316
EquipmentSpec: 8,103
DocumentRequirement: 3,435
serving profile primary WorkProcess links: 4,715 / 4,715 aligned
primary_workprocess_not_in_base_ttl: 1,220 -> 0
guide_usage_profiles PG sync: 1,038 / 1,038, missing Guide 0, missing primary WorkProcess 0, cross-guide primary WorkProcess 0
```

## Stage3 Remaining Gap Support v20 Actionable

`stage3_remaining_gap_support_v20_actionable` keeps the `stage3_remaining_gap_support_v19_dropped_tool` status/penalty/SHE/SR boundary and adds two narrow Guide-support-only contexts: `GREENHOUSE_STRUCTURE_FALL` and `DRY_CLEANING_STEAM_PIPE_HOT_SURFACE`. `SYN-V8-0022` now routes to `C-49-2012` safety harness use for greenhouse-frame high-place fall risk. `SYN-V8-0167` now routes to `P-22-2012` dry-cleaning process safety for exposed hot steam-pipe contact-burn risk. Both rows are trigger-backed support only; status, penalty, SHE approval, asserted mapping, and legal SR evidence remain unchanged.

Source reports:

```text
pictures-json/reports/stage3_remaining_gap_support_v20_artifacts.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v20_actionable.*
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v20_actionable_report_report.*
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v20_actionable.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v20_actionable.*
```

Runtime artifacts:

```text
OHS/backend/app/data/situation_context_taxonomy.v20.json
OHS/backend/app/data/guide_support_candidates.v20.jsonl
OHS/backend/app/services/situation_frame_service.py
```

Remaining `NO_TOP` root-cause audit:

```text
total_no_top: 17
stage2_taxonomy_or_normalization_gap: 11
stage3_she_to_sr_gap: 2
synthetic_fixture_or_safe_controlled_positive: 2
situation_frame_child_context_gap: 1
stage3_she_gap_but_sr_available: 1
```

## Stage3 Remaining Gap Support v19 Dropped Tool

`stage3_remaining_gap_support_v19_dropped_tool` keeps the `stage3_safe_cue_negation_fix2` status/penalty/SHE/SR boundary and adds one narrow Guide-support-only context: `MAINTENANCE_HEIGHT_DROPPED_TOOL`. This fixes `SYN-V8-0323`, a hospital/building high-place maintenance scene with dropped-tool risk, by routing support to `G-60-2012` building management work and `G-44-2011` hand-tool safety instead of exterior-wall painting. Status, penalty, SHE approval, asserted mapping, and legal SR evidence remain unchanged.

Source reports:

```text
pictures-json/reports/stage3_remaining_gap_support_v19_artifacts.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v19_dropped_tool.*
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v19_dropped_tool_report.*
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v19_dropped_tool.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v19_dropped_tool.*
```

Runtime artifacts:

```text
OHS/backend/app/data/situation_context_taxonomy.v19.json
OHS/backend/app/data/guide_support_candidates.v19.jsonl
OHS/backend/app/services/situation_frame_service.py
```

## Stage3 Safe Cue Negation Fix2

`stage3_safe_cue_negation_fix2` keeps the `stage3_remaining_gap_support_v18_narrow10` status/penalty/SHE/SR boundary and fixes a SituationFrame safe-cue parsing problem. Safe terms such as `LOTO` and `정상` are no longer treated as safe when they appear in negated or contrastive phrases such as `LOTO 미적용`, `밀착 미흡`, or `동료 정상 착용과 대비`. Conversely, trigger-only Guide support is suppressed in safe procedure contexts such as `압력 게이지 0`, `잔압 완전 방출`, `방열 장갑 착용`, and `안면 보호대 착용`.

Resolved NO_TOP cases include silica-dust respirator misuse, binding-machine jam clearing without LOTO, and lab eyewash/shower inspection. The remaining 20 NO_TOP cases are now dominated by Stage 2 taxonomy/normalization gaps in service/healthcare and small-facility domains. Two CI no-action regressions remain in welding samples, so the next algorithm pass should focus on CI fallback/WorkProcess relevance rather than widening status-level risk inference.

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_stage3_safe_cue_negation_fix2.*
pictures-json/reports/synthetic_observations_v10_stage3_safe_cue_negation_fix2_report.*
pictures-json/reports/actual_response_samples_stage3_safe_cue_negation_fix2.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_safe_cue_negation_fix2.*
```

Runtime code:

```text
OHS/backend/app/services/situation_frame_service.py
```

## Stage3 Remaining Gap Support v18 Narrow10

`stage3_remaining_gap_support_v18_narrow10` keeps the `stage3_remaining_gap_support_v17b_narrow9b` status/penalty/SHE/SR boundary and adds 4 narrow Stage 3 remaining-gap support contexts: industrial washer vibration/crush, garment sharp-object puncture, EV high-voltage battery PPE gap, and cold-room emergency-release failure. It also tightens the existing binding-machine LOTO support row so actual `기계 미정지` and `용지 걸림 제거` wording can match. One resolved industrial washer case moved from `NO_TOP` to `workprocess_mismatch`, so it remains a WorkProcess-quality follow-up instead of being treated as fully solved.

Source reports:

```text
pictures-json/reports/stage3_remaining_gap_support_v18_artifacts_narrow10.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v18_narrow10.*
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v18_narrow10_report.*
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v18_narrow10.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v18_narrow10.*
```

Runtime artifacts:

```text
OHS/backend/app/data/situation_context_taxonomy.v18.json
OHS/backend/app/data/guide_support_candidates.v18.jsonl
```

## Stage3 Remaining Gap Support v17b Narrow9b

`stage3_remaining_gap_support_v17b_narrow9b` keeps the `stage3_remaining_gap_support_v16c_narrow8c` status/penalty/SHE/SR boundary and adds 8 narrow Stage 3 remaining-gap support contexts: hair chemical eye exposure, hair-wash neck ergonomics, cashier prolonged standing, pet grooming bite/table fall, binding-machine LOTO, truck-coupling pretrip check, and steam-gun face burn PPE. A broader v17 trial was held back because generic `안전핀` wording overmatched a safe rack-inspection scene and an engine-overhaul waste support row produced a weak waste-collection Guide.

Source reports:

```text
pictures-json/reports/stage3_remaining_gap_support_v17b_artifacts_narrow9b.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v17b_narrow9b.*
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v17b_narrow9b_report.*
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v17b_narrow9b.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v17b_narrow9b.*
```

Runtime artifacts:

```text
OHS/backend/app/data/situation_context_taxonomy.v17b.json
OHS/backend/app/data/guide_support_candidates.v17b.jsonl
```

## Stage3 Remaining Gap Support v16c Narrow8c

`stage3_remaining_gap_support_v16c_narrow8c` keeps the `stage2_taxonomy_gap_support_v15_narrow7b` status/penalty/SHE/SR boundary and adds 6 narrow Stage 3 remaining-gap support contexts: wafer-transfer robot sensor bypass, UV sterilizer PPE, silica-dust respirator misuse, yarn-winding hand entry, harvest squatting ergonomics, and adhesive splash eye/face PPE. A v16b EV battery support row was held back because it fixed one NO_TOP case but moved an existing EV battery positive case from an electrical-work Guide to an unrelated welding-fire-blanket Guide.

Source reports:

```text
pictures-json/reports/stage3_remaining_gap_support_v16c_artifacts_narrow8c.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v16c_narrow8c.*
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v16c_narrow8c_report.*
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v16c_narrow8c.*
```

Runtime artifacts:

```text
OHS/backend/app/data/situation_context_taxonomy.v16c.json
OHS/backend/app/data/guide_support_candidates.v16c.jsonl
```

## Stage2 Taxonomy Gap Support v15 Narrow7b

`stage2_taxonomy_gap_support_v15_narrow7b` keeps the `stage3_sr_gap_support_v14_narrow6b` status/penalty/SHE/SR boundary and adds 5 narrow Stage 2 taxonomy-gap support contexts: night/lone-worker care monitoring, client aggression emergency response, chemical cleaner PPE/ventilation, lab eyewash/shower inspection, and glutaraldehyde disinfection PPE/ventilation. The first v15 trial overmatched generic PPE wording (`방진마스크`, `니트릴 장갑`, `고글`) in safe/non-related scenes, so accepted `narrow7b` keeps substance/task-specific child aliases and leaves PPE terms only as profile-alignment/trigger evidence.

Source reports:

```text
pictures-json/reports/stage2_taxonomy_gap_support_v15_artifacts_narrow7b.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_taxonomy_gap_support_v15_narrow7b.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_taxonomy_gap_support_v15_narrow7b.*
pictures-json/reports/synthetic_observations_v10_stage2_taxonomy_gap_support_v15_narrow7b_report.*
pictures-json/reports/actual_response_samples_stage2_taxonomy_gap_support_v15_narrow7b.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v15.json
  OHS/backend/app/data/guide_support_candidates.v15.jsonl
runtime artifacts at v14 acceptance:
  situation_context_taxonomy.v15.json
  guide_support_candidates.v15.jsonl
added support rows: 5
support candidate count: 201 -> 206
child context count: 156 -> 161
Guide mismatch: 136 -> 136
NO_TOP: 52 -> 42
stage2_taxonomy_or_normalization_gap: 20 -> 12
stage3_she_gap_but_sr_available: 11 -> 9
stage3_she_to_sr_gap: 10 -> 10
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 64 -> 64
CI no_action: 487 -> 487
CI guide_boundary_mismatch: 64 -> 64
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 SR Gap Support v14 Narrow6b

`stage3_sr_gap_support_v14_narrow6b` keeps the `stage2_taxonomy_support_v13_narrow5` status/penalty/SHE/SR boundary and adds 13 narrow Stage 3 SHE-to-SR gap support contexts: indoor welding fume respirator gap, sharp metal edge handling, reflow oven residual heat PPE, FOUP stair carrying, excavator slope/signaler gap, confined tank attendant gap, ship heavy-lift sling inspection, vehicle exposed wiring fire gap, scalding tank fall/burn, binding machine jam LOTO, binding machine hotmelt PPE, plate-making chemical PPE, and UV plate-making shielding/PPE. The first v14 trial overmatched short trigger terms (`발판 없이`, generic `슬링/인양`, generic `용접 흄`, generic `보호 장갑 미착용`), so accepted `narrow6b` keeps compound/object-specific triggers. It also marks 2 stale `SOLDERING_ASSEMBLY` rows as `review_only/rejected` because they pointed reflow-oven scenes to explosives/explosion-proof electrical Guides.

Source reports:

```text
pictures-json/reports/stage3_sr_gap_support_v14_artifacts_narrow6b.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_sr_gap_support_v14_narrow6b.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_sr_gap_support_v14_narrow6b.*
pictures-json/reports/synthetic_observations_v10_stage3_sr_gap_support_v14_narrow6b_report.*
pictures-json/reports/actual_response_samples_stage3_sr_gap_support_v14_narrow6b.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v14.json
  OHS/backend/app/data/guide_support_candidates.v14.jsonl
default runtime artifacts:
  situation_context_taxonomy.v14.json
  guide_support_candidates.v14.jsonl
added support rows: 13
rejected stale support rows: 2
support candidate count: 188 -> 201
child context count: 143 -> 156
Guide mismatch: 136 -> 136
NO_TOP: 64 -> 52
stage3_she_to_sr_gap: 22 -> 10
stage2_taxonomy_or_normalization_gap: 20 -> 20
stage3_she_gap_but_sr_available: 11 -> 11
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 64 -> 64
CI no_action: 487 -> 487
CI guide_boundary_mismatch: 64 -> 64
status/penalty/SHE approval/asserted mapping update: 0
```

`stage2_3_support_v10_narrow2` keeps the `stage2_3_support_v9_narrow4` status/penalty/SHE/SR boundary and adds six trigger-backed support-only contexts: powered food-slicer cleaning, bakery oven/hot-tray burn, small-server electrical overload, elevated welding fall control, automotive tire/wheel service, and silica-dust blasting. The first v10 trial overmatched high-pressure washing/electrical-panel and safe elevated-welding scenes, so the accepted narrow2 pass removed that seed and tightened food-slicer, elevated-welding, and silica triggers. It reduced NO_TOP by 11 and CI no_action by 1 while keeping Guide mismatch, industry boundary gap, workprocess mismatch, broad SR overreach, photo top gating, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage2_3_support_v9_narrow4` keeps the `stage2_3_support_v8_narrow2` status/penalty/SHE/SR boundary and adds five trigger-backed support-only contexts: sports-facility slip/trip, powered cardio-equipment maintenance, needlestick/sharps disposal, blood-contaminated waste handling, and flammable-chemical smoking. Earlier v9 trials overmatched generic `전원을 끄지 않고`, generic medical-waste wording, and `담배꽁초`, so the accepted narrow4 pass requires specific child context plus unsafe/observable trigger phrases. It reduced NO_TOP by 8 while keeping Guide mismatch, industry boundary gap, workprocess mismatch, broad SR overreach, CI queues, photo top gating, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage2_3_support_v8_narrow2` keeps the `stage2_service_support_v7_narrow1` status/penalty/SHE/SR boundary and adds six trigger-backed support-only contexts: X-ray radiation control, blasting operation, hot-work permit deviation, shipyard/internal welding, soldering assembly, and solvent-waste fire. The first v8 trial overmatched broad `방사선`, `허가서`, `용접 흄`, and `용제` wording, so the accepted narrow2 pass keeps only specific visual/unsafe phrases. It reduced NO_TOP by 11, improved Guide mismatch by 1, industry boundary gap by 1, and CI no_action by 1 while keeping broad SR overreach, workprocess mismatch, photo top gating, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage2_service_support_v7_narrow1` keeps the `stage3_domain_support2_confirmation_gate2` status/penalty/SHE/SR boundary and adds only two trigger-backed support-only service contexts: display/wiring-device electrical maintenance and floor-polisher/stair-cleaner building cleaning. Broad terms such as `DISPLAY_SETUP`, `형광등`, `청소기`, and `출입 통제` were removed after an overmatch trial. The accepted narrow pass reduced NO_TOP by 7 and CI no_action by 3 while keeping Guide mismatch, industry boundary, workprocess mismatch, broad SR overreach, CI queues, photo top gating, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage3_domain_support2_confirmation_gate2` keeps the `stage3_domain_support1_tight1` status/penalty/SHE/SR boundary and only changes Guide usage/domain gating. `confirmation_required` SituationFrame support can satisfy the gate at score `0.54` instead of `0.78` only when it is trigger-backed, backed by a non-broad SR, and child-context/profile-aligned. This reduced NO_TOP by 9 additional cases and reduced `stage3_she_to_sr_gap` from 46 to 37 while keeping Guide mismatch, industry boundary, workprocess mismatch, broad SR overreach, CI queues, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage3_domain_support1_tight1` adds three narrow `guide_support_only` rows to `guide_support_candidates.v6.jsonl`: spray painting fire/explosion, dry-cleaning solvent ignition, and pesticide/greenhouse re-entry. Each row requires a child context plus trigger evidence and stays outside status, penalty, SHE approval, asserted mapping, and legal SR evidence. The pass reduced NO_TOP by 8 additional cases and improved obvious Guide mismatch by 1 while keeping broad SR overreach at 1. CI no_action increased from 492 to 494 but remains under the current gate and did not affect actual 240 status/penalty behavior.

`stage2_support_usage_gate3_safe_lock1` keeps the `stage2_support_usage_gate2b` status/penalty/SHE/SR boundary and narrows SituationFrame safe-cue detection: generic `잠금` is no longer treated as a safe lockout cue for external-lock/entrapment wording. This allows existing `COLD_ROOM_ACCESS` support rows to create cold-room procedures in unsafe lock-in scenes. It reduced NO_TOP by 5 additional cases without increasing industry boundary gap, broad SR overreach, or actual 240 status drift. It does not approve new SHE patterns, insert asserted mappings, or create legal SR evidence.

## Stage2 Taxonomy Support v13 Narrow5

`stage2_taxonomy_support_v13_narrow5` keeps the `stage3_gap_support_v12_narrow4` status/penalty/SHE/SR boundary and adds seven narrow Stage 2 taxonomy-gap support contexts: high-pressure waterjet PPE, UV lamp eye PPE, UV coating ozone respirator, formalin contact PPE, cold-room PPE, crematorium hot-surface PPE, and sharp-fragment hand PPE. The broad trial overmatched cold-room wording, and a global short-token matching guard regressed Guide quality; the accepted pass keeps object-specific triggers and only blocks the confirmed `P-55-2012` single-character `황` false match against words like `상황`.

Source reports:

```text
pictures-json/reports/stage2_taxonomy_support_v13_artifacts_narrow5.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_taxonomy_support_v13_narrow5.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_taxonomy_support_v13_narrow5.*
pictures-json/reports/synthetic_observations_v10_stage2_taxonomy_support_v13_narrow5_report.*
pictures-json/reports/actual_response_samples_stage2_taxonomy_support_v13_narrow5.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v13.json
  OHS/backend/app/data/guide_support_candidates.v13.jsonl
then-default runtime artifacts:
  situation_context_taxonomy.v13.json
  guide_support_candidates.v13.jsonl
added support rows: 7
support candidate count: 181 -> 188
child context count: 136 -> 143
Guide mismatch: 136 -> 136
NO_TOP: 74 -> 64
stage2_taxonomy_or_normalization_gap: 28 -> 20
stage3_she_gap_but_sr_available: 11 -> 11
stage3_she_to_sr_gap: 24 -> 22
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 64 -> 64
CI no_action: 487 -> 487
CI guide_boundary_mismatch: 64 -> 64
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 Gap Support v12 Narrow4

`stage3_gap_support_v12_narrow4` keeps the `stage2_3_support_v11_narrow3` status/penalty/SHE/SR boundary and adds 13 narrow Stage 3 SHE-gap support contexts for cases where non-broad SRs already exist but no Guide anchor was available. The first v12 trial overmatched safe PPE, high-heat, stair, and electrical-control scenes, so accepted narrow4 keeps only unsafe/object-specific trigger phrases and drops the EV battery seed that moved one case from CI no-action to CI boundary mismatch.

Source reports:

```text
pictures-json/reports/stage3_gap_support_v12_artifacts_narrow4.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_gap_support_v12_narrow4.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_gap_support_v12_narrow4.*
pictures-json/reports/synthetic_observations_v10_stage3_gap_support_v12_narrow4_report.*
pictures-json/reports/actual_response_samples_stage3_gap_support_v12_narrow4.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v12.json
  OHS/backend/app/data/guide_support_candidates.v12.jsonl
default runtime artifacts:
  situation_context_taxonomy.v12.json
  guide_support_candidates.v12.jsonl
added support rows: 13
support candidate count: 168 -> 181
child context count: 123 -> 136
Guide mismatch: 137 -> 136
NO_TOP: 94 -> 74
stage2_taxonomy_or_normalization_gap: 28 -> 28
stage3_she_gap_but_sr_available: 28 -> 11
stage3_she_to_sr_gap: 25 -> 24
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 65 -> 64
CI no_action: 489 -> 487
CI guide_boundary_mismatch: 64 -> 64
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2/3 Support v11 Narrow3

`stage2_3_support_v11_narrow3` keeps the `stage2_3_support_v10_narrow2` status/penalty/SHE/SR boundary and adds five narrow Stage 2 taxonomy-gap support contexts: sharp glass manual handling, lead-paint grinding dust, ice-pick fragment eye exposure, climbing-wall fall surface, and chair-stack manual carry. Earlier v11 trials overmatched PPE-only, generic fall-risk, and generic blocked-visibility wording, so accepted narrow3 requires object-specific triggers such as `판유리`, `전동 그라인더`, `아이스픽`, `클라이밍 월`, or `무거운 의자`.

Source reports:

```text
pictures-json/reports/stage2_3_support_v11_artifacts_stage2_narrow3.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v11_narrow3.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v11_narrow3.*
pictures-json/reports/synthetic_observations_v10_stage2_3_support_v11_narrow3_report.*
pictures-json/reports/actual_response_samples_stage2_3_support_v11_narrow3.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v11.json
  OHS/backend/app/data/guide_support_candidates.v11.jsonl
default runtime artifacts:
  situation_context_taxonomy.v11.json
  guide_support_candidates.v11.jsonl
added support rows: 5
support candidate count: 163 -> 168
child context count: 118 -> 123
Guide mismatch: 137 -> 137
NO_TOP: 100 -> 94
stage2_taxonomy_or_normalization_gap: 33 -> 28
stage3_she_gap_but_sr_available: 29 -> 28
stage3_she_to_sr_gap: 25 -> 25
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 65 -> 65
CI no_action: 489 -> 489
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2/3 Support v10 Narrow2

Source reports:

```text
pictures-json/reports/stage2_3_support_v10_artifacts_narrow2.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v10_narrow2.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v10_narrow2.*
pictures-json/reports/synthetic_observations_v10_stage2_3_support_v10_narrow2_report.*
pictures-json/reports/actual_response_samples_stage2_3_support_v10_narrow2.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v10.json
  OHS/backend/app/data/guide_support_candidates.v10.jsonl
default runtime artifacts:
  situation_context_taxonomy.v10.json
  guide_support_candidates.v10.jsonl
added support rows: 6
support candidate count: 157 -> 163
child context count: 112 -> 118
Guide mismatch: 137 -> 137
NO_TOP: 111 -> 100
stage2_taxonomy_or_normalization_gap: 35 -> 33
stage3_she_gap_but_sr_available: 34 -> 29
stage3_she_to_sr_gap: 28 -> 25
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 65 -> 65
CI no_action: 490 -> 489
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2/3 Support v9 Narrow4

Source reports:

```text
pictures-json/reports/stage2_3_support_v9_artifacts_narrow4.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v9_narrow4.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v9_narrow4.*
pictures-json/reports/synthetic_observations_v10_stage2_3_support_v9_narrow4_report.*
pictures-json/reports/actual_response_samples_stage2_3_support_v9_narrow4.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v9.json
  OHS/backend/app/data/guide_support_candidates.v9.jsonl
default runtime artifacts:
  situation_context_taxonomy.v9.json
  guide_support_candidates.v9.jsonl
added support rows: 5
support candidate count: 152 -> 157
child context count: 110 -> 112
Guide mismatch: 137 -> 137
NO_TOP: 119 -> 111
stage2_taxonomy_or_normalization_gap: 39 -> 35
stage3_she_gap_but_sr_available: 36 -> 34
stage3_she_to_sr_gap: 30 -> 28
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 65 -> 65
CI no_action: 490 -> 490
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2/3 Support v8 Narrow2

Source reports:

```text
pictures-json/reports/stage2_3_support_v8_artifacts_narrow2.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v8_narrow2.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v8_narrow2.*
pictures-json/reports/synthetic_observations_v10_stage2_3_support_v10_narrow2_report.*
pictures-json/reports/actual_response_samples_stage2_3_support_v10_narrow2.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v8.json
  OHS/backend/app/data/guide_support_candidates.v8.jsonl
default runtime artifacts:
  situation_context_taxonomy.v8.json
  guide_support_candidates.v8.jsonl
added support rows: 6
support candidate count: 146 -> 152
child context count: 104 -> 110
Guide mismatch: 138 -> 137
NO_TOP: 130 -> 119
stage2_taxonomy_or_normalization_gap: 42 -> 39
stage3_she_gap_but_sr_available: 37 -> 36
stage3_she_to_sr_gap: 37 -> 30
industry_boundary_gap: 72 -> 71
workprocess_mismatch: 65 -> 65
CI no_action: 491 -> 490
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2 Service Support v7 Narrow1

Source reports:

```text
pictures-json/reports/stage2_service_support_v7_artifacts_narrow1.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_service_support_v7_narrow1.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_service_support_v7_narrow1.*
pictures-json/reports/synthetic_observations_v10_stage2_service_support_v7_narrow1_report.*
pictures-json/reports/actual_response_samples_stage2_service_support_v7_narrow1.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v7.json
  OHS/backend/app/data/guide_support_candidates.v7.jsonl
then-default runtime artifacts:
  situation_context_taxonomy.v7.json
  guide_support_candidates.v7.jsonl
added support rows: 2
support candidate count: 144 -> 146
child context count: 102 -> 104
covered Stage2 NO_TOP cases: 5
Guide mismatch: 138 -> 138
NO_TOP: 137 -> 130
stage2_taxonomy_or_normalization_gap: 47 -> 42
industry_boundary_gap: 72 -> 72
workprocess_mismatch: 65 -> 65
CI no_action: 494 -> 491
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 Confirmation Gate v2

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_stage3_domain_support2_confirmation_gate2.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_domain_support2_confirmation_gate2.*
pictures-json/reports/synthetic_observations_v10_stage3_domain_support2_confirmation_gate2_report.*
pictures-json/reports/actual_response_samples_stage3_domain_support2_confirmation_gate2.*
```

Patch summary:

```text
changed files:
  OHS/backend/app/services/situation_frame_service.py
  OHS/backend/app/services/guide_recommendation_service.py
policy: confirmation_required support can pass Guide usage/domain gates only when trigger-backed, non-broad-SR-backed, and child/profile-aligned
default support threshold: 0.78
confirmation_required support threshold: 0.54
Guide mismatch: 138 -> 138
NO_TOP: 146 -> 137
stage3_she_to_sr_gap: 46 -> 37
industry_boundary_gap: 72 -> 72
workprocess_mismatch: 65 -> 65
CI no_action: 494 -> 494
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 Domain Support v1

Source reports:

```text
pictures-json/reports/stage3_domain_support_v6_artifacts_tight1.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_domain_support1_tight1.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_domain_support1_tight1.*
```

Patch summary:

```text
generated artifacts:
  OHS/backend/app/data/situation_context_taxonomy.v6.json
  OHS/backend/app/data/guide_support_candidates.v6.jsonl
default runtime artifacts:
  situation_context_taxonomy.v6.json
  guide_support_candidates.v6.jsonl
added support rows: 3
support candidate count: 141 -> 144
child context count: 100 -> 102
asserted mapping update: 0
status/penalty/SHE approval update: 0
```

## SituationFrame Safe-Lock Fix v1

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_stage2_support_usage_gate3_safe_lock1.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_support_usage_gate3_safe_lock1.*
```

Patch summary:

```text
changed file: OHS/backend/app/services/situation_frame_service.py
safe-cue change: generic `잠금` removed from SAFE_TERMS
lockout control cue remains: 잠금표지, 잠금 표지, LOTO, lockout, tagout, 잠근 뒤, 전원 잠금
resolved missing_usage_profile cases: 5
resolved workprocess_mismatch cases: 1
new regressions in diff: 0
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2 Support Usage Gate v2b

Source reports:

```text
pictures-json/reports/stage2_support_usage_gate_artifacts_v2.*
OHS/backend/app/data/situation_context_taxonomy.v5.json
OHS/backend/app/data/guide_support_candidates.v5.jsonl
```

Artifact summary:

```text
existing context updates: 6
new support rows: 2
covered Stage2 NO_TOP cases by new seeds: 4
merged support rows: 141
taxonomy child contexts: 102
trigger-only support rows: 5
runtime use: guide_support_only
safe trigger-only suppression: enabled
resolved missing_usage_profile cases in replay: 10
status/penalty/SHE approval/asserted mapping update: 0
```

Rejected sibling experiment:

```text
stage2_support_usage_gate1 reduced NO_TOP more aggressively but regressed Guide mismatch, industry boundary quality, workprocess quality, and broad SR overreach.
Rejected trigger-only rows included display lighting, child outlet, and high-pressure wash style overmatches.
gate2b keeps only narrow support rows that passed v1~v10, v10 smoke, and actual 240 regression.
```

## Stage2 NO_TOP Support v3

Source reports:

```text
pictures-json/reports/stage2_no_top_support_candidates_v3.*
OHS/backend/app/data/situation_context_taxonomy.v3.json
OHS/backend/app/data/guide_support_candidates.v4.jsonl
```

Artifact summary:

```text
curated Stage2 contexts: 12
added support rows: 12
covered Stage2 NO_TOP cases: 20
merged support rows: 139
taxonomy child contexts: 98
runtime use: guide_support_only
new Stage2 rows require trigger hit: true
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 Support Profile Alignment v2

Source reports:

```text
pictures-json/reports/stage3_support_alignment_aliases_v2.*
OHS/backend/app/data/situation_context_taxonomy.v4.json
OHS/backend/app/data/guide_support_candidates.v4.jsonl
```

Artifact summary:

```text
seed child contexts: 7
accepted profile-alignment aliases: 18
affected support rows: 15
affected NO_TOP cases: 15
taxonomy child contexts: 98
runtime use: guide_support_only
aliases stored as profile_alignment_aliases: true
runtime extraction alias update: 0
status/penalty/SHE approval/asserted mapping update: 0
```

## NO_TOP Guide Support v1

Source reports:

```text
pictures-json/reports/no_top_guide_support_candidates_v1.*
OHS/backend/app/data/guide_support_candidates.v3.jsonl
OHS/backend/app/data/guide_support_candidates.v3.preview.jsonl
```

Artifact summary:

```text
input NO_TOP Stage3 rows: 213
Stage3 candidate input: 230
support candidate rows: 127
covered NO_TOP cases: 136
distinct child contexts: 71
distinct Guide codes: 69
runtime use: guide_support_only
status/penalty/SHE approval/asserted mapping update: 0
parent-only match: blocked
generic term-only match: blocked
```

NO_TOP root-cause audit:

```text
report: pictures-json/reports/stage2_5_no_top_root_cause_stage2_taxonomy_support_v13_narrow5.*
total_no_top: 64
primary_root_cause:
  stage2_taxonomy_or_normalization_gap: 20
  stage3_she_to_sr_gap: 22
  stage3_she_gap_but_sr_available: 11
  situation_frame_child_context_gap: 7
  synthetic_fixture_or_safe_controlled_positive: 2
  situation_frame_child_support_gap: 2
domain_bucket:
  service_healthcare_people_gap: 21
  chemical_profile_gap: 16
  other_taxonomy_gap: 9
  machine_profile_gap: 7
  construction_fall_profile_gap: 4
  material_handling_profile_gap: 3
  burn_heat_profile_gap: 2
  electrical_profile_gap: 2
situation_frame:
  child_context_available: 26
  broad_parent_without_child: 27
  support_hit_cases: 9
```

Current NO_TOP root-cause audit:

```text
report: pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v19_dropped_tool.*
total_no_top: 19
primary root causes:
  stage2_taxonomy_or_normalization_gap: 11
  stage3_she_gap_but_sr_available: 3
  stage3_she_to_sr_gap: 2
  synthetic_fixture_or_safe_controlled_positive: 2
  situation_frame_child_context_gap: 1
domain buckets:
  service_healthcare_people_gap: 7
  chemical_profile_gap: 4
  other_taxonomy_gap: 4
  construction_fall_profile_gap: 2
  machine_profile_gap: 1
  material_handling_profile_gap: 1
```

## v10 Smoke

Source report:

```text
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v18_narrow10_report.*
```

Summary:

```text
v10 cases: 330
SHE recall: 100.0%
SHE false negative: 0
SHE false positive: 0
normal suppression: 100.0%
```

## Actual Response 240 Regression

Source report:

```text
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v18_narrow10.*
```

Summary:

```text
total samples: 240
status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
attention cases: 74
penalty counts:
  conditional: 96
  no_penalty: 94
  direct: 50
```

## Historical Guide Recommendation Baseline

`usage_profile11` remains the historical Guide-only comparison baseline.

```text
synthetic Guide v1~v10 total samples: 2,360
legacy obvious top Guide mismatch: 1,145
usage_profile11 obvious top Guide mismatch: 165
reduction count: 980
reduction ratio: 85.59%
Guide-only NO_TOP: 395
Guide-only attention cases: 560
```

## Operating Note

Broadening status-level risk inference or adding generic text aliases was rejected because it changed actual 240 status boundaries. Broad `UNSAFE_TERMS` widening was also rejected because it reduced NO_TOP only slightly while regressing Guide mismatch and industry boundary quality. Trigger-only domain override was rejected because it reduced NO_TOP but reintroduced broad SR overreach. A broad Stage 2 support attempt also regressed Guide mismatch; accepted support rows are trigger-backed, support-only, and blocked in safe checklist-style contexts. Stage 3 profile-alignment aliases are accepted only because they are not extraction aliases. v14 confirmed the same rule again: short terms like `발판 없이`, `슬링`, `용접 흄`, and `보호 장갑 미착용` overmatch safe or unrelated scenes unless tied to object-specific context. Remaining quality work should use SituationFrame child contexts, Guide usage profiles, visual triggers, review-only SHE/SR support candidates, and WorkProcess relevance. The 230 Stage 3 candidates stay review-controlled; automatic approved SHE promotion and asserted mapping updates remain `0`.


## Corpus Gap Guard v1

Accepted runtime baseline: `corpus_gap_guard1`

Previous accepted baseline: `safe_scene_phrase_gate2`

This pass keeps the status/penalty/SHE/SR boundary unchanged and changes only Stage 5 standard-procedure ranking. It preserves `safe_scene_phrase_gate2` safe-scene suppression and adds compound corpus-gap top-procedure guards so lab exit checklist, medication preparation/disposal, and recycling glass-shard walking scenes are not filled by unrelated broad Guides. Rejected follow-up trials tried to force high-pressure gas-cylinder normal transport into the current Guide layer, but they moved cases to other broad Guides; that topic is deferred to WorkProcess/Guide relevance.

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_corpus_gap_guard1.*
pictures-json/reports/industry_boundary_gap_triage_corpus_gap_guard1.*
pictures-json/reports/synthetic_observations_v10_corpus_gap_guard1_report.*
pictures-json/reports/actual_response_samples_corpus_gap_guard1.*
```

Summary:

```text
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 22
NO_TOP: 85
industry_boundary_gap: 1
workprocess_mismatch: 20
broad_sr_overreach: 1
photo_unmatchable_top_count: 0
photo_unmatchable_suppressed_count: 29
followup_only_retained_count: 15
top_replaced_by_photo_actionable_count: 27
CI no_action: 482
CI context_mismatch: 11
CI broad_sr_only: 14
CI needs_review_used: 0
CI guide_boundary_mismatch: 26
v10 SHE recall: 100.0%, FN 0, FP 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
remaining industry_boundary_gap triage: C_corpus_or_followup_gap 1
backend compileall: OK
```

NO_TOP root-cause audit for corpus_gap_guard1:

```text
report: pictures-json/reports/stage2_5_no_top_root_cause_corpus_gap_guard1.*
total_no_top: 85
primary root causes:
  stage2_taxonomy_or_normalization_gap: 39
  situation_frame_child_context_gap: 22
  stage3_she_gap_but_sr_available: 10
  situation_frame_child_support_gap: 5
  stage3_she_to_sr_gap: 4
  synthetic_fixture_or_safe_controlled_positive: 3
  guide_usage_profile_context_gap: 2
```
