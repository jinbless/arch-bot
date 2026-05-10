# KOSHA 온톨로지 Pipe-B — 가이드 → CI 파이프라인 구현 계획

> 최종 작성: 2026-04-25
> 문서 현황: 작성 완료 `phase1_step0.md`, `phase1_step1.md`, `phase2_step1.md`, `phase2_step2.md` / 나머지 step 재현문서는 추후 보강 예정
> Pipe-A 계획서: pipe-A/plan_pipea.md
> Pipe-A 상태: pipe-A/status_pipea.md (Phase 1~2 완료)

> 현재 기준 참고 (2026-05-07): 이 계획은 Pipe-B 추출 체계를 설명하는 역사 문서다. 최신 product 화면에서는 CI만 조치 본체로 보지 않고, `KOSHA Guide / WorkProcess`를 표준 개선 절차의 중심으로 둔다. `ChecklistItem`은 즉시 조치, 시각 단서, 검색 색인, 보조 근거로 사용한다. 전체 Guide JSON 추출 완료 후 이 기준으로 Guide 레이어와 추천 로직을 리빌딩한다.

---

## Context

**Pipe-A 완료** (koshaontology/pipe-A가 정규 시스템):
- Phase 1: 5개 법령 1,227조문 → 656 벌칙경로 → 1,229 NormStatements
- Phase 2: 1,229 NS → 626 SafetyRequirements (48배치, 43카테고리)
- DB: PostgreSQL — articles 1,227행, penalty_routes 656행, norm_statements 1,229행, safety_requirements 626행, sr_ns_mapping 1,020행, sr_article_mapping 626행
- V1~V15 무결성 규칙 ALL PASS

**Pipe-B 목표**: KOSHA 가이드 1,038개 PDF(5개 분야 A/B/C/D/E) → Layer 5 엔티티 5종(CI, DT, WP, ES, DR) 추출 + CI→SR `basedOn` 링크 확정 + SR Phase 3 예약 필드 채우기.

> **Pipe-A와 Pipe-B의 관계 — 쉬운 비유**
>
> Pipe-A는 "법전 편찬"이었다. 법 조문을 읽어서 "무엇을 지켜야 하는가"(SR)를 정리하는 작업. 이것은 모든 현장에 동일하게 적용되는 보편적 원칙이다.
>
> Pipe-B는 "현장 매뉴얼 제작"이다. KOSHA 가이드라는 실무 문서에서 "이 원칙을 현장에서 어떻게 점검하는가"(CI)를 추출하고, 각 CI가 어떤 법적 원칙(SR)에 근거하는지를 연결한다.
>
> ```
> Pipe-A (법전 편찬):    법 조문 → NS → SR (626개 보편 원칙)
>                                        ↑ basedOn
> Pipe-B (매뉴얼 제작):  가이드 PDF → CI (현장 점검항목) ──┘
>                              → DT (용어) + WP (공정) + ES (장비) + DR (문서)
> ```
>
> Pipe-A가 "높이 2m 이상 작업 시 추락방지 조치"(SR-FALL-001)라는 원칙을 세웠다면, Pipe-B는 "외벽도장 작업 시 안전대 부착설비 설치 여부"(CI-DC13-005)라는 구체적 점검항목을 만들고, 이 CI가 SR-FALL-001에 근거한다는 링크를 거는 것이다.

**legacy 시스템(shared/pipe-B/)은 폐기**. 개념적 참고만 차용:
- 4단계 구조 (Step 0~3)
- CI/DT/WP/ES/DR 5종 엔티티 패턴
- 45개 가이드 처리 경험 (3,203 CI, 127 SR 참조)
- 대형 가이드 파트 분리 패턴

---

## 0. 7레이어 온톨로지 대조 — Pipe-B 범위

Pipe-B가 직접 다루는 Layer 5(KOSHA 가이드 구조) 8개 클래스를 대조한다.

### Layer 5 클래스 8개 vs Pipe-B 계획

- **KoshaGuide** — ✅ Pipe-B 핵심. 가이드 메타데이터 테이블 생성.
- **GuideSection** — ⚠️ 암묵적 반영. guide-text JSON의 sections 구조로 표현, 별도 DB 테이블 없음.
- **ChecklistCategory** — ⚠️ 부분 반영. CI의 sourceSection + WP 연결로 대체.
- **ChecklistItem** — ✅ Pipe-B 핵심 산출물. CI 추출 + basedOn 링크.
- **DomainTerm** — ✅ 추출 대상.
- **WorkProcess** — ✅ 추출 대상.
- **DocumentRequirement** — ✅ 추출 대상.
- **EquipmentSpec** — ✅ 추출 대상.
- **GuideInterLink** — ❌ Pipe-C 범위 (가이드 간 상호참조는 교차검증 단계에서 수행).

### Layer 4 예약 필드 채우기 (SR Phase 3)

Pipe-A Phase 2에서 null로 예약해둔 5개 필드를 KOSHA 가이드 데이터를 활용해 채운다:

- **requiresPPE**: 가이드의 보호구 정보 → SR에 역매핑
- **hasCorrectiveAction**: 가이드의 시정조치 권고사항 → SR에 역매핑
- **hasIncidentResponse**: 가이드의 비상대응 절차 → SR에 역매핑
- **applicableIndustry**: 가이드 분야(A~E) → SR 적용 업종 추론
- **hazardAssessment**: 가이드의 위험성평가 데이터 → SR에 역매핑

> **왜 가이드에서 SR 필드를 채우나? — 쉬운 비유**
>
> 법 조문은 "추락방지 조치를 하여야 한다"라고만 말하지, "KS G ISO 10333-1 안전대를 써라"라거나 "비용이 50~300만원이다"라고는 말하지 않는다. KS 규격, 비용, 난이도 같은 실무 정보는 KOSHA 가이드에 있다.
>
> 아파트를 지을 때 미리 뚫어놓은 에어컨 배관 구멍(Phase 2 예약 필드)에 실제 에어컨을 설치하는(가이드 데이터로 채우는) 단계가 바로 이것이다.

---

## 1. Pipe-B 범위 정의

### 포함 (3 Phase, 12 Step)

**Phase 1: Guide Parsing** (PDF → 구조화 JSON)
- Step 0: 가이드 인벤토리 + PDF 인덱스 (`phase1_step0.md`)
- Step 1: v2 스키마 설계 + legacy 호환성 검증 (`phase1_step1.md`)
- Step 2: 가이드 PDF → 텍스트 JSON 추출 (`phase1_step2.md`, 미작성)
- Step 3: 파싱 품질 검증 (`phase1_step3.md`, 미작성)

**Phase 2: CI Extraction** (JSON → 엔티티 추출 + basedOn)
- Step 1: SR 조회 인덱스 생성 (`phase2_step1.md`)
- Step 2: CI 스키마 + 배치 준비 (`phase2_step2.md`)
- Step 3: 추출 에이전트 가이드 작성 (`phase2_step3.md`, 미작성)
- Step 4: CI/DT/WP/ES/DR 추출 실행 (`phase2_step4.md`, 미작성)
- Step 5: 추출 결과 검증 (`phase2_step5.md`, 미작성)

**Phase 3: DB Integration** (DB 적재 + SR 보강)
- Step 1: DB 스키마 확장 (`phase3_step1.md`, 미작성)
- Step 2: 데이터 적재 + 무결성 검증 (`phase3_step2.md`, 미작성)
- Step 3: SR Phase 3 필드 채우기 (`phase3_step3.md`, 미작성)
- Step 4: 전체 무결성 검증 + 회귀 (`phase3_step4.md`, 미작성)

### 제외 (Pipe-C 또는 후속)

