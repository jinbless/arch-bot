# Manual Domain Guard Broad SR Policy

Generated: 2026-05-09

This policy keeps broad SR candidates available as supporting evidence, but prevents them from becoming the primary reason a Guide is recommended as a standard procedure. It does not import to PostgreSQL and does not promote asserted mappings.

## Runtime Rules

- A broad SR candidate must not create a standard procedure by itself.
- A broad SR candidate may only boost a Guide after at least one guide-specific signal matches: `required_context_terms`, visual trigger, non-generic feature, WorkProcess text, or `industry_alignment`.
- For document, measurement, health-screening, and risk-method Guides, broad SR candidates are review-only unless the photo/text context also matches the Guide-specific domain boundary.
- For exclusive Guides, broad SR candidates are ignored when the Guide domain boundary is not matched.
- Broad SR contribution should be capped as a secondary score component, recommended multiplier `<= 0.35`.
- Broad SRs may support immediate actions only when a matched WorkProcess or ChecklistItem carries the same concrete cue.

## Broad SR Candidates

| SR | Count | Distinct domain families | Title | Policy |
|---|---:|---:|---|---|
| SR-PPE-002 | 275 | 251 | 보호구의 지급 등 | secondary signal only |
| SR-CHEMICAL-024 | 268 | 244 | 유해성 등의 주지 | secondary signal only |
| SR-CHEMICAL-025 | 199 | 185 | 호흡용 보호구의 지급 등 | secondary signal only |
| SR-CHEMICAL-026 | 185 | 162 | 보호복 등의 비치 등 | secondary signal only |
| SR-FIRE_EXPLOSION-015 | 126 | 119 | 위험물 등이 있는 장소에서 화기 등의 사용 금지 | secondary signal only |
| SR-MGMT-004 | 106 | 106 | 사전조사 및 작업계획서의 작성 등 | secondary signal only |
| SR-ELECTRIC-024 | 87 | 87 | 정전기로 인한 화재 폭발 등 방지 | secondary signal only |
| SR-FIRE_EXPLOSION-019 | 83 | 83 | 소화설비 | secondary signal only |
| SR-ELECTRIC-011 | 80 | 80 | 폭발위험장소에서 사용하는 전기 기계ㆍ기구의 선정 등 | secondary signal only |
| SR-FIRE_EXPLOSION-008 | 67 | 67 | 폭발 또는 화재 등의 예방 | secondary signal only |
| SR-FIRE_EXPLOSION-001 | 58 | 58 | 위험물질 등의 제조 등 작업 시의 조치 | secondary signal only |
| SR-FIRE_EXPLOSION-037 | 52 | 52 | 안전밸브 등의 설치 | secondary signal only |

## Import Preview Guidance

- Import may preserve these rows as candidates.
- Do not promote these rows to asserted mappings from manual batch evidence alone.
- OHS recommendation scoring should treat these SRs as supporting evidence, not primary Guide selectors.
- Manual review should focus on broad SRs attached to document/risk-method Guides first.
