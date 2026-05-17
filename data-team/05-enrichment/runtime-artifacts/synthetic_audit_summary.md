# Phase 3A — Synthetic KO Audit Summary

Generated: 2026-05-17T07:14:59.380238+00:00

## Config

- openai_model: gpt-4.1
- claude_model: claude-sonnet-4-6
- ensemble: GPT@t=0 + Claude@t=0 + GPT@t=0.7,N=3-majority
- consensus_threshold: ≥ 2/3 voices agree on category → ACCEPT; 3/3 → AUTO_ACCEPT; else → HUMAN

## Overall Stats

- Total: 1914
- by status: {'AUTO_ACCEPT': 727, 'ACCEPT': 959, 'HUMAN': 228}
- by category: {'NEW_CODE_NEEDED': 1007, 'WRONG_AXIS': 464, 'NOT_A_CODE': 203, 'EXISTING_EQUIV': 59, 'SUB_CLASS_OF': 181}
- by axis: {'ppe_state': 157, 'hazardous_agent': 797, 'accident_type': 397, 'ppe_missing': 57, 'environmental': 506}

## Category x Axis Matrix

| axis | EXISTING_EQUIV | NEW_CODE_NEEDED | NOT_A_CODE | SUB_CLASS_OF | WRONG_AXIS |
|---|---|---|---|---|---|
| accident_type | 30 | 123 | 29 | 147 | 68 |
| environmental | 0 | 299 | 108 | 0 | 99 |
| hazardous_agent | 29 | 397 | 58 | 34 | 279 |
| ppe_missing | 0 | 52 | 1 | 0 | 4 |
| ppe_state | 0 | 136 | 7 | 0 | 14 |

## KOSHA 22 mapping (accident_type)

| KOSHA KO | matched count |
|---|---|
| 화학물질누출접촉 | 103 |
| 화재 | 25 |
| 절단베임찔림 | 20 |
| 이상온도물체접촉 | 19 |
| 깔림뒤집힘 | 15 |
| 떨어짐 (FALL) | 11 |
| 폭발파열 | 10 |
| 감전 | 9 |
| 끼임·협착 | 8 |
| 비래·낙하물에 맞음 | 8 |
| 폭력행위 | 7 |
| 산소결핍 | 7 |
| 기타 | 6 |
| 불균형및무리한동작 | 5 |
| 미끄러짐·넘어짐 | 5 |
| 무너짐 (COLLAPSE) | 5 |
| 떨어짐 (FALL): 추락 (고소/저공) | 4 |
| 끼임 | 3 |
| 빠짐익사 | 3 |
| 동물상해 | 3 |
| 떨어짐 | 3 |
| 폭발파열 (EXPLOSION) | 3 |
| 부딪힘 (COLLISION) | 3 |
| 깔림·뒤집힘 | 2 |
| 맞음 (STRUCK_BY) | 2 |
| 부딪힘·충돌 | 2 |
| 절단·베임·찔림 | 2 |
| 절단베임찔림 (CUT_LACERATION) | 1 |
| 말림 (KOSHA 22대 분류에는 '말림'이 별도 항목으로 존재하지 않으나, 실제 산업안전 맥락에서 '말림'은 기계 회전체 등에 신체 일부가 감겨 들어가는 사고로, '끼임'과 유사하나 더 구체적임) | 1 |
| 사업장내교통사고 | 1 |
| 부딪힘 | 1 |
| 산소결핍 질식 | 1 |
| 사업장내교통사고, 사업장외교통사고 | 1 |
| 맞음 | 1 |

## WRONG_AXIS top reloc proposals

| from | to | count |
|---|---|---|
| hazardous_agent | accident_type | 153 |
| accident_type | hazardous_agent | 48 |
| hazardous_agent | accident_cause | 25 |
| hazardous_agent | hazardous_condition | 24 |
| environmental | accident_type | 10 |
| hazardous_agent | work_condition | 7 |
| hazardous_agent | equipment | 6 |
| environmental | hazardous_agent | 6 |
| accident_type | injury_type | 6 |
| hazardous_agent | hazardous_place | 5 |
| hazardous_agent | exposure_route | 5 |
| environmental | activity | 5 |
| environmental | equipment | 5 |
| hazardous_agent | hazardous_object | 4 |
| environmental | hazardous_condition | 4 |

