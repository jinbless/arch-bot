# Manual Enrichment Domain Guard Batch 004

Generated: 2026-05-09  
Manual reviewed: 2026-05-09

This batch was re-read manually by Codex from `pipe-B/data/ci-output/ci-*.json`. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-004.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: inventory order excluding prior manual batches
curation_policy: batch_004_source_json_manual_read
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 48 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 4 |

Guides with no SR candidate:

```text
G-65-2011
G-66-2011
G-71-2011
G-93-2012
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| G-52-2017 | domain_specific | liquid_chemical_piping_construction |
| G-53-2013 | domain_specific | event_crowd_emergency_safety |
| G-55-2012 | domain_specific | vehicle_repair_lift_pit_electrical |
| G-6-2011 | domain_specific | industrial_waste_site_transport_machine |
| G-60-2012 | domain_specific | building_facility_maintenance |
| G-64-2011 | domain_specific | logging_site_first_aid |
| G-65-2011 | general | disabled_worker_task_accommodation |
| G-66-2011 | general | foreign_worker_multilingual_risk_management |
| G-67-2011 | domain_specific | building_exterior_rope_access_cleaning |
| G-70-2011 | domain_specific | zoo_animal_handling_worker_safety |
| G-71-2011 | general | safety_health_benchmarking |
| G-73-2011 | domain_specific | cattle_barn_handling_safety |
| G-76-2011 | domain_specific | air_jacket_gas_manifold_welding_support |
| G-78-2021 | exclusive | hazardous_tank_lorry_loading_static_control |
| G-82-2018 | exclusive | laboratory_chemical_experiment_safety |
| G-87-2012 | general | older_worker_task_adaptation |
| G-88-2012 | domain_specific | roadside_tree_pruning_pesticide_work |
| G-89-2012 | domain_specific | hotel_housekeeping_cleaning |
| G-9-2013 | exclusive | hazardous_material_workplace_signage |
| G-90-2015 | domain_specific | manual_transport_cart_handling |
| G-91-2012 | domain_specific | patient_transfer_hoist_sling |
| G-93-2012 | general | older_worker_safety_training |
| G-94-2012 | general | work_ability_promotion_program |
| G-95-2012 | general | safe_design_lifecycle |
| G-96-2012 | general | human_error_ergonomic_management |
| G-99-2013 | domain_specific | workplace_meeting_crowd_safety |
| X-10-2012 | domain_specific | cold_contact_surface_risk_assessment |
| X-12-2012 | domain_specific | forestry_work_risk_management |
| X-15-2012 | domain_specific | cold_work_risk_management |
| X-27-2012 | exclusive | chemical_process_control_instructions |

## Manual Corrections

The generated draft had several broad keyword errors, including event safety as generic fire/electric, vehicle repair as only electrical work, and transport carts as kitchen/food preparation. These were corrected to source-specific crowd/event, vehicle maintenance, waste handling, rope access, animal handling, tanker static control, laboratory, cleaning, and cold-work profiles.

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`. Asserted mapping updates must remain 0.
