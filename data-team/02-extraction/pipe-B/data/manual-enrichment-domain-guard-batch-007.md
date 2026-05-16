# Manual Enrichment Domain Guard Batch 007

Generated: 2026-05-09  
Manual reviewed: 2026-05-09

This batch was re-read manually by Codex from `pipe-B/data/ci-output/ci-*.json`. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-007.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: inventory order excluding prior manual batches
curation_policy: batch_007_source_json_manual_read
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 86 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |

Guides with no SR candidate:

```text
(none)
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| B-M-22-2026 | exclusive | waste_collection_vehicle_tailgate_hopper |
| B-M-23-2026 | exclusive | industrial_fan_maintenance_vibration_bearing |
| B-M-24-2026 | exclusive | safety_harness_lanyard_inspection |
| B-M-25-2026 | exclusive | lockout_tagout_energy_isolation |
| B-M-26-2026 | exclusive | brush_cutter_mowing_work |
| B-M-27-2026 | exclusive | autoclave_pressure_vessel_interlock |
| B-M-28-2026 | exclusive | hazardous_material_flexible_hose_safety |
| B-M-29-2026 | exclusive | vehicle_repair_lift_pit_tire_lpg |
| B-M-3-2025 | exclusive | stone_crusher_guarding_jam_removal |
| B-M-30-2026 | domain_specific | magnetic_penetrant_testing_chemical_uv |
| B-M-31-2026 | exclusive | molding_core_machine_guarding_foundry |
| B-M-34-2026 | exclusive | overhead_travelling_crane_operation_maintenance |
| B-M-35-2026 | exclusive | pallet_selection_stacking_handling |
| B-M-36-2026 | exclusive | power_press_guarding_die_safety |
| B-M-37-2026 | domain_specific | rotating_machinery_guarding_vibration_monitoring |
| B-M-38-2026 | exclusive | portable_power_drill_safety |
| B-M-39-2026 | exclusive | portable_grinder_wheel_guard_safety |
| B-M-4-2025 | exclusive | wood_chipper_feed_hopper_guarding |
| B-M-5-2025 | exclusive | crusher_grinder_hopper_interlock_loto |
| B-M-6-2025 | exclusive | food_processing_machine_guarding_cleaning |
| B-M-7-2026 | domain_specific | lifting_equipment_general_crane_rigging |
| E-1-2012 | exclusive | overhead_power_line_proximity_work |
| E-10-2013 | exclusive | battery_charging_acid_hydrogen_safety |
| E-100-2021 | domain_specific | low_voltage_electric_shock_protection_systems |
| E-103-2011 | exclusive | low_voltage_protection_device_selection |
| E-104-2011 | domain_specific | electrical_installation_environment_use_condition_assessment |
| E-108-2011 | exclusive | emergency_power_supply_for_safety_equipment |
| E-111-2011 | exclusive | arc_flash_flame_resistant_workwear |
| E-112-2011 | exclusive | surge_protective_device_spd_installation |
| E-115-2011 | exclusive | insulating_ppe_glove_selection_inspection |

## Manual Corrections

The generated draft treated several mechanical Guides as generic machine/electrical/fire cases. This manual pass split them into equipment-centered boundaries: waste collection vehicle tailgate and hopper, industrial fan maintenance, safety lanyard inspection, LOTO energy isolation, brush cutter work, autoclave pressure vessel safety, hazardous-material flexible hoses, vehicle repair with pits/tires/LPG, stone crushers, NDT chemical/UV work, molding/core machines, overhead cranes, pallets, presses, rotating machinery, portable drills, portable grinders, wood chippers, food-processing machines, and general lifting equipment.

The electrical Guides were likewise separated into overhead power line proximity work, battery charging/acid/hydrogen safety, low-voltage shock protection, protection-device selection, electrical installation environment assessment, emergency power, arc-flash flame-resistant workwear, SPD installation, and insulating PPE inspection.

Some SR links are intentionally conservative `needs_review` candidates where the Guide is design/specification oriented or the SR is adjacent rather than directly asserted.

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`. Asserted mapping updates must remain 0.
