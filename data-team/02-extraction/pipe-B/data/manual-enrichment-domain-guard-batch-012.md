# Manual Enrichment Domain Guard Domain Guard Manual Batch 012

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-012.json
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
| SR link candidates | 158 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 0 |
| SR link candidates needing review | 84 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
M-47/M-48/M-49: woodshop, workplace transport road, and loading/unloading Guides separated from generic chemical/electrical defaults into sawdust/fire, pedestrian-vehicle, and dock/cargo boundaries.
M-5/M-56/M-57/M-58/M-7/M-8: broad hot-work defaults corrected into machine guarding, interlock, emergency stop, mold-change, extrusion, blow-molding, window-machine, and thermoforming profiles.
M-51/M-62/M-73/M-75: workplace, woodworking, food/beverage, and pneumatic noise Guides normalized under noise-control profiles with SR-NOISE candidates.
M-52/M-6/M-76/M-9: chainsaw, circular saw bench, powered hand planer, and metal manual circular saw Guides grounded in visible blade, guard, kickback, push-stick, and cutting cues.
M-53/M-67/M-74/M-77: plastics fume, manual arc welding, stainless welding fume, and automotive spray painting Guides mapped to ventilation/PPE/fire-explosion boundaries, with legal SR links kept conservative where title-only evidence is weak.
M-69/M-70/M-71/M-82/M-89/M-90: pressure-vessel, sling/wire-rope, thermoplastic tank, tower-crane installation/access, and hoist wire-rope Guides assigned exclusive technical/equipment boundaries to suppress unrelated field recommendations.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| M-47-2012 | domain_specific | woodworking_general_shop_housekeeping_sawdust_fire |
| M-48-2012 | domain_specific | workplace_transport_road_pedestrian_vehicle_separation |
| M-49-2023 | exclusive | loading_unloading_vehicle_dock_fall_cargo_securement |
| M-5-2012 | domain_specific | general_work_equipment_guarding_control_maintenance |
| M-51-2023 | domain_specific | workplace_noise_control_engineering_program |
| M-52-2012 | exclusive | chainsaw_operation_kickback_ppe_tree_cutting |
| M-53-2012 | exclusive | plastic_injection_molding_fume_ventilation_temperature_control |
| M-56-2020 | exclusive | injection_molding_machine_guard_interlock_mold_change |
| M-57-2020 | exclusive | extruder_machine_screw_guard_hot_surface_purging |
| M-58-2012 | exclusive | window_frame_fabrication_machine_saw_router_clamp_guarding |
| M-59-2012 | domain_specific | service_industry_slip_trip_risk_assessment_floor_tile_cleaning |
| M-6-2012 | exclusive | woodworking_circular_saw_bench_riving_knife_push_stick_dust |
| M-60-2012 | domain_specific | slip_resistance_floor_measurement_method_portable_friction_test |
| M-61-2017 | exclusive | industrial_robot_guard_fence_teaching_interlock_emergency_stop |
| M-62-2012 | domain_specific | woodworking_machine_noise_control_sawing_enclosure_ppe |
| M-67-2012 | exclusive | manual_metal_arc_welding_electric_shock_fume_fire |
| M-69-2012 | exclusive | pressure_vessel_remaining_life_corrosion_mawp_inspection_records |
| M-7-2016 | exclusive | blow_molding_machine_guard_interlock_hot_surface_setting |
| M-70-2013 | exclusive | wire_rope_grommet_cable_laid_sling_wll_manufacturing |
| M-71-2011 | exclusive | thermoplastic_chemical_tank_installation_inspection_static_compatibility |
| M-73-2016 | domain_specific | food_beverage_industry_noise_control_bottling_packaging_compressor |
| M-74-2011 | exclusive | stainless_arc_welding_fume_cr6_ni_ventilation_confined_space |
| M-75-2016 | domain_specific | pneumatic_system_noise_reduction_silencer_nozzle_compressed_air |
| M-76-2013 | exclusive | powered_hand_planer_cutterblock_bridge_guard_push_block_woodworking |
| M-77-2011 | exclusive | automotive_partial_spray_painting_isocyanate_solvent_booth_explosion |
| M-8-2016 | exclusive | thermoforming_machine_guard_interlock_heater_platen_hot_surface |
| M-82-2011 | exclusive | tower_crane_installation_assembly_telescoping_foundation_jib_counterweight |
| M-89-2016 | exclusive | tower_crane_access_ladder_walkway_guardrail_jib_platform |
| M-9-2023 | exclusive | metalworking_manual_circular_saw_auto_guard_noise_cutting_fluid |
| M-90-2011 | exclusive | crane_hoist_wire_rope_selection_drum_sheave_inspection |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
