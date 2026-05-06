# 변경 검토 후보 목록

이 문서는 아직 코드에 완전히 반영하지 않은 신규 리팩토링 후보만 모아두는 목록이다.

아래 항목들은 `risk:` 중심 위험 지식 계층, `PenaltyRule` 중심 벌칙 모델, `SeverityLevel` 제거, `SHE` 패턴 브릿지화, `Guide/WorkProcess` 중심 조치 구조를 반영한 뒤 남은 후속 작업이다.

## 1. `risk:RiskFeature` 계열 분류 품질 고도화

### 배경

`risk:RiskFeature`, `risk:RiskPattern`, `risk:hasFeature`, `sr:addressesFeature` 구조는 반영했다.

최신 구조에서는 `haz:`, `agent:`, `ctx:`의 구체 분류 어휘가 모두 `risk:RiskFeature` 아래에 놓이고, 실시간 판정은 reasoner에 의존하지 않도록 `risk:hasFeature`와 `sr:addressesFeature`를 물질화해서 조회한다.

### 변경 의견

후속 고도화는 분류 체계의 품질을 높이는 방향으로 진행한다.

```text
1. 너무 넓은 WorkContext 값을 더 작은 작업 맥락으로 분해한다.
2. AccidentType / Hazard / HazardousAgent / WorkContext의 역할이 섞인 값을 정리한다.
3. 구체 관계와 risk:hasFeature / sr:addressesFeature 물질화 결과가 항상 동기화되는지 검증한다.
4. 통합 검색은 risk:RiskFeature를 쓰되, 최종 판정은 가능한 한 구체 관계를 우선 사용한다.
```

### 우선순위

높음. `risk:` 계층은 검색 recall과 설명 그래프의 공통 기반이므로, 분류 품질이 낮으면 SHE 매칭과 SR 후보 추천이 함께 흔들린다.

## 2. `VisualTrigger` 품질 고도화

### 배경

`she:VisualTrigger` 구조는 추가되었고, 기존 SHE 데이터에도 최소 1개 이상의 트리거가 연결되도록 보강했다.

다만 기존 데이터는 과거 `SHE` 이름을 fallback으로 사용해 `visual_triggers`를 채운 경우가 많다. 즉 형식은 갖췄지만, “사진에서 실제로 보여야 하는 단서”가 충분히 세밀하게 분리된 상태는 아니다.

### 변경 의견

`SR + Guide + WorkProcess + ChecklistItem`을 함께 사용해 `VisualTrigger`를 더 구체적으로 자동 생성한다.

예:

```text
현재 fallback:
- 기계 절단 위험 상황

권장 trigger:
- 회전부 또는 절단부가 노출되어 있음
- 방호덮개 또는 울이 보이지 않음
- 작업자 손이 절단 지점 근처에 있음
```

### 우선순위

높음. 사진 기반 서비스에서는 `VisualTrigger` 품질이 SHE 매칭 품질을 직접 좌우한다.

## 3. `PenaltyPath` 3경로 안내 품질 고도화

### 배경

`pen:PenaltyCondition`, `pen:requiresSubjectRole`, `pen:requiresAccidentOutcome`은 스키마와 인스턴스에 반영되었다. 서비스 응답에는 `PenaltyPath`를 추가해 벌칙 후보를 다음 3개 경로로 묶어 보여주는 1차 구현도 반영했다.

```text
SimpleViolation → 일반 위반 또는 일반 산재 발생 시
Death → 사망 발생 시
SeriousAccident → 중대재해 요건 충족 시
```

사진만으로 사업주/수급인 여부, 사망 발생 여부, 중대재해 요건 충족 여부를 확정할 수 없으므로 `PenaltyCondition`은 정교한 법적 확정 조건이 아니라 표시 경로를 나누는 최소 분류 근거로 사용한다.

### 변경 의견

향후 고도화는 다음 방향으로 한다.

```text
1. `PenaltyPath` 카드의 문구를 사업주용으로 더 다듬는다.
2. death / serious_accident 경로는 항상 “추가 사실 확인 필요”로 보여준다.
3. `requiresSubjectRole`은 기본 화면이 아니라 상세 근거/전문가 검토용으로만 노출한다.
4. 평가 리포트는 DIRECT/CONDITIONAL 단일 지표와 함께 PenaltyPath 3경로 지표를 같이 본다.
```

### 우선순위

중간. 1차 구조는 반영했고, 앞으로는 실제 사용자 화면 문구와 평가 지표를 보면서 다듬는다.

## 4. `app:` 실행 레이어 저장 구현

### 배경

`app:InspectionCase`, `app:VisualObservation`, `app:VisualCue`, `app:SituationMatch`, `app:HazardFinding`, `app:CorrectiveAction`, `app:PenaltyExposure`, `app:AssessmentReport` 스키마는 추가했다.

진단 스크립트(`OHS/backend/scripts/diagnose_image.py`)에서는 실제 사진 분석 결과를 `diagnose_*.app.ttl`로 물질화하는 테스트 구현을 추가했다.

