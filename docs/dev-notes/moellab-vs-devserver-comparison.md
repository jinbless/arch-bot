# moellab.info/ohs "위험요소" 섹션 vs 우리 dev server — 8개 사진 비교 (2026-05-19)

## Background

**moellab.info/ohs는 현재 프로젝트의 초안.** 사용자 비교 대상:
- ✅ **"위험요소" 섹션 (`hazards[]`) 만** — GPT가 직접 사진에서 생성한 부분
- ❌ "안전지침 & 법조항" (`related_norms`, `legal_reference`) — 무시
- ❌ "체크리스트" (`checklist`) — 무시
- ❌ "관련 자료" (`related_guides`, `resources`) — 무시

사용자 가설:
> "moellab의 위험요소 식별이 우리보다 더 정확해 보임. 그렇다면 GPT의 위험요소 + 예방조치를 받아서, 그 위험요소와 관련된 우리 Guide를 추천하고, Guide 내 (정형) 예방조치를 같이 보여주는 구조가 어떨까?"

## moellab 위험요소 (hazards[]) 8개 사진 정량 분석

| 사진 | overall | hazards 수 | 식별 결과 |
|---|---|---:|---|
| 고소대작업 | high | 4 | 추락 + 낙하물 + 중량물 + 인간공학 |
| 안전대길이 | high | 4 | 추락 + 낙하물 + 전도 + 중량물 |
| 영세제조업 | high | **6** | 끼임/협착 + 절단 + 전도 + 유해물질 + 감전 + 근골격계 |
| 음식점주방 | high | **6** | 화재/폭발 + 절단 + 전도 + 화상 + 유해물질 + 인간공학 |
| 지게차 | high | 5 | 충돌 + 낙하물 + 전도 + 중량물 + 인간공학 |
| 최근대전화재바닥에기름 | high | 3 | 전도 + 유해물질 + 감전 |
| 포크레인주변작업자 | high | 4 | 낙하물 + 충돌 + 끼임 + 전도 |
| 프레스 | high | 5 | 끼임/협착 + 절단/베임 + 전도 + 감전 + 유해물질 |

**합계: 37 hazards / 8 사진 (평균 4.6 / 사진)**

### 위험요소 항목별 schema (GPT 직접 생성)

각 hazard는 다음 5개 필드만 (사용자 비교 범위):
- `name`: 자연어 카테고리 ("끼임/협착", "전도/미끄럼" 등)
- `risk_level`: high / medium / low
- `location`: 사진 어디에서 식별됐는지 ("사진 중앙부 금형(슬라이드) 및 돌출부 주변")
- `description`: 왜 위험한지 자연어 설명 (50-200자)
- `preventive_measures[]`: GPT가 제안한 예방조치 (3-5개)

→ **모두 GPT-4.x 한 번의 호출로 한국어 자연어 직접 생성**.

## 위험요소 식별 정확성 평가 (37/37 합리적)

8개 사진 × 약 5개 = 37 hazards를 검토했을 때:

1. **모든 식별 합리적** — 사진 환경에 부합. 명백한 false positive 없음
2. **자연어 카테고리가 직관적** — "끼임/협착", "전도/미끄럼", "낙하물", "추락", "화상" 등 한국 산업안전 도메인 표준 용어
3. **risk_level이 적절** — 추락/끼임/충돌은 high, 인간공학/유해물질은 medium-low
4. **location 정확** — 사진의 어느 부분에 위험이 있는지 구체 명시
5. **description 풍부** — "왜 위험한지"를 작업자/사진 상황 결합해 설명

### preventive_measures 평가 (GPT 직접 제안)

3-5개씩 제공되며 매우 실용적:

#### 예시: 프레스 끼임/협착의 GPT preventive_measures
1. 기계가동부(금형 등)에 안전커버·인터록 장치 설치 및 정상 작동 여부 매일 점검
2. 비상정지장치 설치/최적화 및 동작 상태 확인
3. 기계 조작시 충분한 교육 실시 및 지정된 절차만 따를 것
4. 운전 중 손, 신체 접근 금지 주의 표지 및 경고문 설치

