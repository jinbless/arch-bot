# 장소성 사진 라우팅 + 앵커 judge (Track A, 2026-08-12) — 플래그 off WIP

> prod 실측에서 출발: 계단·보행로 사진 2건이 보건편 분진 '설비 등의 기준'으로 오귀속.
> 원인 = ① 장소성 의무(계단·통로·작업장 45건)는 cross_cutting이라 앵커 카탈로그에 정답이 없음
> ② 보건편 '설비 기준' 류 4그룹의 라벨이 절 이름 그대로(판별 정보 0) ③ RESOLVE는 강제 선택.
> 사용자 결정: 장소성 사진 = basics 주제 라우팅(장소 앵커 신설 안 함), 계측 = 미니 gold 신설.

## 단계별 결과

| 단계 | 결과 | 상태 |
|---|---|---|
| A-0 미니 gold+러너 | place_gold_v1.csv 12행(prod 3 + 신규 7 + gold51 2) + measure_place_routing.py | 완료 |
| A-1 판별단서 4종 | gimulmul diff 4건·flow diff 0·gold51 0.784/0.961 불변 | **완료·배포** |
| A-2 RESOLVE 프롬프트 | 이탈구도·포괄 강등 — 이득 증거 없음(±1장 변동과 구분 불가), 기권 리스크 관찰 | **기각** |
| A-3 judge+라우팅 | 코드·프론트 완성, 플래그 off 배포(off=종전 동일) | 게이트 미통과 — **on 보류** |
| A-4 플래그 on | — | 보류 |

## A-3 실측 (judge 프롬프트 v2 기준)

judge v1("핵심 위험을 일으키는 후보 / 위험이 장소에서 오면 -1")은 gold51에서 **49장 FP** —
감독 사진 대부분이 추락 계열이라 '위험 종류=추락=장소' 프레임에 빠져 비계·사다리 정답 기인물을
강등했다. v2는 질문을 **실재·주제성**("후보가 장면에 실제로 등장하는가")으로 재프레임:

- gold51(채점 51장 기준) **진짜 FP 2장** — 선우개발 위험물 표지 2매. 후보(석면 해체 그룹)가
  장면에 '작업으로서' 안 보여 judge가 -1. 지식(감독관은 그 창고가 석면 관련임을 앎) vs
  지각(텍스트 장면엔 표지·창고뿐)의 경계 부류 — RESOLVE 재추첨 경계 사례와 같은 사진들.
- resolve 캐시의 채점 외 사진 10장이 place로 전환 — **손실 아님**: truth가 카탈로그 밖
  (개구부·지붕·통로 = cross_cutting)이라 오히려 basics가 정답 내용을 담는 부류.
- 미니 gold: place 6/8 (기준 ≥0.8=7/8) · anchor 1/3 · prod 3장 중 2장.
  - 실패 3건 중 2건은 **기대 라벨 재검토 대상**: 대산 '계단, 2층 단부'는 judge가 철골작업을
    선택(사진에 철골 구조 실재 — 방어 가능), 노원 검사실은 원심기 그룹 선택(검사실 장비 실재).
  - 승원02는 judge가 휴게시설(컨테이너 사무동)을 주제로 봄 — 진짜 오판에 가까움.

## 다음 선택지 (사용자 결정)

1. **미니 gold 라벨 검수**(원래 계획된 체크포인트): 대산 계단→either, 노원→복수 정답 허용 등
   재라벨 후 재계측 — 라벨만으로 G-MINI가 통과할 수 있음. 잔여는 선우개발 FP 2장.
2. **사진 직시 judge 실험**: 텍스트 장면의 한계(위험물 창고를 표지로만 인지)가 FP 2장의 원인 —
   이미지 입력 judge(gpt-4.1)로 그 경계가 갈리는지 A/B. 비용 +1 vision 콜.
3. 선우개발류를 '지식-경계 사진'으로 문서화하고 FP 허용 기준을 재등록(악화 0의 정의 조정) —
   비권장(게이트 흔들기).

## 재료·재현

- 러너: `serving-team/08-app/backend/scripts/measure_place_routing.py` — gold51 Vision·RESOLVE는
  고정 표본(intake_vision_gold + rank_ab_resolve_cache_v2) 재사용, judge만 자체 캐시.
  manifest(프롬프트·카탈로그·매핑 SHA) 불일치 시 자기무효화.
- 산출: `runtime-artifacts/place_routing_report.json` (게이트 판정 포함) · `place_routing_cache.json`.
- 미니 gold: `real-test-photo/place_gold/place_gold_v1.csv` (+ photos/ — prod 3장은 DB 썸네일
  480×360 추출본. 미추적 관례).
- 서빙 코드: `flow_service.judge_anchor/route_decision/place_signals/_place_workflow`,
  플래그 `OHS_ENABLE_ANCHOR_JUDGE`(env `CUE_ANCHOR_JUDGE`) 기본 off. off면 rows[0] 종전 경로.
- ⚠ 계측 함정 2건: ① intake Vision 스키마엔 risk_feature_candidates가 없어 offline canonical이
  비어 place_signals는 계측에서 항상 [] — 결정론 신호는 서빙 전용 보강 계층 ② RESOLVE 재추첨
  변동(선우개발 empty 0↔1) — 측정 정본은 커밋된 캐시(고정 표본), 재생성은 프롬프트/카탈로그
  변경 시에만.
