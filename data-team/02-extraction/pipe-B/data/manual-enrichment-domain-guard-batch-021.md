# Manual Enrichment Domain Guard Domain Guard Manual Batch 021

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-021.json
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
| SR link candidates | 195 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 0 |
| SR link candidates needing review | 25 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
P-77/C-103/C-108/C-11/C-113/C-114: remote shutoff, excavation instrumentation, hot work, temporary stairs, seasonal construction, and dump/cargo truck boundaries separated from broad fire/general construction defaults.
C-14/C-16/C-17/C-18/C-2/C-21/C-22: confined waterproofing, plastering, light steel ceiling, design-for-safety, barge construction, suspension bridge, and cable-stayed bridge cues grounded in visible equipment/documents.
C-25/C-26/C-27/C-29/C-36/C-41/C-45: temporary equipment performance, falling-object net/shelf/vertical net, bridge formwork cart, PSC bridge, and NATM tunnel profiles corrected for exclusive/domain-specific runtime guard use.
C-47/C-48/C-49/C-50/C-52/C-53/C-54/C-55/C-56/C-57: demolition, construction machinery, safety harness, asphalt paving, night construction, PC assembly, tower deep foundation, curtain wall, remodeling, and stonework Guide boundaries added with candidate-only SR links.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| P-77-2011 | exclusive | remote_shutoff_valve_rosov_excess_flow_fire_explosion_release |
| C-103-2014 | exclusive | excavation_instrumentation_inclinometer_settlement_groundwater_monitoring |
| C-108-2017 | domain_specific | construction_hot_work_welding_cutting_fire_gas_electric_shock |
| C-11-2012 | exclusive | temporary_stair_installation_tread_landing_guardrail |
| C-113-2020 | domain_specific | seasonal_construction_multi_hazard_fire_collapse_confined_flood_winter |
| C-114-2020 | domain_specific | dump_truck_cargo_truck_loading_unloading_spotter_route |
| C-14-2012 | exclusive | confined_space_waterproofing_oxygen_deficiency_vapor_ventilation |
| C-16-2016 | domain_specific | plastering_mortar_mixing_material_handling_floor_finisher |
| C-17-2011 | domain_specific | light_steel_ceiling_mbar_panel_nail_gun_overhead_work |
| C-18-2015 | general | construction_design_for_safety_temporary_works_design_review |
| C-2-2020 | exclusive | barge_construction_waterborne_work_lifesaving_mooring_weather |
| C-21-2011 | exclusive | suspension_bridge_construction_cable_high_work_lifting |
| C-22-2011 | exclusive | cable_stayed_bridge_construction_pylon_cable_segment_lifting |
| C-25-2018 | domain_specific | reused_temporary_equipment_performance_scaffold_shoring_inspection |
| C-26-2017 | exclusive | falling_object_prevention_net_installation_building_perimeter |
| C-27-2011 | exclusive | falling_object_protection_shelf_canopy_installation |
| C-29-2017 | exclusive | vertical_protection_net_scaffold_facade_falling_object_fire_retardant |
| C-36-2011 | exclusive | bridge_slab_formwork_dismantling_work_cart_hydraulic_platform |
| C-41-2011 | exclusive | psc_bridge_girder_tensioning_lifting_overturn_prevention |
| C-45-2012 | exclusive | natm_tunnel_blasting_shotcrete_rockbolt_ventilation_support |
| C-47-2023 | exclusive | demolition_work_structural_stability_breaker_cutting_collapse |
| C-48-2022 | exclusive | construction_machinery_vehicle_foundation_machine_pile_driver_safety_device |
| C-49-2012 | exclusive | fall_arrest_harness_lanyard_lifeline_anchor_safety_belt |
| C-50-2012 | domain_specific | asphalt_concrete_paving_paver_roller_dump_truck_traffic_control |
| C-52-2016 | domain_specific | night_construction_lighting_visibility_emergency_handover |
| C-53-2012 | exclusive | precast_concrete_pc_assembly_crane_spreader_beam_slinging |
| C-54-2012 | exclusive | transmission_tower_deep_foundation_liner_plate_excavation_confined |
| C-55-2015 | domain_specific | metal_curtain_wall_unit_installation_embedded_plate_sealant_lifting |
| C-56-2017 | domain_specific | remodeling_demolition_asbestos_interior_repair_reinforcement |
| C-57-2017 | domain_specific | building_stonework_wet_dry_anchor_sealant_cutting_handling |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
