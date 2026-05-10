# Manual Enrichment Domain Guard Batch 034

Generated: 2026-05-09

This batch was manually re-read from extracted Guide JSON by Codex. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-034.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: batch 034 source-JSON manual review; candidate-only
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 63 |
| SR link candidates | 33 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 21 |
| Feature candidates needing review | 55 |
| SR link candidates needing review | 13 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
H-91-2021
H-97-2021
H-99-2023
T-16-2021
T-17-2021
T-19-2020
T-20-2020
T-21-2017
T-22-2021
T-23-2021
T-26-2023
T-28-2018
T-3-2015
T-32-2021
T-33-2023
T-4-2022
T-5-2017
T-6-2017
T-7-2020
T-9-2016
W-10-2023
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| H-91-2021 | domain_specific | worker_fatigue_assessment_management |
| H-92-2012 | domain_specific | electroplating_worker_health_management |
| H-93-2021 | exclusive | healthcare_airborne_infectious_disease_management |
| H-94-2021 | domain_specific | livestock_epidemic_disinfection_worker_self_care |
| H-95-2021 | domain_specific | copd_worker_health_management |
| H-96-2021 | domain_specific | workplace_disease_cluster_investigation |
| H-97-2021 | domain_specific | hematologic_test_abnormality_worker_management |
| H-98-2021 | domain_specific | diabetes_worker_health_management |
| H-99-2023 | exclusive | carbon_monoxide_biological_exposure_indicator_analysis |
| T-12-2022 | exclusive | laboratory_animal_facility_management |
| T-16-2021 | exclusive | single_cell_gel_electrophoresis_genotoxicity_test |
| T-17-2021 | exclusive | mammalian_bone_marrow_chromosome_aberration_test |
| T-19-2020 | exclusive | acute_oral_toxicity_fixed_dose_test |
| T-20-2020 | exclusive | acute_eye_corrosion_irritation_test |
| T-21-2017 | exclusive | reproductive_next_generation_toxicity_test |
| T-22-2021 | exclusive | rodent_dominant_lethal_genotoxicity_test |
| T-23-2021 | exclusive | mammalian_spermatogonial_chromosome_aberration_test |
| T-26-2023 | exclusive | laboratory_animal_necropsy_gross_findings |
| T-27-2022 | exclusive | laboratory_animal_tissue_trimming |
| T-28-2018 | exclusive | acute_inhalation_toxicity_fixed_concentration_test |
| T-3-2015 | exclusive | manufactured_nanomaterial_test_sample_dosimetry |
| T-31-2021 | exclusive | laboratory_animal_tissue_sectioning_staining |
| T-32-2021 | exclusive | laboratory_animal_bronchoalveolar_lavage_test |
| T-33-2023 | exclusive | adverse_outcome_pathway_development_document |
| T-4-2022 | exclusive | ninety_day_repeated_inhalation_toxicity_test |
| T-5-2017 | exclusive | prenatal_developmental_toxicity_test |
| T-6-2017 | exclusive | reproductive_developmental_toxicity_screening_test |
| T-7-2020 | exclusive | in_vitro_mammalian_cell_micronucleus_test |
| T-9-2016 | exclusive | asbestos_body_fiber_biological_sample_analysis |
| W-10-2023 | exclusive | carcinogenicity_animal_test_protocol |

## Manual Correction Notes

- `H-92`: 전기도금은 산세·시안화합물·도금조·국소배기 단서가 있는 화학물질 현장 profile로 강화했다.
- `H-93`: 의료기관 공기매개 감염병은 병원/격리병동/예방접종/노출 후 관리 문맥이 없으면 배타 제외한다.
- `H-94`: 구제역 방역작업은 생물학적 방역과 소독제 화학노출을 함께 보되 축산 방역 단서를 요구한다.
- `H-99`, `T-*`, `W-10`: 생물학적 노출지표·독성시험·조직병리 프로토콜은 현장 시정조치로 직접 전환하지 않도록 no-SR 또는 weak SR 후보로 제한했다.
- `T-9`: 석면해체 작업이 아니라 생체시료 중 석면소체/섬유 분석법으로 분리했다.
