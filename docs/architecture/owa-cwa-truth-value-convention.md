# OWA→CWA 진리값 규약 — matcher 누락 차원 의미론 (MATCH-2 / F1·F3·F24)

> 작성: 2026-06-12. 비판 검토(49-agent, 30 findings)에서 확정된 "미지(unknown)와
> 부재(absent)의 미구분" 격차(F1)의 교정 규약. she_matcher·analysis_pipeline의
> 모든 부정(negation) 사용 지점은 이 문서를 참조해야 하며, 신설 시 §4 인벤토리에
> 등록한다. Track A의 물질화 의미론 계약(C1) 문서가 이 규약을 포섭할 예정.

## 1. 문제 — 열린세계 추출을 닫힌세계 매칭이 소비할 때

Vision LLM 추출(Layer 0)은 **열린세계(OWA)**다: 스키마에 minItems가 없고 빈 배열이
정상 출력이므로, "사고유형이 안 나왔다"는 것은 *사고가 없다*가 아니라 *모른다*일
수 있다. 그러나 매칭(Layer 2, PG)은 **닫힌세계(CWA)** SQL이다: 누락은 자연히
`NOT EXISTS`로 동작한다. 이 경계에서 규약 없이 부정을 쓰면 **negation-as-failure
(NAF)가 미지를 반증으로 변환**해 안전 도메인의 FN-최우선 원칙과 충돌한다.

## 2. 진리값 — 3치 구분

| 값 | 의미 | 데이터 신호 |
|---|---|---|
| **observed-positive** | 위험 신호가 관찰됨 | accident_types/hazardous_agents/unsafe ppe·env 추출됨 |
| **observed-negative** | *정상*이 관찰됨 (확인된 부재) | NORMAL_PPE 등 명시적 정상 코드, safe-normal 시각 증거 |
| **unobserved** | 미지 — 추출이 안 됐을 뿐 | 해당 축 빈 배열 (스키마상 정상 출력) |

## 3. 규약 (normative)

1. **미지는 중립이다.** unobserved 차원은 매칭 가산도 감점도 하지 않는다.
   매칭은 관찰된 차원의 일치로만 진행한다 (min_matched_dims 철학과 정합).
2. **반증(reject)은 observed-negative 증거가 있을 때만 닫는다.** "미추출"만으로
   match를 reject/no_penalty로 닫는 것은 금지. 단 *FP 억제를 위한 의도적 NAF*는
   허용하되 §4에 등록하고, 닫는 대신 **상한 강등**(candidate +
   `confirmation_required`)을 우선 검토한다.
3. **부재 기반 억제의 status_reasons는 출처를 구분한다.**
   `…_without_accident_signal` 단일 라벨 대신:
   - 증거 반증: `normal_evidence_refutation` (observed-negative 동반)
   - 부재 반증: `absence_of_signal` (unobserved만 근거 — 약한 부정)
4. **단조성: 정보가 늘면 결론이 사라지면 안 된다.** 입력 차원이 추가 추출됐다는
   이유만으로 기존 매치가 강등되는 분기는 금지 (F3 — OTHER-context 비단조 강등이
   전례; MATCH-1이 교정). 와일드카드(OTHER) 차원은 모든 축에서 일관되게
   "항상 양립"으로 처리한다 (현행: ppe/env는 와일드카드, work_context만 예외였음).
5. **전 축 미추출은 "안전(low/green)"이 아니라 "판정 불능"으로 라우팅한다 (F24).**
   WS-SAFETY-1이 `_overall_risk_level`을 `unknown`으로 교정해 이미 충족. 추가로
   전-빈-추출을 SHE-무매치와 구분하는 `extraction_degraded` 관측 신호는 WS-OBS-3
   소관(안전 라우팅엔 영향 없음). minItems 강제는 금지 — NEGATIVE(무위험) 사진의
   빈 배열은 정당.

## 4. NAF 사용 지점 인벤토리 (she_matcher.py / analysis_pipeline.py)

| 지점 | 분류 | 규약 적합성 | 비고 |
|---|---|---|---|
| `rejected_by_normal_cue` ①: `safe_normal_visual and not accident_types and not unsafe_state` (she_matcher:625) | 혼합 (observed-negative 시각 증거 + 부재) | 조건부 허용 — safe 증거가 동반되므로 §3.2 의도적 NAF. FP억제 트레이드오프 실측 기록: refactor-candidates.md:536-548 | MATCH-2: 라벨 분리(§3.3) 적용 대상 |
| `rejected_by_normal_cue` ②: `normal_cue and not accident_types and not unsafe_ppe` (she_matcher:656) | 혼합 (observed-negative PPE + 부재) | 동상 | 동상 |
| wc 강등: `"work_context" not in matched_dims and work_contexts` (she_matcher:637) | 비단조 (§3.4 위반) | **부적합 — MATCH-1이 OTHER 예외 + candidate 상한으로 교정** | F3 |
| `has_observable_violation_signal` (she_matcher:447) → SR/Guide/penalty 게이트 (analysis_pipeline:254-293) | 부재 반증 (양성 신호 요구) | 조건부 허용 — penalty FP 억제는 법적 load-bearing 설계(docstring 명시). 단 결과 표시는 "무위험"이 아닌 "미판정"이어야(SAFETY-1/4와 접속) | F1 영향 반경 |
| 빈 추출 → overall_risk_level (analysis_pipeline:1289-1291) | 부재→`unknown`(녹색 아님) | **적합 — WS-SAFETY-1이 `low`→`unknown` 교정 완료.** `_summary`(1302-1309)가 "판정 불가·안전 보장 아님" 명시 | F24 (해소) |

## 5. 집행 (현황 2026-06-12)

- **MATCH-1(F3): §3.4 — 적용·검증 중.** `_classify_match_status:637`의 OTHER-context
  강등 예외 + candidate 상한(confirmation_required). v5 baseline 대비 회귀 게이트 중.
  **SAFETY-1이 커버 안 한 유일한 잔존 matcher 결함이었음.**
- **MATCH-2(F1+F24): 안전 핵심은 WS-SAFETY-1(S0 머지)에 이미 흡수됨.**
  - F24 green-collapse: `_overall_risk_level`이 not_determined/needs_clarification를
    `low`가 아닌 `unknown`으로 반환(:1291) → 전-빈-추출도 녹색 아님. **해소.**
  - F1 NAF: `rejected_by_normal_cue` 두 분기는 positive 안전 증거(safe_normal_visual
    /normal_cue) 동반 = §3.2 "증거 반증"(허용). finding_status가 unknown으로 처리
    (confirmed-safe 아님). **안전 방향 해소.**
  - 잔존(안전 아님): 전-빈-추출 vs SHE-무매치를 구분하는 `extraction_degraded`
    **관측 신호** — 둘 다 unknown으로 올바르게 가되 로그상 원인 구분만 부재.
    → **WS-OBS-3(per-stage drop attribution)로 이관**(matcher 진리값 변경 아님).
- 회귀 가드: 모든 변경은 v5 baseline 대비 `make f1-regression`(FN-방향 비대칭
  veto) + `make latency-gate` 통과 후 머지. 신규 NAF 분기는 코드리뷰에서 이 문서
  §4 등록을 요구한다.