## SUB_CLASS_OF top parents

| parent | sub count |
|---|---|
| CHEMICAL_EXPOSURE | 47 |
| CUT | 19 |
| BURN | 18 |
| HEAT_COLD | 17 |
| FALL | 16 |
| CRUSH | 12 |
| EXPLOSION | 10 |
| COLLAPSE | 5 |
| FALLING_OBJECT | 5 |
| RADIATION_EXPOSURE | 5 |
| ELECTRICITY | 4 |
| ELECTRIC_SHOCK | 4 |
| NOISE | 4 |
| COLLISION | 3 |
| ERGONOMIC | 2 |

## NEW_CODE_NEEDED by axis

| axis | count |
|---|---|
| hazardous_agent | 397 |
| environmental | 299 |
| ppe_state | 136 |
| accident_type | 123 |
| ppe_missing | 52 |

## Top 15 freq -- EXISTING_EQUIV

| axis | ko_code | freq | status | canonical_en | parent | reloc |
|---|---|---|---|---|---|---|
| accident_type | 감전 | 77 | AUTO_ACCEPT | ELECTRIC_SHOCK |  |  |
| hazardous_agent | 전기 | 56 | AUTO_ACCEPT | ELECTRICITY |  |  |
| accident_type | 절단 | 33 | ACCEPT | CUT |  |  |
| accident_type | 근골격계 부상 | 32 | ACCEPT | ERGONOMIC |  |  |
| accident_type | 화재 | 32 | ACCEPT |  |  |  |
| accident_type | 추락 | 27 | AUTO_ACCEPT | FALL |  |  |
| accident_type | 화상 | 26 | ACCEPT | BURN |  |  |
| accident_type | 낙상 | 18 | ACCEPT | FALL |  |  |
| accident_type | 충돌 | 17 | AUTO_ACCEPT | COLLISION |  |  |
| accident_type | 근골격계 장애 | 17 | HUMAN | ERGONOMIC |  |  |
| accident_type | 폭발 | 11 | AUTO_ACCEPT | EXPLOSION |  |  |
| accident_type | 화학 사고 | 7 | ACCEPT | CHEMICAL_EXPOSURE |  |  |
| accident_type | 폭력 | 6 | ACCEPT | VIOLENCE |  |  |
| hazardous_agent | 휘발유 증기 | 6 | AUTO_ACCEPT | GASOLINE_VAPOR |  |  |
| hazardous_agent | 정전기 | 6 | AUTO_ACCEPT | STATIC_ELECTRICITY |  |  |

## Top 15 freq -- SUB_CLASS_OF

| axis | ko_code | freq | status | canonical_en | parent | reloc |
|---|---|---|---|---|---|---|
| accident_type | 낙하 | 21 | ACCEPT | FALLING_OBJECT | FALL |  |
| accident_type | 화학 흡입 | 20 | ACCEPT | CHEMICAL_INHALATION | CHEMICAL_EXPOSURE |  |
| accident_type | 피부 자극 | 20 | ACCEPT | SKIN_IRRITATION | CHEMICAL_EXPOSURE |  |
| accident_type | 찔림 | 20 | ACCEPT | PUNCTURE | CUT |  |
| accident_type | 아크 화상 | 13 | AUTO_ACCEPT | ARC_BURN | BURN |  |
| accident_type | 환자 낙상 | 13 | ACCEPT | PATIENT_FALL | FALL |  |
| accident_type | 화학물질 흡입 | 13 | AUTO_ACCEPT | CHEMICAL_INHALATION | CHEMICAL_EXPOSURE |  |
| accident_type | 베임 | 10 | ACCEPT | LACERATION | CUT |  |
| accident_type | 요통 | 9 | HUMAN | LOW_BACK_PAIN | ERGONOMIC |  |
| accident_type | 가스 중독 | 6 | ACCEPT | GAS_POISONING | CHEMICAL_EXPOSURE |  |
| accident_type | 회전체 부상 | 5 | ACCEPT | ROTATING_PART_INJURY | CRUSH |  |
| accident_type | 고압 분출 | 5 | ACCEPT | HIGH_PRESSURE_RELEASE | EXPLOSION |  |
| accident_type | 극저온 화상 | 5 | AUTO_ACCEPT | EXTREME_COLD_BURN | BURN |  |
| accident_type | 절상 | 4 | ACCEPT | LACERATION | CUT |  |
| accident_type | 피부 접촉 | 4 | ACCEPT | SKIN_CONTACT | CHEMICAL_EXPOSURE |  |

