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

## 재계측 (같은 날 2차 — 라벨 검수 반영)

적용: ① 미니 gold 재라벨(대산 '계단, 2층 단부'→either — 철골 골조 실재로 앵커도 방어 가능,
expect_group_key 복수 허용) ② **재배열 비활성** — judge의 primary>0 재배열은 실측 4건에서
이득 0·해악 2(5222 화기→휴게시설, 승원02→휴게시설)라 rows[0] 유지로 고정, judge의 가치는
장소성(-1) 판정만 ③ **judge 입력에 판별단서 라벨(gimulmul) 제공** — 검수된 카탈로그 데이터의
제공(자유텍스트 힌트 아님). 석면 그룹 라벨('출입구 비닐 밀폐ㆍ경고표지')이 선우개발 장면의 비닐
차단막과 대조돼 FP 2장이 해소됐다 ④ FP 정의를 게이트 등록 취지대로 정밀화(= 정답을 잃는
재라우팅만. 채점 대상 밖/완전 오인식 사진의 장소 전환은 별도 투명 보고 — truth가 개구부·통로라
오히려 개선 부류) ⑤ **러너 스테이지별 manifest 캐시** — 단일 manifest가 judge 프롬프트 변경에
vision·RESOLVE까지 재추첨시키는 사고를 러너 안에서 재현(5220 후보가 표본에 따라 뒤집힘),
스테이지 분리로 격리.

**v3(실재성) vs v4(주제성/배경 분리) 게이트 실측**:

| 게이트 | v3 | v4 |
|---|---|---|
| G-OLD-PLACE-FP(정답 상실) | **0 PASS** | 1 FAIL(엠지에스 — truth 배선·이동전선, judge "전선은 주변 요소") |
| G-MINI-PROD | 3/3 | 3/3 |
| G-MINI-PLACE | 4/7 FAIL | **6/7 PASS**(승원02 잔여) |
| G-MINI-ANCHOR | 3/3 | 3/3 |
| 채점외→장소(참고) | 8 | 25 |

본질: "사진은 장소로 읽히나 감독관은 장비를 인용"(엠지에스·선우개발 부류)과 "배경에 장비가
실재하는 장소 사진"(승원·서울가든 부류)을 한 프롬프트 다이얼로 다 가를 수 없다 —
정밀도-재현율 트레이드오프가 실측으로 고정됐다.

## 상태: **v3/v4 결정 보류 (사용자, 2026-08-12)** — 플래그 off 유지·배포 없음

코드에는 v4가 실려 있으나 미채택(플래그 off라 불활성). 재개 방법: 결정 후
`.venv/bin/python scripts/measure_place_routing.py` 1회(고정 표본 캐시 재사용, LLM 재호출 0)로
게이트 재현 → v3 복귀는 JUDGE_SYS만 git 이력(커밋 bd77a91 직후 v3 문안)에서 되돌리면 된다.

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