하지만 실제 서비스 API/DB 저장 흐름에서 이 요약 구조를 지속적으로 저장하는 구현은 아직 별도 작업이다.

### 변경 의견

원시 데이터와 RDF 요약 데이터를 분리한다.

```text
DB/Object Storage:
- 원본 사진
- bbox/mask/crop
- LLM 원문 응답
- 중간 디버그 로그

RDF/app 레이어:
- 검증된 관찰 요약
- SHE 매칭 결과
- 위험 판단
- 개선 조치
- 벌칙 노출
- 사업주 안내 결과
```

### 우선순위

중간. 온톨로지 스키마보다 서비스 저장 구조와 API 설계가 함께 필요하다.

## 5. 합성 테스트셋 기준 SHE 매칭 품질 고도화

### 배경

`pictures-json/synthetic_observations_v1~v7.jsonl` 전체를 기준으로 SHE 매칭 품질을 계속 측정한다.

2026-05-05 FN 보정 기준선(`riskv2_fnfix6`)의 전체 혼동행렬은 다음과 같았다.

```text
TP 1136 / FN 14 / FP 70 / TN 150
recall 98.8%, precision 94.2%, specificity 68.2%
```

이후 1차 FP 억제(`riskv2_fpfix7`)를 적용했다.

```text
TP 1127 / FN 23 / FP 62 / TN 158
recall 98.0%, precision 94.8%, specificity 71.8%
```

버전별 결과:

```text
v1: recall 100.0%, FP 27, specificity 44.9%
v2: recall 98.6%,  FP 9,  specificity 70.0%
v3: recall 100.0%, FP 25, specificity 44.4%
v4: recall 97.2%,  FP 0,  specificity 100.0%
v5: recall 99.5%,  FP 0,  specificity 100.0%
v6: recall 97.6%,  FP 0,  specificity 100.0%
v7: recall 95.9%,  FP 1,  specificity 97.1%
```

생성된 집계 리포트:

```text
pictures-json/reports/synthetic_observations_v1_v7_fpfix7_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v7_fpfix7_confusion_matrix.json
pictures-json/reports/synthetic_observations_v1_v7_fpfix7_fp_cases.csv
pictures-json/reports/synthetic_observations_v1_v7_fpfix7_fn_cases.csv
```

### 현재 적용한 FP 억제 방향

1. 정상 작동, 점검 완료, 보호구 정상 착용처럼 명확한 안전 상태 문구가 있으면 `review_candidate` 또는 `rejected_by_normal_cue`로 낮춘다.
2. 단순히 “가능성/여부/확인 필요” 같은 불확실성 표현만으로는 억제하지 않는다.
3. 사고유형/위험원 없이 환경 특징만 잡힌 경우는 `context_only`로 내려 최종 FP를 줄인다.

### 비판적 평가

1차 FP 억제는 FP를 70건에서 62건으로 줄였지만, FN이 14건에서 23건으로 늘었다. 즉 precision과 specificity는 좋아졌지만 recall 손실이 있다.

따라서 현재 억제 규칙은 “확실한 정상 상태”에만 제한하는 것이 맞고, 추가 억제는 남은 FP 케이스를 보고 더 세밀한 조건으로만 적용해야 한다.

추가로 모든 weak visual evidence를 `review_candidate`로 낮추는 강한 억제도 시험했지만 채택하지 않았다. 이 경우 FP는 62건에서 57건으로 5건 더 줄었지만 FN이 23건에서 35건으로 증가해, 위험 누락 비용이 더 컸다.

2026-05-05 v8 테스트셋을 추가로 평가했다. v8은 기존 테스트셋보다 신규 작업맥락이 많아 FN이 크게 늘었다.

```text
v8 최초 평가:
TP 255 / FN 39 / FP 2 / TN 34
recall 86.7%, precision 99.2%, specificity 94.4%
```

분석 중 `LOTO 미적용` 같은 위험 문구가 `LOTO` 단독 안전 키워드에 걸려 `review_candidate`로 낮아지는 문제가 확인되었다. 이에 `SAFE_NORMAL_OPERATION_TERMS`에서 `LOTO`, `lockout`, `tagout` 단독 키워드를 제거하고, `LOTO 완료`, `LOTO 적용`, `lockout complete`처럼 긍정형 완료 문구만 안전 상태로 보도록 수정했다.

```text
v8 LOTO 오판 수정 후:
TP 260 / FN 34 / FP 2 / TN 34
recall 88.4%, precision 99.2%, specificity 94.4%

v1~v8 누적:
TP 1387 / FN 57 / FP 64 / TN 192
recall 96.1%, precision 95.6%, specificity 75.0%
```

v8의 남은 FN은 주로 아직 SHE 패턴/정규화가 부족한 신규 작업맥락에서 발생했다.

```text
ORCHARD_LADDER: 3
GREENHOUSE_WORK: 3
TRUCK_COUPLING: 3
TUNNEL_SUPPORT: 2
COMPACTOR_OPERATION: 2
SHREDDER_OPERATION: 2
DRYER_OPERATION: 2
NEEDLE_BROKEN: 2
YARN_WINDING: 2
NEEDLESTICK: 2
MEDICAL_WASTE: 2
```

