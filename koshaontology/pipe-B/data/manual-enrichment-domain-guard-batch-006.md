# Manual Enrichment Domain Guard Batch 006

Generated: 2026-05-09  
Manual reviewed: 2026-05-09

This batch was re-read manually by Codex from `pipe-B/data/ci-output/ci-*.json`. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-006.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: inventory order excluding prior manual batches
curation_policy: batch_006_source_json_manual_read
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 67 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |

Guides with no SR candidate:

```text
(none)
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| B-E-10-2026 | exclusive | deenergized_electrical_work_loto |
| B-E-11-2026 | exclusive | energized_electrical_work_arc_shock |
| B-E-12-2026 | domain_specific | electrical_work_safety_management |
| B-E-13-2026 | exclusive | substation_switchgear_maintenance |
| B-E-14-2026 | exclusive | earth_leakage_circuit_breaker_installation |
| B-E-15-2026 | exclusive | electrical_equipment_working_clearance |
| B-E-16-2026 | domain_specific | electrical_equipment_preventive_maintenance |
| B-E-17-2026 | exclusive | paint_spray_static_explosion_zone |
| B-E-18-2026 | domain_specific | electromagnetic_compatibility_testing |
| B-E-2-2025 | exclusive | underground_cable_manhole_work |
| B-E-22-2026 | domain_specific | electrical_wire_identification |
| B-E-4-2025 | exclusive | portable_electrical_cord_plug_connector |
| B-E-5-2025 | exclusive | emergency_power_generator_ups |
| B-E-6-2025 | exclusive | electric_fence_installation |
| B-E-7-2025 | exclusive | construction_site_temporary_electrical_installation |
| B-E-8-2026 | domain_specific | process_instrumentation_selection_installation |
| B-E-9-2026 | exclusive | grounding_system_installation_testing |
| B-M-1-2025 | exclusive | fixed_ladder_design_fall_protection |
| B-M-10-2025 | domain_specific | chemical_equipment_installation_pressure_vessel_lift |
| B-M-12-2025 | exclusive | crane_rigging_wire_rope |
| B-M-13-2025 | exclusive | chainsaw_logging_work |
| B-M-14-2025 | exclusive | grinding_wheel_machine_safety |
| B-M-15-2026 | exclusive | high_temperature_dyeing_pressure_vessel |
| B-M-16-2026 | exclusive | mechanical_parking_system |
| B-M-17-2026 | domain_specific | machine_visual_audible_warning_signal |
| B-M-18-2026 | domain_specific | piping_life_management_inspection |
| B-M-19-2026 | exclusive | pipeline_major_accident_emergency_plan |
| B-M-2-2025 | exclusive | mixer_machine_interlock_safety |
| B-M-20-2026 | domain_specific | pipe_support_installation_welding |
| B-M-21-2026 | exclusive | bulk_solid_silo_hopper_storage_dust_explosion |

## Manual Corrections

The generated draft treated many electrical Guides as a broad `electrical_work` bucket and carried weak default features into mechanical Guides. This manual pass split electrical Guides into concrete boundaries such as deenergized work/LOTO, energized work, leakage breaker installation, construction temporary power, underground cable manhole work, EMC testing, grounding, and emergency power. It also corrected mechanical Guides into equipment-centered profiles such as fixed ladders, rigging wire rope, chainsaw logging, grinding wheels, high-temperature dyeing pressure vessels, mechanical parking systems, machine warning signals, piping life management, pipeline emergency planning, mixer interlocks, pipe supports, and bulk-solid silo dust explosion controls.

Several links remain intentionally candidate-only or `needs_review` where the Guide is technical/design-oriented rather than a direct legal SR fit, especially `B-E-8-2026`, `B-M-10-2025`, `B-M-17-2026`, and `B-M-20-2026`.

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`. Asserted mapping updates must remain 0.
