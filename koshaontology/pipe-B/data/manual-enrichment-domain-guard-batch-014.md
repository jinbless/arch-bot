# Manual Enrichment Domain Guard Domain Guard Manual Batch 014

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-014.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: inventory order excluding prior manual batches
manual_review: source-JSON reviewed on 2026-05-09
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 138 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 7 |
| SR link candidates needing review | 64 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
C-C-25/C-C-26/C-C-31/C-C-44: batch/fuel-gas/chemical-process operation Guides corrected from broad fire/electrical defaults into process-operation, inerting, gas detection, static-control, and abnormal-reaction boundaries.
C-C-28/C-C-3/C-C-4: oxidizer, water-reactive/flammable solid, and ethylene-oxide Guides assigned exclusive chemical storage/equipment/fire-explosion profiles.
C-C-30/C-C-32/C-C-33/C-C-5: runaway reaction, flame arrester, drying equipment, and safety-valve test Guides grounded in visible/specific pressure-relief, venting, burner, PRV, and test-equipment cues.
C-C-34/C-C-49: fire brigade and safe-work-permit Guides separated into emergency-response/SCBA and hot-work/confined-space permit boundaries.
C-C-27/C-C-35/C-C-36/C-C-37/C-C-38/C-C-39/C-C-40/C-C-41/C-C-42/C-C-43/C-C-45/C-C-46/C-C-47/C-C-48/C-C-50/C-C-51: process safety KPI, risk-analysis, human-error, CEI, leak-modeling, maintenance, contractor, and training documents kept domain_specific with conservative SR candidates.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| C-C-25-2026 | domain_specific | batch_process_human_error_abnormal_operation |
| C-C-26-2026 | exclusive | fuel_gas_piping_precommissioning_inerting_blowing |
| C-C-27-2026 | domain_specific | process_safety_performance_indicator_kpi |
| C-C-28-2026 | exclusive | oxidizing_liquid_solid_storage_segregation_fire_control |
| C-C-29-2026 | domain_specific | chemical_warning_label_hazard_communication |
| C-C-3-2025 | exclusive | water_reactive_flammable_solid_storage_metal_fire |
| C-C-30-2026 | exclusive | runaway_reaction_thermal_hazard_calorimetry_pressure_relief |
| C-C-31-2026 | exclusive | chemical_process_equipment_operation_abnormal_reaction_control |
| C-C-32-2026 | exclusive | flame_arrester_vent_flammable_tank_deflagration_detonation |
| C-C-33-2026 | exclusive | drying_equipment_fire_explosion_ventilation_burner_interlock |
| C-C-34-2026 | domain_specific | industrial_fire_brigade_emergency_response_scba_hose |
| C-C-35-2026 | domain_specific | refinery_petrochemical_process_safety_kpi_incident_indicator |
| C-C-36-2026 | domain_specific | process_risk_assessment_checklist_method |
| C-C-37-2026 | domain_specific | continuous_process_hazop_risk_assessment |
| C-C-38-2026 | domain_specific | what_if_process_risk_assessment |
| C-C-39-2026 | domain_specific | fault_tree_analysis_process_reliability |
| C-C-4-2025 | exclusive | ethylene_oxide_equipment_storage_sterilizer_blanketing_fire_explosion |
| C-C-40-2026 | domain_specific | fmea_criticality_analysis_process_reliability |
| C-C-41-2026 | domain_specific | batch_process_hazop_reactor_pump_relief_assessment |
| C-C-42-2026 | domain_specific | event_tree_analysis_safety_function |
| C-C-43-2026 | domain_specific | consequence_analysis_probit_fire_explosion_toxic_release |
| C-C-44-2026 | exclusive | batch_process_safe_operation_static_inerting_distillation_drying_maintenance |
| C-C-45-2026 | domain_specific | human_error_analysis_process_task_tank_unloading |
| C-C-46-2026 | domain_specific | chemical_exposure_index_toxic_release_cei_erpg |
| C-C-47-2026 | domain_specific | chemical_leak_source_modeling_release_rate_vessel_pipe |
| C-C-48-2026 | domain_specific | hazardous_equipment_inspection_maintenance_reliability_psm |
| C-C-49-2026 | exclusive | safe_work_permit_hot_work_confined_space_chemical_equipment |
| C-C-5-2025 | exclusive | safety_valve_set_pressure_seat_tightness_test_inert_gas |
| C-C-50-2026 | domain_specific | contractor_psm_safety_management_plan_permit_information |
| C-C-51-2026 | domain_specific | process_safety_training_contractor_worker_competency |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