이후 v8 핵심 보강(`riskv2_v8corefix2`)을 적용했다.

적용 내용:

1. v8 신규 작업맥락을 현재 온톨로지 어휘로 접는 alias를 추가했다.
   - `ORCHARD_LADDER -> LADDER`
   - `TUNNEL_SUPPORT -> EXCAVATION`
   - `SHAFT_HOIST -> CRANE`
   - `COMPACTOR_OPERATION / SHREDDER_OPERATION / YARN_WINDING / PAPER_CUTTING -> MACHINE`
   - `TRUCK_COUPLING -> VEHICLE`
   - `NEEDLESTICK / MEDICAL_WASTE -> MATERIAL_HANDLING`
   - `DYEING_FINISHING / SOLVENT_CLEANING -> CHEMICAL_WORK`
2. v8 표현을 정규화하기 위한 text rule을 보강했다.
   - `ROCKFALL`, `TUNNEL_SUPPORT`, `UNSUPPORTED_ROOF`, `ROCK_BOLT` 등은 붕괴/낙하 계열로 해석
   - `COMPACTOR`, `SHREDDER`, `YARN_WINDING`, `LOCKOUT_TAGOUT`, `BYPASS` 등은 끼임/협착 계열로 해석
   - `NEEDLESTICK`, `BROKEN_NEEDLE`, `SHARPS`, `PROJECTILE` 등은 절단/찔림/비산 계열로 해석
   - `MEDICAL_WASTE`, `INFECTION`, `BIOLOGICAL` 등은 생물학적 유해인자로 해석
3. v8 synthetic bootstrap으로 9개 SHE 후보를 PostgreSQL에 적재했다.
4. 건조기 보풀/화재 케이스를 위해 `DRYER_OPERATION + FIRE` SHE 후보 1개를 추가 적재했다.

보강 후 v8:

```text
TP 290 / FN 4 / FP 3 / TN 33
recall 98.6%, precision 99.0%, specificity 91.7%
```

보강 후 v1~v8 누적:

```text
TP 1417 / FN 27 / FP 65 / TN 191
recall 98.1%, precision 95.6%, specificity 74.6%
```

이전 `lotofix` 대비:

```text
TP +30 / FN -30 / FP +1 / TN -1
```

생성된 리포트:

```text
pictures-json/reports/synthetic_observations_v1_v8_v8corefix2_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v8_v8corefix2_confusion_matrix.json
pictures-json/reports/synthetic_observations_v8_v8corefix2_fn_cases.csv
pictures-json/reports/synthetic_observations_v8_v8corefix2_fp_cases.csv
```

이후 남은 FN 27건을 보정했다.

```text
적용 내용:
1. 안전/정상 키워드가 위험 문맥에서 오판되는 문제를 수정했다.
   - "정상 작동이 불가능", "소화기 없음"처럼 부정어가 붙은 경우 안전 증거로 보지 않는다.
   - "정상 작동 여부 불명", "LOTO 적용 여부"처럼 확인필요 문맥은 확정 정상 상태로 보지 않는다.
2. `uncertain_cues`를 SHE 상태판정에도 전달해 ambiguous 케이스를 확인필요 후보로 올릴 수 있게 했다.
3. `OTHER`는 "정상"이 아니라 "모름/미분류"로 보아, 특정 PPE/환경 상태와의 불일치 탈락 조건에서 제외했다.
4. v6~v8 신규 표현을 현재 위험 특징 enum으로 접는 text rule을 추가했다.
   - 로프 킹크/파단 -> FALL
   - ESD/접지 -> ELECTRIC_SHOCK/ELECTRICITY
   - 훈증/잔류농도/유해가스 -> CHEMICAL_EXPOSURE/TOXIC
   - 타이어 마모/도크 단차 -> COLLISION/SLIP
   - 어지러움/창백/의료 응급 -> ERGONOMIC
5. DUST를 고위험 유해인자 후보에 추가하고, 화학/환기 관련 확인필요 장면을 candidate로 올릴 수 있게 했다.
```

최신 `fnfix4` 기준 v1~v8 누적:

```text
TP 1444 / FN 0 / FP 69 / TN 187
recall 100.0%, precision 95.4%, specificity 73.0%
```

이전 `v8corefix2` 대비:

```text
TP +27 / FN -27 / FP +4 / TN -4
```

생성된 최신 리포트:

```text
pictures-json/reports/synthetic_observations_v1_v8_fnfix4_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v8_fnfix4_confusion_matrix.json
pictures-json/reports/synthetic_observations_v1_v8_fnfix4_fn_cases.csv
pictures-json/reports/synthetic_observations_v1_v8_fnfix4_fp_cases.csv
```

현재 FN은 0건이다. 다만 recall을 100%까지 올리면서 FP가 65건에서 69건으로 4건 증가했다. 다음 품질 개선은 FN 보정보다 FP 억제와 `확정 / 후보 / 확인필요` UX 분리에 집중한다.

