# SHE L2 패턴 보강 — SR 매핑 검토 시트 (37 패턴)

> OWA→CWA 라이브검증 gap 보강으로 추가한 37개 focused SHE 패턴의 SR(안전요구사항) 링크.
> 모두 **best-effort, 사용자 검토 대상**. 라이브 추출이 실제로 산출하는 canonical 코드 기준으로 키잉.
> 공통: `source_model=phase3c/direct-llm-gpt-4.1`, `ppe_state/environmental=OTHER`(specific_mismatch 회피), `broadness_score=0.55`.

## 🔴 검토 우선순위 1 — CUT 계열 (SR 링크 약함)
손칼 베임(정육·수산·꽃꽂이)에 대한 **전용 SR(방검장갑/체인메일)이 레지스트리에 부재**. 차선책으로 `SR-MACHINE-010`(회전 기계 밀착형 안전장갑) 연결 — "장갑"은 맞으나 "회전 기계"용이라 의미 부정확. **더 적합한 SR 지정 또는 신규 SR 정의 후보.**

| 패턴 | work_context | accident_type | SR(best-effort) |
|---|---|---|---|
| SHE-KNIFEWORK-L2T01~03 | KNIFE_WORK | CUT/LACERATION/PUNCTURE | `SR-MACHINE-010` |
| SHE-FISHCUTTING-L2T04~05 | FISH_CUTTING | CUT/LACERATION | `SR-MACHINE-010` |
| SHE-FLORALARR-L2T06~08 | FLORAL_ARRANGEMENT | CUT/LACERATION/PUNCTURE | `SR-MACHINE-010` |

## 🟢 검토 우선순위 2 — 나머지 (링크 적정, 확인만)
| 패턴 | work_context | 코드 | SR |
|---|---|---|---|
| SHE-SHARPSDISP-L2T09~10 | SHARPS_DISPOSAL | PUNCTURE/INFECTION | `SR-PATHOGEN-003/004/007` |
| SHE-DENTALPROC-L2T11~12 | DENTAL_PROCEDURE | INFECTION/PUNCTURE | `SR-PATHOGEN-003/007/008` |
| SHE-HIGHRISEWIN-L2T13~18 | HIGH_RISE_WINDOW | FALL_* (6 subcode) | `SR-FALL-003/001`, `SR-LIFTING-013`, `SR-MGMT-003` |
| SHE-EXTROPE-L2T19~21 | EXTERIOR_ROPE | ROPE/KNOT/FRICTION FALL | `SR-FALL-003/006` |
| SHE-DEEPFRYING-FG01~03 | DEEP_FRYING | BURN/FIRE_AND_EXPLOSION/EXPLOSION | `SR-FIRE_EXPLOSION-030/001/015`, `SR-HEAT-013` |
| SHE-GASAPPLIANCE-FG04~07 | GAS_APPLIANCE | BURN/FIRE_AND_EXPLOSION/EXPLOSION/GAS_LEAK | `SR-FIRE_EXPLOSION-030/008/015` |
| SHE-HOTBEVERAGE-FG08 | HOT_BEVERAGE | BURN | `SR-FIRE_EXPLOSION-030`, `SR-HEAT-013` |
| SHE-KITCHENCOOK-FG09 | KITCHEN_COOKING | BURN | `SR-FIRE_EXPLOSION-030` |
| SHE-SERVINGFLOOR-FG10~11 | SERVING_FLOOR | BURN/FIRE_AND_EXPLOSION | `SR-FIRE_EXPLOSION-030/015` |
| SHE-COLDSTORAGE-FG12 | COLD_STORAGE | (ha) PROLONGED_COLD_EXPOSURE | `SR-HEAT-004/013` |
| SHE-BIOMEDWASTE-ID01~02 | BIOMEDICAL_WASTE | PUNCTURE/BLADE_LACERATION | `SR-PATHOGEN-003/004/007` |
| SHE-CONFINEDSPC-ID03 | CONFINED_SPACE | (ha) OXYGEN_DEFICIENCY | `SR-CONFINED-001/002` |
| SHE-ELECWORK-ID04 | ELECTRICAL_WORK | ELECTRIC_SHOCK | `SR-ELECTRIC-001/021` |

## 검토 방법
- 각 패턴의 `source_sr_ids`는 `she_pattern_proposals.json`에서 marker(`owacwa-l2tune/foodgas/ind-20260608`)로 검색.
- 수정 시: proposals.json의 해당 `source_sr_ids` 편집 → `DELETE`(해당 she_id의 she_sr_mapping) → `make she-import ARGS='--apply'` 재적재.
- 검증된 라이브 효과: 서비스 5업종 recall +0.133, 식음료 3업종 +0.221, 산업 6케이스. 모두 회귀가드 PASS(fp FLAT).
