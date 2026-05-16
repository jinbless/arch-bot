# Phase 2 Step 2: SR 배치 준비 스크립트 (카테고리 기반)

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 SR 위험 연결은 `risk:RiskFeature`, `sr:addressesFeature`, 구체 위험 관계를 함께 물질화하는 구조로 확장되었다.

> 최종 업데이트: 2026-04-12
> 산출물: `data/safety-requirements/sr-batch-*-input.json` (48배치)
> 스크립트: `scripts/step5_prepare_sr_batch.py`
> 선행: phase2_step1 (sr-section-category-map.json), phase1_step3 (ns-batch-*.json)

---

## 1. 목적

NS 배치 출력에서 OBLIGATION/PROHIBITION NS만 필터하고, 조문별로 그룹핑한 뒤 카테고리별로 배치를 생성한다. phase1_step2의 `step2_prepare_batch.py`와 동일한 패턴:
- `preAssignedId`로 SR 식별자 사전 할당 (LLM 창작 금지)
- `hasSanction`을 penalty-routes.json에서 사전 복사 (LLM 작성 금지)

## 2. 전제조건

- phase2_step1 완료: `sr-section-category-map.json` (128개 section exact match, 43카테고리)
- phase1_step3 완료: `ns-batch-*.json` (33파일, 1,229 NS)
- phase1_step1 완료: `penalty-routes.json` (656라우트)

## 3. 배치 전략 (카테고리 기반)

같은 카테고리의 모든 SR을 연속 배치로 묶음:
- 20개 이하 → 1배치, 21~40 → 2배치, ... ceil(n/20)배치
- 소규모(5개 이하) 카테고리는 관련 카테고리와 묶기 (SMALL_CATEGORY_MERGES):
  - PPE(4) + WELFARE(4) → PPE-WELFARE
  - STEELWORK(4) + DEMOLITION(1) → STEELWORK-DEMOLITION
  - ROBOT(3) + SPECIAL_WORKER(3) + CONVEYOR(5) → ROBOT-CONVEYOR-SPECIAL
  - WASTE → WASTE (단독)
  - 나머지 소규모(COLLAPSE, HEAVY_LOAD, LOGGING, OTHER_HAZARD 등) → MISC-SMALL
- 배치 ID: `sr-batch-{CATEGORY}` 또는 `sr-batch-{CATEGORY}-{NN}`
- `categoryContext` 필드 추가: 카테고리 전체 맥락을 LLM에 전달

## 4. 핵심 설계

### 4.1 카테고리 매칭

`sr-section-category-map.json`에서 section 문자열을 키로 **완전 일치(`dict.get()`)** 매칭:
- 128개 고유 section이 모두 키로 등록 → UNCATEGORIZED 0건 보장

### 4.2 preAssignedId 생성

`SR-{카테고리}-{3자리순번}`: 카테고리 내 조문 번호 순으로 001부터 순번.

### 4.3 categoryContext

```json
{
  "categoryContext": {
    "categories": ["CHEMICAL"],
    "totalSRsInCategory": 26,
    "batchNumber": 1,
    "totalBatches": 2,
    "description": "관리대상 유해물질 취급·보호"
  }
}
```

## 5. 실행 결과

```
python3 scripts/step5_prepare_sr_batch.py --all --batch-size 20
```

- 1,229 NS → OBLIGATION/PROHIBITION 1,020개 필터
- 626개 조문 그룹 → 626개 SR (GENERAL skip 해제)
- **48배치**, 42개 카테고리 (GENERAL은 skipSR로 SR 미생성)
- 대규모: FIRE_EXPLOSION 4배치, MACHINE/EXCAVATION 각 3배치, CHEMICAL/ELECTRIC/HAZMAT/PRESSURE 각 2배치
- 소규모 묶음 5개: PPE-WELFARE, STEELWORK-DEMOLITION, ROBOT-CONVEYOR-SPECIAL, WASTE, MISC-SMALL

---

## 6. 재현 방법

```bash
cd koshaontology/pipe-A

# 기존 배치 삭제 후 재생성
rm -f data/safety-requirements/sr-batch-*-input.json
python3 scripts/step5_prepare_sr_batch.py --all --batch-size 20

# dry-run으로 통계만 확인
python3 scripts/step5_prepare_sr_batch.py --all --batch-size 20 --dry-run
```

---

*다음 스텝: phase2_step3.md (SR 생성 LLM 에이전트 가이드)*