- GuideInterLink (가이드 간 상호참조) → Pipe-C step1
- basedOn 최종 확정 (교차검증) → Pipe-C step2
- sr-registry.json 재구축 → Pipe-C step3
- Neo4j 전환 → 장기 과제
- 대시보드 재빌드 → Pipe-B/C 완료 후

**근거**: Pipe-A가 법령 → NS → SR을 결정론적으로 구축한 것처럼, Pipe-B도 가이드 → CI + 부속 엔티티 추출에 집중. 교차검증과 최종 링크 확정은 Pipe-C의 역할.

---

## 2. 데이터 현황 분석

### 2.1 KOSHA 가이드 PDF 분포

- A (산업안전일반): 124개
- B (기계/전기안전): 232개
- C (화학안전): 238개
- D (건설안전): 73개
- E (보건위생): 371개
- **합계: 1,038개**

### 2.2 legacy 처리 현황

- 이미 파싱된 가이드 (텍스트 JSON): 41개 (병합 완료) + 9개 파트 파일 (`kosha-guides/parsed/`)
- legacy CI 파일: 45개 (3,203 CI) (`shared/output/checklists/`)
- 미처리 가이드: 242개 (796/1,038 추출 완료, `kosha-guides/{A~E}/`)

### 2.3 Pipe-A DB 현황 (basedOn 참조 대상)

- safety_requirements: 626행 (CI.basedOn 대상)
- sr_article_mapping: 626행 (가이드 인용조문 → SR 역추적)
- sr_ns_mapping: 1,020행 (SR → NS 추적)
- articles: 1,227행 (가이드 인용조문 검증)

> **왜 legacy CI 3,203개를 버리고 다시 추출하나? — 쉬운 비유**
>
> 이전에 만든 45개 가이드의 CI는 옛날 공장에서 만든 부품이다. 새 공장(Pipe-B v2)은 JSON Schema가 다르고, basedOn이 legacy sr-registry(127 SR)가 아닌 Pipe-A DB(626 SR)를 참조해야 하며, identifier 규칙도 바뀌었다. 옛 부품을 하나하나 검사/수정하는 것보다 새 공장 라인에서 다시 찍는 게 빠르다.
>
> 다만, legacy CI를 "참고"는 한다. LLM이 CI를 추출할 때 legacy 파일을 예시로 제공하면 추출 품질이 올라간다. 폐기하되 참고하는 전략.

---

## 3. 스키마 설계

### 3.1 CI 식별자 규칙

```
CI ID: ^CI-[A-Z0-9]+-[0-9]+$
예: CI-AG4-001, CI-DC13-042, CI-BE7-015
```

- shortCode = 가이드코드에서 하이픈/연도 제거 (A-G-4-2025 → AG4)
- 순번 = 가이드 내 순차 (001부터)

### 3.2 ChecklistItem (CI) JSON 구조

```json
{
  "identifier": "CI-AG4-001",
  "text": "이동식 사다리의 발판 간격은 230mm 이상 400mm 이내로 균등하게 설치되어 있는지 확인",
  "basedOn": ["SR-LADDER-001"],
  "guideContext": "이동식 사다리 사용 현장",
  "additionalDetail": "KS B 6251 기준에 따라 발판 간격이 균등하게 설치되어야 하며, 상부 돌출 길이 60cm 이상 확보",
  "workProcessPhase": "WP-AG4-01",
  "bindingForce": "MANDATORY",
  "sourceSection": "4.(1)",
  "sourceGuide": "A-G-4-2025",
  "requirementType": "EQUIPMENT_STANDARD"
}
```

**필수 필드**: identifier, text, basedOn, bindingForce, sourceSection, sourceGuide
**선택 필드 (null 허용, 생략 금지)**: guideContext, additionalDetail, workProcessPhase, requirementType

**basedOn 규칙**:
- MANDATORY CI → basedOn 필수 (1개 이상 SR)
- RECOMMENDED CI → basedOn 선택 (null 허용)
- basedOn의 모든 SR은 safety_requirements 테이블에 존재해야 함 (FK)

> **왜 MANDATORY CI는 basedOn이 필수인가?**
>
> "~하여야 한다"(MANDATORY)라고 말하려면 법적 근거가 있어야 한다. 근거 없이 강제하면 그것은 법이 아니라 의견이다. RECOMMENDED CI는 가이드 자체의 권고사항이므로 법적 근거(SR) 없이도 가능.

### 3.3 DomainTerm (DT) JSON 구조

```json
{
  "identifier": "DT-AG4-001",
  "term": "발판 (Step)",
  "definition": "일정한 간격으로 사다리의 버팀대에 부착되어 상·하로 이동 시 발을 디딜 수 있는 수평부재를 말한다.",
  "relatedSR": ["SR-LADDER-001"],
  "sourceGuide": "A-G-4-2025",
  "sourceSection": "3.(1)"
}
```

**필수**: identifier, term, definition, sourceGuide, sourceSection
**선택**: relatedSR (null 허용)
**금지**: termName, name 필드명 사용 금지 → 반드시 `term`

### 3.4 WorkProcess (WP) JSON 구조

```json
{
  "identifier": "WP-AG4-01",
  "processOrder": 1,
  "processName": "사다리 선정 및 사전점검",
  "safetyMeasures": "제24조 구조기준 충족 여부 확인. 접합부·녹·미끄럼방지 점검",
  "requiredSR": ["SR-LADDER-001"],
  "requiredPPE": ["SAFETY_HELMET"],
  "sourceGuide": "A-G-4-2025",
  "sourceSection": "4"
}
```

**필수**: identifier, processOrder, processName, safetyMeasures, sourceGuide
**선택**: requiredSR, requiredPPE, sourceSection (null 허용)

### 3.5 EquipmentSpec (ES) JSON 구조

```json
{
  "identifier": "ES-AG4-001",
  "equipmentName": "이동식 사다리 (일반)",
  "specifications": {
    "maxLength": "7m",
    "stepInterval": "230~400mm",
    "stepWidth": "30cm 이상",
    "sideRailSpacing": "30cm 이상"
  },
  "relatedSR": ["SR-LADDER-001"],
  "sourceGuide": "A-G-4-2025",
  "sourceSection": "4.(10)"
}
```

**필수**: identifier, equipmentName, specifications, sourceGuide
**선택**: relatedSR, sourceSection (null 허용)
**금지**: name, specName, equipmentType → 반드시 `equipmentName`

### 3.6 DocumentRequirement (DR) JSON 구조

```json
{
  "identifier": "DR-DC13-001",
  "documentType": "WORK_PLAN",
  "title": "외벽도장보수공사 작업계획서",
  "requiredSections": ["작업 개요", "위험요인 분석", "안전조치 계획"],
  "relatedSR": ["SR-PLAN-001", "SR-FALL-001"],
  "sourceGuide": "D-C-13-2026",
  "sourceSection": "6"
}
```

**필수**: identifier, documentType, title, sourceGuide
**선택**: requiredSections, relatedSR, sourceSection (null 허용)

**documentType enum**: WORK_PLAN, RISK_ASSESSMENT, SAFETY_CHECKLIST, MSDS, INCIDENT_REPORT, TRAINING_RECORD

### 3.7 KoshaGuide 메타데이터 구조

```json
{
  "guideCode": "A-G-4-2025",
  "shortCode": "AG4",
  "title": "이동식 사다리의 사용에 관한 기술지원규정",
  "domain": "A",
  "subCategory": "일반안전",
  "totalPages": 10,
  "citedArticles": ["제24조", "제42조", "제44조"],
  "linkedSR": ["SR-LADDER-001", "SR-FALL-001"],
  "ciCount": 15,
  "dtCount": 3,
  "wpCount": 4,
  "esCount": 2,
  "drCount": 0,
  "pdfPath": "kosha-guides/A/A-G-4-2025 이동식 사다리의 사용에 관한 기술지원규정.pdf",
  "parsedJsonPath": "kosha-guides/parsed/guide-AG4.json",
  "processedAt": "2026-04-15T00:00:00Z"
}
```