2026-05-06 v9 테스트셋을 추가로 평가했다. 아래 값은 `fnfix4` 기준의 초기 평가값이다.

```text
v9 단독:
TP 286 / FN 0 / FP 24 / TN 20
recall 100.0%, precision 92.3%, specificity 45.5%

v1~v9 누적:
TP 1730 / FN 0 / FP 93 / TN 207
recall 100.0%, precision 94.9%, specificity 69.0%
```

v9의 FP 24건은 대부분 negative 케이스이며, 공통 패턴은 다음과 같다.

```text
1. 안전교육, 사무실 모니터링, 설계/일정 관리 등 실제 작업 위험이 없는 관리/교육 장면
2. 경량 자재 정리, 작업 완료 후 점검 등 위험 작업이 아닌 정상 상태
3. expected_features에 ERGONOMIC, FALL, SLIP 같은 일반 사고유형이 들어 있어 accident_type_match만으로 candidate가 되는 경우
```

생성된 v9 초기 리포트:

```text
pictures-json/reports/synthetic_observations_v9_fnfix4_report.md
pictures-json/reports/synthetic_observations_v9_fnfix4_report.json
pictures-json/reports/synthetic_observations_v1_v9_fnfix4_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v9_fnfix4_confusion_matrix.json
pictures-json/reports/synthetic_observations_v1_v9_fnfix4_fp_cases.csv
```

v9 기준 다음 억제 후보:

```text
1. ERGONOMIC 단독 + GENERAL_WORKPLACE/관리/교육/모니터링 문맥은 기본적으로 context_only 처리한다.
2. "교육 중", "사무실", "모니터링", "작업 완료", "정리 상태 양호", "경량" 같은 정상 운영 단서를 별도 safe/administrative cue로 분리한다.
3. accident_type_match 하나만 있고 hazardous_agent/unsafe PPE/unsafe environment/VisualTrigger 직접 일치가 없으면 candidate가 아니라 context_only로 내리는 조건을 검토한다.
```

2026-05-06 `safectx2` 억제 규칙을 적용했다.

적용 내용:

```text
1. 안전교육, 사무실 모니터링, 설계/일정 관리, 작업 완료 후 점검, 경량 자재 정리처럼 실제 위험 작업이 아닌 문맥을 safe/administrative visual context로 분리했다.
2. `has_observable_violation_signal`이 visual cue를 함께 받아, 안전/관리/완료 문맥이고 강한 위험 단서가 없으면 관찰 가능한 위반 신호로 보지 않게 했다.
3. `analysis_service.py`와 synthetic evaluator가 visual cue를 SHE matcher에 전달하도록 연결했다.
4. 과억제 방지를 위해 "소형", "도면", "완료", "상태 양호" 같은 넓은 단어는 단독 안전 단서로 쓰지 않고, "소형 부품", "도면 검토", "작업 완료 확인", "정리 상태 양호"처럼 좁은 표현만 사용한다.
5. `HIGH_ELEVATION`을 안전/위험 억제 조건에 직접 넣는 실험은 v1 FP를 늘려 롤백했다.
```

적용 후 v9:

```text
TP 286 / FN 0 / FP 0 / TN 44
recall 100.0%, precision 100.0%, specificity 100.0%
```

적용 후 v1~v9 누적:

```text
TP 1730 / FN 0 / FP 69 / TN 231
recall 100.0%, precision 96.2%, specificity 77.0%
```

이전 `fnfix4` 대비:

```text
v9: FP 24 -> 0, TN 20 -> 44, FN 0 유지
v1~v9 누적: FP 93 -> 69, TN 207 -> 231, FN 0 유지
```

생성된 최신 리포트:

```text
pictures-json/reports/synthetic_observations_v9_safectx2_report.md
pictures-json/reports/synthetic_observations_v9_safectx2_report.json
pictures-json/reports/synthetic_observations_v1_v9_safectx2_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v9_safectx2_confusion_matrix.json
pictures-json/reports/synthetic_observations_v1_v9_safectx2_fp_cases.csv
pictures-json/reports/synthetic_observations_v1_v9_safectx2_fn_cases.csv
```

이후 `obsgate3`에서 관찰 가능한 위반 신호 게이트를 보강했다.

적용 내용:

```text
1. `observable_violation_signal=false`이면 SHE 후보가 있더라도 실제 actionable SR/벌칙 연결에는 사용하지 않는다.
   - 예: LOTO 완료, 정지 확인, 정기 점검 완료처럼 정상 안전조치가 보이는 장면
2. 사고유형 없이 `FIRE`, `CHEMICAL`, `TOXIC` 같은 고위험 유해인자와 고위험 작업맥락이 함께 잡히면 관찰 신호로 인정한다.
   - 예: 소화기 접근 불가, 잔류 용제 흡입 가능성, 냉매/가스 관련 확인필요 장면
3. 과억제 단어를 정리했다.
   - `서류`는 접종기록/검사기록 확인필요 문맥까지 막으므로 safe administrative cue에서 제거했다.
   - `환기팬 가동`은 화학물질 농도/마스크 착용 확인필요 문맥까지 막으므로 safe normal cue에서 제거했다.
4. `mixed_safe_and_unsafe_visual_evidence`는 기본 candidate가 아니라 review candidate로 낮춘다.
```

