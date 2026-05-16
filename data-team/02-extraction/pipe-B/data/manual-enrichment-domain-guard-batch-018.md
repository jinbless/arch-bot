# Manual Enrichment Domain Guard Domain Guard Manual Batch 018

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-018.json
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
| SR link candidates | 189 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 2 |
| SR link candidates needing review | 13 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
P-115/P-116/P-117/P-12/P-120/P-121/P-122: petrochemical firefighting, alarm/SIS management, chemical protective clothing, special gas, design-risk review, air separation, and semiconductor bulk gas separated from broad chemical/electrical defaults.
P-123/P-126/P-128/P-129/P-131/P-132/P-133/P-134: furnace, carbon disulfide drum, metal/chemical dust explosion, instrument calibration, runaway reaction, interlock, and facility-layout Guides grounded in equipment and document cues.
P-137/P-138/P-139/P-14/P-142/P-143/P-144/P-148/P-149/P-153: oxygen detector/enriched atmosphere, gas-cylinder emergency, FRP, hydroxylamine, molten-metal furnace, agricultural food dust, wastewater sump, cylinder cabinet, and toxic gas boundaries corrected from generic fire/chemical matches.
P-156/P-158/P-159/P-16/P-160: sludge carbonization, long-distance pipeline, oxygen/inert vent, semiconductor HPM fire protection, and nitrocellulose storage use visible process/equipment cues instead of title-only ranking.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| P-115-2012 | exclusive | refinery_petrochemical_firefighting_hydrant_water_spray_foam |
| P-116-2012 | domain_specific | process_alarm_sis_hmi_priority_management |
| P-117-2012 | exclusive | chemical_protective_clothing_selection_use_decontamination |
| P-12-2012 | exclusive | electronics_special_gas_cylinder_purge_remote_shutoff |
| P-120-2012 | general | design_redesign_risk_assessment_alarp_safety_review |
| P-121-2012 | exclusive | air_separation_oxygen_nitrogen_cryogenic_process |
| P-122-2012 | exclusive | semiconductor_bulk_gas_delivery_cylinder_tube_trailer |
| P-123-2012 | exclusive | industrial_furnace_burner_combustion_purge_safety_control |
| P-126-2012 | exclusive | carbon_disulfide_drum_unloading_dip_leg_scba_grounding |
| P-128-2012 | exclusive | metal_dust_fire_explosion_collector_grounding_explosion_vent |
| P-129-2013 | domain_specific | chemical_plant_instrument_calibration_traceability_interlock |
| P-131-2013 | exclusive | chemical_process_dust_explosion_inerting_vent_silo_collector |
| P-132-2013 | exclusive | chemical_mixing_runaway_reaction_reactor_interlock_cooling |
| P-133-2013 | domain_specific | chemical_process_interlock_bypass_jumper_moc_esd_logic |
| P-134-2013 | domain_specific | chemical_plant_facility_layout_safety_distance_wind_direction |
| P-137-2018 | exclusive | oxygen_detector_installation_calibration_alarm_maintenance |
| P-138-2013 | exclusive | oxygen_enriched_atmosphere_fire_cleaning_ventilation_hot_work |
| P-139-2013 | exclusive | gas_cylinder_emergency_leak_fire_crv_scba_response |
| P-14-2012 | exclusive | frp_manufacturing_organic_peroxide_resin_flammable_liquid_dust |
| P-142-2014 | exclusive | hydroxylamine_fire_explosion_temperature_contamination_control |
| P-143-2014 | exclusive | molten_metal_furnace_ladle_pit_cooling_water_tilting |
| P-144-2014 | exclusive | agricultural_food_dust_explosion_silo_marine_leg_relief_panel |
| P-148-2015 | exclusive | chemical_wastewater_sump_flammable_vapor_blower_gas_detector |
| P-149-2016 | exclusive | gas_cylinder_storage_cabinet_segregation_esov_rfo |
| P-153-2016 | exclusive | toxic_gas_facility_detection_ventilation_ppe_emergency_management |
| P-156-2017 | exclusive | sewage_sludge_carbonization_dryer_pyrolysis_gas_combustion |
| P-158-2017 | domain_specific | long_distance_transfer_pipeline_corrosion_grounding_insulation_flange |
| P-159-2017 | exclusive | oxygen_inert_atmospheric_vent_design_dispersion_exclusion_zone |
| P-16-2012 | exclusive | semiconductor_hpm_fire_protection_gas_detection_emergency_control |
| P-160-2017 | exclusive | nitrocellulose_storage_handling_water_spray_static_control |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
