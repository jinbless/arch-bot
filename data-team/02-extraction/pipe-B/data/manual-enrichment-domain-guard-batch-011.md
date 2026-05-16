# Manual Enrichment Domain Guard Domain Guard Manual Batch 011

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-011.json
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
| SR link candidates | 178 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 1 |
| SR link candidates needing review | 51 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
M-159/M-165/M-166/M-188: farm/vehicle defaults corrected into excavator, tractor, ATV, and agricultural-machine operation boundaries.
M-16/M-168: grain mill and paper-machine Guides separated from generic fire/chemical defaults into machine, dust, access, roll-nip, and confined-space profiles.
M-169/M-176/M-178/M-179/M-181/M-183/M-25/M-27: woodworking, food cutting, bandknife, circular saw, router, bone saw, narrow band saw, and four-sided moulder Guides moved to equipment-specific saw/cut/guard domains.
M-171/M-182/M-187/M-22/M-4: lift, hydraulic press brake, injection molding, metal shearing, and multipurpose metalworker Guides mapped to machinery/lifting/press guarding rather than hot-work defaults.
M-184/M-191/M-192: technical design/calculation Guides kept exclusive so they do not surface as generic field procedures without pressure-vessel or SRP/CS context.
M-193/M-20/M-21/M-37/M-39: printing press, lathe emery cloth, metalworking-fluid, noise-assessment, and ergonomics Guides assigned to visual/profile boundaries that match actual work signals.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| M-159-2012 | exclusive | tree_work_excavator_forestry_overhead_powerline_slope |
| M-16-2012 | exclusive | grain_mill_machine_conveyor_access_dust_fire |
| M-161-2012 | exclusive | food_packaging_machine_guarding_capping_sealing |
| M-165-2013 | exclusive | tractor_safe_driving_pto_trailer_rollover |
| M-166-2013 | exclusive | atv_offroad_vehicle_towing_rollover |
| M-168-2013 | exclusive | paper_machine_roll_nip_confined_maintenance |
| M-169-2013 | exclusive | woodworking_shaper_cutter_guard_kickback |
| M-171-2013 | exclusive | automotive_repair_lift_vehicle_hoist |
| M-176-2014 | exclusive | bandknife_shearing_machine_guarding_dust_exhaust |
| M-177-2014 | exclusive | scrap_baling_machine_compressor_guarding |
| M-178-2014 | exclusive | veneer_cutting_machine_blade_clamp_guarding |
| M-179-2014 | exclusive | woodworking_manual_circular_saw_guarding |
| M-180-2023 | exclusive | fabric_cutting_machine_blade_guard_lint_fire |
| M-181-2014 | exclusive | woodworking_router_cnc_manual_guarding_dust_noise |
| M-182-2015 | exclusive | hydraulic_press_brake_photoelectric_laser_guarding |
| M-183-2015 | exclusive | meat_bone_band_saw_food_cutting_guarding |
| M-184-2015 | exclusive | pressure_vessel_pwht_technical_heat_treatment |
| M-187-2016 | exclusive | injection_molding_machine_guard_interlock_hot_surface |
| M-188-2015 | exclusive | agricultural_machine_safe_stop_guard_maintenance |
| M-191-2017 | exclusive | machine_safety_control_mttfd_calculation |
| M-192-2017 | exclusive | machine_safety_control_srp_cs_pl_design |
| M-193-2020 | exclusive | printing_press_guarding_cleaning_solvent_nip |
| M-20-2012 | exclusive | lathe_emery_cloth_rotating_entanglement |
| M-21-2012 | exclusive | metalworking_fluid_mist_skin_respiratory_exposure |
| M-22-2012 | exclusive | metal_shearing_machine_guarding_noise_blade_change |
| M-25-2012 | exclusive | woodworking_narrow_band_saw_guard_push_stick |
| M-27-2012 | exclusive | four_sided_wood_moulder_guard_noise_dust |
| M-37-2012 | domain_specific | workplace_machine_noise_assessment_program |
| M-39-2012 | domain_specific | workplace_ergonomics_work_system_design |
| M-4-2016 | exclusive | multipurpose_metalworker_punch_shear_bend_guarding |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
