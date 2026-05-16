# Manual Enrichment Domain Guard Batch 005

Generated: 2026-05-09  
Manual reviewed: 2026-05-09

This batch was re-read manually by Codex from `pipe-B/data/ci-output/ci-*.json`. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-005.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: inventory order excluding prior manual batches
curation_policy: batch_005_source_json_manual_read
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 27 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 16 |

Guides with no SR candidate:

```text
X-34-2014
X-35-2014
X-43-2011
X-45-2014
X-47-2011
X-58-2012
X-6-2012
X-69-2016
X-70-2016
X-71-2016
X-72-2017
X-73-2017
X-74-2017
X-76-2018
X-77-2018
X-8-2012
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| X-34-2014 | domain_specific | process_risk_assessment_method_selection |
| X-35-2014 | domain_specific | probabilistic_risk_assessment |
| X-36-2016 | exclusive | moving_lift_truck_work |
| X-41-2011 | domain_specific | lone_worker_monitoring |
| X-43-2011 | domain_specific | cause_consequence_analysis_method |
| X-44-2016 | exclusive | mobile_elevating_work_platform |
| X-45-2014 | exclusive | road_rail_high_visibility_vest |
| X-47-2011 | domain_specific | what_if_checklist_risk_analysis |
| X-49-2018 | exclusive | hazardous_tank_truck_transport_qra |
| X-58-2012 | domain_specific | risk_communication_stakeholder_meeting |
| X-6-2012 | domain_specific | fmea_process_failure_analysis |
| X-61-2013 | domain_specific | production_machine_assembly_installation |
| X-62-2013 | domain_specific | production_facility_fire_response_risk_assessment |
| X-63-2013 | domain_specific | production_facility_explosion_response_risk_assessment |
| X-65-2013 | domain_specific | production_equipment_maintenance_risk_management |
| X-66-2013 | domain_specific | production_logistics_pack_transport_storage |
| X-68-2015 | exclusive | confined_space_entry_rescue_management |
| X-69-2016 | domain_specific | human_reliability_therp_control_room |
| X-70-2016 | domain_specific | operator_action_analysis_event_tree |
| X-71-2016 | domain_specific | cognitive_reliability_error_analysis |
| X-72-2017 | domain_specific | sherpa_human_error_prediction |
| X-73-2017 | domain_specific | human_error_hazop_analysis |
| X-74-2017 | domain_specific | heart_human_error_quantification |
| X-76-2018 | exclusive | safety_instrumented_system_common_cause_failure |
| X-77-2018 | exclusive | safety_instrumented_system_hardware_failure_probability |
| X-78-2018 | exclusive | lng_flammable_gas_storage_tank_qra |
| X-8-2012 | domain_specific | preliminary_hazard_analysis_process_design |
| X-9-2012 | domain_specific | thermal_work_environment_risk_assessment |
| B-6-2011 | exclusive | barge_marine_cargo_work |
| B-E-1-2025 | exclusive | lightning_protection_system_support |

## Manual Corrections

The generated draft overused broad fire, chemical, electrical, and warehouse defaults for risk-analysis method Guides. This manual pass corrected pure analysis documents such as `X-34-2014`, `X-35-2014`, `X-43-2011`, `X-47-2011`, `X-6-2012`, and `X-8-2012` into document/analysis profiles with no SR candidate. It also tightened physical or highly specific Guides such as `X-36-2016`, `X-44-2016`, `X-68-2015`, `B-6-2011`, and `B-E-1-2025` into exclusive profiles with concrete visual cues.

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`. Asserted mapping updates must remain 0.
