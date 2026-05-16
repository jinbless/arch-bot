# Phase 2 Step 1: SR 스키마 설계 + 카테고리 매핑

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 SR 위험 연결은 `risk:RiskFeature`, `sr:addressesFeature`, 구체 위험 관계를 함께 물질화하는 구조로 확장되었다.

> 최종 업데이트: 2026-04-12
> 산출물: `schemas/sr-file.schema.json`, `config/sr-section-category-map.json` (최종, 128개 exact match)
> 선행: phase1_step 0 (data/article-texts.json의 section 컬럼)

---

## 1. 수행 내용

### 1.1 schemas/sr-file.schema.json 작성

SR 배치 파일의 JSON Schema를 정의했다. Phase 1의 `ns-file.schema.json`과 동일한 구조:
- `additionalProperties: false` 전역 적용
- `metadata` + `safetyRequirements[]` 루트 구조
- Phase 2 필수 필드 + Phase 3 예약 필드 (nullable) 포함

핵심 필드:
- `identifier`: `^SR-[A-Z_]+-[0-9]+$` (FIRE_EXPLOSION 등 언더스코어 카테고리 지원)
- `referencesArticle`: `^제\d+조(의\d+)?$` 배열
- `mandatedBy`: `^NS-[A-Z0-9]+-[0-9A-Z]+$` 배열
- `addressesHazard`: 12개 표준 키워드 enum(FALL, COLLAPSE, STRUCK_BY, CAUGHT_IN, ELECTRIC_SHOCK, FIRE_EXPLOSION, CHEMICAL_EXPOSURE, ERGONOMIC, CONFINED_SPACE, SCAFFOLDING, NOISE_VIBRATION, HEAT_COLD)
- `requirementType`: 8개 enum
- `hasSanction`: NS와 동일한 criminal/administrative 구조 (재사용)
- structuralRequirements.items[]: parameter/condition/value/unit + source(선택)

Phase 3 예약 (모두 nullable):
- `requiresPPE`, `hasCorrectiveAction`, `hasIncidentResponse`, `applicableIndustry`, `hazardAssessment`

### 1.2 config/sr-section-category-map.json 작성

- `extract_sections.py`로 article-texts.json에서 128개 고유 section 추출
- 각 section을 43개 카테고리에 매핑 (dict.get() 완전 일치)
- 편1~편4 카테고리 목록
	- 편1 총칙: GENERAL, WORKPLACE, PASSAGE, PPE, MGMT, FALL, COLLAPSE, SCAFFOLD, VENTILATION, WELFARE, WASTE (11개)
	- 편2 안전: MACHINE, CRANE, RIGGING, LIFTING, VEHICLE, CONVEYOR, CONSTRUCTION_EQUIP, ROBOT, FIRE_EXPLOSION, ELECTRIC, SHORING, EXCAVATION, STEELWORK, DEMOLITION, HEAVY_LOAD, CARGO, LOGGING, RAIL (18개)
	- 편3 보건: CHEMICAL, HAZMAT, PROHIBITED_CHEM, NOISE, PRESSURE, HEAT, RADIATION, PATHOGEN, DUST, CONFINED, OFFICE, ERGONOMIC, OTHER_HAZARD (13개)
	- 편4: SPECIAL_WORKER (1개)

### 1.3 검증 결과

- 128개 고유 section 중 **128개 매칭 (100%)**
- 656개 활성 RULE 조문 100% 커버
- UNCATEGORIZED 0건

---

## 2. 재현 방법

```bash
cd data-team/02-extraction/pipe-A

# section 추출 + 카테고리 분류 템플릿 생성
python3 scripts/extract_sections.py


# 매칭 검증
python3 -c "
import json
with open('data/article-texts.json') as f:
    articles = json.load(f)
with open('config/sr-section-category-map.json') as f:
    secmap = json.load(f)
rules = articles['laws']['RULE']
sections = {v['section'] for v in rules.values() if v.get('section')}
missed = [s for s in sections if s not in secmap]
print(f'{len(sections)-len(missed)}/{len(sections)} matched, missed: {missed}')
"
```

---

*다음 스텝: phase2_step2.md (SR 배치 준비 스크립트)*
