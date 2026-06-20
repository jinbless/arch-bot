# Guide 추천 정확도 개선 — CI 변별력 + Guide 직접 위험 매핑 레이어

**Date**: 2026-05-28
**Plan**: `~/.claude/plans/tingly-snuggling-wand.md`
**문제**: 실 서비스에서 사진 분석 시 CI(체크리스트)는 정확하나 KoshaGuide가 엉뚱하게 추천됨.

## 진단 (read-only 데이터 분석으로 확정)

사용자 직관("의미적으로 동일한 CI가 Guide마다 다른 식별자로 흩어져 있어 엉뚱한 Guide 역추적") 검증:

| 지표 | 값 |
|---|---|
| CI text semantic 중복 | 동일 텍스트 CI가 2+ Guide에 = 876 그룹 / **3,953 CI (7.2%)** (정확 일치만) |
| boilerplate CI | 시험법 공통문구가 최대 **130개 Guide**에 중복 ("이 시험법에서 사용하는 모든 유리 기구는 KS L 2302...") |
| **SR→Guide fan-out** | 한 SR이 CI 경유로 **평균 21개·중앙값 9·최대 218개 Guide로 fan-out** |
| 근본 원인 | `get_guides_from_srs()`가 **CI 개수 단독 랭킹** + Guide 자체 위험 직접 매핑 부재 |

→ CI identifier는 Guide별 unique지만 **의미는 N:M 중복**. boilerplate CI가 변별력 없이 fan-out → CI 개수 랭킹이 엉뚱한 Guide 상위 노출.

## 해결 (P0~P3)

### P1 — CI 변별력 (inverse-guide-frequency)
- `checklist_items.guide_frequency` 컬럼 (`models.py`) + `compute_ci_guide_frequency.py`.
- text별 distinct source_guide 수 backfill (**3,953 CI 갱신, max 130**). `ci_weight = 1/log2(1+freq)` (gf=130 → 0.14).

### P0 — Guide 랭킹 교체
- `hazard_rule_engine.py:get_guides_from_srs()`: CI **개수** → **Σ(ci_weight) 변별력 가중합** + 정규화 + 산업 일치.
- boilerplate CI는 weight 낮아 자동 억제.

### P2 — Guide 직접 위험 매핑 레이어 (근본)
- `derive_guide_hazard_features.py`: Guide SR집합 → accident_type/hazardous_agent/work_context를 **CI 변별력 가중 다수결** → 상위 N → `guide_entity_feature_candidates(entity_type='GUIDE')` **2,115행 적재** (659 Guide).
- `hazard_rule_engine.py:get_guides_by_hazard_features()` 신규 — hazard코드 → GUIDE feature **직접 조회** (CI 경유 없음).
- `hazard_to_guide_service.py:_merge_guide_paths()` — 직접 매핑 우선 + CI 경유 union (교집합 bonus +0.15).
- 단위테스트: FALL → 추락방호망/안전대, ELECTRICITY → 방폭전기설비 (정확).

### P3 — 온톨로지 정합
- TBox `kosha-ontology-v4-guide-hazard-patch.ttl`: `guide:addressesHazard` / `guideAddressesAgent` / `guideAppliesToContext` / `ciGuideFrequency` / `isBoilerplate`.
- `export_guide_hazard_to_abox.py` → `kosha-instances-guide-hazard.ttl` (**659 Guide, 2,115 triple**). ⚠️ **2026-06-20**: 이 파일은 이후 `archive/`로 이동, 현행 fine ABox `kosha-instances-guide-fine.ttl`(957 guide / 9,415 triple)이 대체.
- **참고**: plan의 SHACL CONSTRUCT 대신 PG 가중 다수결 → ABox export 채택. ontology ABox에 Guide→CI→SR→hazard runtime chain이 없어(Phase B/C-J 발견) SHACL CONSTRUCT는 fire 0. PG의 `safety_requirements.accident_types` 집계가 정확한 사실 소스 → "온톨로지 사실 보유 + 런타임 랭킹" 원칙 유지.

## 검증 (8 photo eval before/after)

| 지표 | before(baseline) | after(P0~P2) |
|---|---|---|
| mapping rate | 80% | **100%** (27/27) |
| Guide mapping_type | sr_ci_link (CI 개수 랭킹) | **guide_hazard_direct 32 + direct+ci 1 + sr_ci_link 6** (직접 85%) |
| boilerplate Guide(화학 시험법) 출현 | 발생 | **0** |
| photo별 정합 | 엉뚱 혼입 | 추락→추락방호망/안전대, 제조→제조Guide, 지게차→차량Guide |

→ 사용자 문제(엉뚱한 Guide) 해소: **변별력 가중(P0/P1)이 boilerplate noise 제거 + 직접 매핑(P2)이 hazard 정합 Guide 우선**.

## Critical Files
- `serving-team/08-app/backend/app/services/hazard_rule_engine.py` (get_guides_from_srs 랭킹 + get_guides_by_hazard_features 신규)
- `serving-team/08-app/backend/app/services/hazard_to_guide_service.py` (_merge_guide_paths union)
- `serving-team/08-app/backend/app/db/models.py` (PgChecklistItem.guide_frequency)
- `data-team/05-enrichment/llm-scripts/compute_ci_guide_frequency.py` / `derive_guide_hazard_features.py` / `export_guide_hazard_to_abox.py` (신규)
- `ontology-team/06-reasoning/ontology/kosha-ontology-v4-guide-hazard-patch.ttl` / `kosha-instances-guide-hazard.ttl` (신규)

## 후속
- 프레스 등 일부 사진은 GUIDE feature 미매칭(guides 0) — top-n/min-conf 튜닝 또는 hazardous_agent 보강 여지.
- LLM 없이 (PG 가중) 도출했으므로, 저신뢰 Guide는 Sonnet 분류로 보정 가능 (선택).
- 의미 유사 CI 클러스터링(SafetyConcept canonical)은 현 변별력 가중으로 충분하면 보류.
