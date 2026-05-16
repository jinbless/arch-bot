# Manual Enrichment Domain Guard Batch 031

Generated: 2026-05-09

This batch was manually re-read from extracted Guide JSON by Codex. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-031.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: batch 031 source-JSON manual review; candidate-only
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 148 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 2 |
| Feature candidates needing review | 19 |
| SR link candidates needing review | 31 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
H-162-2023
H-163-2021
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| H-155-2019 | exclusive | radiation_nondestructive_testing |
| H-158-2021 | domain_specific | chemical_sds_training |
| H-16-2021 | exclusive | fluoride_biological_exposure_indicator_analysis |
| H-160-2014 | domain_specific | hearing_protection_fit_management |
| H-162-2023 | general | workplace_health_promotion_program |
| H-163-2021 | domain_specific | customer_emotional_labor_assessment |
| H-169-2015 | domain_specific | diesel_engine_exhaust_exposure |
| H-17-2021 | exclusive | cadmium_biological_exposure_indicator_analysis |
| H-170-2015 | domain_specific | indium_itoc_dust_exposure_management |
| H-171-2023 | exclusive | tmah_semiconductor_corrosive_poisoning |
| H-172-2015 | domain_specific | asphalt_paving_fume_heat_exposure |
| H-173-2015 | domain_specific | dye_dust_process_exposure |
| H-175-2015 | domain_specific | sanitation_worker_washing_facility |
| H-176-2015 | domain_specific | older_worker_health_checklist |
| H-177-2015 | domain_specific | hand_arm_vibration_tool_management |
| H-178-2022 | domain_specific | worker_rest_facility_installation |
| H-180-2021 | exclusive | methanol_acute_poisoning_clinical_response |
| H-181-2021 | exclusive | chlorine_acute_poisoning_clinical_response |
| H-182-2021 | exclusive | formic_acid_acute_poisoning_clinical_response |
| H-183-2021 | exclusive | ethylene_glycol_acute_poisoning_clinical_response |
| H-184-2021 | exclusive | ethylene_oxide_acute_poisoning_clinical_response |
| H-186-2016 | domain_specific | airborne_infectious_disease_workplace_prevention |
| H-187-2021 | general | industrial_accident_first_aid |
| H-188-2021 | domain_specific | worker_chronic_kidney_disease_management |
| H-189-2021 | domain_specific | worker_epilepsy_fit_for_work_management |
| H-190-2021 | domain_specific | shift_worker_chronic_disease_management |
| H-191-2021 | exclusive | livestock_culling_burial_biohazard |
| H-192-2021 | domain_specific | smelting_worker_metal_fume_heat_noise |
| H-193-2021 | exclusive | asbestos_removal_worker_health_management |
| H-194-2021 | domain_specific | occupational_disease_work_relatedness_assessment |

## Manual Correction Notes

- `H-155`: hot-work default corrected to radiation nondestructive testing, management area, shielding, and dosimeter context.
- `H-158`: bounded to SDS/MSDS education, warning labels, and chemical-handling training.
- `H-16`/`H-17`: kept as biological exposure indicator analysis protocols, not field emergency guides.
- `H-160`/`H-177`: separated into hearing-protection and hand-arm vibration tool management profiles.
- `H-180`~`H-184`: acute poisoning clinical response Guides kept exclusive to named chemical emergency context.
- `H-191`: livestock culling/burial health Guide linked to biohazard plus excavation context.
- `H-193`: asbestos removal worker health Guide made exclusive to asbestos removal/protection cues.
- `H-162`/`H-163`/`H-188`~`H-190`: health-management/taxonomy-gap Guides kept weak or no-SR to avoid legal overclaiming.

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`. Asserted mapping updates must remain 0.
