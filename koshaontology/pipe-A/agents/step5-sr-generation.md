# Step 5: SafetyRequirement 생성 에이전트 가이드

> 현재 기준 참고 (2026-05-07): 이 프롬프트는 Pipe-A SR 생성 재현용이다. 최신 구조에서는 SR의 위험 연결을 `risk:RiskFeature`와 `sr:addressesFeature`로 물질화해 OHS serving에서 조회한다.

> 입력: `data/safety-requirements/sr-batch-*-input.json`
> 출력: `data/safety-requirements/sr-batch-*.json`
> 스키마: `schemas/sr-file.schema.json`

---

## 1. 역할

당신은 NormStatement(NS) 그룹을 읽고, 가이드 독립적인 정규화된 SafetyRequirement(SR)을 생성합니다.

1개 SR = 같은 조문의 OBLIGATION/PROHIBITION NS들을 통합·정규화한 "현장에서 지켜야 할 안전요구사항" 1건.

---

## 1.5. 카테고리 컨텍스트

배치 입력에 `categoryContext`가 포함된다:

```json
{
  "categoryContext": {
    "categories": ["CHEMICAL"],
    "totalSRsInCategory": 123,
    "batchNumber": 1,
    "totalBatches": 7,
    "description": "유해물질 취급·보호"
  }
}
```

이 정보를 활용하여:
- **같은 카테고리의 SR은 일관된 스타일**로 title/text를 작성한다
- `batchNumber`/`totalBatches`를 참고하여 "이 배치는 CHEMICAL 카테고리의 1/7번째"임을 인지한다
- 이전 배치의 SR과 스타일이 달라지지 않도록 한다

---

## 2. 입력 구조

배치 입력의 각 `srGroups[]` 항목:

```json
{
  "preAssignedId": "SR-FALL-001",          // ★ 반드시 이 ID 사용
  "articleCode": "제42조",
  "title": "추락의 방지",
  "section": "편1 총칙 > 장6 추락 또는 붕괴...",
  "category": "FALL",
  "nsGroup": [                              // 통합 대상 NS 목록
    {
      "identifier": "NS-RULE42-0",
      "paragraphRef": "제42조 제1항",
      "text": "사업주는 높이 2미터 이상인 장소에서...",
      "hasModality": "OBLIGATION",
      "hasSubjectRole": "사업주",
      "hasAction": "설치하여야 한다",
      "hasObject": "작업발판",
      "hasCondition": {
        "conditionType": "QUANTITATIVE",
        "text": "높이가 2미터 이상인 장소"
      }
    }
  ],
  "exemptionNS": [...],                    // 면제 NS (hasModificationLink용)
  "quantitativeConditions": [...],          // QUANTITATIVE 조건 목록 (정량값 힌트)
  "hasSanction": { ... }                   // ★ 그대로 복사
}
```

---

## 3. 출력 구조

```json
{
  "metadata": {
    "generatedAt": "2026-04-11T...",
    "batchId": "sr-batch-001",
    "totalSafetyRequirements": 20
  },
  "safetyRequirements": [
    {
      "identifier": "SR-FALL-001",           // preAssignedId 그대로
      "title": "높이 2m 이상 작업 시 추락방지 조치",
      "text": "사업주는 높이 2m 이상에서 근로자가 추락할 위험이 있는 경우...",
      "requirementType": "PHYSICAL_PROTECTION",
      "bindingForce": "MANDATORY",
      "referencesArticle": ["제42조"],
      "mandatedBy": ["NS-RULE42-0", "NS-RULE42-1"],
      "addressesHazard": ["FALL"],
      "structuralRequirements": {
        "items": [
          {"parameter": "작업높이", "condition": ">=", "value": 2, "unit": "m", "source": "제42조 제1항"}
        ]
      },
      "hasSanction": { ... },                // 입력에서 그대로 복사
      "hasModificationLink": null,
      "requiresPPE": null,
      "hasCorrectiveAction": null,
      "hasIncidentResponse": null,
      "applicableIndustry": null,
      "hazardAssessment": null
    }
  ]
}
```

---

## 4. 생성 규칙

### 4-1. 식별자 (절대 규칙)

- `identifier`는 입력의 `preAssignedId`를 **그대로** 사용한다. 절대 변경하지 않는다.
- `mandatedBy`는 입력 `nsGroup[].identifier`를 그대로 나열한다.
- `referencesArticle`은 입력의 `articleCode`를 배열로 넣는다. **"제42조" 형식만** 사용.

### 4-2. title 작성

- 핵심 의무사항을 **50자 이내**로 요약한다.
- 조문 제목과 NS의 핵심 내용을 조합한다.
- 예: "높이 2m 이상 작업 시 추락방지 조치", "사다리식 통로 구조기준"

### 4-3. text 작성

- nsGroup의 NS들을 읽고, 의미를 통합하여 **하나의 정규화된 문장**으로 작성한다.
- NS 원문을 단순히 연결하지 말고, 핵심 의무사항을 정규화하여 표현한다.
- 모든 정량값(높이, 하중, 각도 등)을 빠짐없이 포함한다.
- 최소 50자 이상.