## Top 15 freq -- NEW_CODE_NEEDED

| axis | ko_code | freq | status | canonical_en | parent | reloc |
|---|---|---|---|---|---|---|
| environmental | 실험실 | 44 | ACCEPT | LABORATORY |  |  |
| accident_type | 끼임 | 30 | HUMAN | CAUGHT_IN |  |  |
| environmental | 정리정돈_완비 | 30 | HUMAN | ORDERLINESS_COMPLETED |  |  |
| accident_type | 질식 | 29 | HUMAN | ASPHYXIA |  |  |
| ppe_state | 장갑 | 29 | ACCEPT | GLOVES |  |  |
| ppe_state | 절연장갑 | 29 | AUTO_ACCEPT | INSULATING_GLOVES |  |  |
| accident_type | 미끄러짐 | 22 | HUMAN | SLIP |  |  |
| accident_type | 감염 | 22 | ACCEPT | INFECTION |  |  |
| environmental | 복도 | 22 | ACCEPT | CORRIDOR |  |  |
| ppe_missing | 안전모 | 21 | ACCEPT | SAFETY_HELMET |  |  |
| environmental | 야간 | 19 | ACCEPT | NIGHT_TIME |  |  |
| environmental | 습기 | 19 | AUTO_ACCEPT | HUMIDITY |  |  |
| hazardous_agent | 중량물 | 18 | ACCEPT | HEAVY_OBJECT |  |  |
| ppe_state | 안전화 | 18 | ACCEPT | SAFETY_SHOES |  |  |
| environmental | 병실 | 18 | ACCEPT | HOSPITAL_ROOM |  |  |

## Top 15 freq -- WRONG_AXIS

| axis | ko_code | freq | status | canonical_en | parent | reloc |
|---|---|---|---|---|---|---|
| environmental | 전기_기구 | 19 | ACCEPT |  |  | hazardous_agent |
| hazardous_agent | 밀폐 공간 | 13 | ACCEPT | CONFINED_SPACE |  | hazardous_place |
| ppe_state | 전원 차단 | 12 | AUTO_ACCEPT | POWER_SHUTOFF |  | hazard_control_action |
| environmental | 인체공학적_위험 | 12 | ACCEPT |  |  | ergonomic_hazard |
| ppe_state | 전원 잠금 | 10 | ACCEPT |  |  | equipment_state_or_lockout_state |
| hazardous_agent | 높이 | 9 | AUTO_ACCEPT |  |  | accident_type |
| hazardous_agent | 고소 작업 | 8 | AUTO_ACCEPT | WORK_AT_HEIGHT |  | work_condition |
| environmental | 컨베이어_벨트 | 8 | ACCEPT |  |  | equipment_or_machine |
| environmental | 차단기 차단 | 7 | ACCEPT |  |  | equipment_status_or_safety_device_action |
| environmental | 고소_작업 | 7 | ACCEPT |  |  | activity_type |
| accident_type | 기계 오작동 | 6 | ACCEPT |  |  | equipment_failure |
| ppe_state | 검전기 사용 | 6 | ACCEPT |  |  | ppe_usage |
| environmental | 무전압 확인 | 6 | ACCEPT |  |  | work_procedure / electrical_safety |
| environmental | 전원 미차단 | 6 | ACCEPT |  |  | accident_type |
| environmental | LOTO 이행 | 6 | ACCEPT |  |  | safety_procedure |

## Top 15 freq -- NOT_A_CODE