### 3.8 출력 파일 구조 (가이드 단위)

```json
{
  "metadata": {
    "guideCode": "A-G-4-2025",
    "shortCode": "AG4",
    "generatedAt": "2026-04-15T00:00:00Z",
    "generatedBy": "pipe-B step4 v1.0",
    "batchId": "pipeb-batch-A-001",
    "totalCI": 15,
    "totalDT": 3,
    "totalWP": 4,
    "totalES": 2,
    "totalDR": 0
  },
  "checklistItems": [],
  "domainTerms": [],
  "workProcesses": [],
  "equipmentSpecs": [],
  "documentRequirements": []
}
```

**5개 배열 모두 필수 (0건이어도 `[]`로 명시, 키 생략 금지)**

---

## 4. Phase 1: Guide Parsing (가이드 파싱)

**목표**: 1,038 KOSHA 가이드 PDF → 구조화된 텍스트 JSON 캐시
**완료 조건**: 1,038개 guide JSON 생성, 파싱 검증 PASS
**독립 가치**: Phase 2 없이도 가이드 텍스트 DB가 완성됨 — 검색/참조 가능

> **Pipe-A와의 대칭**
>
> ```
> Pipe-A Phase 1: 법령 → NS    (Step 0~4, LLM 1회)
> Pipe-B Phase 1: PDF → JSON   (Step 0~3, LLM 1회)
> ```

### P1-Step 0: 가이드 인벤토리 + PDF 인덱스 (`phase1_step0.md`)

**유형**: 100% 스크립트 (결정론적)
**스크립트**: `pipe-B/scripts/step0_build_inventory.py`

**산출물**:
- `pipe-B/data/guide-inventory.json` — 1,038개 가이드 전수 목록 (domain, guideCode, shortCode, title, totalPages, pdfPath)
- `pipe-B/data/guide-pdf-index.json` — shortCode → PDF 경로 매핑 (legacy guide-pdf-index.json의 v2 버전)
- `pipe-B/data/domain-batch-plan.json` — 분야별 배치 계획

**로직**:
1. `kosha-guides/{A,B,C,D,E}/` 디렉토리 스캔
2. PDF 파일명에서 guideCode, title 파싱
3. shortCode 생성 (하이픈 제거, 연도 제거)
4. 분야별 가이드 수, 총 페이지 수 집계
5. 배치 계획 생성 (분야별 처리 순서, 예상 시간)

> **왜 인벤토리를 먼저 만드나?**
>
> 건물을 지을 때 자재 목록(BOM)을 먼저 만드는 것과 같다. 1,038개 PDF를 무작정 처리하면 "어디까지 했지?"를 추적할 수 없다. 인벤토리가 있으면 진행률 = 처리된 가이드 수 / 1,038로 명확해진다.

**위험**: 낮음. 디렉토리 스캔이므로 실패 가능성 거의 없음.

---

### P1-Step 1: v2 스키마 설계 + legacy 호환성 검증 (`phase1_step1.md`)

**유형**: 스크립트 + 설계
**산출물**: `pipe-B/schemas/guide-text-v2.schema.json`

**v2 호환성 검증 기준**:
- metadata.tocSections 존재
- sections[].sectionNumber, sectionTitle, text, tables, images 필드 존재
- subsections 구조 (7.1이 sections에 직접 있으면 비호환)
- 빈 text + 빈 tables + 빈 images인 섹션이 없음

**legacy 41개 가이드 스캔**: v2 스키마로 검증 → 호환 목록 생성 → 호환 가이드는 Phase 1 Step 2에서 재사용.

**위험**: 낮음.

---

### P1-Step 2: 가이드 PDF → 텍스트 JSON (`phase1_step2.md`)

**유형**: LLM 필수 (PDF 내용 추출은 결정론적 스크립트로 불가)
**스크립트**: `step1_parse_pdf_vlm.py` + `agents/step1-vlm-parse-prompt.md` (claude CLI 에이전트 기반 VLM)

**산출물**: `kosha-guides/parsed/guide-{shortCode}.json` (가이드 1,038개)

**처리 전략 — 3단계 우선순위**:

1. **기존 파싱 결과 재사용** (41개): 이미 `parsed/`에 있는 가이드. P1-Step 1에서 v2 호환 확인된 것만 재사용.
2. **소형 가이드 (~15p) 일괄 처리**: 1세션 1가이드 완결.
3. **대형 가이드 (40p+) 파트 분리**: legacy 패턴 그대로 — part1, part2, ... → merge-parts.py 병합.

> **왜 기존 41개를 재사용하나?**
>
> Pipe-A Phase 2에서 카테고리 매핑을 128키 exact match로 바꿨을 때 "전부 다시"를 했다. 그때는 카테고리가 바뀌어서 어쩔 수 없었다. 하지만 guide-text JSON은 원문 캐시이므로 스키마만 호환되면 재사용이 가능하다. 1,038개를 전부 다시 파싱하면 LLM 비용만 수백 달러.

**처리 순서**: D(73) → A(124) → B(232) → C(238) → E(371)

> **왜 D 분야부터?**
>
> D(건설안전)는 PDF 수가 73개로 가장 적으면서, legacy 45개 가이드 중 상당수가 D 분야(DC3, DC7, DC11, DC12, DC13 등)이다. 가장 잘 아는 분야를 먼저 처리하면 파이프라인 문제를 일찍 발견할 수 있다. 소프트웨어의 "smoke test" 원리.

**세션 분할 가이드라인**:

- 소 (~15p): 1세션, guide-{code}.json 직접 생성
- 중 (15~40p): 1~2세션, 1세션 완결 또는 파트 분리
- 대 (40~70p): 2~3세션, 파트 분리 필수
- 특대 (70p+): 3~4세션, 파트 분리 필수

**위험**: 높음 (LLM 의존, 1,000+ 가이드 처리). **완화**: 기존 41개 재사용으로 ~960개만 신규 처리. 분야별 순차 처리로 문제 조기 발견.

---

### P1-Step 3: 파싱 품질 검증 (`phase1_step3.md`)

**유형**: 100% 스크립트 (결정론적)
**스크립트**: `pipe-B/scripts/step0_validate_parsing.py`

**산출물**: `pipe-B/data/parsing-report.json`

**검증 항목**:
1. guide-text-v2.schema.json 대조 (전수)
2. 섹션 커버리지: PDF 목차 vs JSON 섹션 매칭
3. 빈 섹션 탐지 (text + tables + images 모두 비어있는 섹션)
4. 분야별 통계: 평균 섹션 수, 평균 표 수, 파트 분리 비율

**Phase 1 완료 조건**:
- 1,038개 guide JSON 존재
- 스키마 검증 PASS (ERROR 0건)
- 빈 섹션 비율 < 5%

**위험**: 낮음.

---

## 5. Phase 2: CI Extraction (엔티티 추출)

**목표**: 텍스트 JSON → CI/DT/WP/ES/DR 추출 + basedOn 링크 확정
**선행 조건**: Phase 1 완료 (1,038개 guide JSON 존재)
**완료 조건**: ~70,000 CI 추출, B1~B14 Hard Error 0건
**독립 가치**: CI→SR basedOn 링크 확정, 가이드별 체크리스트 완성

> **Pipe-A와의 대칭**
>
> ```
> Pipe-A Phase 2: NS → SR      (Step 1~6, LLM 1회)
> Pipe-B Phase 2: JSON → CI    (Step 1~5, LLM 1회)
> ```