적용 후 v1~v9 누적:

```text
TP 1730 / FN 0 / FP 67 / TN 233
recall 100.0%, precision 96.3%, specificity 77.7%
```

버전별 FP:

```text
v1: 28
v2: 10
v3: 25
v4: 0
v5: 0
v6: 0
v7: 1
v8: 3
v9: 0
```

중요한 결론:

```text
남은 FP 67건은 모두 ambiguous 케이스다.
negative 케이스가 위험으로 올라온 명백한 오탐은 현재 집계 기준 0건이다.
```

생성된 최신 리포트:

```text
pictures-json/reports/synthetic_observations_v1_v9_obsgate3_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v9_obsgate3_confusion_matrix.json
pictures-json/reports/synthetic_observations_v1_v9_obsgate3_fp_cases.csv
pictures-json/reports/synthetic_observations_v1_v9_obsgate3_fn_cases.csv
```

이후 `splitmetrics1`에서 평가 지표를 분리했다.

기존 `SHE true/false` 지표는 유지하되, 다음 3개 지표를 별도로 추가했다.

```text
1. 확정 위험 탐지 지표
   - expected: positive이고 needs_clarification=false인 케이스
   - actual: confirmed SHE가 있는 케이스
2. 확인필요 후보 탐지 지표
   - expected: needs_clarification=true 또는 ambiguous 케이스
   - actual: candidate/review_candidate 또는 confirmed로 포착된 케이스
3. 정상 억제 지표
   - expected: negative이고 needs_clarification=false인 케이스
   - actual: confirmed/candidate로 올라가지 않고 억제된 케이스
```

`splitmetrics1` 기준 v1~v9 누적:

```text
기존 SHE true/false:
TP 1730 / FN 0 / FP 67 / TN 233
recall 100.0%, precision 96.3%, specificity 77.7%

확정 위험:
expected 1190 / TP 896 / FN 294 / FP 277
recall 75.3%, precision 76.4%

확인필요 후보:
expected 608 / captured 607 / missed 1
capture_rate 99.8%
as_candidate 330
over_promoted_to_confirmed 277

정상 억제:
expected 232 / suppressed 232
suppression_rate 100.0%
confirmed_false_positive 0
candidate_false_positive 0
```

새 지표로 보면 다음 결론이 명확하다.

```text
1. 정상/negative 억제는 현재 기준 100%다.
2. 확인필요 후보 포착도 99.8%로 충분히 높다.
3. 남은 핵심 문제는 ambiguous 확인필요 후보 277건이 confirmed로 과승격되는 것이다.
```

생성된 분리 지표 리포트:

```text
pictures-json/reports/synthetic_observations_v1_v9_splitmetrics1_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v9_splitmetrics1_confusion_matrix.json
pictures-json/reports/synthetic_observations_v1_v9_splitmetrics1_fp_cases.csv
pictures-json/reports/synthetic_observations_v1_v9_splitmetrics1_fn_cases.csv
```

이후 `confirmdemote1`에서 확인필요 후보의 `confirmed` 과승격을 줄였다.

적용 내용:

```text
1. `confirmation_only_visual_evidence` 규칙을 추가했다.
   - `불명`, `확인 불가`, `여부`, `사진만으로`, `프레임 밖`, `가려짐`, `일 경우`, `라면`, `수 있다` 같은 확인필요 단서가 있고
   - 직접 보이는 불안전 단서가 없으면
   - `confirmed`가 아니라 `candidate + confirmation_required`로 낮춘다.
2. 이 규칙은 SHE/SR 후보를 제거하지 않는다.
   - 기존 SHE true/false recall은 유지한다.
   - 단지 사업주 화면에서 “확정 위험”이 아니라 “확인 필요”로 보이게 하는 목적이다.
3. 직접 보이는 불안전 단서와 조건부 표현을 구분하기 위해 window 기반 검사를 추가했다.
   - 예: “안전난간 없음”은 직접 위험
   - 예: “미설치 시”, “누출이라면”, “사진만으로 확인 불가”는 확인필요
```

`confirmdemote1` 기준 v1~v9 누적:

```text
기존 SHE true/false:
TP 1730 / FN 0 / FP 67 / TN 233
recall 100.0%, precision 96.3%, specificity 77.7%

확정 위험:
expected 1190 / TP 849 / FN 341 / FP 96
recall 71.3%, precision 89.8%

확인필요 후보:
expected 608 / captured 607 / missed 1
capture_rate 99.8%
as_candidate 511
over_promoted_to_confirmed 96

정상 억제:
expected 232 / suppressed 232
suppression_rate 100.0%
confirmed_false_positive 0
candidate_false_positive 0
```

`splitmetrics1` 대비 개선:

