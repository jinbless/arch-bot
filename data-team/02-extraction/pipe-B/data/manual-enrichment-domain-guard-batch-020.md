# Manual Enrichment Domain Guard Domain Guard Manual Batch 020

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-020.json
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
| SR link candidates | 226 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 2 |
| SR link candidates needing review | 2 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
P-4/P-41/P-42/P-43/P-44/P-46: factory building risk, dust deflagration vent, ethanol distillation, fire-water pump, toy fireworks, and cleanroom Guides separated from broad chemical/fire defaults.
P-47/P-48/P-49/P-5/P-50/P-52/P-53/P-54/P-55: hydrogen fuel-cell, cylinder PRD, dust process selection, printing solvent, hazardous waste, isolation, runaway reaction, acetylene, and sulfur process boundaries grounded in equipment/procedure cues.
P-57/P-58/P-59/P-6/P-60/P-62/P-63/P-64/P-65: fire door/window, hazmat response, acid tank, spray booth, ammonia refrigeration, organic paint, HVAC, iron sulfide, and rupture-disc sizing profiles corrected with visible devices and documents.
P-68/P-7/P-72/P-74/P-75/P-76: aluminum dust, portable flammable liquid containers, outdoor fireworks, packaged dangerous-goods warehouse, flammable liquid handling, and chemical laboratory Guides assigned usage-boundary cues for runtime exclusion/penalty.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| P-4-2012 | domain_specific | factory_building_risk_assessment_fire_explosion_toxic_release |
| P-41-2015 | exclusive | dust_deflagration_vent_design_reduced_pressure_area |
| P-42-2012 | exclusive | ethanol_distillation_fire_explosion_ventilation_tank_flame_arrester |
| P-43-2012 | domain_specific | chemical_fire_water_calculation_fire_pump_main_line_maintenance |
| P-44-2012 | exclusive | toy_fireworks_storage_handling_display_ignition_source_control |
| P-46-2012 | exclusive | cleanroom_hazardous_material_silane_gas_cabinet_sprinkler_exhaust |
| P-47-2021 | exclusive | vehicle_hydrogen_fuel_cell_system_prd_shutoff_barrier |
| P-48-2012 | exclusive | compressed_gas_cylinder_pressure_relief_device_burst_disc_safety_valve |
| P-49-2012 | exclusive | combustible_dust_process_system_selection_enclosure_vent_suppression |
| P-5-2012 | exclusive | printing_organic_solvent_fire_explosion_press_dryer_ventilation |
| P-50-2012 | domain_specific | hazardous_waste_handling_cleanup_emergency_response_program |
| P-52-2012 | exclusive | plant_equipment_positive_isolation_spade_dbb_purge_permit |
| P-53-2012 | exclusive | exothermic_reaction_runaway_protection_rupture_disc_quench_dcs |
| P-54-2012 | exclusive | acetylene_generation_compression_cylinder_filling_ventilation_relief_panel |
| P-55-2012 | exclusive | sulfur_pulverizing_dust_fire_explosion_venting_water_spray |
| P-57-2012 | domain_specific | fire_door_fire_window_closing_latching_inspection |
| P-58-2012 | exclusive | hazardous_material_incident_response_hot_zone_monitoring_ppe |
| P-59-2012 | exclusive | hydrochloric_nitric_acid_tank_storage_corrosion_scrubber_dike |
| P-6-2011 | exclusive | flammable_liquid_spray_booth_lfl_ventilation_exproof_static |
| P-60-2012 | exclusive | ammonia_refrigerant_leak_detection_ventilation_ppe_eyewash |
| P-62-2012 | exclusive | organic_paint_manufacturing_flammable_liquid_kettle_mixer_storage |
| P-63-2012 | domain_specific | hvac_air_duct_fire_smoke_damper_detection_test |
| P-64-2012 | exclusive | pyrophoric_iron_sulfide_wetting_steam_purge_vessel_entry |
| P-65-2012 | domain_specific | runaway_reaction_rupture_disc_sizing_arc_vsp_rsst |
| P-68-2012 | exclusive | aluminum_dust_explosion_collection_cleaning_no_water_static |
| P-7-2011 | exclusive | portable_flammable_liquid_container_storage_room_emergency_vent_dike |
| P-72-2011 | exclusive | outdoor_fireworks_display_mortar_electric_firing_fallout_area |
| P-74-2011 | exclusive | packaged_dangerous_goods_warehouse_segregation_dike_exproof_fire_protection |
| P-75-2011 | exclusive | flammable_liquid_use_handling_substitution_transfer_hose_exproof |
| P-76-2011 | exclusive | chemical_laboratory_storage_hood_gas_cylinder_fire_emergency |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
