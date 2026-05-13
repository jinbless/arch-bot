# Evaluation Baseline

Latest updated: 2026-05-13

Accepted runtime baseline: `ci_wp_relevance8d_profile_tight2_ci_safe_gate`

Previous accepted baseline: `ci_wp_relevance7_profile_tight1`

The full report bodies under `pictures-json/reports/**` are local/external artifacts. Root git tracks `pictures-json/reports-manifest.json` and this summary instead of adding historical report files to repository history.

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
photo_actionable: 637
photo_conditional_followup: 36
photo_unmatchable: 365
measurement_analysis role overrides: 8 field-action Guides restored to photo_actionable
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
pictures-json/reports/pipeline_quality_v1_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate.*
```

Summary:

```text
total samples: 2,360
Stage failure counts:
  stage2: 775
  stage3: 1,288
  stage4: 612
  stage5: 546
SHE TP/FN/FP: 1,107 / 909 / 82
SHE recall: 54.9%
SR TP/FN/FP: 1,414 / 270 / 211
SR recall: 84.0%
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
```

Comparison against `ci_wp_relevance7_profile_tight1`:

```text
SHE/SR status metrics: unchanged
Guide mismatch: 110 -> 87
Stage 2~5 NO_TOP: 24 -> 26
industry_boundary_gap: 70 -> 70
workprocess_mismatch: 39 -> 16
broad_sr_overreach: 1 -> 1
CI no_action: 481 -> 438
CI context_mismatch: 16 -> 16
CI broad_sr_only: 16 -> 14
CI guide_boundary_mismatch: 50 -> 48
photo_unmatchable_top_count: 0 -> 0
photo_unmatchable_suppressed_count: 16 -> 13
top_replaced_by_photo_actionable_count: 14 -> 17
```

## CI/WP Relevance8d Profile Tight2 CI Safe Gate

`ci_wp_relevance8d_profile_tight2_ci_safe_gate` keeps the `ci_wp_relevance7_profile_tight1` status/penalty/SHE/SR boundary and changes only Stage 5 Guide/WorkProcess/CI relevance. It tightens selected feature-only overpromotion Guides, reorders primary WorkProcess IDs for concrete photo-actionable Guides, and allows same-top-Guide local CI fallback only when observable violation context is present and non-negated safe-control wording is absent. The accepted guard specifically blocks fallback on safe/normal contexts such as `완비`, `정상`, `보관 중`, `준비 중`, and `조립 전`.

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate.*
pictures-json/reports/synthetic_observations_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate_report.*
pictures-json/reports/actual_response_samples_ci_wp_relevance8d_profile_tight2_ci_safe_gate.*
```

Validation:

```text
v10 SHE recall: 100.0%
v10 SHE false negative: 0
v10 SHE false positive: 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
asserted mapping update: 0
runtime SHE approved update: 0
legal SR evidence change: 0
public API shape change: none
```

## CI/WP Relevance7 Profile Tight1

`ci_wp_relevance7_profile_tight1` keeps the v20 status/penalty/SHE/SR boundary and changes only Stage 5 recommendation relevance. It tightens three over-broad photo-top Guide usage profiles: `H-192-2021` (제련작업자 건강관리), `O-1-2011` (설비보수용 용접재료 선정), and `G-28-2016` (요양시설 안전). These Guides now require their own observable/domain terms instead of being promoted by broad heat, welding, or burn features. The NO_TOP increase is intentional: the added NO_TOP cases are safe-controlled positives, out-of-scope public/customer/animal safety cases, corpus gaps without an exact photo-actionable Guide, or previously wrong support-candidate links.

Source reports:

```text
pictures-json/reports/pipeline_quality_v1_v10_ci_wp_relevance7_profile_tight1.*
pictures-json/reports/stage2_5_no_top_root_cause_ci_wp_relevance7_profile_tight1.*
pictures-json/reports/stage2_5_no_top_actionability_ci_wp_relevance7_profile_tight1.*
pictures-json/reports/synthetic_observations_v10_ci_wp_relevance7_profile_tight1_report.*
pictures-json/reports/actual_response_samples_ci_wp_relevance7_profile_tight1.*
```

Validation:

```text
v10 SHE recall: 100.0%
v10 SHE false negative: 0
v10 SHE false positive: 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
NO_TOP actionability: runtime repair candidates 0 / outside scope 10 / safe-controlled 7 / corpus gap 3 / reject stale support 2 / follow-up only 2
asserted mapping update: 0
runtime SHE approved update: 0
legal SR evidence change: 0
public API shape change: none
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