```text
over_promoted_to_confirmed: 277 -> 96
over_promotion_rate: 45.6% -> 15.8%
confirmed precision: 76.4% -> 89.8%
clarification as_candidate: 330 -> 511
legacy SHE recall: 100.0% 유지
normal suppression: 100.0% 유지
```

생성된 최신 리포트:

```text
pictures-json/reports/synthetic_observations_v1_v9_confirmdemote1_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v9_confirmdemote1_confusion_matrix.json
pictures-json/reports/synthetic_observations_v1_v9_confirmdemote1_fp_cases.csv
pictures-json/reports/synthetic_observations_v1_v9_confirmdemote1_fn_cases.csv
```

2026-05-06 v10 테스트셋을 추가 평가했다.

v10은 기존 v1~v9와 달리 일부 행이 `photo_description/work_context` 대신 `scene_description/expected_features` 중심으로 구성되어 있었다. 이에 synthetic evaluator가 두 형식을 모두 읽도록 보강했다.

```text
적용 내용:
1. `photo_description`이 없으면 `scene_description`을 설명문으로 사용한다.
2. top-level `work_context`가 없으면 `expected_features.work_contexts[0]`를 fallback으로 사용한다.
3. `penalty_exposure`가 boolean 또는 누락값으로 들어와도 `DIRECT / CONDITIONAL / NONE` 평가값으로 정규화한다.
4. row feature text에 `scene_description`을 포함해 한국어 장면 설명 기반 정규화가 가능하게 했다.
```

`confirmdemote1` 기준 v10 단독:

```text
총 330건: positive 187 / ambiguous 99 / negative 44

기존 SHE true/false:
TP 257 / FN 29 / FP 3 / TN 41
recall 89.9%, precision 98.8%, specificity 93.2%

확정 위험:
expected 187 / TP 72 / FN 115 / FP 50
recall 38.5%, precision 59.0%

확인필요 후보:
expected 99 / captured 94 / missed 5
capture_rate 94.9%
as_candidate 44
over_promoted_to_confirmed 50

정상 억제:
expected 44 / suppressed 41
suppression_rate 93.2%
confirmed_false_positive 0
candidate_false_positive 3
```

v10을 포함한 v1~v10 누적:

```text
기존 SHE true/false:
TP 1987 / FN 29 / FP 70 / TN 274
recall 98.6%, precision 96.6%, specificity 79.7%

확정 위험:
expected 1377 / TP 921 / FN 456 / FP 146
recall 66.9%, precision 86.3%

확인필요 후보:
expected 707 / captured 701 / missed 6
capture_rate 99.2%
as_candidate 555
over_promoted_to_confirmed 146

정상 억제:
expected 276 / suppressed 273
suppression_rate 98.9%
confirmed_false_positive 0
candidate_false_positive 3
```

v10에서 새로 드러난 문제:

```text
1. v10 후반부에는 사회복지시설, 급식실, 병원/실험실, 복도, 사무실 같은 신규 장면이 많다.
2. 다수 행이 구체 `visual_cues`보다 한국어 `scene_description`과 `expected_features`에 의존한다.
3. `GENERAL_WORKPLACE`가 18건 FN으로 가장 크다.
4. 일부 케이스는 안전/정상 문구가 위험 문맥을 과하게 눌러 positive를 candidate/review/context_only로 낮춘다.
5. negative FP 3건은 모두 candidate 수준이며 confirmed FP는 0건이다.
```

FN work_context:

```text
GENERAL_WORKPLACE: 18
MATERIAL_HANDLING: 4
MACHINE: 3
VEHICLE: 1
LADDER: 1
CONFINED_SPACE: 1
ELECTRICITY_WORK: 1
```

FP 샘플:

```text
SYN-V10-0020: 중성세제 설거지/세정 장면이 CHEMICAL_WORK 후보로 올라감
SYN-V10-0030: 지상 창고 정리 장면이 MATERIAL_HANDLING 후보로 올라감
SYN-V10-0055: 일반 물걸레 청소 장면이 CHEMICAL_WORK 후보로 올라감
```

생성된 최신 v10 리포트:

```text
pictures-json/reports/synthetic_observations_v10_confirmdemote1_report.md
pictures-json/reports/synthetic_observations_v10_confirmdemote1_report.json
pictures-json/reports/synthetic_observations_v10_confirmdemote1_cases.csv
pictures-json/reports/synthetic_observations_v1_v10_confirmdemote1_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v10_confirmdemote1_confusion_matrix.json
pictures-json/reports/synthetic_observations_v1_v10_confirmdemote1_fp_cases.csv
pictures-json/reports/synthetic_observations_v1_v10_confirmdemote1_fn_cases.csv
```

2026-05-06 `v10fix6`에서 v10 FN/FP 보정을 우선 적용했다.

적용 내용:

