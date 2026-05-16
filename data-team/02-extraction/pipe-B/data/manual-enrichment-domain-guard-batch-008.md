# Manual Enrichment Domain Guard Batch 008

Updated: 2026-05-09

Batch 008 has been upgraded from generated draft to source-JSON manual review. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-008.json
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
| SR link candidates | 90 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 0 |
| SR link candidates needing review | 23 |
| Visual trigger candidates needing review | 0 |

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| E-116-2021 | exclusive | overcurrent_protective_device_selection_installation |
| E-121-2012 | exclusive | esd_shielding_standard_test |
| E-123-2012 | exclusive | sf6_gas_analysis_recovery_electrical_equipment |
| E-129-2012 | exclusive | low_voltage_switchgear_controlgear_rating_maintenance |
| E-13-2012 | exclusive | fuel_station_static_electricity_bonding |
| E-130-2012 | exclusive | voltage_applied_static_eliminator_safety |
| E-131-2012 | exclusive | low_voltage_switchgear_emc_malfunction_test |
| E-132-2013 | exclusive | high_voltage_switchgear_38kv_maintenance |
| E-134-2013 | exclusive | medical_electrical_system_patient_environment |
| E-135-2013 | exclusive | low_voltage_switchgear_type_routine_testing |
| E-139-2013 | exclusive | emergency_luminaire_functional_safety |
| E-140-2013 | exclusive | emergency_luminaire_battery_management |
| E-141-2013 | exclusive | combustible_dust_cable_fire_risk |
| E-142-2013 | exclusive | pneumatic_grinder_static_control |
| E-147-2015 | exclusive | communication_cable_manhole_pole_installation |
| E-15-2012 | exclusive | switchgear_operation_maintenance_sf6 |
| E-158-2017 | exclusive | ex_equipment_manufacturer_quality_management |
| E-16-2012 | exclusive | building_construction_site_temporary_distribution |
| E-163-2017 | domain_specific | special_power_systems_installation |
| E-164-2017 | exclusive | specific_use_electrical_equipment_installation |
| E-168-2018 | exclusive | hospital_medical_location_electrical_installation |
| E-17-2012 | exclusive | high_voltage_switchgear_maintenance |
| E-170-2023 | exclusive | photovoltaic_pv_array_installation |
| E-171-2018 | exclusive | splash_filling_flammable_liquid_static_fire |
| E-173-2018 | exclusive | anti_static_wrist_strap_test |
| E-178-2020 | exclusive | hazardous_area_static_property_measurement |
| E-179-2020 | exclusive | esd_contamination_control_cleanroom |
| E-18-2012 | exclusive | low_voltage_switchgear_maintenance |
| E-181-2020 | exclusive | non_electrical_equipment_hazardous_area_ignition_control |
| E-182-2021 | exclusive | static_fire_explosion_accident_investigation |

## Manual Correction Examples

```text
E-116/E-129/E-135/E-18: broad electrical/fire defaults -> overcurrent and switchgear-specific profiles
E-121/E-131/E-173/E-178: test-method documents -> ESD/EMC/static-measurement boundaries with conservative SR candidates
E-13/E-171/E-142: static electricity guides split into fuel-station, splash-filling, and pneumatic-grinder contexts
E-147: generic electrical draft -> communication cable manhole/pole work with confined-space and fall SR candidates
E-168/E-170: hospital electrical and photovoltaic installation profiles separated from generic electrical work
E-181/E-182: hazardous-area non-electrical equipment and accident-investigation guides kept exclusive to avoid broad recommendation leakage
```

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
