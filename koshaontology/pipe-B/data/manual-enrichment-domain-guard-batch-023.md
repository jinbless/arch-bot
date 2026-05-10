# Manual Enrichment Domain Guard Domain Guard Manual Batch 023

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-023.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: inventory order excluding prior manual batches
manual_review: source-JSON reviewed on 2026-05-09
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 153 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 0 |
| SR link candidates needing review | 75 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
D-C-11/D-C-12/D-C-13/D-C-14/D-C-15: excavation/earthwork, assembled steel post, exterior wall painting, elevator shaft platform, and concrete/formwork technical-support boundaries grounded in work-area and temporary-structure cues.
D-C-3/D-C-4/D-C-5/D-C-6/D-C-8/D-C-9: steel erection, excavator, excavation slope, blasting, gang/system/slip form, and formwork/shoring profiles corrected with SR candidates from construction-specific registries.
A-1/A-10/A-11: metal workplace measurement Guides separated from field improvement procedures and kept as sampling/analysis document profiles.
A-100~A-118 subset: organic solvent/toxic substance workplace measurement Guides constrained to pump, adsorption tube, GC/FID, AAS, hood, PPE, and lab-analysis evidence so they do not over-rank as generic chemical corrective procedures.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| D-C-11-2026 | exclusive | excavation_earthwork_trench_shoring_slope_underground_utility |
| D-C-12-2026 | exclusive | assembled_steel_post_temporary_bent_shoring_bridge_support |
| D-C-13-2026 | exclusive | exterior_wall_painting_repair_rope_descent_suspended_scaffold_meWP |
| D-C-14-2026 | exclusive | elevator_shaft_temporary_work_platform_lug_bracket_lifting |
| D-C-15-2026 | exclusive | concrete_slab_formwork_shoring_gangform_slipform_vibrator |
| D-C-3-2025 | exclusive | steel_erection_deck_plate_crane_fall_protection_bolting |
| D-C-4-2025 | exclusive | excavator_operation_quick_coupler_rops_lifting_attachment |
| D-C-5-2025 | exclusive | excavation_slope_safe_gradient_geotechnical_investigation |
| D-C-6-2025 | exclusive | blasting_work_explosives_detonator_wiring_charge_evacuation |
| D-C-8-2026 | exclusive | gang_form_system_form_slip_form_climbing_platform_crane_lift |
| D-C-9-2026 | exclusive | formwork_shoring_material_inspection_system_support_concrete_pour |
| A-1-2018 | exclusive | work_environment_measurement_analysis_구리 |
| A-10-2018 | exclusive | work_environment_measurement_analysis_알루미늄 |
| A-100-2018 | exclusive | work_environment_measurement_analysis_디메틸아닐린 |
| A-101-2018 | exclusive | work_environment_measurement_analysis_테트라하이드로퓨란 |
| A-102-2018 | exclusive | work_environment_measurement_analysis_황산디메틸 |
| A-103-2018 | exclusive | work_environment_measurement_analysis_요오드화메틸 |
| A-104-2018 | exclusive | work_environment_measurement_analysis_메틸에틸케톤 |
| A-105-2018 | exclusive | work_environment_measurement_analysis_디이소부틸케톤 |
| A-106-2018 | exclusive | work_environment_measurement_analysis_메틸_n_부틸케톤 |
| A-107-2018 | exclusive | work_environment_measurement_analysis_메틸_n_아밀케톤 |
| A-108-2018 | exclusive | work_environment_measurement_analysis_메틸이소부틸케톤 |
| A-11-2018 | exclusive | work_environment_measurement_analysis_은 |
| A-110-2018 | exclusive | work_environment_measurement_analysis_아세톤 |
| A-111-2018 | exclusive | work_environment_measurement_analysis_비닐아세테이트 |
| A-112-2018 | exclusive | work_environment_measurement_analysis_스토다드솔벤트 |
| A-113-2018 | exclusive | work_environment_measurement_analysis_아세토니트릴 |
| A-115-2018 | exclusive | work_environment_measurement_analysis_nn_디메틸아세트아미드 |
| A-116-2018 | exclusive | work_environment_measurement_analysis_14_디옥산 |
| A-118-2018 | exclusive | work_environment_measurement_analysis_에틸렌글리콜모노메틸에테르 |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