### P2-Step 1: SR 조회 인덱스 생성 (`phase2_step1.md`)

**유형**: 100% 스크립트 (결정론적)
**스크립트**: `pipe-B/scripts/step2_build_sr_index.py`

**산출물**:
- `pipe-B/data/sr-article-index.json` — 조문코드 → SR 목록 역인덱스
- `pipe-B/data/sr-category-index.json` — 위험유형 → SR 목록 역인덱스
- `pipe-B/data/sr-keyword-index.json` — SR 키워드 → SR ID 매핑

**basedOn 링킹 3단계 전략**:

> **basedOn 링크가 왜 어려운가? — 쉬운 비유**
>
> 독후감(CI)을 쓸 때 "이 문장은 교과서 3장 2절에서 나왔습니다"라고 출처를 적어야 한다. 하지만 교과서가 626권(SR)이나 되면, LLM에게 626권을 다 읽히고 "이 CI는 어떤 SR에 근거하나?" 물어보는 건 비현실적이다.
>
> 해결: **좁혀서 물어본다.**
>
> 1단계(결정론): 가이드가 인용한 조문 → sr_article_mapping으로 관련 SR 후보 추출 (평균 5~15개)
> 2단계(결정론): CI의 키워드/위험유형으로 SR 후보 추가 필터
> 3단계(LLM): 후보 SR 5~15개 중에서 CI에 맞는 SR 선택
>
> 626개 전체를 보는 대신 5~15개 후보만 보면 되므로, LLM의 정확도가 올라가고 비용이 내려간다.

**sr-article-index.json 구조**:
```json
{
  "제24조": ["SR-LADDER-001"],
  "제42조": ["SR-FALL-001", "SR-FALL-002"],
  "제44조": ["SR-FALL-001", "SR-PPE-001"],
  "제301조": ["SR-ELECTRIC-001", "SR-ELECTRIC-002"]
}
```

이 인덱스는 `sr_article_mapping` + `articles` 테이블에서 자동 생성. Pipe-A DB가 SSOT.

**SR 후보 추출 알고리즘 (배치 준비 스크립트에서 사전 계산)**:
1. 가이드 텍스트에서 인용 조문 추출 (정규식: `제\d+조(의\d+)?`)
2. sr-article-index에서 해당 조문의 SR 목록 수집 → 1차 후보
3. 가이드 분야(A~E) + 위험유형 키워드로 sr-category-index 필터 → 2차 후보
4. 중복 제거, 최대 20개 SR 후보 선정

**위험**: 중간. 인용 조문이 없는 가이드(E 분야 보건 가이드 일부)는 후보 SR이 0개일 수 있음. → 키워드 인덱스로 보완 + basedOn=null 허용(RECOMMENDED CI).

---

### P2-Step 2: CI 스키마 + 배치 준비 (`phase2_step2.md`)

**유형**: 100% 스크립트 (결정론적)
**스크립트**: `pipe-B/scripts/step3_prepare_ci_batch.py`

**산출물**:
- `pipe-B/schemas/ci-file.schema.json` — CI 출력 JSON Schema
- `pipe-B/data/ci-batches/pipeb-batch-{domain}-{NNN}-input.json`

**로직**:
1. guide-inventory.json에서 처리 대상 가이드 목록 로드
2. 각 가이드에 대해:
   a. guide-{shortCode}.json (텍스트 JSON) 로드
   b. 인용 조문 추출 → SR 후보 계산 (P2-Step 1 인덱스 사용)
   c. preAssignedId 범위 사전 할당: CI-{shortCode}-{001~NNN}
   d. legacy CI 참고 데이터 연결 (있으면)
3. 분야별 배치 분할:
   - 소형 가이드(~15p): 5개 가이드/배치
   - 중형 가이드(15~40p): 3개 가이드/배치
   - 대형 가이드(40p+): 1개 가이드/배치

**배치 입력 구조**:
```json
{
  "metadata": {
    "batchId": "pipeb-batch-D-001",
    "domain": "D",
    "guideCount": 3,
    "totalEstimatedCI": 90
  },
  "guides": [
    {
      "guideCode": "D-C-13-2026",
      "shortCode": "DC13",
      "title": "외벽도장보수공사 안전작업지침",
      "textJsonPath": "kosha-guides/parsed/guide-DC13.json",
      "citedArticles": ["제42조", "제44조", "제57조", "제63조"],
      "candidateSR": [
        {"id": "SR-FALL-001", "title": "높이 2m 이상 작업 시 추락방지 조치", "referencesArticle": ["제42조", "제44조"]},
        {"id": "SR-SCAFFOLD-001", "title": "비계 구조 및 안전기준", "referencesArticle": ["제57조"]},
        {"id": "SR-SCAFFOLD-002", "title": "달비계 안전기준", "referencesArticle": ["제63조"]}
      ],
      "preAssignedIdRange": {"start": "CI-DC13-001", "end": "CI-DC13-100"},
      "legacyReference": "shared/output/checklists/cl-DC13-round2.json"
    }
  ]
}
```

> **Pipe-A 패턴 재사용: 사전 할당 + SSOT 복사**
>
> ```
> Pipe-A Step 2: NS preAssignedId + hasSanction 사전 복사 → LLM은 text만 생성
> Pipe-B P2-Step 2: CI preAssignedId 범위 + candidateSR 사전 계산 → LLM은 text + basedOn 선택만
> ```
>
> LLM의 역할을 최소화하는 원칙은 동일. identifier 창작 금지, SR 후보 외 SR 참조 금지.

**위험**: 중간. SR 후보 계산의 정확도가 basedOn 품질을 좌우. → 파일럿으로 검증.

---

### P2-Step 3: 추출 에이전트 가이드 작성 (`phase2_step3.md`)

**유형**: LLM 에이전트 프롬프트 설계
**에이전트 가이드**: `pipe-B/agents/step4-entity-extraction.md`

**LLM이 해야 할 일**:
1. guide-text JSON을 섹션별로 읽기
2. 각 섹션에서 5종 엔티티 추출:
   - **CI**: 점검항목 → text 원문 그대로 + basedOn 후보 SR 중 선택
   - **DT**: 용어 정의 섹션의 정의 → term + definition
   - **WP**: 작업 순서/공정 → processName + safetyMeasures
   - **ES**: 장비/자재 규격 → equipmentName + specifications
   - **DR**: 문서 요구사항 → documentType + title + requiredSections
3. basedOn 선택: candidateSR 목록에서 의미적 매칭
4. bindingForce 분류: "~하여야 한다" → MANDATORY, "~하는 것이 좋다" → RECOMMENDED
5. sourceSection 기록: 실제 가이드 섹션 번호

**LLM 금지 사항** (Pipe-A 원칙 계승):
- identifier 창작 → preAssignedId 범위 내에서 순차 사용
- candidateSR 밖의 SR 참조 → 목록에 없으면 basedOn=null + 코멘트
- 스키마 외 필드 추가
- {} 빈 객체 (null 사용)
- "" 빈 문자열 (minLength: 1 위반)
- text 축약/의역 → 원문 그대로

**추출 우선순위**:
1. CI 추출이 최우선 (Pipe-B 핵심 산출물)
2. DT는 "용어의 정의" 섹션에서 거의 기계적 추출
3. WP는 작업 순서/공정 섹션에서 추출
4. ES는 장비/자재 규격 섹션에서 추출
5. DR은 0건 허용 (가이드에 없을 수 있음)

> **CI vs ES 구분 기준**
>
> "사다리 발판 간격은 230~400mm 이내여야 한다" → 이것은 CI인가 ES인가?
> - CI: "발판 간격이 230~400mm 이내인지 점검" (점검 행위)
> - ES: "이동식 사다리의 발판 간격 규격: 230~400mm" (기술 사양)
> 둘 다 추출한다. CI는 "확인하라"는 행위, ES는 "규격은 이렇다"는 사실.

