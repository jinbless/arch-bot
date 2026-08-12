# 앵커 정정 시 '지금 당장' 재선별 (2026-08-12)

> 사용자 질문에서 출발: "서술에서 함께 확인된 상황에 대해서도 지금 당장 조치해야 하는 것들을
> 알려줄 수 있지?" — 대안 칩·직접 검색으로 기인물을 바꾸면 '지금 당장' 스트립이 숨고
> "다시 계산하지 않습니다" 안내만 뜨던 것(2026-08-09 통합 때의 보수적 스코프)을,
> **클릭 시 재계산**으로 연다. 재료가 전부 로컬 파일+PG라 LLM 0·비용 0.

## 적용

- **백엔드**: `GET /api/v1/flow`가 `WorkFlowWithActions`(WorkFlow + statute_actions)를 반환.
  `accident_code` 반복 쿼리 파라미터로 원래 분석의 사고형태 신호를 승계(없으면 순위 없이
  행위형·법정·작업전 정렬만). 매핑은 `flow_service.statute_actions_corrective`로 공용화 —
  분석 응답(`_build_statute_actions`)이 여기로 위임해 urgency/confidence 규칙 드리프트를 막는다.
- **프론트**: WorkFlowPanel에 `currentActions` 상태 — 정정 시 응답의 재선별 값으로 스트립을
  교체 렌더("직접 고른 기인물의 조문에서 … 다시 선별" 표기), 타임라인 '지금' 배지도 같은
  값(actNowShown)에서 파생. 정정 모드 하이라이트 점프 재활성(AI 대조는 정정 시 통째로 숨어
  stale 점프 불가). ResultPage가 `risk_features`의 accident_type 코드를 승계 전달.
  **AI 제안 대조는 재계산하지 않음 유지**(LLM 정렬 필요 + 제안 자체가 원 매체 기준) — 안내문을
  대조에만 남김.

## 잠복 버그 수정 (9번째): 순위 신호가 사실상 공집합

`flow_service.statute_actions`의 SR 순위 신호가 **2026-08-09 통합 이후 사실상 죽어 있었다**:
사진 사고형태는 `_facet_canon`으로 신 카탈로그 canonical(COLLISION)화하면서, SR은 구 enum
원컬럼(`addresses_hazard`=STRUCK_BY·CAUGHT_IN)을 읽어 교집합이 이름 우연 일치(ELECTRIC_SHOCK·
CHEMICAL_EXPOSURE) 빼고는 빈 집합 → `hazard_hit` False → urgency 전부 planned. 주석이
경고하던 바로 그 실패("변환 없이 교집합하면 항상 공집합")를 변환을 **반쪽만** 넣어 재현한 것.
`_facet_canon`은 원래 `*_canonical` 컬럼 매칭용이다(query_ci_for_facets 참조).

수정: SR 히트를 **두 컬럼 합집합**(`accident_types_canonical` ∪ `addresses_hazard`)으로 계산
+ UNCLASSIFIED 제외. canonical 단독 교체는 리뷰가 회귀를 적발했다 — canonical 컬럼은 626행 중
284행·7종(COLLISION·CAUGHT_IN·FALL·COLLAPSE·STRUCK_BY·CUT_LACERATION·ERGONOMIC_STRAIN)만
채워져 있어, 레거시 이름이 canonical과 우연히 같아 **수정 전에도 히트 가능했던**
ELECTRIC_SHOCK·CHEMICAL_EXPOSURE 클래스를 도로 죽인다. 합집합은 양쪽 동작의 strict superset.

실측: 지게차+COLLISION → 제172조(출입 제한)류 6건 planned→**immediate** + 순서 변화,
전기+ELECTRIC_SHOCK → 제307조·제310조 immediate(레거시 컬럼 경유 복원). 분석 경로
(immediate_actions)에도 같은 효과 — '계획 조치' 배지가 전 항목에 붙던 것이 의도대로 분리된다.

⚠ **커버리지 한계(다음 계측 때 버그로 재오인 금지)**: FIRE_EXPLOSION 계열(레거시 101행)은
canonical 어휘(EXPLOSION·FIRE_INJURY)와 이름이 달라 합집합으로도 히트 불가 — 화재·폭발
사고형태에서는 여전히 전부 '계획 조치'로 표시된다. 해소하려면 SR canonical 컬럼 데이터 보강
(Phase-2 이관 완성) 필요. 코드가 아니라 데이터 과제다.

## 검증

- 로컬 스모크: 서비스 직접 호출 + TestClient 엔드포인트(반복 파라미터 배선) + 파이프라인 위임
  동등성 True + 순위 신호 효과(order/urgency changed) 확인.
- 로컬 스택(airgap compose) 재기동 후 API E2E: 텍스트 분석(지게차, COLLISION) →
  `immediate_actions` 6건 immediate → 대안 그룹 `GET /flow?...&accident_code=COLLISION` →
  해당 기인물 조문의 재선별 반환. 프론트 번들에 새 문구·파라미터 포함 확인.
- 3렌즈(백엔드 계약·프론트 상태·무회귀) + 적대적 검증 워크플로 리뷰(13 agents): 발견 10건 중
  생존 7건 — canonical 단독 회귀(위 절, **수정**), AnchorPicker busy 미적용·pick 동시요청
  레이스(기존 결함, **수정**: busy prop+가드), 스트립 점프 다중 칸 하이라이트 경합(기존,
  **수정**: slotForAction으로 목적 칸 지정 — 백엔드 seen-dedup과 동일 규칙), 나머지는 수용
  (아래). 반박 3건(오류-빈값 구분·canonical 컬럼 전제 등 — 검증자가 코드로 기각).
- 구 백엔드/구 기록 호환: `statute_actions` 없으면 프론트가 빈 배열로 폴백(스트립 숨김+안내문),
  분석 응답 스키마는 불변(WorkFlowWithActions는 정정 API 전용 서브클래스).

## 수용한 발견 (수정하지 않음, 알고 있는 상태)

- **CI 폴백 기록의 '지금 당장' 2중 표시(low)**: 분석 시점 조문 선별이 비어 CI 폴백 패널이 뜬
  기록에서, 앵커를 정정하면 흐름 패널 안에 재선별 스트립이 추가로 나타나 화면에 '지금 당장'이
  둘이 된다. 두 블록 모두 출처 라벨이 있고(CI 패널=원 분석, 스트립="직접 고른 기인물의
  조문에서 재선별"), 상태 자체가 희귀(흐름은 있는데 작업전·작업중 조문이 없는 앵커)라 수용.
  거슬리면 ResultPage-WorkFlowPanel 간 콜백으로 폴백 패널을 접는 조정이 필요하다.
- **버그 기간(08-09~12) 저장 기록의 표시 비일관(info)**: 저장된 스트립은 전부 '계획 조치',
  정정→원복 재선택 경로는 재계산이라 immediate 표시 — stale 저장 데이터 한정, 무해.

## 한계

- 재선별의 순위 신호는 **원래 분석의 사고형태**를 그대로 잇는다 — 사용자가 기인물을 바꿨다고
  사고형태를 재추론하지는 않는다(그건 LLM 재호출이고, 매체가 이미 그 위험을 보여준 게 아니므로
  선별 근거가 약해진다). 신호가 없으면 행위형·법정·작업전 정렬로 열화.
- AI 제안 대조는 여전히 처음 인식 기준(위 '적용' 참조).
