# hybrid_attach SSOT curation 후보 (수동 검토)

> ⚠️ 자동 생성. **SSOT(canonical_vocab/SHE TTL/TBox) 자동 적용 금지.** 
> 사람 승인 + reasoner 일관성 + SHACL + manifest 게이트 후 편입.
> 파생 캐시(learned.json)는 자동 승격됨(support≥2). 본 report는 SSOT 편입 후보만.

## link 후보 (code_sig → verified guide), promoted 19건
SHE 패턴 미커버분은 신규 she:SituationalHazardPattern anchor 후보.

| support | code_sig | top guides |
|---|---|---|
| 6 | `accident_type.CRUSH|hazardous_agent.ELECTRICITY|work_context.GENERAL_WORKPLACE` | B-E-10-2026, B-E-11-2026, E-100-2021 |
| 6 | `accident_type.COLLISION|work_context.VEHICLE` | G-10-2023, B-M-11-2025, A-G-3-2025 |
| 5 | `accident_type.COLLAPSE|work_context.EXCAVATION` | D-C-11-2026, D-C-1-2025, C-45-2012 |
| 4 | `accident_type.FALL|work_context.SCAFFOLD` | D-C-7-2026, A-G-1-2025, C-21-2011 |
| 4 | `accident_type.FALLING_OBJECT|work_context.CRANE` | B-M-7-2026, B-M-8-2025, B-M-9-2025 |
| 3 | `accident_type.CRUSH|accident_type.CUT|work_context.MACHINE` | B-M-3-2025, B-M-36-2026, B-M-37-2026 |
| 3 | `accident_type.COLLAPSE|hazardous_agent.CHEMICAL|hazardous_agent.TOXIC|work_context.GENERAL_WORKPLACE` | E-G-19-2026, D-24-2012, G-9-2013 |
| 3 | `accident_type.COLLAPSE|hazardous_agent.CHEMICAL|hazardous_agent.CORROSION|work_context.GENERAL_WORKPLACE` | C-18-2015, D-24-2012, P-117-2012 |
| 3 | `accident_type.COLLAPSE|hazardous_agent.TOXIC|work_context.CONFINED_SPACE` | C-45-2012, C-C-1-2025, D-21-2012 |
| 2 | `accident_type.COLLAPSE|accident_type.FALL|work_context.SCAFFOLD` | D-C-7-2026, C-36-2011, D-C-14-2026 |
| 2 | `accident_type.FALL|accident_type.FALLING_OBJECT|work_context.SCAFFOLD` | B-M-8-2025, C-17-2011, C-21-2011 |
| 2 | `work_context.EXCAVATION` | G-29-2011, A-G-2-2025, M-48-2012 |
| 2 | `accident_type.CRUSH|hazardous_agent.ARC_FLASH|hazardous_agent.ELECTRICITY|work_context.GENERAL_WORKPLACE` | B-E-12-2026, B-E-10-2026, B-E-15-2026 |
| 2 | `work_context.GENERAL_WORKPLACE` | B-M-25-2026, B-E-12-2026, B-E-10-2026 |
| 2 | `accident_type.COLLAPSE|hazardous_agent.CHEMICAL|hazardous_agent.TOXIC|work_context.CONFINED_SPACE` | E-G-18-2026, C-45-2012, D-21-2012 |
| 2 | `work_context.CONFINED_SPACE` | C-14-2012, E-G-18-2026, C-C-70-2025 |
| 2 | `accident_type.COLLISION|accident_type.FALLING_OBJECT|work_context.CRANE` | B-M-7-2026, B-M-9-2025, B-M-8-2025 |
| 2 | `work_context.CRANE` | B-M-34-2026, C-85-2013, B-M-8-2025 |
| 2 | `work_context.VEHICLE` | G-10-2023, B-M-11-2025, G-100-2013 |

## alias 후보 (name → codes), promoted 1건
canonical_vocab alias 편입 후보 (0-코드 hazard 해소).

| support | name_norm | codes |
|---|---|---|
| 3 | 사진에서 관찰 가능한 위험 요소가 없다. | work_context.CONVEYOR, work_context.CRANE, work_context.VEHICLE |