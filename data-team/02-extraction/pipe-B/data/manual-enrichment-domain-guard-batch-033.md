# Manual Enrichment Domain Guard Batch 033

Generated: 2026-05-09

This batch was manually re-read from extracted Guide JSON by Codex. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-033.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: batch 033 source-JSON manual review; candidate-only
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 62 |
| SR link candidates | 85 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 9 |
| Feature candidates needing review | 40 |
| SR link candidates needing review | 16 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
H-4-2021
H-43-2021
H-47-2021
H-50-2021
H-72-2015
H-74-2015
H-75-2015
H-81-2021
H-83-2021
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| H-4-2021 | domain_specific | general_health_exam_aftercare |
| H-41-2021 | domain_specific | chest_radiology_abnormality_followup |
| H-42-2021 | domain_specific | chemical_protective_glove_selection |
| H-43-2021 | exclusive | exercise_stress_test_fit_for_work |
| H-44-2021 | domain_specific | respiratory_sensitizer_exposure_health_management |
| H-45-2022 | domain_specific | special_health_exam_pre_survey |
| H-46-2021 | domain_specific | asthma_fit_for_work_assessment |
| H-47-2021 | domain_specific | long_working_hours_health_management |
| H-48-2020 | domain_specific | occupational_cancer_work_relatedness_assessment |
| H-49-2021 | domain_specific | autumn_febrile_vector_borne_disease_prevention |
| H-5-2021 | domain_specific | influenza_pandemic_workplace_management |
| H-50-2021 | domain_specific | cardio_cerebrovascular_return_to_work_fit_assessment |
| H-51-2021 | domain_specific | skin_sensitizer_contact_dermatitis_health_management |
| H-52-2021 | domain_specific | lumbar_instability_fit_for_work_assessment |
| H-53-2021 | exclusive | hospital_anesthetic_gas_exposure_control |
| H-56-2023 | exclusive | pure_tone_audiometry_protocol |
| H-57-2023 | domain_specific | worksite_emergency_response_system |
| H-59-2021 | general | field_cpr_first_aid |
| H-6-2020 | domain_specific | antimony_exposure_worker_health_management |
| H-62-2021 | exclusive | ionizing_radiation_worker_health_management |
| H-70-2020 | exclusive | asbestos_removal_work_control |
| H-71-2015 | domain_specific | organic_compound_handling_health_control |
| H-72-2015 | exclusive | sorbent_tube_thermal_desorption_gc_analysis |
| H-73-2015 | domain_specific | welding_fume_health_management |
| H-74-2015 | exclusive | pump_sorbent_tube_thermal_desorption_gc_analysis |
| H-75-2015 | domain_specific | work_environment_evaluation_and_improvement |
| H-77-2012 | domain_specific | local_vibration_measurement_evaluation |
| H-78-2012 | exclusive | uv_sterilizer_exposure_evaluation |
| H-81-2021 | exclusive | chemical_genotoxicity_lab_test_protocol |
| H-83-2021 | exclusive | acute_dermal_toxicity_animal_lab_test_protocol |

## Manual Correction Notes

- `H-42`/`H-51`: 보호장갑·피부감작물질은 화학물질 피부노출 문맥으로 묶되, 일반 장갑 사진에는 과추천하지 않도록 required context를 둔다.
- `H-53`: 병원 수술실 마취가스 배기·환기 문맥이 없으면 배타 제외한다.
- `H-62`/`H-78`: 전리방사선과 자외선 소독기 노출평가를 분리했다. 자외선은 현재 taxonomy/SR gap으로 약한 후보만 둔다.
- `H-70`: 석면해체 전용 경계로 유지하고 일반 철거·분진 작업과 분리한다.
- `H-72`/`H-74`/`H-81`/`H-83`: 분석실·독성시험 프로토콜이라 현장 안전조치 추천에서는 기본 제외한다.