**위험**: 높음. 프롬프트 품질이 전체 품질을 결정. **완화**: legacy CI 45파일을 few-shot 예시로 제공.

---

### P2-Step 4: CI/DT/WP/ES/DR 추출 실행 (`phase2_step4.md`)

**유형**: LLM 배치 실행

**5단계 점진 확장**:

1. **파일럿 A** (D 분야 5개 가이드): legacy CI가 있는 가이드로 시작 → legacy와 비교하여 품질 평가
2. **파일럿 B** (D 분야 나머지 ~70개): D 분야 전체 완료
3. **A 분야** (124개): 파일럿 경험 반영
4. **B+C 분야** (232+238개): 병렬 처리 가능
5. **E 분야** (371개): 가장 큰 분야, 마지막 처리

**각 단계 완료 조건**:
- P2-Step 5 검증 PASS
- basedOn FK 위반 0건 (MANDATORY CI 한정)
- 섹션 커버리지 90% 이상

> **왜 5단계로 나누나?**
>
> Pipe-A에서도 48배치를 4라운드(5+15+15+13)로 나눠 실행했다. 1,038개를 한 번에 돌리면 프롬프트 문제가 1,038개 파일에 전파된다. 5단계로 나누면 각 단계에서 문제를 잡고 다음 단계에 반영할 수 있다.

**예상 산출물**:
- CI: ~70,000개 (1,038 가이드 x 평균 ~67 CI)
- DT: ~5,000개
- WP: ~4,000개
- ES: ~3,000개
- DR: ~1,500개

> **예상치 근거**: legacy 45개 가이드에서 3,203 CI → 가이드당 평균 71 CI. 1,038개 가이드 전체는 대부분 소형이므로 평균을 약간 낮춘 67개로 추정.

**위험**: 높음 (파일럿 + 점진 확장으로 완화).

---

### P2-Step 5: 추출 결과 검증 (`phase2_step5.md`)

**유형**: 100% 스크립트 (결정론적)
**스크립트**: `pipe-B/scripts/step6_validate_entities.py`

**검증 규칙 20개**:

**구조적 검증 (Hard Error, 0건이어야 PASS)**:
- B1: JSON Schema 검증 (ci-file.schema.json 대조)
- B2: CI identifier 중복 없음 (가이드 내 + 가이드 간)
- B3: CI identifier 정규식 `^CI-[A-Z0-9]+-[0-9]+$`
- B4: MANDATORY CI의 basedOn이 safety_requirements에 존재 (FK)
- B5: basedOn 배열이 candidateSR 범위 내 (후보 외 SR 참조 없음)
- B6: text 비어있지 않음 (minLength: 1)
- B7: bindingForce enum 유효성 (MANDATORY / RECOMMENDED)
- B8: sourceSection이 guide-text JSON의 실제 섹션에 존재
- B9: DT identifier 정규식 + term 필드명 확인 (termName 사용 시 ERROR)
- B10: ES identifier 정규식 + equipmentName 필드명 확인
- B11: WP processOrder 순서 일관성 (1, 2, 3... 연속)
- B12: DR documentType enum 유효성
- B13: 5개 배열 키 존재 확인 (checklistItems, domainTerms, workProcesses, equipmentSpecs, documentRequirements)
- B14: sourceGuide가 guide-inventory에 존재

**의미적 검증 (Warning, 수동 확인)**:
- B15: 섹션 커버리지 — guide-text의 모든 섹션이 CI로 변환되었는지
- B16: basedOn 의미적 일관성 — CI text와 SR text의 주제 유사도
- B17: MANDATORY vs RECOMMENDED 분류 일관성 — "~하여야 한다" 패턴 확인
- B18: DT definition이 가이드 원문과 일치하는지 (축약 감지)
- B19: CI 수 대비 WP 수 비율 이상치 (WP 0건인데 CI 50개 이상이면 Warning)
- B20: 동일 SR에 대한 CI 집중도 — 단일 SR에 CI 50% 이상 집중 시 Warning

> **B4와 B5가 왜 중요한가?**
>
> B4는 "이 CI의 법적 근거가 실제로 존재하는가"를 확인한다. DB에 없는 SR을 참조하면 근거가 허공에 매달린다.
>
> B5는 더 엄격하다. "사전에 계산한 후보 SR 목록 밖의 SR을 참조했는가"를 확인한다. LLM이 제멋대로 SR-FALL-099 같은 존재하지 않는 SR이나, 후보 목록에 없었던 SR을 참조하면 잡아낸다. Pipe-A의 "preAssignedId만 사용" 원칙과 동일한 안전장치.

**Phase 2 완료 조건**:
- ~70,000 CI 추출
- B1~B14 Hard Error 0건
- basedOn 커버리지 100% (MANDATORY CI)
- 섹션 커버리지 >= 90%

**위험**: 중간.

---

## 6. Phase 3: DB Integration (DB 통합 + SR 보강)

**목표**: DB 적재 + SR Phase 3 예약 필드 채우기
**선행 조건**: Phase 2 완료 (CI/DT/WP/ES/DR 검증 통과)
**완료 조건**: V16~V30 ALL PASS, SR Phase 3 null→값 전환
**독립 가치**: 완전한 Layer 5 DB, SR 예약 필드 보강 완료

> **Pipe-B만 Phase 3까지 있는 이유**
>
> SR Phase 3 필드 채우기는 CI 추출과 성격이 다른 작업(역방향 집계 + LLM 구조화)이므로 별도 Phase로 분리. Pipe-A의 Phase 2 Step 6(DB 적재)에 해당하는 것이 Phase 3 전체.

### P3-Step 1: DB 스키마 확장 (`phase3_step1.md`)

**유형**: SQL DDL
**산출물**: `pipe-B/db/schema_pb.sql`

