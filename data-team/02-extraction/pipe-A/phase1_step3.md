# Phase 1 Step 3: NS 생성 (LLM)

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 product에서 LLM은 법령 판단자가 아니라 관찰 사실/시각 단서 추출기로 제한된다. Pipe-A의 NS 생성 방식은 재현 기록으로 보존한다.

> 최종 업데이트: 2026-04-11
> 에이전트 프롬프트: `agents/step3-ns-generation.md`
> 스키마: `schemas/ns-file.schema.json`

---
## 1. 목적

LLM(Opus 4.6)으로 산업안전보건기준에관한규칙(RULE)의 조문을 NormStatement(규범문장)로 분해한다.

- 입력: Step 2에서 생성한 `batch-NNN-input.json`
- 출력: `ns-batch-NNN.json` (NormStatement 배열)

## 2. 전제조건

- Step 2 완료: `data/norm-statements/batch-*-input.json` 존재
- LLM 에이전트 프롬프트: `agents/step3-ns-generation.md`
- NS 스키마: `schemas/ns-file.schema.json`

## 3. 에이전트 핵심 규칙

> 전문: `agents/step3-ns-generation.md`

### 3.1 4대 원칙

1. **식별자는 사전 할당됨** — 입력의 `preAssignedIds`를 순서대로 사용. 절대 새로 만들지 않음.
2. **hasSanction은 사전 제공됨** — 입력의 hasSanction 블록을 그대로 복사. 수정하지 않음.
3. **스키마 엄수** — `additionalProperties: false`. 스키마에 없는 필드 추가 금지.
4. **null vs 생략** — 선택필드가 없으면 반드시 `null`. 필드 자체를 생략하지 않음. `{}`도 금지.

### 3.2 NS 분해 규칙

- **1항 = 1 NS**: 각 항(또는 단일항 본문)마다 1개 NS 생성
- **단서는 별도 NS**: "다만, ~" 단서는 별도 NS로, `hasModificationLink`로 연결
- **삭제 항 건너뜀**: "삭제 <개정 YYYY.M.D>" 인 항은 NS 미생성
- **정의 조문**: DEFINITION 모달리티, hasSanction: null, roleGuidance: null
- **식별자 순서**: preAssignedIds를 0부터 순서대로 소진

### 3.3 hasModality 분류 기준

- **OBLIGATION**: "~하여야 한다", "~을 갖추어야 한다" → 의무
- **PROHIBITION**: "~하여서는 아니 된다", "~을 금지한다" → 금지
- **PERMISSION**: "~할 수 있다" (재량) → 허용
- **POWER**: "~할 수 있다" (권한 부여) → 권한
- **EXEMPTION**: "~하지 아니할 수 있다", "제외한다", "적용하지 아니한다" → 면제
- **DEFINITION**: "~을 말한다", "~이란" → 정의

### 3.4 paragraphRef 작성법

- 단일항: `"제24조 본문"`
- 복수항: `"제24조 제1항"`, `"제24조 제2항"`
- 단서: `"제24조 제1항 단서"`

## 4. NS 출력 스키마

> 전문: `schemas/ns-file.schema.json`

NS 객체 필수 필드: `identifier`, `articleCode`, `lawId`, `paragraphRef`, `text`, `hasModality`

선택 필드 (null 허용): `hasSubjectRole`, `hasAction`, `hasObject`, `hasCondition`(JSONB), `hasSanction`(JSONB), `hasModificationLink`(JSONB), `roleGuidance`(JSONB)

## 5. 실행 방법

33개 배치를 4병렬 × 9라운드로 처리:

| 라운드 | 배치 | 에이전트 |
|--------|------|---------|
| R1 | batch-001 ~ 004 | 4개 병렬 |
| R2 | batch-005 ~ 008 | 4개 병렬 |
| R3 | batch-009 ~ 012 | 4개 병렬 |
| R4 | batch-013 ~ 016 | 4개 병렬 |
| R5 | batch-017 ~ 020 | 4개 병렬 |
| R6 | batch-021 ~ 024 | 4개 병렬 |
| R7 | batch-025 ~ 028 | 4개 병렬 |
| R8 | batch-029 ~ 032 | 4개 병렬 |
| R9 | batch-033 | 1개 |

각 에이전트에 전달:
1. 입력: `data/norm-statements/batch-NNN-input.json`
2. 규칙: `agents/step3-ns-generation.md`
3. 스키마: `schemas/ns-file.schema.json`
4. 출력: `data/norm-statements/ns-batch-NNN.json`

## 6. 실행 결과 (656조문 전체, legalize-kr 커밋 d8c121b2 기준)

- 총 NormStatements: 1,229개 (653개 조문 커버, 3개 조문은 fullText 비어 NS 미생성)
- hasModality 분포: OBLIGATION 917 (74.6%), EXEMPTION 145 (11.8%), PROHIBITION 103 (8.4%), PERMISSION 34 (2.8%), DEFINITION 30 (2.4%)
- 단서 NS (hasModificationLink 있음): ~145개

---

*이 문서는 Step 3(NS 생성, LLM)만 다룹니다. 배치 준비는 `phase1_step2.md`, 검증은 `phase1_step4.md`를 참조하세요.*
