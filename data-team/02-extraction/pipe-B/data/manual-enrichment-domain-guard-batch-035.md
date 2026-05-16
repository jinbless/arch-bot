# Manual Enrichment Domain Guard Batch 035

Generated: 2026-05-09

This batch was manually re-read from extracted Guide JSON by Codex. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-035.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: batch 035 source-JSON manual review; candidate-only
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 18 |
| Guide domain profiles | 18 |
| Feature candidates | 38 |
| SR link candidates | 42 |
| Visual trigger candidates | 36 |
| Guides with no SR candidate | 5 |
| Feature candidates needing review | 23 |
| SR link candidates needing review | 15 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
W-22-2016
W-4-2021
W-5-2021
W-8-2021
W-9-2021
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| W-15-2020 | domain_specific | safety_data_sheet_authoring |
| W-16-2020 | domain_specific | chemical_hazard_classification_ghs |
| W-17-2015 | domain_specific | cold_work_environment_management |
| W-19-2012 | domain_specific | pesticide_application_worker_safety_health |
| W-2-2021 | domain_specific | safety_data_sheet_reliability_evaluation |
| W-20-2012 | domain_specific | nanomaterial_manufacturing_handling_worker_control |
| W-21-2019 | exclusive | biosafety_level_3_laboratory_safety_health |
| W-22-2016 | exclusive | non_ionizing_electromagnetic_field_measurement_evaluation |
| W-23-2016 | domain_specific | workplace_noise_measurement_evaluation |
| W-24-2017 | domain_specific | airborne_manufactured_nanomaterial_exposure_assessment |
| W-25-2017 | domain_specific | carbon_nanotube_exposure_concentration_management |
| W-26-2022 | exclusive | institutional_food_service_ventilation |
| W-3-2021 | exclusive | biosafety_level_1_2_laboratory_safety_health |
| W-4-2021 | exclusive | chronic_toxicity_animal_test_protocol |
| W-5-2021 | exclusive | acute_oral_toxicity_toxic_class_method |
| W-6-2021 | domain_specific | chemical_hazard_risk_assessment_document |
| W-8-2021 | exclusive | acute_inhalation_toxicity_test_protocol |
| W-9-2021 | exclusive | skin_sensitization_animal_test_protocol |

## Manual Correction Notes

- `W-15`/`W-16`/`W-2`/`W-6`: SDS, GHS, 신뢰성평가, 유해성·위험성 평가는 문서 profile로 두고 직접 현장 조치 후보로 승격하지 않는다.
- `W-17`: 한랭작업은 등가냉각온도, 방한보호구, 저체온증·동상 단서로 경계를 잡았다.
- `W-19`: 농약방제는 농약/훈증/방제복/출입제한 단서가 있어야 chemical/CONFINED 후보와 결합한다.
- `W-20`/`W-24`/`W-25`: 나노물질 일반, 공기 중 노출평가, 탄소나노튜브 농도관리를 서로 분리했다.
- `W-21`/`W-3`: 생물안전 3등급과 1·2등급 실험실을 각각 배타 profile로 분리했다.
- `W-26`: 단체급식시설 환기는 급식 조리실 후드/덕트/배풍량 단서가 있을 때만 추천되도록 했다.