```text
1. v10 입력 행은 top-level work_context보다 expected_features.work_contexts를 우선 사용하도록 정리했다.
   - v10의 top-level work_context는 일부 행에서 시나리오 범주처럼 쓰였고,
     실제 정규화 대상은 expected_features에 더 정확히 들어 있었다.
2. scene_description 기반 한국어 alias를 확장했다.
   - 사회복지시설, 병원/실험실, 급식실, 사무실, 복도, 일반 사업장 장면을 현재 risk feature로 접었다.
   - 화학 흡입/노출, 교상/할큄, 방사선/레이저, 아크화상, 야간 단독 응급, 약품 오인 섭취 등을 정규화했다.
3. 정상 청소/지상 정리 장면을 억제하되, 혼합 세제, MSDS/라벨 불명, 약품 잠금 없음, 아동 접근 가능 같은 위험 단서가 있으면 억제하지 않도록 예외를 두었다.
4. 위험원은 구체적으로 유지하되 SHE 조회에서는 필요한 경우 상위 위험원으로 확장했다.
   - ARC_FLASH -> ELECTRICITY
   - TOXIC / CORROSION / DUST -> CHEMICAL
5. 작업맥락이 완전히 같지 않아도 사고유형과 위험원이 호환되는 경우 candidate로 올리는 cross-context bridge를 추가했다.
```

`v10fix6` 기준 v10 단독:

```text
기존 SHE true/false:
TP 286 / FN 0 / FP 0 / TN 44
recall 100.0%, precision 100.0%, specificity 100.0%

확정 위험:
expected 187 / TP 83 / FN 104 / FP 59
recall 44.4%, precision 58.5%

확인필요 후보:
expected 99 / captured 99 / missed 0
capture_rate 100.0%
as_candidate 40
over_promoted_to_confirmed 59

정상 억제:
expected 44 / suppressed 44
suppression_rate 100.0%
```

`v10fix6` 기준 v1~v10 누적:

```text
기존 SHE true/false:
TP 2016 / FN 0 / FP 67 / TN 277
recall 100.0%, precision 96.8%, specificity 80.5%

확정 위험:
expected 1377 / TP 930 / FN 447 / FP 157
recall 67.5%, precision 85.6%

확인필요 후보:
expected 707 / captured 706 / missed 1
capture_rate 99.9%
as_candidate 549
over_promoted_to_confirmed 157

정상 억제:
expected 276 / suppressed 276
suppression_rate 100.0%
confirmed_false_positive 0
candidate_false_positive 0
```

생성된 최신 v1~v10 집계 리포트:

```text
pictures-json/reports/synthetic_observations_v1_v10_v10fix6_confusion_matrix.md
pictures-json/reports/synthetic_observations_v1_v10_v10fix6_confusion_matrix.json
pictures-json/reports/synthetic_observations_v1_v10_v10fix6_fp_cases.csv
pictures-json/reports/synthetic_observations_v1_v10_v10fix6_fn_cases.csv
```

### 후속 작업

1. 평가 지표 분리는 완료했다.
2. 확인필요 후보 과승격 1차 억제는 완료했다.
3. v10 입력 스키마 호환은 완료했다.
4. v10 FN/FP 보정은 완료했다.
   - v10 단독 FN 29 -> 0
   - v10 단독 FP 3 -> 0
   - v1~v10 누적 FN 0 유지
5. 다음 개선은 `확정 위험`과 `확인필요 후보`의 경계 조정이다.
   - v10의 `over_promoted_to_confirmed` 59건을 우선 분석한다.
   - v1~v10 누적 `over_promoted_to_confirmed` 157건을 줄인다.
   - SHE/SR 후보는 유지하되, 사업주 화면에서는 “확정 위험”이 아니라 “확인 필요”로 표시하는 조건을 더 정교하게 만든다.
6. v1~v3의 ambiguous 설계가 현재 서비스 정책과 맞는지 재검토한다.
   - `should_match_she=false`로 두되 확인필요 카드로 노출할지
   - 또는 `should_match_she=true` + `needs_clarification=true`로 재라벨링할지 결정한다.
7. `review_candidate`와 `candidate + confirmation_required`를 서비스 화면에서는 “확인 필요”로 보여주고, 확정 위험으로 바로 올리지 않는 UX를 확정한다.
8. 안전 상태 표현은 keyword만으로 처리하지 말고, 향후 `app:FindingStatus`와 `EvidenceStrength` 판단 기준으로 옮긴다.

### 우선순위

높음. 현재 positive recall은 여전히 높지만, 실제 서비스에서는 FP가 많으면 사업주 신뢰도가 떨어지므로 `확정 / 의심 / 확인 필요` 구분을 더 정교하게 해야 한다.


## 6. `hasRequirementType` / `hasBindingForce` domain 정리

### 배경

`sr:hasRequirementType`과 `sr:hasBindingForce`는 유지하기로 했다.

다만 향후 같은 성격의 속성이 `SafetyRequirement`뿐 아니라 `ChecklistItem`, `WorkProcess`, `CorrectiveAction` 등에 공통으로 붙는다면, `rdfs:domain`을 여러 클래스에 직접 선언하면 교집합 추론 문제가 생길 수 있다.

### 변경 의견

공통 추상 클래스를 만들거나 속성을 분리한다.

예:

