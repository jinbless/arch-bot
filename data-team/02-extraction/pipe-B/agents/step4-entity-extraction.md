# 5종 엔티티 추출 에이전트 (P2-Step 4)

## 역할

guide-text JSON을 읽고, CI/DT/WP/ES/DR 5종 엔티티를 추출하여 `ci-file.schema.json`에 맞는 JSON을 생성한다.

## 입력

배치 입력 JSON (`pipeb-batch-{domain}-{NNN}-input.json`)에 포함된 정보:
- `guides[].textJsonPath` → guide-text JSON 경로
- `guides[].candidateSR` → basedOn 후보 SR 목록 (최대 50개)
- `guides[].preAssignedIdRange` → CI/DT/WP/ES/DR ID 범위
- `guides[].citedArticles` → 인용 조문 목록

## 출력

가이드별 1개 파일: `koshaontology/pipe-B/data/ci-output/ci-{shortCode}.json`

## 5종 엔티티 추출 규칙

### 1. ChecklistItem (CI)

**추출 기준**: "~하여야 한다", "~확인한다", "~점검한다", "~금지한다" 등 점검·의무 문구

```json
{
  "identifier": "CI-DC13-001",          // preAssigned 범위 내 순차
  "text": "비계 조립·해체 시 ...",        // 원문 그대로 (축약 금지)
  "guideContext": "외벽도장 보수공사",     // 가이드 맥락 (선택)
  "additionalDetail": null,              // 추가 설명 (선택)
  "workProcessPhase": "비계 설치",        // 관련 작업공정 (선택)
  "bindingForce": "MANDATORY",           // "~하여야 한다" → MANDATORY
  "requirementType": "PHYSICAL_PROTECTION",
  "sourceSection": "4.2",                // 출처 섹션 번호
  "basedOn": ["SR-SCAFFOLD-001"]         // candidateSR에서 선택
}
```

**bindingForce 분류**:
- `MANDATORY`: "~하여야 한다", "~금지한다", "~해서는 안 된다"
- `RECOMMENDED`: "~하는 것이 좋다", "~하는 것이 바람직하다", "~할 수 있다"

**basedOn 규칙**:
- candidateSR 목록에서만 선택 (목록 외 SR 참조 절대 금지)
- CI 내용과 SR 내용의 의미적 연관성 판단
- 매칭되는 SR이 없으면 `basedOn: null`
- **MANDATORY CI에 매칭되는 candidateSR이 없으면**:
  1. `basedOn: null` 설정
  2. `bindingForce`를 `"RECOMMENDED"`로 변경
  3. `guideContext`에 `"(법령 근거 미확인)"` 추가
- RECOMMENDED CI의 basedOn null은 정상

**requirementType 분류 가이드** (null 최소화):
- `PHYSICAL_PROTECTION`: 방호장치, 안전난간, 덮개, 방호울, 낙하물방지망
- `PPE_REQUIREMENT`: 안전모, 안전대, 보호구, 안전화, 보안경, 방진마스크
- `PROCEDURAL`: 점검, 확인, 검사, 조사, 측정, 순찰, 감시, 작업 전 확인
- `TRAINING`: 교육, 훈련, 자격, 면허, 숙지, 안전교육
- `EQUIPMENT_STANDARD`: 장비 규격, KS 표준, 내하중, 사용하중, 규격 기준
- `ENVIRONMENTAL`: 환기, 조명, 온도, 습도, 소음, 분진, 가스 농도
- `MANAGEMENT_SYSTEM`: 작업계획서, 안전관리, 관리감독, 작업허가, 위험성평가
- `EMERGENCY_RESPONSE`: 비상조치, 응급처치, 대피, 경보, 소화기, 구조

### 2. DomainTerm (DT)

**추출 기준**: "용어의 정의" 섹션, "(가) ~라 함은 ~을 말한다" 패턴

```json
{
  "identifier": "DT-DC13-001",
  "term": "달비계",
  "definition": "와이어로프나 체인에 의하여...(원문 그대로)",
  "sourceSection": "3",
  "relatedSR": null
}
```

### 3. WorkProcess (WP)

**추출 기준**: 작업 순서, 공정 단계, 안전조치가 포함된 절차

```json
{
  "identifier": "WP-DC13-01",
  "processOrder": 1,
  "processName": "비계 조립",
  "safetyMeasures": "작업발판 폭 40cm 이상...",
  "requiredPPE": ["안전대", "안전모", "안전화"],
  "sourceSection": "4.1",
  "relatedSR": ["SR-SCAFFOLD-001"]
}
```

### 4. EquipmentSpec (ES)

