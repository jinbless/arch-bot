# Phase 2 Step 3: SR 생성 LLM 에이전트 가이드

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 SR 위험 연결은 `risk:RiskFeature`, `sr:addressesFeature`, 구체 위험 관계를 함께 물질화하는 구조로 확장되었다.

> 최종 업데이트: 2026-04-12
> 산출물: `agents/step5-sr-generation.md`
> 선행: phase2_step1 (sr-file.schema.json), phase2_step2 (배치 입력)

---

## 1. 목적

LLM이 SR 배치 입력을 읽고 SafetyRequirement를 생성하기 위한 에이전트 가이드를 정의한다. Phase 1의 `step3-ns-generation.md`와 동일한 패턴:
- 입력 구조 정의
- 출력 구조 정의
- 생성 규칙 10개
- 금지 패턴

## 2. Phase 1 패턴 재사용

```
Phase 1: batch-input (preAssignedIds + hasSanction) → LLM → NS
Phase 2: sr-batch-input (preAssignedId + hasSanction) → LLM → SR
```

동일한 제약:
- `identifier` = `preAssignedId` 그대로 (LLM 창작 금지)
- `hasSanction` = 입력에서 verbatim 복사 (LLM 수정 금지)
- Phase 3 예약 필드 = 모두 `null`

## 3. 핵심 설계

### 3.1 categoryContext 도입

배치 전략(phase2_step2)에 따라 각 배치에 카테고리 컨텍스트를 포함:
- LLM이 "이 배치는 해당 카테고리의 N/M번째"임을 인지
- 같은 카테고리 내 SR의 title/text 스타일 일관성 보장

### 3.2 생성 규칙 10개

| 규칙   | 내용                                                         |
| ---- | ---------------------------------------------------------- |
| 4-1  | identifier: preAssignedId 그대로 사용                           |
| 4-2  | title: 50자 이내 핵심 의무사항 요약                                   |
| 4-3  | text: NS 통합 정규화 문장, 50자 이상                                 |
| 4-4  | requirementType: 8개 enum 중 1개                              |
| 4-5  | addressesHazard: 12개 키워드 중 선택, **반드시 배열**                  |
| 4-6  | structuralRequirements: QUANTITATIVE 조건에서 수치 파싱            |
| 4-7  | hasSanction: 입력에서 verbatim 복사                              |
| 4-8  | hasModificationLink: 같은 SR 내부 면제는 null                     |
| 4-9  | bindingForce: OBLIGATION→MANDATORY, PERMISSION→RECOMMENDED |
| 4-10 | Phase 3 예약 필드: 모두 null                                     |

## 4. 금지 패턴

- identifier 창작/변경
- hasSanction 수정/작성/생략
- referencesArticle에 "규칙" 접두사
- addressesHazard 12개 키워드 외 값, **문자열 타입 금지**
- `{}` 빈 객체, `""` 빈 문자열
- additionalProperties 추가
- Phase 3 예약 필드에 값 채우기

---

## 5. 재현 방법

에이전트 가이드 파일: `agents/step5-sr-generation.md`

실행 시 LLM에게 다음을 전달:
1. 에이전트 가이드 전문
2. 배치 입력 파일 (`sr-batch-{CATEGORY}-input.json`)
3. 출력 파일명 (`sr-batch-{CATEGORY}.json`)
4. SR 스키마 (`sr-file.schema.json`)

---

*다음 스텝: phase2_step4.md (SR 생성 실행)*
