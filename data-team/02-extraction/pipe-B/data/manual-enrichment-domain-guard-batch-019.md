# Manual Enrichment Domain Guard Domain Guard Manual Batch 019

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-019.json
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
| SR link candidates | 244 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 2 |
| SR link candidates needing review | 5 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
P-161/P-162/P-164/P-165/P-167/P-17: waste solvent, water spray, pilot plant, atmospheric tank, chemical sampling, and dip-tank Guides separated from broad welding/fire defaults.
P-170/P-171/P-173/P-178/P-179: oxygen piping, automatic burner control, hydrogen equipment, hydrogen PSA, and mixed-gas explosibility calculation grounded in oxygen/hydrogen/burner/control/document cues.
P-18/P-180/P-2/P-21/P-22: flammable-liquid leak, waste-plastic pyrolysis, tank overfill prevention, hydrofluoric acid, and dry-cleaning Guides strengthened with detector, ventilation, level, PPE, and process-equipment cues.
P-25/P-26/P-27/P-28/P-3: fire-wall/barrier, flammable-liquid mixing, waste-solvent recovery, ship-vessel gas hazard, and small-tank cleaning mapped to fire barrier, explosion vent, distiller, tankship, inerting, and gas measurement cues.
P-30/P-31/P-32/P-33/P-34/P-35/P-36/P-38/P-39: hydrogen station, tank vehicle, oxygen supply, dry chlorine piping, drum storage, hot work, pulp/paper, exothermic reaction, and dangerous-goods transport boundaries corrected with equipment-specific triggers.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| P-161-2017 | exclusive | waste_solvent_refining_distillation_carbon_adsorber_fire_protection |
| P-162-2017 | exclusive | petrochemical_fixed_water_spray_deluge_system_design |
| P-164-2018 | exclusive | research_pilot_plant_reactor_pressure_hazop_leak_test |
| P-165-2019 | exclusive | flammable_atmospheric_storage_tank_sampling_transfer_loading |
| P-167-2020 | exclusive | chemical_handling_sampling_container_hazard_classification |
| P-17-2012 | exclusive | dip_tank_flammable_liquid_ventilation_overflow_emergency_shower |
| P-170-2021 | exclusive | oxygen_piping_material_velocity_particle_impact_grounding |
| P-171-2021 | exclusive | automatic_burner_control_flame_sensor_sequence_safety_shutdown |
| P-173-2021 | exclusive | hydrogen_equipment_storage_purge_leak_detection_fire_response |
| P-178-2022 | exclusive | hydrogen_psa_adsorber_buffer_tank_container_ventilation |
| P-179-2022 | domain_specific | mixed_gas_explosibility_lel_calculation_iso10156_document |
| P-18-2012 | exclusive | flammable_liquid_leak_detection_pid_ventilation_spill_response |
| P-180-2023 | exclusive | waste_plastic_pyrolysis_reactor_gas_oil_incinerator_exproof |
| P-2-2012 | exclusive | storage_tank_overfill_prevention_level_detector_shutdown |
| P-21-2010 | exclusive | hydrofluoric_acid_process_scrubber_scba_eyewash_emergency |
| P-22-2012 | exclusive | dry_cleaning_solvent_machine_tank_ventilation_fire_protection |
| P-25-2012 | domain_specific | fire_wall_fire_barrier_damper_penetration_protection |
| P-26-2012 | exclusive | flammable_liquid_mixing_room_explosion_ventilation_fire_barrier |
| P-27-2012 | exclusive | waste_solvent_recovery_package_distiller_carbon_absorber_explosion_vent |
| P-28-2012 | exclusive | ship_tank_vessel_gas_hazard_hot_work_inerting_tank_cleaning |
| P-3-2012 | exclusive | small_tank_cleaning_inerting_purging_bonding_gas_measurement |
| P-30-2021 | exclusive | hydrogen_fueling_station_dispenser_hose_gas_detector_emergency_shutdown |
| P-31-2012 | exclusive | flammable_liquid_tank_vehicle_cargo_tank_shutoff_valve_pressure_test |
| P-32-2012 | exclusive | bulk_oxygen_supply_loX_tank_vaporizer_safety_distance |
| P-33-2012 | exclusive | dry_chlorine_piping_gasket_valve_relief_dry_clean |
| P-34-2012 | exclusive | flammable_liquid_drum_storage_yard_firewall_dike_spill_sump |
| P-35-2012 | domain_specific | small_business_hot_work_permit_gas_measurement_blind_lockout |
| P-36-2012 | exclusive | pulp_paper_digestion_bleaching_flammable_chemical_dust_ventilation |
| P-38-2012 | domain_specific | exothermic_reaction_runaway_dsc_reaction_calorimeter_limit_setting |
| P-39-2012 | domain_specific | dangerous_goods_transport_emergency_spill_kit_ppe_response_vehicle |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