### 4-4. requirementType 결정

8개 중 1개 선택:

| 타입 | 기준 | 예시 |
|------|------|------|
| PHYSICAL_PROTECTION | 물리적 방호장치 설치 | 안전난간, 방호망, 덮개 |
| PPE_REQUIREMENT | 보호구 착용 의무 | 안전대, 안전모, 보안경 |
| PROCEDURAL | 절차적 요구사항 | 작업계획서, 점검, 허가 |
| TRAINING | 교육·훈련 의무 | 안전교육, 특별교육 |
| EQUIPMENT_STANDARD | 장비·자재 기준 | KS 적합, 안전계수, 하중 |
| ENVIRONMENTAL | 작업환경 조건 | 풍속, 조도, 환기, 온도 |
| MANAGEMENT_SYSTEM | 관리체계 의무 | 관리감독자, 위험성평가 |
| EMERGENCY_RESPONSE | 비상대응 의무 | 비상연락, 대피, 응급처치 |

입력의 `category`를 참고하되, NS 내용에 따라 변경 가능하다.

### 4-5. addressesHazard 결정

12개 표준 키워드 중 선택 (1개 이상):

FALL, COLLAPSE, STRUCK_BY, CAUGHT_IN, ELECTRIC_SHOCK, FIRE_EXPLOSION, CHEMICAL_EXPOSURE, ERGONOMIC, CONFINED_SPACE, SCAFFOLDING, NOISE_VIBRATION, HEAT_COLD

입력의 `category`를 참고한다:
- category=FALL → addressesHazard=["FALL"]
- category=ELECTRIC → addressesHazard=["ELECTRIC_SHOCK"]
- category=SCAFFOLD → addressesHazard=["FALL", "SCAFFOLDING"]
- category=CHEMICAL → addressesHazard=["CHEMICAL_EXPOSURE"]
- category=MACHINE → NS 내용에서 판단 (CAUGHT_IN, STRUCK_BY 등)

### 4-6. structuralRequirements 추출

입력의 `quantitativeConditions`를 참고하여, NS text에서 정량값을 추출한다.

| NS text | 추출 결과 |
|---------|----------|
| "높이가 2미터 이상인 장소" | `{parameter: "작업높이", condition: ">=", value: 2, unit: "m"}` |
| "75럭스 이상의 채광" | `{parameter: "조도", condition: ">=", value: 75, unit: "lux"}` |
| "바닥면으로부터 10센티미터 이상" | `{parameter: "발끝막이판 높이", condition: ">=", value: 10, unit: "cm"}` |
| "풍속이 초당 10미터 이상" | `{parameter: "풍속", condition: ">=", value: 10, unit: "m/s"}` |
| "기울기를 75도 이하" | `{parameter: "사다리 기울기", condition: "<=", value: 75, unit: "도"}` |

QUANTITATIVE 조건이 없으면 `null`로 설정한다.

### 4-7. hasSanction (절대 규칙)

- 입력의 `hasSanction`을 **있는 그대로 복사**한다.
- 어떤 필드도 수정, 추가, 삭제하지 않는다.
- `null`이면 `null`로 유지한다.

### 4-8. hasModificationLink (면제 관계)

입력에 `exemptionNS`가 있으면:
1. 해당 면제 NS의 `hasModificationLink.modifiesNS`가 가리키는 원본 NS를 확인
2. 원본 NS가 같은 SR의 mandatedBy에 포함되면, 이 SR의 hasModificationLink는 `null` (같은 SR 내부 면제)
3. 원본 NS가 다른 SR의 mandatedBy에 포함되면, `modifiesSR`에 해당 SR의 preAssignedId를 기입

대부분의 면제는 같은 조문 내이므로 `hasModificationLink: null`이 대다수이다.

### 4-9. bindingForce 결정

- OBLIGATION/PROHIBITION → `"MANDATORY"` (기본값)
- 입력의 NS에 PERMISSION이 섞여 있으면 → `"RECOMMENDED"`

### 4-10. Phase 3 예약 필드 (모두 null)

다음 필드는 모두 `null`로 설정한다:
- `requiresPPE`
- `hasCorrectiveAction`
- `hasIncidentResponse`
- `applicableIndustry`
- `hazardAssessment`

---

## 5. 금지 패턴

```
절대 하지 마라:
- identifier를 창작하거나 변경 (preAssignedId 사용)
- hasSanction을 수정, 작성, 생략
- referencesArticle에 "규칙" 접두사 추가 ("제42조"만 허용)
- addressesHazard에 12개 키워드 외 값 사용
- ★ addressesHazard를 문자열("FALL")로 넣기 — 반드시 배열(["FALL"])이어야 함
- {} 빈 객체 (null 사용)
- "" 빈 문자열 (minLength: 1 위반)
- additionalProperties 추가
- Phase 3 예약 필드에 값 채우기
```

---

## 6. 출력 파일명

- 입력: `sr-batch-001-input.json`
- 출력: `sr-batch-001.json`

출력 파일의 `safetyRequirements` 배열 순서는 입력의 `srGroups` 순서를 따른다.
