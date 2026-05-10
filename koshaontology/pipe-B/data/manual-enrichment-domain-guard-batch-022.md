# Manual Enrichment Domain Guard Domain Guard Manual Batch 022

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-022.json
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
| SR link candidates | 213 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 0 |
| SR link candidates needing review | 24 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
C-59/C-60/C-61/C-62/C-64/C-66: roof work, top-down basement, Shield-TBM, gondola, masonry, and interior construction separated from broad construction/fire defaults.
C-68/C-70/C-71/C-74/C-75/C-77: reinforced earth wall, cold-storage insulation fire prevention, pile driving, MEWP, landscaping/tree planting, and suspension-bridge pylon profiles grounded in equipment and work-area cues.
C-78/C-79/C-80/C-81/C-82/C-83/C-84/C-85: retaining wall, high-rise construction, steel arch bridge, front jacking, offshore RCD, PCT girder, truss girder, and truck-mounted crane boundaries added with candidate-only SR links.
C-88/C-89/C-91/C-93/C-94/C-96/C-98/D-27/D-61/D-C-1: NTR tunnel, immersed tunnel, high-rise fire, well foundation, Rahmen bridge, temporary-structure design change, tower construction, hydrogen storage, flare backfire prevention, and earth-retaining technical support profiles corrected.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| C-59-2022 | exclusive | roof_work_fall_skylight_ladder_weather_material_falling |
| C-60-2015 | exclusive | top_down_basement_construction_slurry_wall_rcd_excavation_monitoring |
| C-61-2012 | exclusive | shield_tbm_tunnel_muck_car_segment_erector_vertical_shaft |
| C-62-2012 | exclusive | gondola_suspended_platform_wire_rope_winding_device_lifeline |
| C-64-2018 | domain_specific | masonry_brick_block_material_handling_scaffold_acid_cleaning |
| C-66-2016 | domain_specific | interior_ceiling_wall_board_stud_scaffold_temporary_electric |
| C-68-2012 | exclusive | reinforced_earth_block_retaining_wall_excavation_backfill_compaction |
| C-70-2012 | exclusive | cold_storage_insulation_urethane_foam_hot_work_fire_watch |
| C-71-2012 | exclusive | precast_concrete_pile_driving_pile_driver_leader_wire_rope |
| C-74-2015 | exclusive | mobile_elevating_work_platform_outrigger_overload_emergency_stop |
| C-75-2013 | domain_specific | landscaping_tree_planting_excavator_mobile_crane_sling_ladder |
| C-77-2013 | exclusive | suspension_bridge_pylon_slipform_heavy_lifting_cross_beam |
| C-78-2016 | exclusive | concrete_retaining_wall_excavation_formwork_rebar_concrete_pump |
| C-79-2015 | exclusive | high_rise_construction_tower_crane_cpb_acs_cocoon_falling_object |
| C-80-2013 | exclusive | steel_arch_bridge_bent_method_arch_rib_hanger_high_work |
| C-81-2013 | exclusive | front_jacking_tunnel_pipe_roof_reaction_wall_hydraulic_jack |
| C-82-2020 | exclusive | offshore_rcd_cast_in_place_pile_bridge_foundation_diving_crane |
| C-83-2013 | exclusive | pct_girder_bridge_launching_jack_nose_sliding_pad_steam_curing |
| C-84-2013 | exclusive | truss_girder_bridge_segment_crane_bent_high_work |
| C-85-2013 | exclusive | truck_mounted_cargo_crane_outrigger_hook_overload_prevention |
| C-88-2013 | exclusive | ntr_tunnel_pipe_jacking_hydraulic_jack_grouting_inner_excavation |
| C-89-2013 | exclusive | immersed_tunnel_dry_dock_towing_sinking_joint_diving_marine |
| C-91-2015 | exclusive | high_rise_construction_fire_prevention_evacuation_zone_fire_control_room |
| C-93-2013 | exclusive | well_foundation_caisson_sinking_tremie_excavation_pumping |
| C-94-2013 | exclusive | rahmen_bridge_formwork_shoring_rebar_concrete_pile_foundation |
| C-96-2014 | domain_specific | temporary_structure_design_change_request_contract_document |
| C-98-2014 | exclusive | transmission_tower_construction_climbing_lifeline_helicopter_stringing |
| D-27-2021 | exclusive | hydrogen_storage_vessel_ventilation_explosion_relief_emergency_shutdown |
| D-61-2017 | exclusive | flare_system_flame_arrest_liquid_seal_dry_molecular_velocity_seal |
| D-C-1-2025 | exclusive | earth_retaining_wall_shoring_hpile_strut_anchor_soil_nailing_instrumentation |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
