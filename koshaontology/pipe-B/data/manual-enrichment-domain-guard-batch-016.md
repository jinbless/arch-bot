# Manual Enrichment Domain Guard Domain Guard Manual Batch 016

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-016.json
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
| SR link candidates | 148 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 3 |
| SR link candidates needing review | 66 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
C-C-8/C-C-90/C-C-94: flange/gasket, safety-valve, and rupture-disc Guides grounded in pressure equipment, leakage, set-pressure, relief-capacity, and maintenance cues.
C-C-83/D-1/D-16/D-12: deflagration vent, low-pressure venting, explosion suppression, and dust explosion Guides assigned exclusive explosion-protection boundaries.
C-C-84/C-C-85/C-C-87: VOC oxidizer, inert-gas purge, and gas detector Guides strengthened with LEL, flame arrester, purge, calibration, alarm, and emergency-power cues.
C-C-88/C-C-89/C-C-93/D-21/D-30/D-32: dike, fireproofing, atmospheric tank, foam fire protection, pressure-vessel heat protection, and control-room design separated from generic fire defaults.
D-13/D-2/D-3/D-20/D-24/D-28: chlorine storage, activated-carbon adsorption, solvent extraction, rubber lining, safe design, and small-workplace fire/explosion mapped to chemical equipment and emergency protection.
C-C-80/C-C-81/C-C-86/C-C-92/D-22: M&A, Dow/Mond, integrated form, self-audit, and explosion-limit calculation kept as document/analysis profiles with conservative SR candidates.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| C-C-8-2026 | domain_specific | flange_gasket_joint_leak_prevention_pressure_chemical_piping |
| C-C-80-2026 | general | ma_due_diligence_process_safety_assessment_document_review |
| C-C-81-2026 | domain_specific | dow_mond_relative_risk_index_fire_explosion_loss_estimation |
| C-C-82-2026 | exclusive | thermal_oil_boiler_expansion_tank_hot_oil_piping_fire_protection |
| C-C-83-2026 | exclusive | gas_deflagration_vent_enclosure_pred_pstat_vent_area |
| C-C-84-2026 | exclusive | voc_thermal_oxidizer_rto_rco_lel_flame_arrester_emergency_vent |
| C-C-85-2026 | exclusive | inert_gas_purging_nitrogen_co2_moc_oxygen_reduction |
| C-C-86-2026 | general | psm_integrated_forms_chemical_accident_prevention_documents |
| C-C-87-2026 | exclusive | gas_leak_detector_alarm_calibration_explosionproof_power |
| C-C-88-2026 | exclusive | tank_dike_impermeable_containment_drain_capacity |
| C-C-89-2026 | exclusive | fireproofing_structure_hazardous_area_supports_cable_instrument_lines |
| C-C-9-2026 | exclusive | emergency_shutoff_valve_fail_close_remote_switch_toxic_flammable_transfer |
| C-C-90-2026 | exclusive | safety_valve_relief_capacity_set_pressure_discharge_system |
| C-C-91-2026 | exclusive | chemical_piping_ndt_heat_treatment_rt_ut_mt_pt_weld_integrity |
| C-C-92-2026 | general | psm_self_audit_checklist_team_field_interview_corrective_action |
| C-C-93-2026 | exclusive | atmospheric_storage_tank_fixed_floating_roof_vent_inerting_static |
| C-C-94-2026 | exclusive | rupture_disc_install_replace_burst_pressure_relief_capacity |
| D-1-2021 | exclusive | low_pressure_piping_deflagration_vent_deflector_duct_area |
| D-12-2012 | exclusive | dust_explosion_prevention_collector_grounding_inerting_isolation_vent_suppression |
| D-13-2012 | exclusive | chlorine_storage_tank_scrubber_gas_detector_dike_esv_prv |
| D-16-2012 | exclusive | explosion_suppression_detector_controller_high_speed_extinguisher |
| D-2-2012 | exclusive | activated_carbon_adsorber_voc_lfl_co_temperature_hotspot_purge |
| D-20-2017 | exclusive | chemical_equipment_rubber_lining_surface_prep_curing_no_hot_work |
| D-21-2012 | exclusive | outdoor_storage_tank_foam_fire_protection_fixed_outlet_pump_concentrate |
| D-22-2012 | domain_specific | flammable_gas_vapor_explosion_limit_calculation_lel_uel |
| D-24-2012 | exclusive | chemical_equipment_safe_design_inherent_passive_active_procedural_safeguards |
| D-28-2012 | exclusive | small_workplace_fire_explosion_prevention_extinguisher_detector_esv_flame_arrester |
| D-3-2012 | exclusive | solvent_extraction_process_flammable_solvent_deluge_foam_shutdown_purge |
| D-30-2012 | exclusive | pressure_vessel_external_fire_heat_protection_water_spray_insulation_depressurization |
| D-32-2012 | exclusive | control_room_siting_blast_toxic_gas_positive_pressure_emergency_exit |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
