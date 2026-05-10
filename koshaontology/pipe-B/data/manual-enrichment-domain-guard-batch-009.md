# Manual Enrichment Domain Guard Batch 009

Updated: 2026-05-09

Batch 009 has been upgraded from generated draft to source-JSON manual review. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-009.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: inventory order excluding prior manual batches
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 102 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 0 |
| SR link candidates needing review | 26 |
| Visual trigger candidates needing review | 0 |

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| E-184-2021 | exclusive | portable_chainsaw_ppe_upper_body_boots |
| E-185-2021 | exclusive | lithium_ion_ess_installation_maintenance |
| E-186-2021 | exclusive | hazardous_area_ex_personnel_competency_assessment |
| E-187-2021 | exclusive | hazardous_area_gas_detector_use |
| E-188-2021 | domain_specific | static_electricity_fire_explosion_prevention_general |
| E-189-2022 | exclusive | insulating_rubber_ppe_selection_use_management |
| E-19-2012 | exclusive | electrical_test_equipment_safe_use |
| E-2-2012 | exclusive | high_pressure_steam_cleaner_electrical_hazard |
| E-20-2012 | exclusive | production_line_electrical_testing_barrier_interlock |
| E-22-2012 | exclusive | explosive_atmosphere_protective_system_functional_safety_assessment |
| E-25-2012 | exclusive | portable_electric_sprayer_tool_safety |
| E-3-2012 | exclusive | performance_venue_stage_electrical_safety |
| E-31-2014 | exclusive | wiring_device_plug_receptacle_maintenance |
| E-36-2012 | exclusive | forestry_overhead_power_line_safety |
| E-4-2012 | exclusive | arc_welding_equipment_selection_use |
| E-40-2013 | exclusive | circuit_breaker_testing_barrier_probe |
| E-41-2012 | exclusive | portable_low_voltage_generator_safety_check |
| E-44-2012 | exclusive | electric_kiln_safe_use |
| E-46-2013 | exclusive | electrical_single_line_diagram_management |
| E-55-2022 | exclusive | insulating_protective_cover_hose_blanket_mat |
| E-57-2020 | exclusive | molded_case_circuit_breaker_general_management |
| E-58-2013 | exclusive | electrical_work_ppe_arc_flash_insulating_gear |
| E-6-2012 | exclusive | switchgear_management_fire_sf6_maintenance |
| E-65-2012 | exclusive | agricultural_work_near_overhead_power_lines |
| E-66-2012 | exclusive | quarry_electrical_safety |
| E-74-2011 | exclusive | flammable_material_electrostatic_spray_equipment |
| E-76-2013 | exclusive | arc_welding_equipment_installation_use |
| E-77-2015 | exclusive | portable_electrical_equipment_maintenance |
| E-79-2011 | exclusive | overhead_power_communication_line_work |
| E-80-2011 | exclusive | shipbuilding_shiprepair_temporary_electrical_installation |

## Manual Correction Examples

```text
E-184: electrical_work draft -> portable chainsaw PPE / cutting boundary
E-185: generic fire/explosion -> lithium-ion ESS rack, BMS, ventilation, fire compartment boundary
E-186/E-22/E-46: operational document profiles kept exclusive with conservative SR candidates
E-187/E-188/E-74: gas detector, static prevention, and electrostatic spray equipment split by visual/domain cues
E-3/E-36/E-65/E-66/E-80: venue, forestry, agriculture, quarry, and shipbuilding electrical contexts separated
E-4/E-76: arc welding guides separated from generic hot-work/fire defaults
```

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
