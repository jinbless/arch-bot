# Phase 1 Step 2: NS 배치 입력 준비

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 product 기준은 루트 `README.md`, `온톨로지_통합구조_및_흐름도.md`, `OHS/README.md`, 그리고 이 Pipe의 `status_pipea.md`를 우선 확인한다.

> 최종 업데이트: 2026-04-11
> 스크립트: `scripts/step2_prepare_batch.py`

---
## 1. 목적

`step2_prepare_batch.py`로 LLM 에이전트(Step 3)용 배치 입력 JSON을 생성한다.
- article-texts.json(Step 0 출력) + penalty-routes.json(Step 1 출력)을 읽어
- 조문별로 `preAssignedIds`(결정론적 NS 식별자)와 `hasSanction`(벌칙 블록)을 사전 계산
- batch-size 단위로 분할하여 `batch-NNN-input.json` 파일을 생성

## 2. 전제조건

- Step 0 완료: `data/article-texts.json` 존재 (1,227조문)
- Step 1 완료: `data/penalty-routes.json` 존재 (656라우트)
- Python 3.12+

## 3. 핵심 설계: preAssignedIds

LLM이 NS 식별자를 창작하면 매번 다른 ID가 나올 수 있다. 이를 방지하기 위해 스크립트가 `NS-{법령ID}{조문번호}-{순번}` 형식으로 미리 생성한다.

- **paragraphCount + 단서("다만,") 수**만큼 ID를 할당
- 예: 2항 + 단서 1개 → `["NS-RULE3-0", "NS-RULE3-1", "NS-RULE3-2"]` (3개)
- LLM은 이 ID를 순서대로 사용하며 절대 새로 만들지 않음

### 3.1 암묵적 역할: 출력 상한 제약

preAssignedIds 개수는 LLM이 생성할 수 있는 NS의 **상한**으로도 기능한다. "1항 = 1 NS" 규칙과 결합하여:

- 항 내부 과분해 방지 (예: 하나의 의무 조항을 A/B/C로 쪼개는 것)
- 호·목의 불필요한 NS 승격 방지
- 조문에 없는 의무·금지를 환각 생성하는 것 방지

### 3.2 ID 부족 시 처리

`"다만,"` 외의 단서 표현("이 경우", "다만 ~한 때에는" 등)이 있으면 사전 계산보다 NS가 더 필요할 수 있다. 이 경우:

- LLM: ID가 부족하면 남은 항/단서를 마지막 NS에 병합하고, `text`에 전문을 포함
- Step 4: 검증 시 조문별 NS 수와 preAssignedIds 수의 불일치를 WARNING으로 보고 (R14_ID_COUNT_MISMATCH)

## 4. 파일 구성 (의존성 순서)

### 4.1. `lib/article_code.py`

- 조문코드 정규화 유틸리티. `제24조`, `제332조의2` 형식 처리

### 4.2. `lib/ns_identifier.py`

- NS 식별자 알고리즘 생성. `article_code.py`에 의존.

## 5. 메인 스크립트

- `scripts/step2_prepare_batch.py`

함수:
- `load_data()`: article-texts.json + penalty-routes.json 로드
- `build_sanction_block(route)`: penalty-routes.json에서 criminal/administrative 복사
- `prepare_article(law_id, article_code, article, penalties)`: 단일 조문의 배치 입력 항목 생성
  - `max_ids = max(paragraph_count + proviso_count, 1)` — 단서 수 반영
- `main()`: CLI 파싱 및 배치 파일 생성

## 6. 실행 방법

```bash
cd koshaontology/pipe-A

# 모드 1: 특정 조문 지정
python3 scripts/step2_prepare_batch.py --articles 제24조,제42조 --batch-id batch-001

# 모드 2: 조문 번호 범위
python3 scripts/step2_prepare_batch.py --law-id RULE --range 3-50 --batch-id batch-002

# 모드 3: 전체 조문 자동 분할
python3 scripts/step2_prepare_batch.py --law-id RULE --all --batch-size 20

# --skip-deleted: 삭제 조문 건너뜀 (기본: True)
```

## 7. 배치 입력 필드 설명

### 배치 레벨

| 필드       | 타입     | 설명                      |
| -------- | ------ | ----------------------- |
| batchId  | string | 배치 식별자 (예: "batch-001") |
| lawId    | string | 대상 법령 ID (예: "RULE")    |
| articles | array  | 조문 목록 (아래 참조)           |

### articles 배열 내 항목

| 필드 | 타입 | 설명 |
|------|------|------|
| articleCode | string | 정규화된 조문코드 (예: "제3조") |
| lawId | string | 법령 ID ("RULE") |
| title | string | 조문 제목 |
| fullText | string | 조문 전문 (①②③ 항 포함) |
| section | string/null | 법령 내 위치 (편>장>절>관) |
| paragraphCount | int | 항 수 |
| deleted | bool | 삭제 조문 여부 |
| preAssignedIds | string[] | 스크립트가 사전 생성한 NS 식별자 목록 |
| hasSanction | object/null | penalty-routes.json에서 복사한 벌칙 정보 |

## 8. 실행 결과 (656조문 전체)

```
[OK] batch-001-input.json: 20조문
[OK] batch-002-input.json: 20조문
...
[OK] batch-033-input.json: 16조문

[DONE] 33개 배치 생성 완료 (총 656조문)
```

---

*이 문서는 Step 2(배치 입력 준비)만 다룹니다. NS 생성은 `phase1_step3.md`, NS 검증은 `phase1_step4.md`를 참조하세요.*
