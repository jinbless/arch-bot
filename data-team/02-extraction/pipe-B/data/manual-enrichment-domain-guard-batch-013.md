# Manual Enrichment Domain Guard Domain Guard Manual Batch 013

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-013.json
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
| Feature candidates | 61 |
| SR link candidates | 148 |
| Visual trigger candidates | 61 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 0 |
| SR link candidates needing review | 82 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
M-91/M-92/M-93/M-94: tower-crane support, mobile lifting table, stacker, and round-sling drafts corrected into crane/lifting/rigging equipment boundaries.
M-96/M-98/M-99/O-2: lathe, drill, boring-machine, and bolt/nut Guides moved from broad chemical/fire defaults to machine guard or fastening technical profiles.
P-79/C-C-21/C-C-24: M-HAZOP, risk-priority, and process-safety-culture documents kept as management/risk-assessment profiles with conservative SR candidates. C-73 was corrected on 2026-05-10 to a steel-box-girder bridge construction boundary after parsed/CI regeneration.
P-56/C-05/C-06/C-07: cellular-plastic storage, rush construction, tile work, and sheet waterproofing mapped to visible storage/fire/night-work/fall/electric/chemical cues.
C-C-1/C-C-10/C-C-11/C-C-13/C-C-17/C-C-18/C-C-19: tank cleaning, venting, PRV, thermal expansion valve, pressure test, flare, and rupture-disc documents assigned exclusive pressure/chemical equipment boundaries.
C-C-12/C-C-14/C-C-15/C-C-20/C-C-22/C-C-23: P&ID/PFD, piping/material selection, PVC fire-explosion, and RBI Guides kept technical so they do not surface as generic field procedures without process-equipment context.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| M-91-2011 | exclusive | tower_crane_wall_wire_support_mast_wind_tensioning |
| M-92-2013 | exclusive | mobile_lifting_table_scissor_lift_crush_stability_emergency_stop |
| M-93-2011 | exclusive | stacker_pallet_lifting_stability_tiller_handle_fork_load |
| M-94-2011 | exclusive | synthetic_fiber_round_sling_wll_inspection_lifting_angle |
| M-96-2012 | exclusive | lathe_guarding_chuck_cutting_area_coolant_chip_guard |
| M-98-2012 | exclusive | drilling_machine_spindle_guard_emergency_stop_interlock |
| M-99-2012 | exclusive | boring_machine_guard_trip_probe_working_area_interlock |
| O-2-2023 | domain_specific | bolt_nut_selection_fastening_torque_thread_locking |
| P-79-2011 | domain_specific | machine_factory_mhazop_risk_assessment_process_line |
| P-56-2012 | exclusive | cellular_plastic_foam_storage_fire_smoke_static_separation |
| C-73-2012 | exclusive | steel_box_girder_bridge_mobile_crane_formwork_slab_concrete |
| C-05-2016 | domain_specific | construction_rush_work_night_shift_simultaneous_work_fire_fall |
| C-06-2015 | exclusive | tile_work_mixer_grinder_scaffold_cement_chemical_material_handling |
| C-07-2012 | exclusive | sheet_waterproof_asphalt_primer_torch_fall_electric_fire |
| C-C-1-2025 | exclusive | flammable_residue_tank_cleaning_gas_freeing_confined_space_inerting |
| C-C-10-2026 | exclusive | atmospheric_storage_tank_vent_breather_emergency_vent |
| C-C-11-2026 | exclusive | process_safety_valve_prv_orifice_set_pressure_inspection |
| C-C-12-2026 | exclusive | pid_process_piping_instrument_diagram_document_control |
| C-C-13-2026 | exclusive | thermal_expansion_relief_valve_blocked_liquid_piping_heat_source |
| C-C-14-2026 | exclusive | pfd_process_flow_diagram_material_heat_balance_psm_document |
| C-C-15-2026 | exclusive | chemical_piping_material_selection_corrosion_pressure_rating |
| C-C-17-2026 | exclusive | chemical_equipment_pressure_test_hydro_pneumatic_blind_flange_gauge |
| C-C-18-2026 | exclusive | flare_system_prv_header_knockout_drum_stack_depressuring |
| C-C-19-2026 | exclusive | safety_valve_rupture_disk_series_pressure_relief_combination |
| C-C-2-2025 | exclusive | chemical_equipment_maintenance_repair_work_plan_permit_contractor_hot_work |
| C-C-20-2026 | exclusive | chemical_equipment_material_selection_pressure_vessel_corrosion_brittle_fracture |
| C-C-21-2026 | domain_specific | process_risk_priority_assessment_major_accident_ranking |
| C-C-22-2026 | exclusive | pvc_vcm_polymerization_fire_explosion_static_dust_emergency |
| C-C-23-2026 | exclusive | rbi_risk_based_inspection_chemical_pressure_equipment_reliability |
| C-C-24-2026 | domain_specific | process_safety_culture_management_leadership_monitoring |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
