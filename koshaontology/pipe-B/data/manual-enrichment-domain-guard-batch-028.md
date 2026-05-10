# Manual Enrichment Domain Guard Batch 028

Generated: 2026-05-09

This batch was produced locally from extracted Pipe-B Guide JSON. No external API was used, DB import was not run, and asserted mappings remain unchanged.

## Summary

- Guides: 30
- Feature candidates: 60 (needs_review 2)
- SR link candidates: 145 (needs_review 41)
- Visual trigger candidates: 60 (needs_review 0)
- Guides with no SR candidate: 0
- Boundary: first 8 A-series measurement documents plus E-G ergonomics, diving, confined space, respirator, asbestos, ventilation, heat, vibration, office, and waste-incineration technical support Guides.

## Guides

- `A-89-2018` 프탈릭언하이드라이드에 대한 작업환경측정·분석 기술지침 - phthalic_anhydride_measurement_analysis / exclusive
- `A-9-2018` 아연에 대한 작업환경측정·분석 기술지침 - zinc_measurement_analysis / exclusive
- `A-92-2018` o-톨루이딘에 대한 작업환경측정·분석 기술지침 - o_toluidine_measurement_analysis / exclusive
- `A-93-2018` 니트로벤젠에 대한 작업환경측정·분석 기술지침 - nitrobenzene_measurement_analysis / exclusive
- `A-94-2018` o-메틸시클로헥사논에 대한 작업환경측정·분석 기술지침 - o_methylcyclohexanone_measurement_analysis / exclusive
- `A-95-2018` 메틸시클로헥사놀에 대한 작업환경측정·분석 기술지침 - methylcyclohexanol_measurement_analysis / exclusive
- `A-97-2018` 아크릴아미드에 대한 작업환경측정·분석 기술지침 - acrylamide_measurement_analysis / exclusive
- `A-98-2018` 알파나프틸아민에 대한 작업환경측정·분석 기술지침 - alpha_naphthylamine_measurement_analysis / exclusive
- `E-G-1-2025` 근골격계질환 예방을 위한 기술지원규정 - ergonomic_msd_prevention_program / domain_specific
- `E-G-10-2026` 잠수용 생명줄에 관한 기술지원규정 - diver_umbilical_lifeline_management / exclusive
- `E-G-11-2026` 공기잠수 감압에 관한 기술지원규정 - air_diving_decompression_management / exclusive
- `E-G-12-2026` 잠수용 기압조절실을 이용한 치료표 운용에 관한 기술지원규정 - diving_chamber_treatment_table_operation / exclusive
- `E-G-13-2026` 잠수용 호흡기체의 질 및 분압에 관한 기술지원규정 - diving_breathing_gas_quality_management / exclusive
- `E-G-14-2026` 잠수기어업 표면공급식 잠수작업에 관한 기술지원규정 - surface_supplied_fishing_diving_work / exclusive
- `E-G-15-2026` 잠수작업 보건관리에 관한 기술지원규정 - diving_health_and_equipment_management / exclusive
- `E-G-16-2026` 잠수작업 안전관리에 관한 기술지원규정 - diving_work_safety_underwater_cutting / exclusive
- `E-G-17-2026` 생식독성물질 취급 사업장의 보건관리에 관한 기술지원규정 - reproductive_toxicant_workplace_health_management / domain_specific
- `E-G-18-2026` 밀폐공간 작업 프로그램 수립 및 시행에 관한 기술지원규정 - confined_space_program_management / exclusive
- `E-G-19-2026` 호흡보호구의 선정·사용 및 관리에 관한 기술지원규정 - respiratory_protection_selection_management / domain_specific
- `E-G-2-2025` 직무스트레스로 인한 건강장해 예방 기술지원규정 - job_stress_health_management / domain_specific
- `E-G-20-2026` 건축물 등의 석면조사에 관한 기술지원규정 - asbestos_survey_management / exclusive
- `E-G-21-2026` 산업환기설비에 관한 기술지원규정 - industrial_ventilation_system_management / domain_specific
- `E-G-22-2026` 고열작업환경 관리에 관한 기술지원규정 - heat_work_environment_management / domain_specific
- `E-G-23-2026` 작업자의 진동 제어 및 건강 예방에 관한 기술지원규정 - vibration_exposure_control_health_management / domain_specific
- `E-G-3-2025` 영상표시단말기를 사용하는 사무환경 관리에 관한 기술지원규정 - vdt_office_ergonomics_management / domain_specific
- `E-G-4-2025` 근골격계질환 예방을 위한 업종직종별 기술지원규정 - industry_task_msd_prevention_management / domain_specific
- `E-G-5-2025` 직무스트레스로 인한 건강장해 예방을 위한 업종별, 직종별 기술지원규정 - industry_task_job_stress_management / domain_specific
- `E-G-6-2025` 건강한 사무환경 구축 기술지원규정 - healthy_office_environment_air_quality_management / domain_specific
- `E-G-7-2025` 폐기물 소각시설의 작업관리 기술지원규정 - waste_incineration_facility_work_management / exclusive
- `E-G-8-2026` 잠수용 기압조절실에 관한 기술지원규정 - diving_pressure_chamber_management / exclusive

## Review Notes

- A-series measurement links remain non-asserted and mostly `needs_review`.
- Diving and confined-space Guides are exclusive profiles; they require diving/pressure/chamber or confined-space permit/gas-measurement context.
- Job-stress Guides expose a taxonomy/SR gap and therefore keep weak `needs_review` links rather than forcing a legal SR mapping.
- Broad office, ventilation, heat, vibration, and respiratory-protection Guides are domain_specific so unrelated photos are penalized, not blindly excluded.
