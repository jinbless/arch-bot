# Manual Domain Guard Semantic Audit

Generated: 2026-05-09

This audit checks the semantic fit of the 35 candidate-only manual enrichment batches. It does not call external APIs, does not import to PostgreSQL, and does not promote asserted mappings.

## Summary

| Item | Count |
|---|---:|
| Batch files | 35 |
| Guides | 1038 |
| Guides with any flag | 747 |
| High-risk guides | 0 |
| Total flags | 2112 |
| Guides with no SR candidate | 76 |

## Severity Counts

| Severity | Count |
|---|---:|
| low | 817 |
| medium | 1295 |

## Issue Counts

| Issue | Count |
|---|---:|
| high_conf_sr_lacks_profile_token_overlap | 810 |
| sr_category_context_mismatch | 498 |
| generic_feature_only_for_exclusive | 336 |
| document_profile_has_many_generic_control_sr | 175 |
| too_many_sr_candidates | 98 |
| exclusive_without_negative_context | 78 |
| exclusive_without_industry_alignment | 62 |
| required_terms_not_grounded | 28 |
| operational_guide_without_sr_candidate | 17 |
| physical_guide_has_document_only_visual_triggers | 7 |
| method_or_planning_profile_has_field_control_sr | 3 |

## Top Overused SR Candidates

High counts are not automatically wrong, but broad SRs used across many unrelated domain families are likely to need ranking dampening or review-only treatment.

| SR | Count | Distinct domain families | Title |
|---|---:|---:|---|
| SR-PPE-002 | 275 | 251 | 보호구의 지급 등 |
| SR-CHEMICAL-024 | 268 | 244 | 유해성 등의 주지 |
| SR-CHEMICAL-025 | 199 | 185 | 호흡용 보호구의 지급 등 |
| SR-CHEMICAL-026 | 185 | 162 | 보호복 등의 비치 등 |
| SR-FIRE_EXPLOSION-015 | 126 | 119 | 위험물 등이 있는 장소에서 화기 등의 사용 금지 |
| SR-MGMT-004 | 106 | 106 | 사전조사 및 작업계획서의 작성 등 |
| SR-ELECTRIC-024 | 87 | 87 | 정전기로 인한 화재 폭발 등 방지 |
| SR-FIRE_EXPLOSION-019 | 83 | 83 | 소화설비 |
| SR-ELECTRIC-011 | 80 | 80 | 폭발위험장소에서 사용하는 전기 기계ㆍ기구의 선정 등 |
| SR-FIRE_EXPLOSION-008 | 67 | 67 | 폭발 또는 화재 등의 예방 |
| SR-FIRE_EXPLOSION-001 | 57 | 57 | 위험물질 등의 제조 등 작업 시의 조치 |
| SR-FIRE_EXPLOSION-037 | 52 | 52 | 안전밸브 등의 설치 |
| SR-CHEMICAL-014 | 47 | 47 | 사고 시의 대피 등 |
| SR-MACHINE-003 | 44 | 44 | 기계의 동력차단장치 |
| SR-MACHINE-002 | 42 | 42 | 원동기ㆍ회전축 등의 위험 방지 |
| SR-FALL-001 | 41 | 41 | 추락의 방지 |
| SR-CHEMICAL-010 | 41 | 41 | 경보설비 등 |
| SR-FIRE_EXPLOSION-049 | 41 | 41 | 계측장치 등의 설치 |
| SR-MGMT-001 | 41 | 41 | 관리감독자의 유해ㆍ위험 방지 업무 등 |
| SR-MACHINE-007 | 39 | 39 | 정비 등의 작업 시의 운전정지 등 |

## Watch Guides

| Guide | Profile | Domain family | Flags | Issues |
|---|---|---|---:|---|
| A-G-18-2026 | exclusive | port_cargo | 2 | high_conf_sr_lacks_profile_token_overlap, high_conf_sr_lacks_profile_token_overlap |
| G-116-2014 | exclusive | shipbuilding_dock | 0 |  |
| B-5-2011 | exclusive | shipbuilding_general | 1 | operational_guide_without_sr_candidate |
| B-M-11-2025 | domain_specific | forklift_operation | 0 |  |
| B-M-32-2026 | domain_specific | steel_product_storage | 1 | sr_category_context_mismatch |
| A-G-10-2025 | exclusive | food_service_facility | 1 | operational_guide_without_sr_candidate |
| B-E-21-2026 | domain_specific | hazardous_area_electrical | 0 |  |
| D-57-2016 | domain_specific | acute_toxic_gas_loading | 1 | sr_category_context_mismatch |
| C-C-16-2026 | exclusive | chemical_eyewash_shower_corrosive_exposure | 1 | generic_feature_only_for_exclusive |
| B-E-3-2025 | exclusive | substation_pressurization_positive_pressure | 1 | generic_feature_only_for_exclusive |
| H-110-2013 | exclusive | crystalline_silica_exposure | 3 | generic_feature_only_for_exclusive, high_conf_sr_lacks_profile_token_overlap, high_conf_sr_lacks_profile_token_overlap |
| H-221-2023 | domain_specific | logistics_center_air_quality | 0 |  |

## High-Risk Examples

| Guide | Issue | Message |
|---|---|---|


## Interpretation

- These are review queues, not automatic fixes.
- The strongest risk is document/analysis/medical Guides receiving operational field-control SRs.
- The second risk is broad chemical/PPE/workplace SRs appearing across too many unrelated domain families.
- Candidate JSON remains candidate-only; asserted mapping update count remains zero.