**추출 기준**: 장비·자재 규격, KS 표준, 수치 사양

```json
{
  "identifier": "ES-DC13-001",
  "equipmentName": "강관비계용 강관",
  "specifications": {
    "outerDiameter": "48.6mm",
    "thickness": "2.4mm 이상",
    "ksStandard": "KS D 3566"
  },
  "sourceSection": "4.3",
  "relatedSR": null
}
```

### 5. DocumentRequirement (DR)

**추출 기준**: 필요 문서, 작업계획서, 위험성평가 양식

```json
{
  "identifier": "DR-DC13-001",
  "documentType": "WORK_PLAN",
  "title": "외벽도장 보수공사 작업계획서",
  "requiredSections": ["작업공정", "안전조치", "비상연락망"],
  "sourceSection": "2.1",
  "relatedSR": null
}
```

**documentType 유효값**: WORK_PLAN, RISK_ASSESSMENT, SAFETY_CHECKLIST, MSDS, INCIDENT_REPORT, TRAINING_RECORD

## 절대 규칙

1. **identifier 창작 금지**: preAssignedIdRange 내에서 순차 사용
2. **candidateSR 밖 참조 금지**: basedOn은 반드시 candidateSR에 있는 SR만
3. **text 원문 보존**: 축약·의역·요약 금지
4. **빈 문자열 금지**: minLength: 1 필드에 "" 사용 불가
5. **빈 객체 금지**: null 사용, {} 금지
6. **5개 배열 키 필수**: 0건이어도 빈 배열 `[]` 명시
7. **additionalProperties 금지**: 스키마에 없는 필드 추가 금지
8. **JSON 직접 출력 필수**: 반드시 JSON을 직접 텍스트로 출력하라. Python 스크립트 생성, Write 도구 사용, 파일 저장 시도 등 우회 방법을 절대 사용하지 마라. 출력이 크더라도 반드시 JSON 텍스트를 그대로 출력하라.

## 추출 우선순위

1. **CI 추출 최우선** — Pipe-B 핵심 산출물
2. **DT** — "용어의 정의" 섹션에서 기계적 추출
3. **WP** — 작업 순서/공정 섹션
4. **ES** — 장비/자재 규격 섹션
5. **DR** — 0건 허용 (가이드에 없을 수 있음)

## 검증

출력 JSON은 `ci-file.schema.json`으로 검증 후 저장:

```bash
python3 -c "
import json
from jsonschema import validate
schema = json.load(open('koshaontology/pipe-B/schemas/ci-file.schema.json'))
doc = json.load(open('koshaontology/pipe-B/data/ci-output/ci-{shortCode}.json'))
validate(doc, schema)
print('PASS')
"
```

---

## 분할 추출 모드 (Split Mode)

가이드 텍스트가 매우 길 경우, Claude CLI 타임아웃을 피하기 위해 가이드를 여러 Part로 나누어 호출한다.
이 경우 입력 프롬프트의 "## 분할 추출 컨텍스트" 절이 활성화된다.

### Part X/N 처리 규칙

1. **이 Part에 포함된 섹션에서만 엔티티를 추출한다.** 참조용으로 첨부된 섹션 3(용어의 정의)에서는 어떤 엔티티도 추출하지 않는다.
2. **DT는 Part 1에서만 추출한다.** Part 2 이상에서는 `domainTerms: []` 빈 배열을 반환한다. 참조용 섹션 3은 다른 엔티티(CI/WP)의 의미 매칭 컨텍스트로만 사용한다.
3. **CI/WP/ES/DR의 ID 순번은 입력에서 부여된 ID 범위 내에서만 사용한다.** 범위를 벗어나면 검증에서 자동 탈락된다.
4. **`processOrder`는 이 Part 내에서 1부터 시작한다.** 병합 시 글로벌 순서로 재정렬된다.
5. **`sourceSection`은 반드시 "포함 섹션" 목록 중 하나여야 한다.** 참조 섹션 번호("3")를 sourceSection으로 사용하면 안 된다 (DT 제외).
6. **`basedOn` / `relatedSR`은 전체 candidateSR 풀에서 선택 가능하다** (Part마다 풀이 동일).

### Part 별 책임 매트릭스

| Part | DT | CI | WP | ES | DR |
|------|----|----|-----|-----|-----|
| 1 | YES (전체) | YES (해당 섹션) | YES | YES | YES |
| 2..N | NO (빈 배열) | YES | YES | YES | YES |

### 출력 형식

분할 모드에서도 출력 JSON 구조는 동일하다 (5개 배열 키 모두 필수, 0건이어도 `[]`).
