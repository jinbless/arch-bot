# Manual Enrichment Domain Guard Batch 002

Generated: 2026-05-09

This pilot batch was rechecked against extracted Guide JSON and normalized to the source-JSON manual review schema used for batches 003-035. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-002.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: batch 002 source-JSON pilot recheck; candidate-only
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 66 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 6 |
| Feature candidates needing review | 11 |
| SR link candidates needing review | 20 |
| Visual trigger candidates needing review | 10 |

Guides with no SR candidate:

```text
A-G-5-2025
A-G-7-2025
A-G-8-2025
A-R-1-2026
A-R-2-2026
A-R-3-2026
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| A-46-2018 | exclusive | chemical_measurement_iodine |
| A-48-2018 | exclusive | chemical_measurement_vanadium_pentoxide |
| A-G-11-2025 | domain_specific | welding_fire_blanket |
| A-G-12-2026 | general | personal_protective_equipment |
| A-G-13-2026 | domain_specific | belt_sling_rigging |
| A-G-15-2026 | general | emergency_action_plan |
| A-G-16-2026 | domain_specific | workplace_lighting_electrical |
| A-G-17-2026 | domain_specific | manual_material_handling |
| A-G-19-2026 | domain_specific | high_visibility_marking |
| A-G-2-2025 | domain_specific | workplace_access_stairs_ladders |
| A-G-20-2026 | domain_specific | grating_floor_installation |
| A-G-3-2025 | domain_specific | motorcycle_delivery |
| A-G-4-2025 | domain_specific | portable_ladder_use |
| A-G-5-2025 | exclusive | food_service_cooking_tools |
| A-G-6-2025 | exclusive | school_cafeteria_work |
| A-G-7-2025 | exclusive | apartment_security_auxiliary_work |
| A-G-8-2025 | general | incident_record_classification |
| A-G-9-2025 | domain_specific | warehouse_work |
| A-R-1-2026 | general | safety_management_system |
| A-R-2-2026 | general | production_system_lifecycle_safety |
| A-R-3-2026 | general | bowtie_risk_assessment |
| F-2-2011 | domain_specific | wood_processing_fire_explosion |
| F-3-2014 | exclusive | rigid_polyurethane_foam_fire |
| G-1-2023 | domain_specific | small_tank_drum_hot_work |
| G-10-2023 | domain_specific | workplace_transport_vehicle |
| G-100-2013 | domain_specific | forklift_operator_training |
| G-101-2013 | domain_specific | transport_vehicle_fall_prevention |
| G-102-2013 | domain_specific | farm_safety_management |
| G-106-2013 | exclusive | silica_dust_work |
| G-108-2014 | domain_specific | cultivator_farm_machinery |

## Recheck Notes

- Added `recommendation_boundary`, `negative_context_terms`, `industry_alignment`, and `notes` to match batches 003-035.
- `A-G-12` PPE, `A-G-15` emergency action plan, `A-G-16` lighting, and `A-G-4` ladder were remapped to more direct SR candidates.
- `A-R-2` and `A-R-3` were kept no-SR because they are management/risk-assessment method Guides, not direct field corrective actions.
- `F-2`, `G-1`, `G-10`, `G-100`, `G-106`, and `G-108` were corrected away from early broad electrical/fire defaults.