```sql
-- Pipe-B: Layer 5 KOSHA 가이드 구조

-- 가이드 메타데이터
CREATE TABLE IF NOT EXISTS kosha_guides (
    guide_code      VARCHAR(20) NOT NULL PRIMARY KEY,
    short_code      VARCHAR(10) NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    domain          VARCHAR(1) NOT NULL CHECK(domain IN ('A','B','C','D','E')),
    sub_category    TEXT,
    total_pages     INTEGER,
    pdf_path        TEXT,
    parsed_json_path TEXT,
    ci_count        INTEGER NOT NULL DEFAULT 0,
    dt_count        INTEGER NOT NULL DEFAULT 0,
    wp_count        INTEGER NOT NULL DEFAULT 0,
    es_count        INTEGER NOT NULL DEFAULT 0,
    dr_count        INTEGER NOT NULL DEFAULT 0,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 체크리스트 항목 (Layer 5 핵심)
CREATE TABLE IF NOT EXISTS checklist_items (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^CI-[A-Z0-9]+-[0-9]+$'),
    text            TEXT NOT NULL CHECK(length(text) > 0),
    guide_context   TEXT,
    additional_detail TEXT,
    work_process_phase VARCHAR(30),
    binding_force   VARCHAR(15) NOT NULL
                    CHECK(binding_force IN ('MANDATORY','RECOMMENDED')),
    requirement_type VARCHAR(25)
                    CHECK(requirement_type IS NULL OR requirement_type IN (
                        'PHYSICAL_PROTECTION','PPE_REQUIREMENT','PROCEDURAL','TRAINING',
                        'EQUIPMENT_STANDARD','ENVIRONMENTAL','MANAGEMENT_SYSTEM','EMERGENCY_RESPONSE'
                    )),
    source_section  TEXT NOT NULL,
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- L5→L4: basedOn (CI → SR) N:N 매핑
CREATE TABLE IF NOT EXISTS ci_sr_mapping (
    ci_id   VARCHAR(30) NOT NULL REFERENCES checklist_items(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (ci_id, sr_id)
);

-- 도메인 용어
CREATE TABLE IF NOT EXISTS domain_terms (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^DT-[A-Z0-9]+-[0-9]+$'),
    term            TEXT NOT NULL CHECK(length(term) > 0),
    definition      TEXT NOT NULL CHECK(length(definition) > 0),
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    source_section  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- DT → SR 연결 (선택적)
CREATE TABLE IF NOT EXISTS dt_sr_mapping (
    dt_id   VARCHAR(30) NOT NULL REFERENCES domain_terms(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (dt_id, sr_id)
);

-- 작업공정
CREATE TABLE IF NOT EXISTS work_processes (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^WP-[A-Z0-9]+-[0-9]+$'),
    process_order   INTEGER NOT NULL,
    process_name    TEXT NOT NULL CHECK(length(process_name) > 0),
    safety_measures TEXT,
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    source_section  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- WP → SR 연결
CREATE TABLE IF NOT EXISTS wp_sr_mapping (
    wp_id   VARCHAR(30) NOT NULL REFERENCES work_processes(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (wp_id, sr_id)
);

-- WP → PPE 연결
CREATE TABLE IF NOT EXISTS wp_ppe (
    wp_id       VARCHAR(30) NOT NULL REFERENCES work_processes(identifier),
    ppe_type    VARCHAR(30) NOT NULL,
    PRIMARY KEY (wp_id, ppe_type)
);

-- 장비규격
CREATE TABLE IF NOT EXISTS equipment_specs (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^ES-[A-Z0-9]+-[0-9]+$'),
    equipment_name  TEXT NOT NULL CHECK(length(equipment_name) > 0),
    specifications  JSONB NOT NULL,
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    source_section  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ES → SR 연결
CREATE TABLE IF NOT EXISTS es_sr_mapping (
    es_id   VARCHAR(30) NOT NULL REFERENCES equipment_specs(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (es_id, sr_id)
);

-- 문서요구사항
CREATE TABLE IF NOT EXISTS document_requirements (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^DR-[A-Z0-9]+-[0-9]+$'),
    document_type   VARCHAR(25) NOT NULL CHECK(document_type IN (
        'WORK_PLAN','RISK_ASSESSMENT','SAFETY_CHECKLIST',
        'MSDS','INCIDENT_REPORT','TRAINING_RECORD'
    )),
    title           TEXT NOT NULL CHECK(length(title) > 0),
    required_sections JSONB,
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    source_section  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- DR → SR 연결
CREATE TABLE IF NOT EXISTS dr_sr_mapping (
    dr_id   VARCHAR(30) NOT NULL REFERENCES document_requirements(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (dr_id, sr_id)
);

-- 가이드 인용 조문 매핑
CREATE TABLE IF NOT EXISTS guide_article_mapping (
    guide_code   VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    law_type     VARCHAR(10) NOT NULL,
    article_code VARCHAR(20) NOT NULL,
    PRIMARY KEY (guide_code, law_type, article_code),
    FOREIGN KEY (law_type, article_code) REFERENCES articles(law_type, article_code)
);
```

**인덱스**:
```sql
CREATE INDEX IF NOT EXISTS idx_ci_guide ON checklist_items(source_guide);
CREATE INDEX IF NOT EXISTS idx_ci_binding ON checklist_items(binding_force);
CREATE INDEX IF NOT EXISTS idx_ci_sr_sr ON ci_sr_mapping(sr_id);
CREATE INDEX IF NOT EXISTS idx_dt_guide ON domain_terms(source_guide);
CREATE INDEX IF NOT EXISTS idx_wp_guide ON work_processes(source_guide);
CREATE INDEX IF NOT EXISTS idx_es_guide ON equipment_specs(source_guide);
CREATE INDEX IF NOT EXISTS idx_dr_guide ON document_requirements(source_guide);
CREATE INDEX IF NOT EXISTS idx_guide_domain ON kosha_guides(domain);
CREATE INDEX IF NOT EXISTS idx_guide_art_art ON guide_article_mapping(law_type, article_code);
```

> **왜 N:N 매핑 테이블이 5개나 되나?**
>
> CI, DT, WP, ES, DR 모두 SR과 N:N 관계이다. 하나의 CI가 여러 SR에 근거할 수 있고, 하나의 SR이 여러 가이드의 CI에서 참조된다. Pipe-A에서 sr_ns_mapping과 sr_article_mapping을 분리한 것과 같은 원리.
>
> guide_article_mapping은 "이 가이드가 어떤 조문을 인용하는가"를 추적한다. 법 개정 시 "제42조가 바뀌면 어떤 가이드가 영향받나?"를 즉시 조회할 수 있다.

**위험**: 낮음.

---

### P3-Step 2: 데이터 적재 + 무결성 검증 (`phase3_step2.md`)

**유형**: Python 스크립트 (결정론적)
**스크립트**: `pipe-B/db/import_pipeb.py`

**산출물**: PostgreSQL 적재 완료, V16~V28 PASS

**로직**:
1. kosha_guides 적재 (guide-inventory.json 기반)
2. checklist_items + ci_sr_mapping 적재 (CI JSON)
3. domain_terms + dt_sr_mapping 적재
4. work_processes + wp_sr_mapping + wp_ppe 적재
5. equipment_specs + es_sr_mapping 적재
6. document_requirements + dr_sr_mapping 적재
7. guide_article_mapping 적재 (가이드 인용 조문)

**DB 무결성 검증 (V16~V28)**:
- V16: kosha_guides 행 수 = 처리된 가이드 수
- V17: checklist_items 행 수 = CI JSON 총 CI 수
- V18: ci_sr_mapping의 모든 sr_id가 safety_requirements에 존재
- V19: ci_sr_mapping의 모든 ci_id가 checklist_items에 존재
- V20: MANDATORY CI 중 ci_sr_mapping에 없는 CI 없음 (basedOn 커버리지)
- V21: domain_terms 행 수 = DT JSON 총 DT 수
- V22: work_processes 행 수 = WP JSON 총 WP 수
- V23: equipment_specs 행 수 = ES JSON 총 ES 수
- V24: document_requirements 행 수 = DR JSON 총 DR 수
- V25: guide_article_mapping의 모든 (law_type, article_code)가 articles에 존재
- V26: checklist_items.source_guide가 kosha_guides에 존재
- V27: CI identifier 중복 없음 (전역)
- V28: DT/WP/ES/DR identifier 중복 없음 (각각)

**위험**: 중간.

---

### P3-Step 3: SR Phase 3 필드 채우기 (`phase3_step3.md`)

**유형**: 100% 스크립트 (결정론적, SQL 집계 기반)
**스크립트**: `pipe-B/scripts/step7_fill_sr_phase3.py`
**함수 5개**: `fill_requires_ppe()`, `fill_has_incident_response()`, `fill_applicable_industry()`, `fill_has_corrective_action()`, `fill_hazard_assessment()`

CI 추출 완료 후, 가이드 데이터를 역으로 SR에 반영한다.

**로직**:
1. 각 SR에 연결된 CI/WP/ES 수집
2. WP.requiredPPE 집계 → SR.requiresPPE 생성
3. ES.specifications에서 KS 규격 추출 → SR.requiresPPE.ksStandard
4. CI/WP의 안전조치 텍스트에서 시정조치 추출 → SR.hasCorrectiveAction
5. DR에서 비상대응 절차 추출 → SR.hasIncidentResponse
6. 가이드 domain 집계 → SR.applicableIndustry (D→CONSTRUCTION, B→MANUFACTURING 등)
7. 가이드의 위험성평가 데이터 → SR.hazardAssessment