#### 예시: 포크레인주변 낙하물의 GPT preventive_measures
1. 굴삭기 및 크레인 작업 시 중량물 하부 출입 금지
2. 작업 구역 내 접근 제한을 위한 바리케이드 및 경고 표지 설치
3. 작업자는 작업구역 내에서 헬멧 등 보호구 필수 착용
4. 작업 전후 중량물 고정 및 버킷 내 적재물 확인
5. 기계와 작업자 간 신호체계 확립 및 감독자 배치

**특징**:
- 도메인 일반 상식 + 사진 context 결합
- 법령 인용 없음 (KOSHA Guide 조항 인용 없음)
- 한국 사업주가 즉시 이해 가능한 행동 지침
- 그러나 **항목별로는 일반적** — "정기 점검", "안전모 착용" 같은 표준 절차 위주

## 우리 dev server의 "위험요소" 표시 약점

[t4-77-she-manual-review-results.md](t4-77-she-manual-review-results.md) Step 2 결과로 입증:

| 측면 | 우리 현재 | moellab |
|---|---|---|
| 위험요소 표시 형식 | code-based (work_context=PRESS, accident_type=BODY_CAUGHT 등) | **자연어** ("끼임/협착") |
| 위험요소 식별 chain | observations → risk_features → SHE → SR → ... | **단일 GPT 호출** |
| 매칭 안정성 | SHE matcher 회귀 (Step 2: -10.17%p VETOED) | GPT 직접 출력 (회귀 없음) |
| 사진 location 표시 | risk_features의 metadata에 없음 | hazard.location 명시 |
| 위험요소별 예방조치 | Guide의 procedure (간접) | hazard.preventive_measures (직접) |

→ 사용자가 moellab을 더 정확하다고 느낀 본질: **GPT 자연어 출력의 직관성 + 회귀 없는 안정성**.

## 사용자 제안 architecture 검증

> **"GPT 위험요소 + GPT 예방조치 → 그 위험요소와 관련된 우리 Guide 추천 → Guide 내 예방조치 같이 표시"**

### 단계별 검증

**1단계 — GPT 위험요소 식별 그대로 활용**

✅ 가능. 현재 우리도 OpenAI Vision API 호출 중 (Layer 0). schema만 moellab 스타일로 변경:
```
현재: ONTOLOGY_OBSERVATION_SCHEMA → risk_feature_candidates
변경: HAZARD_DIRECT_SCHEMA → hazards[] (name, risk_level, location, description, preventive_measures)
```

**2단계 — 위험요소 → 우리 Guide 추천**

✅ 가능. hazard.name (예: "끼임/협착")을 우리 catalog 529 codes에 매핑:
- "끼임/협착" → accident_type=BODY_CAUGHT (alias 이미 존재, T1.C `alias_candidate_meta.jsonl`)
- "전도/미끄럼" → accident_type=SLIP_FALL
- "추락" → accident_type=FALL_FROM_HEIGHT
- ...

매핑 후 우리 ontology reasoning 활용:
- catalog code → SR (penalty_accuracy +27.16%p 검증)
- code → Guide (kosha-guides parsed 1,038 PDFs)
- Guide → CI (relatedChecklistCue)

**3단계 — Guide 내 예방조치 표시**

✅ 우리 backend의 `standard_procedures` 필드를 활용. 추가:
- hazard마다 매핑된 Guide의 procedure section 표시
- 사용자 화면: GPT preventive (general) + Guide procedure (formal/법령 기반) 병기

**4단계 — SHE matcher 의존도 감소**

✅ 핵심 가치. SHE matcher 회귀 문제 (Step 2 -10.17%p) **우회 가능**:
- 위험요소 → Guide 직접 매핑 (hazard.name → catalog → Guide)
- SHE는 보조 track (matcher refactor 완료 후 fallback)