| axis | ko_code | freq | status | canonical_en | parent | reloc |
|---|---|---|---|---|---|---|
| ppe_state | 없음 | 53 | AUTO_ACCEPT |  |  |  |
| environmental | 창고 | 10 | ACCEPT |  |  |  |
| environmental | 2인 협력 | 9 | AUTO_ACCEPT |  |  |  |
| hazardous_agent | 야간 단독 | 6 | ACCEPT |  |  |  |
| environmental | 화장실 | 6 | ACCEPT |  |  |  |
| environmental | 단독 순찰 | 4 | ACCEPT |  |  |  |
| environmental | 야간 단독 | 4 | ACCEPT |  |  |  |
| environmental | 노래방 복도 | 4 | ACCEPT |  |  |  |
| accident_type | 야간 응급 | 3 | AUTO_ACCEPT |  |  |  |
| accident_type | 야간 단독 위험 | 3 | AUTO_ACCEPT |  |  |  |
| accident_type | 야간 단독 응급 | 3 | AUTO_ACCEPT |  |  |  |
| accident_type | 사망 | 3 | AUTO_ACCEPT |  |  |  |
| hazardous_agent | 야간 취약 | 3 | ACCEPT |  |  |  |
| hazardous_agent | 아동 접근 | 3 | ACCEPT |  |  |  |
| environmental | 회의실 | 3 | ACCEPT |  |  |  |

## HUMAN Queue Distribution

- total: 228
- by axis: {'accident_type': 86, 'ppe_state': 3, 'hazardous_agent': 63, 'environmental': 76}
- by category: {'NEW_CODE_NEEDED': 216, 'SUB_CLASS_OF': 7, 'EXISTING_EQUIV': 3, 'NOT_A_CODE': 1, 'WRONG_AXIS': 1}

## HUMAN Queue Top 25 (freq)

| axis | ko_code | freq | consensus_cat | voice categories |
|---|---|---|---|---|
| accident_type | 끼임 | 30 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| environmental | 정리정돈_완비 | 30 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / WRONG_AXIS / NOT_A_CODE |
| accident_type | 질식 | 29 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| accident_type | 미끄러짐 | 22 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| accident_type | 근골격계 장애 | 17 | EXISTING_EQUIV | EXISTING_EQUIV / WRONG_AXIS / SUB_CLASS_OF |
| accident_type | 전도 | 16 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| accident_type | 협착 | 9 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| accident_type | 요통 | 9 | SUB_CLASS_OF | SUB_CLASS_OF / WRONG_AXIS / NEW_CODE_NEEDED |
| accident_type | 말림 | 8 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| accident_type | 갇힘 | 7 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| hazardous_agent | 스파크 | 6 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / SUB_CLASS_OF / WRONG_AXIS |
| accident_type | 익수 | 5 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| accident_type | 걸림 | 4 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| accident_type | 저체온증 | 4 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| environmental | 2인 배치 | 4 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / WRONG_AXIS / NOT_A_CODE |
| environmental | 보조자 지지 | 4 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / NOT_A_CODE / WRONG_AXIS |
| accident_type | 찰과상 | 3 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / WRONG_AXIS / SUB_CLASS_OF |
| accident_type | 미끄럼 전도 | 3 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / EXISTING_EQUIV / SUB_CLASS_OF |
| accident_type | 타박 | 3 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / WRONG_AXIS / NOT_A_CODE |
| accident_type | 흡입 | 3 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / SUB_CLASS_OF / WRONG_AXIS |
| accident_type | 눈 UV 손상 | 3 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / SUB_CLASS_OF / WRONG_AXIS |
| hazardous_agent | 인화성 | 3 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / SUB_CLASS_OF / WRONG_AXIS |
| hazardous_agent | 맨손 취급 | 3 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / WRONG_AXIS / NOT_A_CODE |
| environmental | 환기 확인 | 3 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / NOT_A_CODE / WRONG_AXIS |
| environmental | 지면 작업 | 3 | NEW_CODE_NEEDED | NEW_CODE_NEEDED / NOT_A_CODE / WRONG_AXIS |

