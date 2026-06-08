# SHE L2 패턴 보강 — SR 매핑 검토 시트 (37 패턴)

> OWA→CWA 라이브검증 gap 보강으로 추가한 37개 focused SHE 패턴의 SR(안전요구사항) 링크.
> **검토 완료(2026-06-08)** — 약한 링크 2건 교체 적용. 공통: `source_model=phase3c/direct-llm-gpt-4.1`,
> `ppe_state/environmental=OTHER`(specific_mismatch 회피), `broadness_score=0.55`.

## ✅ 검토 반영 (2026-06-08) — 2건 교체
| 대상 | 변경 전 | 변경 후 | 이유 |
|---|---|---|---|
| CUT 계열 8패턴 (KNIFE/FISH/FLORAL) | `SR-MACHINE-010` | **`SR-PPE-002`** | SR-MACHINE-010은 "**회전 기계** 밀착형 안전장갑"이라 손칼 작업에 부정확. SR-PPE-002("작업별 보호구 지급 및 착용 의무")가 방검장갑의 정확한 법적 근거. |
| SHE-EXTROPE-L2T19 | `SR-FALL-003`+`SR-FALL-006` | **`SR-FALL-003`** | SR-FALL-006("**수상·선박건조** 구명장구")은 외벽 로프작업에 부적합 → 제거. 안전대(SR-FALL-003)만 유지. |

PG 반영 완료(she_catalog.source_sr_ids + she_sr_mapping 재파생, stale 0 확인).

## 최종 SR 매핑 (37 패턴)
| 패턴 | work_context | 코드 | SR | 적합 |
|---|---|---|---|:--:|
| SHE-KNIFEWORK-L2T01~03 | KNIFE_WORK | CUT/LACERATION/PUNCTURE | `SR-PPE-002` | ✅ |
| SHE-FISHCUTTING-L2T04~05 | FISH_CUTTING | CUT/LACERATION | `SR-PPE-002` | ✅ |
| SHE-FLORALARR-L2T06~08 | FLORAL_ARRANGEMENT | CUT/LACERATION/PUNCTURE | `SR-PPE-002` | ✅ |
| SHE-SHARPSDISP-L2T09~10 | SHARPS_DISPOSAL | PUNCTURE/INFECTION | `SR-PATHOGEN-003/004/007` | ✅ |
| SHE-DENTALPROC-L2T11~12 | DENTAL_PROCEDURE | INFECTION/PUNCTURE | `SR-PATHOGEN-003/007/008` | ✅ |
| SHE-HIGHRISEWIN-L2T13~18 | HIGH_RISE_WINDOW | FALL_* (6 subcode) | `SR-FALL-003/001`, `SR-LIFTING-013`, `SR-MGMT-003` | ✅ |
| SHE-EXTROPE-L2T19~21 | EXTERIOR_ROPE | ROPE/KNOT/FRICTION FALL | `SR-FALL-003` | ✅ |
| SHE-DEEPFRYING-FG01~03 | DEEP_FRYING | BURN/FIRE_AND_EXPLOSION/EXPLOSION | `SR-FIRE_EXPLOSION-030/001/015`, `SR-HEAT-013` | ✅ |
| SHE-GASAPPLIANCE-FG04~07 | GAS_APPLIANCE | BURN/FIRE_AND_EXPLOSION/EXPLOSION/GAS_LEAK | `SR-FIRE_EXPLOSION-030/008/015` | ✅ |
| SHE-HOTBEVERAGE-FG08 | HOT_BEVERAGE | BURN | `SR-FIRE_EXPLOSION-030`, `SR-HEAT-013` | ✅ |
| SHE-KITCHENCOOK-FG09 | KITCHEN_COOKING | BURN | `SR-FIRE_EXPLOSION-030` | ✅ |
| SHE-SERVINGFLOOR-FG10~11 | SERVING_FLOOR | BURN/FIRE_AND_EXPLOSION | `SR-FIRE_EXPLOSION-030/015` | ✅ |
| SHE-COLDSTORAGE-FG12 | COLD_STORAGE | (ha) PROLONGED_COLD_EXPOSURE | `SR-HEAT-004/013` | ✅ |
| SHE-BIOMEDWASTE-ID01~02 | BIOMEDICAL_WASTE | PUNCTURE/BLADE_LACERATION | `SR-PATHOGEN-003/004/007` | ✅ |
| SHE-CONFINEDSPC-ID03 | CONFINED_SPACE | (ha) OXYGEN_DEFICIENCY | `SR-CONFINED-001/002` | ✅ |
| SHE-ELECWORK-ID04 | ELECTRICAL_WORK | ELECTRIC_SHOCK | `SR-ELECTRIC-001/021` | ✅ |

## SR 수정 절차 (⚠️ import ON CONFLICT 주의)
1. `she_pattern_proposals.json`의 `source_sr_ids` 편집 (소스 정본).
2. ⚠️ **import은 `ON CONFLICT(she_id) DO NOTHING`이라 기존 she_catalog row의 source_sr_ids를 갱신하지 않음.** 기존 PG에 이미 적재된 패턴을 수정할 때는 **직접 `UPDATE she_catalog SET source_sr_ids = CAST('[...]' AS jsonb) WHERE she_id=...`**.
3. `DELETE FROM she_sr_mapping WHERE she_id = ANY(...)` → 재파생 `INSERT ... SELECT jsonb_array_elements_text(source_sr_ids), 0.75, 'phase3c' FROM she_catalog WHERE she_id = ANY(...)`.
4. (신규 PG 배포는 빈 테이블 fresh insert라 ①+`make she-import ARGS='--apply'`로 충분.)

검증된 라이브 효과: 서비스 5업종 recall +0.133, 식음료 3업종 +0.221, 산업 6케이스. 모두 회귀가드 PASS(fp FLAT).
