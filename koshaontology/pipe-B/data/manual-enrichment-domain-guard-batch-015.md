# Manual Enrichment Domain Guard Domain Guard Manual Batch 015

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-015.json
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
| SR link candidates | 139 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 4 |
| SR link candidates needing review | 81 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
C-C-52/C-C-53/C-C-59/C-C-77: PSSR, MOC, SOP, and PSM operational-discipline Guides corrected into domain_specific management/procedure profiles instead of broad electrical defaults.
C-C-55/C-C-69/C-C-74: emergency-plan Guides grounded in alarm, evacuation, control-center, fire/explosion/toxic-release response, and emergency equipment cues.
C-C-56/C-C-58/C-C-7: consequence, worst/alternative scenario, and QRA Guides kept as analysis documents with conservative SR candidates.
C-C-60/C-C-70: loss-mitigation and hazardous-space Guides strengthened with gas detector, ventilation, alarm, SCBA, toxic-gas, and evacuation boundaries.
C-C-65/C-C-78: semiconductor specialty-gas and refinery-operation Guides assigned exclusive process/equipment boundaries to prevent generic fire/electrical overexposure.
C-C-75/C-C-76/C-C-79: corrosion-risk, integrity-monitoring, and CCD Guides normalized under corrosion/damage-mechanism/IOW profiles.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| C-C-52-2026 | domain_specific | pre_startup_safety_review_pssr_mechanical_electrical_piping_instrument |
| C-C-53-2026 | domain_specific | management_of_change_moc_normal_emergency_temporary_change |
| C-C-54-2026 | domain_specific | process_incident_investigation_near_miss_report |
| C-C-55-2026 | exclusive | chemical_emergency_response_plan_alarm_evacuation_control_center |
| C-C-56-2026 | domain_specific | consequence_modeling_source_dispersion_fire_explosion_bleve |
| C-C-57-2026 | domain_specific | major_industrial_accident_investigation_root_cause_action |
| C-C-58-2026 | domain_specific | worst_alternative_accident_scenario_selection_endpoint |
| C-C-59-2026 | domain_specific | safe_operating_procedure_sop_process_operation |
| C-C-6-2025 | exclusive | atmospheric_storage_tank_inspection_repair_corrosion_thickness_scaffold |
| C-C-60-2026 | domain_specific | chemical_plant_loss_mitigation_leak_detection_shutdown_response |
| C-C-61-2026 | domain_specific | kosha_process_safety_review_kpsr_hazop_like_assessment |
| C-C-62-2026 | domain_specific | lopa_independent_protection_layer_sis_sil_prv_bpcs |
| C-C-63-2026 | exclusive | process_safety_checklist_piping_valve_instrument_fail_safe |
| C-C-64-2026 | domain_specific | aging_equipment_corrosion_electrical_control_integrity_management |
| C-C-65-2026 | exclusive | semiconductor_specialty_gas_cleanroom_exhaust_interlock_electrical_radiation |
| C-C-66-2026 | domain_specific | chemical_equipment_failure_rate_availability_reliability_data |
| C-C-67-2026 | domain_specific | job_risk_assessment_jsa_jra_vam_unloading_vehicle_task |
| C-C-68-2026 | domain_specific | chemical_plant_contractor_autonomous_safety_management_permit_communication |
| C-C-69-2026 | exclusive | small_chemical_plant_emergency_plan_alarm_evacuation_control_center |
| C-C-7-2026 | domain_specific | quantitative_risk_assessment_qra_consequence_frequency_risk_map |
| C-C-70-2025 | exclusive | hazardous_space_gas_ventilation_alarm_scba_confined_entry |
| C-C-71-2026 | domain_specific | root_cause_analysis_accident_flow_causal_factor |
| C-C-72-2026 | exclusive | chemical_security_vulnerability_assessment_tuc_access_control_cctv |
| C-C-73-2026 | domain_specific | periodic_process_hazard_assessment_revalidation_moc_pssr |
| C-C-74-2026 | exclusive | scenario_based_emergency_response_plan_fire_explosion_toxic_bleve |
| C-C-75-2026 | domain_specific | corrosion_risk_assessment_damage_mechanism_rbi_map |
| C-C-76-2026 | domain_specific | integrity_operating_window_iow_corrosion_monitoring |
| C-C-77-2026 | domain_specific | psm_operational_discipline_operations_excellence_procedure_compliance |
| C-C-78-2026 | exclusive | refinery_cdu_vdu_fired_heater_flare_tank_fire_protection_startup |
| C-C-79-2026 | domain_specific | corrosion_control_document_ccd_damage_mechanism_iow_rbi |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