> **왜 별도 스크립트로 분리하나?**
>
> CI 추출(Phase 2)과 SR 필드 채우기(Phase 3)를 같은 LLM 패스에서 하면, LLM의 부담이 커지고 실패 시 양쪽 모두 재실행해야 한다. 분리하면 CI 추출이 완료된 후 결정론적 스크립트로 SR 필드를 채울 수 있다. "에어컨 설치"를 "건물 준공" 후에 하는 것과 같다.

**위험**: 중간.

---

### P3-Step 4: 전체 무결성 검증 + 회귀 (`phase3_step4.md`)

**유형**: 100% 스크립트 (결정론적)
**스크립트**: `pipe-B/db/import_pipeb.py --verify-all`

**검증 항목**:
- V29: SR Phase 3 필드 UPDATE 후 safety_requirements 행 수 불변 (626)
- V30: Pipe-A 회귀 — V1~V15 여전히 PASS

**Phase 3 완료 조건**:
- V16~V30 ALL PASS
- SR Phase 3 예약 필드 null → 값 전환 확인 (626 SR 대상)

**위험**: 낮음.

---

## 7. basedOn 링킹 상세 전략

### 5.1 3단계 좁히기

```
전체 SR (626개)
      │
      │ 1단계: 인용 조문 필터
      ▼
후보 SR (~15개)      ← sr-article-index.json 사용
      │
      │ 2단계: 위험유형 필터
      ▼
정제 SR (~8개)       ← sr-category-index.json 사용
      │
      │ 3단계: LLM 의미적 매칭
      ▼
최종 basedOn (1~3개) ← LLM이 CI text와 SR text 비교
```

### 5.2 인용 조문이 없는 가이드 처리

E 분야(보건위생) 가이드 중 일부는 법 조문을 직접 인용하지 않는다.

**대응 전략**:
1. 가이드 제목 + 핵심 키워드에서 HazardCategory 추론 (예: "소음" → NOISE_VIBRATION)
2. sr-category-index에서 해당 HazardCategory의 SR 후보 추출
3. 후보가 0개면 → RECOMMENDED CI로 분류, basedOn = null

### 5.3 basedOn 품질 보장

- **파일럿 대조**: legacy CI의 basedOn과 새 CI의 basedOn 비교 (45개 가이드)
- **규칙 B4/B5**: FK + 후보 범위 검증으로 거짓 링크 차단
- **수동 샘플 검토**: 분야별 10개 가이드에서 CI basedOn 정확성 확인

---

## 8. SR Phase 3 필드 채우기 전략

### 6.1 채우기 순서

Phase 3 예약 필드 5개를 가이드 데이터에서 역추론하여 채운다.

- **requiresPPE**: WP.requiredPPE + ES(보호구) → PPE 타입별 집계, KS 규격은 ES에서 추출
- **hasCorrectiveAction**: CI.text + WP.safetyMeasures → 시정조치 패턴 추출 (LLM)
- **hasIncidentResponse**: DR(INCIDENT_REPORT) + 가이드 비상대응 섹션 → 대응유형/기한/책임자 추출
- **applicableIndustry**: kosha_guides.domain 집계 → 분야 → 업종 매핑
- **hazardAssessment**: 가이드 위험성평가 섹션 → hazardFactor/severity/likelihood 추출 (LLM)

### 6.2 applicableIndustry 매핑

```
가이드 domain → IndustryType:
  A (산업안전일반)  → ["MANUFACTURING", "CONSTRUCTION"]
  B (기계/전기)     → ["MANUFACTURING"]
  C (화학안전)      → ["CHEMICAL", "MANUFACTURING"]
  D (건설안전)      → ["CONSTRUCTION"]
  E (보건위생)      → ["MANUFACTURING", "CONSTRUCTION", "HEALTHCARE"]
```

SR에 연결된 CI의 소속 가이드 domain을 집계하여, 해당 SR에 적용 업종을 결정한다.

### 6.3 결정론적 vs LLM 구분

- **applicableIndustry**: 결정론적 — domain → 업종 매핑이 고정 테이블
- **requiresPPE.ppeType**: 결정론적 — WP.requiredPPE에서 직접 추출
- **requiresPPE.ksStandard**: LLM — ES에서 KS 규격 번호 파싱 필요
- **hasCorrectiveAction**: LLM — 자연어 텍스트에서 시정조치 패턴 추출
- **hasIncidentResponse**: LLM — 비상대응 절차 구조화 필요
- **hazardAssessment**: LLM — 위험도 수준 판단 필요

---

## 9. 의존성 그래프

### Phase 간 의존성

```
Phase 1: Guide Parsing          Phase 2: CI Extraction          Phase 3: DB Integration
─────────────────────           ──────────────────────          ───────────────────────
P1-Step 0 (인벤토리)
    │
P1-Step 1 (v2 스키마)
    │
P1-Step 2 (PDF→JSON, LLM)
    │
P1-Step 3 (파싱 검증)
    │
    ╰─── Phase 1 완료 ──────→ P2-Step 1 (SR 인덱스)
                                    │
                               P2-Step 2 (CI 스키마+배치)
                                    │
                               P2-Step 3 (에이전트 가이드)
                                    │
                               P2-Step 4 (추출 실행, LLM)
                                    │
                               P2-Step 5 (검증)
                                    │
                                    ╰─── Phase 2 완료 ──→ P3-Step 1 (DB 스키마)
                                                                │
                                                           P3-Step 2 (데이터 적재)
                                                                │
                                                           P3-Step 3 (SR Phase 3, LLM)
                                                                │
                                                           P3-Step 4 (전체 검증)
```

### Phase 내 병렬 가능 구간

**Phase 1**: P1-Step 0 → P1-Step 1은 순차 필수. P1-Step 2는 P1-Step 1 완료 후 시작.
**Phase 2**: P2-Step 1과 P2-Step 3(에이전트 가이드)는 병렬 가능. P2-Step 2 → P2-Step 4는 순차 필수.
**Phase 3**: 모든 Step 순차.

### Pipe-A/B 대칭 비교

```
Pipe-A Phase 1: 법령 → NS    (Step 0~4, LLM 1회)
Pipe-A Phase 2: NS → SR      (Step 1~6, LLM 1회)

Pipe-B Phase 1: PDF → JSON   (Step 0~3, LLM 1회)
Pipe-B Phase 2: JSON → CI    (Step 1~5, LLM 1회)
Pipe-B Phase 3: CI → DB+SR   (Step 1~4, LLM 1회 — SR Phase 3만)
```

---

## 10. 위험 분석

### 위험 매트릭스

- **높음** — Phase 1 P1-Step 2: 1,000+ PDF 파싱 LLM 비용. **완화**: 기존 41개 재사용, 분야별 순차, 소형 가이드 우선
- **높음** — Phase 2 P2-Step 4: CI basedOn 정확도. **완화**: 3단계 좁히기, 파일럿 대조, 규칙 B4/B5
- **높음** — Phase 2 P2-Step 4: LLM 프롬프트 품질. **완화**: legacy CI few-shot, 5단계 점진 확장
- **중간** — Phase 2 P2-Step 1: SR 후보 0개 가이드. **완화**: 키워드 인덱스 보완, RECOMMENDED 허용
- **중간** — Phase 3 P3-Step 3: SR Phase 3 품질. **완화**: 결정론적 필드 우선, LLM 필드는 별도 검증
- **낮음** — Phase 1 P1-Step 2: 대형 가이드 파트 병합 실패. **완화**: merge-parts.py dry-run 필수
- **낮음** — Phase 3 P3-Step 1: DB 마이그레이션. **완화**: Pipe-A Phase 2에서 nullable로 예약 완료

