# Manual Enrichment Domain Guard Batch 032

Generated: 2026-05-09

This batch was manually re-read from extracted Guide JSON by Codex. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-032.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: batch 032 source-JSON manual review; candidate-only
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 104 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 5 |
| Feature candidates needing review | 38 |
| SR link candidates needing review | 39 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
H-201-2018
H-203-2018
H-204-2018
H-211-2020
H-37-2021
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| H-195-2021 | domain_specific | worker_fit_for_work_assessment |
| H-197-2021 | exclusive | workplace_tuberculosis_case_management |
| H-199-2018 | exclusive | asbestos_removal_supervision_audit |
| H-2-2010 | exclusive | methacholine_airway_hyperresponsiveness_test |
| H-200-2018 | domain_specific | cardiovascular_risk_assessment_followup |
| H-201-2018 | general | corporate_health_promotion_index |
| H-203-2018 | domain_specific | customer_service_worker_health_manual |
| H-204-2018 | domain_specific | workplace_bullying_prevention_management |
| H-205-2018 | domain_specific | health_hazard_risk_assessment |
| H-206-2020 | domain_specific | liver_biliary_abnormality_worker_management |
| H-207-2020 | domain_specific | lead_blood_level_management |
| H-208-2020 | domain_specific | urinary_abnormality_worker_management |
| H-209-2022 | exclusive | indium_biological_exposure_indicator_analysis |
| H-21-2021 | exclusive | lead_biological_exposure_indicator_analysis |
| H-211-2020 | general | workplace_oral_health_promotion_program |
| H-212-2022 | exclusive | call_center_infectious_disease_office_environment |
| H-213-2021 | domain_specific | dichloropropane_worker_health_management |
| H-214-2021 | domain_specific | cancer_survivor_fit_for_work_assessment |
| H-215-2021 | domain_specific | workplace_radon_measurement_reduction |
| H-217-2022 | domain_specific | night_work_special_health_exam_followup |
| H-218-2022 | domain_specific | night_shift_sleep_disorder_followup |
| H-22-2019 | domain_specific | shift_work_health_management |
| H-220-2023 | domain_specific | emerging_airborne_infectious_disease_prevention_bcp |
| H-222-2023 | domain_specific | driver_fit_for_work_assessment |
| H-223-2023 | exclusive | special_health_neurobehavioral_test_protocol |
| H-25-2011 | domain_specific | building_cleaner_msd_slip_chemical_prevention |
| H-26-2020 | domain_specific | kitchen_cook_ergonomic_heat_health |
| H-3-2010 | exclusive | occupational_asthma_peak_flow_monitoring |
| H-36-2021 | domain_specific | major_accident_acute_stress_response |
| H-37-2021 | domain_specific | workplace_suicide_depression_prevention |

## Manual Correction Notes

- `H-197`/`H-220`: bounded to workplace tuberculosis and emerging airborne infectious disease response, not generic mask photos.
- `H-199`/`H-193` family: asbestos removal supervision separated from generic demolition.
- `H-209`/`H-21`: kept as biological exposure indicator analysis protocols, not field exposure controls.
- `H-207`/`H-213`: lead and 1,2-dichloropropane worker health-management Guides connected to named chemical/PPE/SR candidates.
- `H-212`: call-center infection office-environment profile tied to cubicles, HVAC, background noise, and hygiene cues.
- `H-25`/`H-26`: cleaner and cooking worker Guides mapped to ergonomic, slip, heat, and cleaning/kitchen work context.
- `H-201`/`H-203`/`H-204`/`H-211`/`H-37`: management or psychosocial Guides kept no-SR where registry coverage is absent.

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`. Asserted mapping updates must remain 0.
