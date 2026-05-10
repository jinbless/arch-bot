# Manual Enrichment Domain Guard Domain Guard Manual Batch 017

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-017.json
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
| SR link candidates | 175 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 6 |
| SR link candidates needing review | 79 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
D-33/D-4/D-42/D-43/P-1/P-112: gas/vapor, isolation, hydrogen vent, collector, pneumatic conveying, and magnesium dust explosion Guides separated by explosion-protection devices and static/grounding cues.
D-34/D-38/K-1/P-109: ammonia, sulfuric/oleum, hazardous chemical, and organic peroxide storage Guides grounded in substance-specific tank, labeling, separation, corrosion, emergency, and containment cues.
D-37/D-5/D-52/D-62/D-64: process vessel, system design, piping, check-valve, and centrifugal-pump Guides corrected from broad defaults into process-design/equipment profiles with conservative SR candidates where legal directness is weak.
D-55/D-56: liquid chemical loading/unloading and blind installation/removal mapped to trench/sump/curb, spill control, isolation, purge, permit, and tag cues.
D-58/D-7: MCFC and fuel-cell Guides separated into hydrogen/gas, electrical-output, shutdown, ventilation, and ex-proof boundaries.
D-60/D-63/D-68: flare knockout drum, safety-valve discharge piping, and breaking-pin device grounded in relief/discharge/pressure-protection boundaries.
D-46/P-104/P-11/P-114: chemical-plant fire prevention, VOC treatment, EPS pentane fire prevention, and static measurement/control strengthened with ignition, LEL, ventilation, grounding, and treatment-equipment cues.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| D-33-2012 | exclusive | gas_vapor_fire_explosion_design_vent_containment_suppression |
| D-34-2013 | exclusive | anhydrous_ammonia_storage_tank_piping_esv_prv_purge |
| D-37-2012 | exclusive | chemical_process_equipment_design_pressure_vessel_distillation_reactor |
| D-38-2012 | exclusive | sulfuric_oleum_storage_tank_corrosion_dike_eyewash |
| D-4-2012 | exclusive | explosion_isolation_fast_valve_flame_arrester_rotary_valve |
| D-42-2021 | exclusive | hydrogen_vent_stack_piping_static_ring_purge_dispersion |
| D-43-2012 | exclusive | dust_collector_explosion_bag_filter_grounding_duct_cyclone |
| D-46-2013 | exclusive | chemical_plant_fire_prevention_ignition_inerting_static_fire_protection |
| D-5-2012 | exclusive | chemical_process_system_design_pid_piping_pressure_tank_relief |
| D-51-2020 | exclusive | pipeline_flange_insulation_cathodic_protection_overvoltage |
| D-52-2013 | exclusive | chemical_piping_process_design_valves_esv_static_velocity |
| D-55-2016 | exclusive | liquid_chemical_loading_unloading_leak_containment_trench_sump |
| D-56-2016 | exclusive | blind_install_removal_isolation_purge_permit_tag |
| D-58-2016 | exclusive | molten_carbonate_fuel_cell_mcfc_stack_gas_shutdown_pcu |
| D-6-2012 | exclusive | refrigeration_system_pressure_relief_refrigerant_machinery_room |
| D-60-2017 | exclusive | flare_system_knockout_drum_liquid_separation_header_stack |
| D-62-2018 | exclusive | check_valve_backflow_water_hammer_pump_compressor_piping |
| D-63-2018 | exclusive | safety_valve_discharge_piping_backpressure_equivalent_length |
| D-64-2018 | exclusive | centrifugal_pump_minimum_flow_npsh_cavitation_bypass |
| D-65-2018 | exclusive | blast_protective_structure_wall_pressure_reinforced_concrete |
| D-68-2020 | exclusive | breaking_pin_device_pressure_relief_set_pressure_capacity |
| D-69-2020 | domain_specific | sis_sif_sil_hra_functional_safety_lifecycle |
| D-7-2012 | exclusive | fuel_cell_hydrogen_storage_electrical_output_ventilation_exproof |
| K-1-2023 | exclusive | hazardous_chemical_storage_transport_handling_emergency_equipment |
| P-1-2012 | exclusive | pneumatic_conveying_combustible_dust_duct_separator_explosion |
| P-104-2012 | exclusive | voc_treatment_oxidation_adsorption_absorption_condensation_biofilter |
| P-109-2012 | exclusive | organic_peroxide_storage_temperature_sprinkler_separation |
| P-11-2012 | exclusive | eps_pentane_fire_prevention_storage_ventilation_hot_wire |
| P-112-2014 | exclusive | magnesium_dust_explosion_melting_casting_machining_dry_collection |
| P-114-2020 | exclusive | static_electricity_measurement_control_chemical_equipment_bonding |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
