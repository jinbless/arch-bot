# Manual Enrichment Domain Guard Batch 003

Generated: 2026-05-09  
Manual reviewed: 2026-05-09

This batch was re-read manually by Codex from `pipe-B/data/ci-output/ci-*.json`. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-003.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: inventory order excluding prior manual batches
curation_policy: batch_003_source_json_manual_read
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 48 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 5 |

Guides with no SR candidate:

```text
G-120-2015
G-135-2021
G-23-2011
G-37-2012
G-5-2017
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| G-11-2017 | domain_specific | slip_trip_fall_prevention |
| G-110-2014 | domain_specific | waste_paper_baler_conveyor |
| G-111-2014 | domain_specific | agricultural_machine_whole_body_vibration |
| G-112-2014 | domain_specific | tree_climbing_ladder_work |
| G-117-2014 | exclusive | ship_interior_spray_painting |
| G-120-2015 | general | human_error_prevention |
| G-121-2015 | domain_specific | illuminance_meter_measurement |
| G-125-2017 | domain_specific | earthquake_emergency_response |
| G-126-2018 | exclusive | explosives_factory_process |
| G-131-2020 | domain_specific | municipal_waste_collection_compactor |
| G-133-2020 | domain_specific | wire_rope_sling_rigging |
| G-134-2023 | domain_specific | chain_sling_rigging |
| G-135-2021 | domain_specific | smart_factory_safety_assessment |
| G-14-2011 | exclusive | human_subject_vibration_experiment |
| G-17-2017 | domain_specific | compressed_air_system_safety |
| G-20-2011 | domain_specific | steel_material_storage_handling |
| G-23-2011 | general | return_to_work_rehabilitation |
| G-24-2011 | exclusive | radioactive_material_machine_safety |
| G-26-2013 | domain_specific | workplace_lighting_design |
| G-28-2016 | domain_specific | care_facility_slip_burn_fall |
| G-32-2016 | general | pregnant_worker_hazard_management |
| G-34-2012 | exclusive | pottery_silica_lead_exposure |
| G-36-2012 | general | safety_health_signage |
| G-37-2012 | general | general_worker_health_management |
| G-4-2011 | domain_specific | hazardous_pipeline_labeling |
| G-40-2012 | domain_specific | cargo_transport_packaging_shipping |
| G-41-2012 | exclusive | fumigation_chemical_exposure |
| G-44-2011 | domain_specific | hand_tool_use_safety |
| G-47-2012 | domain_specific | filming_location_work_safety |
| G-5-2017 | general | occupational_accident_investigation |

## Manual Corrections

The generated draft had several broad keyword errors, including `G-11-2017` as chemical exposure, `G-110-2014` as fire/chemical, and `G-44-2011` as welding/fire. These were corrected to source-specific slip/trip, waste-baler/conveyor, and hand-tool profiles.

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`. Asserted mapping updates must remain 0.