### 결정 — 두 layer 동시 표시 가치

| 출처 | 강점 | 약점 |
|---|---|---|
| GPT preventive_measures | 사진 context 반영, 즉시 이해 | 일반적, 법령 인용 없음 |
| Guide procedure | 법령 기반, 정형, 인용 가능 | 일반화된 절차, 사진 context 약함 |

→ **두 가지 동시 표시가 정보 가치 최대화**. 사용자 화면:
```
[위험요소] 끼임/협착 (high)
  위치: 사진 중앙부 금형(슬라이드) 주변
  설명: ...
  
  ▣ 즉시 점검 사항 (GPT 자연어 제안)
    1. 안전커버·인터록 정상 작동 확인
    2. 비상정지장치 작동 상태 확인
    ...
  
  ▣ KOSHA Guide 예방조치 (B-M-36-2026 프레스 위험방지)
    절차 1: ...
    절차 2: ...
    근거 법조항: 산안법 시행규칙 제103조
```

## 권장 architecture pivot

```
사진 입력
  ↓
OpenAI Vision (HAZARD_DIRECT_SCHEMA)
  └─ hazards[] (name, risk_level, location, description, preventive_measures[])
  ↓
hazard.name → catalog 529 codes (T1.C alias 활용)
  ↓
catalog code → 우리 Guide 추천 (ontology reasoning)
  └─ hazard마다 top-N Guide
  ↓
응답 통합:
  - hazards[] (GPT 자연어, moellab 스타일)
  - related_guides_by_hazard[] (우리 ontology 추천)
  - guide_procedures[] (각 Guide의 정형 procedure)
  - penalty_paths[] (우리 3-경로 차별점 유지)
```

핵심 효과:
- **위험요소 식별 정확성** = moellab 수준 (GPT 그대로)
- **Guide 추천 정확성** > moellab (우리 ontology, moellab은 title_match)
- **법령/벌칙 매핑** > moellab (우리 penalty 3-경로 + Tier 4 SWRL)
- **SHE matcher 회귀 부담** ↓ (Step 2 -10.17%p 우회)

## 다음 sprint candidate

새 sprint plan 후보: `docs/workplans/hazard-direct-architecture-pivot.md`

| Phase | 작업 | 소요 |
|---|---|---|
| Phase 1 | HAZARD_DIRECT_SCHEMA 정의 + GPT prompt 갱신 | 3일 |
| Phase 2 | hazard.name → catalog code alias 매핑 (T1.C 확장) | 1주 |
| Phase 3 | hazards-based Guide 추천 layer (기존 SHE-based와 병행) | 1주 |
| Phase 4 | 응답 schema 확장 (hazards + guides + procedures + penalty 통합) | 3일 |
| Phase 5 | A/B 검증 + Gate 3 + 정본 문서 갱신 | 3일 |

기존 [she-matcher-broadness-refactor.md](../workplans/she-matcher-broadness-refactor.md)와의 관계:
- **본 sprint 우선 진행** (hazard-direct가 SHE 의존도를 낮춤)
- SHE matcher refactor는 Phase 3 보조 track으로 통합 또는 후행

## Resources

- moellab 8개 응답 raw (위험요소 추출용, 외부 서비스 캡처): `.compare_moellab/*.json` (git 미추적)
- 우리 backend schema: `serving-team/08-app/backend/app/models/analysis.py` (`AnalysisResponse`)
- 우리 alias 인프라: `data-team/05-enrichment/runtime-artifacts/alias_candidate_meta.jsonl` (T1.C)
- 관련 dev-notes:
  - [t4-77-she-manual-review-results.md](t4-77-she-manual-review-results.md) — SHE matcher 회귀 입증
  - [F.1-auto-register-aliases.md](F.1-auto-register-aliases.md) — alias closed loop
  - [phase-g.3-penalty-rule-index-pg.md](phase-g.3-penalty-rule-index-pg.md) — penalty 차별점