### 열린 설계 질문

1. **CI ID 충돌**: 동일 가이드 코드가 다른 연도에 존재할 때 shortCode가 같아질 수 있음 (A-G-4-2025 → AG4, A-G-4-2020 → AG4). → 최신 연도만 처리, 구버전은 제외.
2. **E 분야 보건 가이드**: 법 조문 인용이 없는 가이드의 비율이 높을 수 있음. → E 분야 파일럿에서 실제 비율 확인 후 전략 조정.
3. **CI 대량 생성 시 identifier 범위**: 가이드당 CI가 200개 이상이면 3자리 순번(001~999)이 부족할 수 있음. → 4자리(0001~9999)로 확장 가능, 하지만 3자리로 시작.
4. **가이드 간 DT 중복**: 같은 용어가 여러 가이드에서 정의될 수 있음. → 가이드 단위로 독립 저장, Pipe-C에서 중복 통합.

---

## 11. 수정 대상 파일 목록

### 신규 생성 (koshaontology/pipe-B/)

**디렉토리 구조**:
```
koshaontology/pipe-B/
├── agents/
│   ├── step1-vlm-parse-prompt.md     VLM PDF 파싱 에이전트 프롬프트
│   └── step4-entity-extraction.md    CI/DT/WP/ES/DR 추출 에이전트
├── config/
│   └── domain-industry-map.json      가이드 domain → IndustryType 매핑
├── data/
│   ├── guide-inventory.json          가이드 인벤토리
│   ├── guide-pdf-index.json          shortCode → PDF 경로
│   ├── domain-batch-plan.json        분야별 배치 계획
│   ├── sr-article-index.json         조문 → SR 역인덱스
│   ├── sr-category-index.json        위험유형 → SR 역인덱스
│   ├── sr-keyword-index.json         키워드 → SR 매핑
│   └── ci-batches/                   배치 입출력 디렉토리
│       └── pipeb-batch-{D}-{NNN}-input.json
├── db/
│   ├── schema_pb.sql                 Pipe-B DDL (Layer 5 테이블)
│   └── import_pipeb.py               JSON → PostgreSQL 임포트 + V16~V30
├── schemas/
│   ├── ci-file.schema.json           CI 출력 JSON Schema
│   ├── guide-text-v2.schema.json     guide-text JSON Schema (v2)
│   └── guide-inventory.schema.json   인벤토리 JSON Schema
└── scripts/
    ├── step0_build_inventory.py      가이드 인벤토리 생성
    ├── step0_validate_parsing.py     파싱 품질 검증
    ├── step1_parse_pdf_vlm.py        VLM PDF 파싱 (Claude CLI 기반)
    ├── step2_build_sr_index.py       SR 조회 인덱스 생성
    ├── step3_prepare_ci_batch.py     배치 입력 생성
    ├── step4_extract_entities.py     CI/DT/WP/ES/DR 추출 실행
    ├── step6_validate_entities.py    추출 결과 검증 (B1~B20)
    ├── step7_fill_sr_phase3.py       SR Phase 3 필드 채우기 (SQL 기반)
    ├── fix_parsed_json.py            파싱 JSON 수동 수정 유틸
    ├── fix_parsed_schema.py          파싱 스키마 호환성 수정 유틸
    └── lib/
        ├── guide_code.py             가이드코드 파싱 유틸
        ├── ci_identifier.py          CI/DT/WP/ES/DR 식별자 생성 유틸
        ├── guide_splitter.py         대형 가이드 파트 분리
        ├── ci_merger.py              분리 추출 결과 병합
        └── paths.py                  경로 상수
```

**재현 문서**: `koshaontology/phase1_step0.md` ~ `phase1_step3.md`, `phase2_step1.md` ~ `phase2_step5.md`, `phase3_step1.md` ~ `phase3_step4.md`

### 수정 (koshaontology/pipe-A/)

- `pipe-A/db/schema_pg.sql` — Pipe-B 테이블 포함 또는 별도 `pipe-B/db/schema_pb.sql`에서 실행
- `pipe-A/db/import_and_verify.py` — V16~V30 검증 추가 (또는 별도 `pipe-B/db/import_pipeb.py`)

### 수정 (koshaontology/)

- `koshaontology/pipe-A/CLAUDE.md` — Pipe-A 오케스트레이터 (Pipe-B 참조 시)
- `koshaontology/plan_pipeb.md` — 이 문서
- `koshaontology/status_pipeb.md` — 진행 상태 (신규)

### 재사용 (Pipe-A 모듈)

- `pipe-A/scripts/lib/article_code.py` — 조문코드 파싱
- `pipe-A/scripts/lib/schema_validator.py` — JSON Schema 검증
- `pipe-A/db/schema_pg.sql` — 기존 테이블 참조 (FK)

---

## 12. 검증 전략 총괄

### Phase 1 완료 검증

- 1,038개 guide JSON 존재
- guide-text-v2.schema.json 대조 PASS
- 빈 섹션 비율 < 5%
- parsing-report.json 생성 완료

### Phase 2 완료 검증

**파일럿 검증** (P2-Step 4 파일럿 후, D 분야 5개 가이드):
1. JSON Schema 통과 확인
2. basedOn FK 전수 검증 (MANDATORY CI 한정)
3. legacy CI 대조: 같은 가이드에서 추출된 CI 수, basedOn SR 비교
4. 수동 샘플 5개 품질 검토 (text 정확성, basedOn 적절성)
5. 섹션 커버리지 확인 (guide-text 섹션 대비)

**분야별 검증** (각 분야 완료 후):
- B1~B14 Hard Error 0건
- B15~B20 Warning 수동 확인
- 분야별 통계: CI/DT/WP/ES/DR 수, basedOn 커버리지

### Phase 3 완료 검증

- V16~V28 DB 무결성 검증 ALL PASS (P3-Step 2)
- V29~V30 SR Phase 3 + Pipe-A 회귀 ALL PASS (P3-Step 4)
- SR Phase 3 필드 채우기 검증 (null → 값 전환 확인)
- V1~V15 회귀 테스트 (Pipe-A 데이터 불변)

### 핵심 수치 목표

- 처리 가이드 수: 1,038 / 1,038 (Phase 1)
- CI 추출 수: ~70,000 (Phase 2)
- MANDATORY CI basedOn 커버리지: 100% (FK 위반 0) (Phase 2)
- 섹션 커버리지: >= 90% (분야 평균) (Phase 2)
- Hard Error (B1~B14): 0건 (Phase 2)
- DB V16~V30: ALL PASS (Phase 3)
- Pipe-A 회귀 V1~V15: ALL PASS (Phase 3)

---

*이 문서는 KOSHA 온톨로지 Pipe-B의 설계 계획서입니다. 각 Phase·Step의 재현 문서는 `phase1_step0.md` ~ `phase3_step4.md`로 구현 시 별도 작성됩니다.*

## Pipe-C 범위 완료 메모 (2026-04-17 추가)

plan_pipeb.md에서 "Pipe-C 또는 후속"으로 표기했던 항목들의 완료 상태:

- GuideInterLink (가이드 간 상호참조) → **Pipe-C Step 5에서 완료** (83건 탐지, DB 5건)
- basedOn 최종 확정 (교차검증) → **Pipe-C Step 1~3에서 완료** (감사 1,235건, 복원 후보 274건)
- sr-registry.json 재구축 → **Pipe-C Step 4에서 완료** (626 SR, 807KB)
- DT 중복 통합 → **Pipe-C Step 2에서 완료** (16그룹 135건, 교차 도메인 9건)
