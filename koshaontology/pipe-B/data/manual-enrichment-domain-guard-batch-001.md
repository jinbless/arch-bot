# Manual Enrichment Domain Guard Batch 001

Generated: 2026-05-09

This pilot batch was rechecked against extracted Guide JSON and normalized to the source-JSON manual review schema used for batches 003-035. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-001.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: batch 001 source-JSON pilot recheck; candidate-only
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 65 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 3 |
| Feature candidates needing review | 0 |
| SR link candidates needing review | 3 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
B-5-2011
A-G-10-2025
O-1-2011
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| A-G-18-2026 | exclusive | port_cargo |
| G-116-2014 | exclusive | shipbuilding_dock |
| B-5-2011 | exclusive | shipbuilding_general |
| B-M-11-2025 | domain_specific | forklift_operation |
| B-M-32-2026 | domain_specific | steel_product_storage |
| A-G-10-2025 | exclusive | food_service_facility |
| B-E-21-2026 | domain_specific | hazardous_area_electrical |
| D-57-2016 | domain_specific | acute_toxic_gas_loading |
| C-C-16-2026 | exclusive | chemical_eyewash_shower |
| B-E-3-2025 | exclusive | substation_pressurization |
| B-E-19-2026 | exclusive | lightning_protection |
| H-110-2013 | exclusive | crystalline_silica_exposure |
| H-221-2023 | domain_specific | logistics_center_air_quality |
| A-G-14-2026 | domain_specific | hot_work_welding_fire |
| D-C-10-2026 | domain_specific | construction_equipment_lift_plan |
| B-M-9-2025 | domain_specific | mobile_crane_stability |
| A-G-1-2025 | domain_specific | fall_protection_net |
| B-E-20-2026 | exclusive | electrostatic_painting |
| D-C-7-2026 | domain_specific | scaffold_work |
| M-1-2013 | exclusive | cnc_lathe_flying_workpiece |
| P-24-2012 | exclusive | hydrocarbon_tank_abrasive_blasting |
| B-M-33-2026 | domain_specific | conveyor_safety |
| E-M-4-2025 | exclusive | bloodborne_pathogen_lab_healthcare |
| D-C-2-2025 | domain_specific | bridge_superstructure_construction |
| O-1-2011 | domain_specific | welding_material_selection |
| B-M-8-2025 | domain_specific | mobile_crane_operation |
| D-53-2013 | exclusive | hydrogen_peroxide_storage |
| G-29-2011 | domain_specific | excavation_underground_utility |
| H-115-2013 | exclusive | hydrogen_cyanide_emergency |
| P-10-2012 | exclusive | chlorine_facility |

## Recheck Notes

- Added `recommendation_boundary`, `negative_context_terms`, `industry_alignment`, and `notes` to match batches 003-035.
- `B-M-11`, `M-1`, and `B-M-33` received vehicle/machine/conveyor SR candidates instead of remaining no-SR or using broad construction equipment defaults.
- `E-M-4` was corrected from a chemical SR default to pathogen/PPE candidates.
- `H-110` was strengthened as crystalline silica/dust rather than generic chemical exposure.