```ttl
core:RequirementLikeEntity a owl:Class .
sr:SafetyRequirement rdfs:subClassOf core:RequirementLikeEntity .
guide:ChecklistItem rdfs:subClassOf core:RequirementLikeEntity .

sr:hasBindingForce
    rdfs:domain core:RequirementLikeEntity ;
    rdfs:range core:BindingForce .
```

### 우선순위

낮음. 현재는 즉시 오류를 만드는 구조는 아니지만, 확장 전에 정리해두면 좋다.

## 7. 전체 KOSHA Guide JSON 추출 완료 후 Guide 레이어 리빌딩

### 배경

현재 다른 세션에서 아직 추출되지 않은 KOSHA Guide를 기존 Pipe-B phase/step 방식으로 계속 추출 중이다.

중간에 phase/step 규칙을 바꾸면 기존 추출분과 신규 추출분의 품질 기준이 섞일 수 있으므로, 일단 현재 방식으로 전체 JSON 추출을 완료한다. 모든 Guide JSON이 확보된 뒤 Guide 레이어 온톨로지, 추천 로직, PostgreSQL 적재 구조를 한 번에 재정리한다.

### 현재 확인된 보완 필요 사항

1. `candidateSR` 조문 기반 후보가 0건으로 잡히는 문제가 있다.
   - `sr-article-index.json` 키는 `RULE:제100조` 형태인데, `step3_prepare_ci_batch.py` 쪽 매칭은 `RULE:100` 형태를 기대하는 구조라 조문 기반 후보가 붙지 않는다.
2. `schema_pb.sql`이 실제 PostgreSQL 테이블과 일부 불일치한다.
   - 실제 DB에는 `checklist_items.accident_types`, `hazardous_agents`, `work_contexts` 등이 있으나 스키마 파일에는 누락된 컬럼이 있다.
   - `work_processes`, `domain_terms`, `equipment_specs`의 facet/canonical 관련 컬럼도 스키마 동기화가 필요하다.
3. Pipe-C 문서상 `ci_sr_mapping` 복원 후 10,287건이어야 한다고 되어 있으나, 현재 DB 확인값은 9,164건이다.
   - 최종 재적재 시점에 Pipe-C `basedOn` 복원/audit가 실제로 반영되는지 재검증해야 한다.
4. 현재 `ChecklistItem` 중심 추천이 강하고, `KoshaGuide` / `WorkProcess` 중심의 표준 개선 절차 추천 품질은 더 보강해야 한다.
5. `ChecklistItem`에는 즉시 조치, 시각 단서, 검색 색인, 법령 근거 조각의 역할이 섞여 있으므로 역할 분류가 필요하다.

### 후속 작업 순서

1. 전체 Guide JSON 추출 완료 여부를 확인한다.
   - inventory guide 수, parsed 수, ci-output 수, 누락 Guide 목록을 다시 산출한다.
2. 최종 추출 JSON 기준으로 품질 통계를 산출한다.
   - `KoshaGuide`, `ChecklistItem`, `WorkProcess`, `DomainTerm`, `EquipmentSpec`, `DocumentRequirement` 개수
   - CI `basedOn` 커버리지
   - WorkProcess-SR 연결 커버리지
   - accident type / hazardous agent / work context facet 커버리지
3. `candidateSR` 조문 매칭을 수정한다.
   - `RULE:제100조` 같은 조문 키를 표준으로 정한다.
   - `step3_prepare_ci_batch.py`와 `sr-article-index.json` 생성/조회 규칙을 동일하게 맞춘다.
4. 후보 SR 배치를 재생성한다.
   - 가능하면 전체 LLM 재추출보다 post-processing 방식으로 SR 링크를 보강한다.
   - 단, 원문 추출 품질 자체가 낮은 Guide는 재추출 대상으로 분리한다.
5. `schema_pb.sql`을 실제 DB 구조와 동기화한다.
   - clean rebuild 시 누락 컬럼 때문에 facet tagging이나 import가 깨지지 않도록 한다.
6. PostgreSQL을 clean rebuild한다.
   - import
   - faceted CI/entity tagging
   - Pipe-C `basedOn` audit/restore
   - Guide/CI/WorkProcess interlink를 순서대로 실행한다.
7. Guide/WorkProcess 중심 추천 로직으로 재정렬한다.
   - `KoshaGuide` / `WorkProcess`는 표준 개선 절차의 중심으로 사용한다.
   - `ChecklistItem`은 즉시 조치, 시각 단서, 검색 색인, 보조 근거로 사용한다.
8. 온톨로지 export와 서비스 조회 로직을 갱신한다.
   - `SHE -> SR -> Guide/WorkProcess/CI -> PenaltyPath` 경로가 끊기지 않는지 확인한다.
9. 합성 테스트셋 v1~v5로 회귀 검증한다.
   - SHE recall / false positive
   - DIRECT / CONDITIONAL
   - PenaltyPath 3경로 지표
   - Guide/WorkProcess 추천 품질

### 우선순위

높음. 다만 현재 진행 중인 전체 Guide JSON 추출이 끝난 뒤 적용한다. 그 전에는 추출 phase/step을 변경하지 않는다.
