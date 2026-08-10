# 모델 전환 실험 — gpt-5.6-terra(Vision+RESOLVE) + Claude Opus 5 검수 (2026-08-10)

> 사용자 요청: "gpt모델을 gpt-5.6 terra로 변경해봐. 서빙 이미지 분석하고 resolve 모두.
> 그리고 다시 측정해봐. 그리고 검수는 클로드 opus 5로 해봐." — **실험**이며 채택 결정 아님.
> 결론 먼저: **terra 전환 이득 없음(채택 비권고)**. 부산물로 카탈로그 이탈 키 버그 1건 발견.

## 설계

- 러너: [measure_model_ab_terra.py](../../serving-team/08-app/backend/scripts/measure_model_ab_terra.py)
  — 프롬프트(VIS_SYS v2 체크리스트·RESOLVE_SYS)·카탈로그·채점 규칙을 현행과 완전 동일하게
  고정하고 **모델만** 교체. 정본 캐시(intake_vision_gold, rank_ab_resolve_cache_v2) 불변.
- A(현행) = anchor_accuracy.json per_photo 그대로 (vision gpt-4.1 + RESOLVE gpt-5.4, 2026-08-10 정식)
- B(terra) = gold 51장을 gpt-5.6-terra로 Vision 재판독 → gpt-5.6-terra로 RESOLVE
- 검수: [probe_terra_opus_review.py](../../serving-team/08-app/backend/scripts/probe_terra_opus_review.py)
  — 두 팔의 선택이 다른 사진을 claude-opus-5가 **사진을 직접 보고** 블라인드 판정
  (선택지 순서 사진명 해시로 셔플, 모델 정체 비공개, 닫힌 카탈로그 범위만 — 조문 판단 금지 유지)

## 결과 1 — 모델 A/B (51장, 실패 0)

| 지표 | 현행(4.1+5.4) | terra(5.6+5.6) |
|---|---|---|
| exact | **0.765** | 0.745 |
| flow_valid | **0.922** | **0.922** |

- flip: exact 회복 1(핸드그라인더) / 악화 2(석면 출입경고표지, 한솔 비계) · flow 회복 1/악화 1
- 악화 양상: 석면 사진에서 terra 서술이 비닐 밀폐·경고표지 단서를 놓치고 배선으로 이탈;
  한솔 비계는 강관비계 단일 선택으로 좁힘(비계 상속 덕에 flow는 유지)
- **회복 1장의 정체**: 모델 능력 차가 아니었다 — 아래 버그 발견 참조

## 결과 2 — 카탈로그 이탈 키 버그 (부산물, 겉보기-오류=버그 클래스 9번째)

51장 전수 감사: RESOLVE가 낸 group_key 중 카탈로그(닫힌 집합)에 없는 키
- 현행(5.4): **1건** — 핸드그라인더 사진에서 `절8 사출성형기 등 > 관8?` (실제 키는
  `절8 사출성형기 등`; 존재하지 않는 하위 계층을 지어붙임)
- terra(5.6): 0건

채점·서빙 모두 이 키를 조용히 버린다(gkey_coord 미스 → 예측 공집합). 즉 현행 exact 0.765의
오답 1장은 판단 오류가 아니라 **형식 이탈 + 미정규화**. Opus 검수도 리뷰 중 이 깨진 키를
지적했다("선택 1은 '관8?' 같은…").

**개선 후보(미구현, 사용자 결정 대기)**: RESOLVE 출력 키를 카탈로그에 prefix-매칭으로
정규화(측정 채점부 + 서빙 `cue_article_service._norm_gk` 동일 규칙). 적용 시 현행
exact 0.765 → 0.784 예상(+1장). terra의 유일한 우위가 소멸한다.

## 결과 3 — Claude Opus 5 검수 (불일치 42장, 실패 0, 거부 0)

- 유효 불일치는 38장(4장은 접미사 표기 차이뿐인 동일 선택 — Opus가 정확히 '동등' 판정)
- **gold가 판가름낸 3장(flip) 모두 Opus가 gold와 일치(3/3)** — 사유도 정확
  (석면 비닐 밀폐 관찰, 이동식비계 구조 식별, 깨진 키 지적)
- 선호 분포: 현행 20 · terra 18 · 동등 4 · 둘다부적절 0 — 양쪽 다 맞은 31장에서는
  13:14로 반반(정상: 둘 다 유효한 선택), 양쪽 다 틀린 8장에서는 5:3
- 양쪽 다 틀린 8장의 사유는 잔여 오인식 개별 분해에 바로 쓸 만한 품질
  (예: 등촌역 2장 "주 기인물은 강관비계" — gold는 다른 절, 라벨 특성 재확인)

## 결론·권고

1. **terra 전환 비권고**: exact 소폭 열세(-0.020), flow 동률, 유일한 회복 1장도 버그
   보정 시 소멸. reasoning 토큰으로 호출당 비용·지연만 증가.
2. **Claude Opus 5는 검수자로 유효**: 판가름 사진 3/3 gold 일치 + 깨진 키까지 발견.
   Sol(gpt-5.6-sol) 검수의 대안/이중화 후보 — 특히 **사진이 필요한 검수**는 Opus가 적임
   (Sol은 텍스트 검수로만 써 왔음).
3. **즉시 개선 후보**: group_key 카탈로그 정규화(prefix 매칭) — 측정+서빙 동시 적용,
   gold 재계측 동반. 사용자 지시 대기.

## 산출물·비용

- `runtime-artifacts/terra_ab_{cache,report}.json`, `terra_opus_review.json`
- 호출: terra 102콜(51 vision+51 resolve), claude-opus-5 42콜(사진+카탈로그) — 합계 한 자릿수 $
- 서빙 코드·모델 변경 없음(실험은 별도 러너로만 수행)
