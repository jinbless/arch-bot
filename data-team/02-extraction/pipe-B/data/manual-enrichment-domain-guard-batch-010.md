# Manual Enrichment Domain Guard Domain Guard Manual Batch 010

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-010.json
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
| SR link candidates | 87 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 1 |
| SR link candidates needing review | 38 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
E-85/E-94/E-96/E-97: broad fire/electrical defaults -> electrical installation, machine controlgear, emergency-stop, and petrochemical ex-proof power-system profiles.
M-10/M-14: generic chemical/electrical drafts -> sharp-edge and hand-knife cut-prevention boundaries.
M-103/M-107/M-109/M-111/M-113/M-146/M-150: pressure, pneumatic, NDT, welding, repair, aging-equipment, and inert-gas test profiles separated from generic hot-work/fire.
M-124/M-128/M-13/M-133/M-134/M-135/M-142/M-155: machine-specific guarding and operation boundaries strengthened with visual equipment triggers.
M-114/M-121/M-131: diagnostic/analysis Guides kept exclusive and linked only to conservative machine-defect review candidates.
M-139/M-153/M-154: slip measurement, wood-panel stacking, and GRP tank chemical/static/confined-space contexts split into distinct profiles.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| E-85-2017 | domain_specific | electrical_installation_wiring_grounding_overcurrent |
| E-94-2011 | exclusive | industrial_machine_electrical_equipment_controlgear |
| E-96-2011 | exclusive | industrial_machine_emergency_stop_design |
| E-97-2022 | exclusive | petrochemical_plant_electrical_installation_exproof_power_system |
| M-10-2012 | domain_specific | sharp_edge_manual_handling_cut_prevention |
| M-103-2017 | exclusive | pneumatic_system_compressed_air_safety |
| M-107-2012 | exclusive | pressure_vessel_ultrasonic_testing_ndt |
| M-109-2012 | exclusive | pressure_vessel_thickness_loss_risk_assessment |
| M-111-2015 | exclusive | pressure_vessel_welding_design_ndt |
| M-113-2012 | exclusive | pressure_vessel_repair_welding_pwht |
| M-114-2012 | exclusive | lubricating_oil_analysis_machine_fault_diagnosis |
| M-121-2012 | exclusive | machine_condition_monitoring_performance_parameters |
| M-123-2012 | domain_specific | machine_risk_assessment_safeguarding |
| M-124-2012 | exclusive | textile_scouring_machine_steam_pressure_interlock |
| M-128-2012 | exclusive | cement_block_molding_machine_guarding |
| M-13-2012 | exclusive | plastic_film_winding_nip_guarding |
| M-131-2012 | exclusive | machine_fault_diagnosis_data_analysis |
| M-133-2012 | exclusive | agricultural_machinery_guarding_operation |
| M-134-2012 | exclusive | wire_drawing_machine_guarding_emergency_stop |
| M-135-2023 | exclusive | rubber_plastic_roller_machine_guarding |
| M-136-2012 | exclusive | construction_lift_pinion_shaft_ultrasonic_testing |
| M-137-2023 | domain_specific | machine_lifecycle_risk_assessment_safeguarding |
| M-139-2012 | domain_specific | ceramic_floor_slip_measurement_control |
| M-14-2012 | domain_specific | hand_knife_cutting_tool_safety |
| M-142-2012 | exclusive | high_pressure_metal_die_casting_machine_guarding |
| M-146-2012 | exclusive | aging_equipment_damage_life_assessment_ndt |
| M-150-2022 | exclusive | inert_gas_leak_tightness_testing_pressure |
| M-153-2012 | exclusive | wood_panel_stacking_storage_material_handling |
| M-154-2012 | exclusive | grp_tank_manufacturing_chemical_static_confined |
| M-155-2023 | exclusive | mobile_elevated_work_platform_selection_operation |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
