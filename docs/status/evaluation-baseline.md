# Evaluation Baseline

Latest updated: 2026-08-01 — **⭐앵커(기인물) 인식 정확도 정정: 좌표를 (절,관)으로만 비교하고 편·장을 버리던 버그를 고쳐 관 0.778→0.711 · 절 0.800→0.733 · 완전 오인식 20%→26.7%. 부풀림 +0.067. 서빙 경로는 무영향(group_keys 직접 조회).** 같은 날: **⭐정식 FP 측정 2라운드 완결: 현행은 정상 현장의 94.8%/94.5%에 조문을 낸다(독립 표본 재현). A+C(yes만 노출 + 포괄조문 분리) 채택 후 정상 오탐 0.308·gold 침묵률 0.155 — 개선은 재현됐으나 노출 기준(<0.20) 미달로 `CUE_ARTICLES` 계속 off. 남은 오탐은 구체조문(제43·20·14조)이라 조문 제거로는 끝 → 다음은 결여 신호 구조화.** 같은 날: **변별 프로브 v2: 형제조문 변별은 병목이 아니다(형제 JPA 0.875 > 전체 0.810). 프롬프트 정보 보강은 4번째로 무효.** 이전(2026-07-31): **Track A RANK A/B v2 (라벨 2차검수 완료 후 재실행): cue-pool union이 P@1 +4.6pt·Hit@3 +7.2pt·Hit@5 +9.1pt 유의 개선 확정(전부 CI 0 배제) ⭐. promote-1 하이브리드는 사전등록 기각(union 단독 우세로 불필요).** 이전: RANK A/B v1(비열등만 확정 — 당시 top1의 40%가 미판정이라 과소평가였음이 판명) + 후보천장 A/B(84.5%→93.0%).

Accepted runtime baseline: `ci_cross_guide_broad_only_guard1`

Previous accepted baseline: `ci_unrelated_action_filter1`

The full report bodies under `data-team/05-enrichment/eval-data/reports/**` are local/external artifacts. Root git tracks `data-team/05-enrichment/eval-data/reports-manifest.json` and this summary instead of adding historical report files to repository history.

> ⚠️ **측정 caveat — 정본 (WS-OBS-2)**: 본 문서의 합성 corpus 지표(SHE recall 54.9%, SR 84.0%, overall 0.3258 등)는 **Layer 1–3 metric**이다 — replay harness(`build_fake_result`)가 `expected_features`를 confidence 0.9로 주입해 **Layer 0(Vision)을 우회**하므로, Vision이 현장 위험을 놓치는 end-to-end false-negative는 이 수치에 **포함되지 않는다**. 또한 합성 corpus는 제빵/주방 위주(KOSHA guide=산업)라 도메인 미스매치 caveat가 있다. Vision 포함 end-to-end recall + scene-correctness는 별도 사람-라벨 gold set(WS-EVAL-2)로만 측정된다.

## Gate Baseline 거버넌스 (MEAS-2, F14) — 기계 검증 anchor

회귀게이트(`make f1-regression`)의 현행 보호선. **baseline 채택 = 4-포인터 원자 갱신**(baseline 파일 생성 → Makefile `F1_BASELINE` → `regression_gate.DEFAULT_BASELINE` → 아래 anchor)을 **단일 커밋**으로 수행하고 `make verify-baseline`으로 종료 확인한다. 아래 블록은 `verify_baseline_governance.py`가 파싱하는 기계 anchor — 수치를 손으로 고치지 말고 채택 절차로만 갱신.

```json
{
  "_anchor": "gate-baseline",
  "file": "replay_baseline_v6.json",
  "she_accuracy": 0.5915,
  "sr_accuracy": 0.7797,
  "penalty_accuracy": 0.4903,
  "overall_accuracy": 0.3479,
  "false_positive_rate": 0.0906,
  "false_negative_rate": 0.1489,
  "she_recall_miss_rate": 0.3994,
  "guide_coverage_rate": 0.6718
}
```

> ✅ **v6 — VT backfill (visual_triggers 복구)**: importer가 INSERT 컬럼에서 visual_triggers를 누락해 phase3c 531패턴의 시각단서가 전량 유실됐던 버그(커밋 `036c379` 수정 + reconcile 복구)를 바로잡은 뒤 재캡처. v5 대비 **overall 0.3258→0.3479(+0.0221)·penalty 0.4729→0.4903(+0.0174)·she 0.589→0.5915**, `false_positive_rate`/`false_negative_rate` 무변화(개선이 FP/FN 비용 없이 달성). visual_score가 제대로 기여해 candidate→confirmed 승격이 정상화된 결과. 측정: semantic-alive + rerank off, errored 0. perf_baseline도 동반 재캡처(VT scoring 증가로 p95 282→327ms, compute 경로).
>
> 이전 — **v5 정직 baseline (MEAS-1/MEAS-3, F19·F14)**: 평가 정답(ecd) 주입 오염 제거 후 재캡처. `false_positive_rate` 0.8696→0.0906(ecd 보유 negative 상수 → 실측 25/276), `false_negative_rate` 0.0→0.1489(구조적 불능 → 실측 205/1377). FN-최우선 차단 지표가 처음으로 실측·게이트화. **다음 재캡처는 MEAS-2 절차(4-포인터 원자 갱신 + `make verify-baseline`)로만.**

## 앵커 — 흐름 기준 유효율 신설 + 비계 공통 상속(A안) (2026-08-10 ⭐)

카탈로그 104종(크레인 분할 후)·채점 51장 기준. A0 계측 스프린트(오류 18건 선분류·셔플·confidence,
`docs/dev-notes/anchor-a0-metrics-2026-08-09.md`)가 **오류의 절반(9건)이 모델이 아니라 비계 공통 절
미상속**임을 밝혀, 사용자 A안(제54·55·56 + 제58만 상속, 제57·조립 별표 제외 — Sol 검수 2라운드 경유)을
적용했다.

| 지표 | 값 | CI95 | 비고 |
|---|---|---|---|
| 관 단위 정확 일치(exact) | **0.725** | [0.608, 0.843] | 판별 단서 보강 후(fa4aa9b). 상속 직후엔 0.647(좌표 정의 불변) |
| **흐름 기준 유효율 (신설)** | **0.902** | [0.824, 0.980] | exact ∪ 선택 그룹 **흐름**이 gold 조문 포함. 상속 직후 0.824 → 판별 단서 후 0.902 |

**판별 단서 보강**(같은 날 2차): 라벨이 절 이름 그대로였던 4그룹(사출성형기 등·석면·화기·전기
기계기구)에 소속 조문 근거의 대상 나열(연삭기·핸드그라인더, 출입구 비닐 밀폐·경고표지 등)을 부착
→ RESOLVE 재실행(129장). **회복 4장(석면2·그라인더2)·악화 0.** 동명이기 함정: 별표21 '롤러기'
(도로 롤러)가 라벨 매칭에 걸려 대여 조문이 오부착 → 라벨에서 제외. 잔여 오인식 14장
(석면1·화기1·접지1·경계2 + 기타).

- 셔플 계측: 위치 편향은 병목 아님(팔 간 exact 불일치 3.9%, 다수결 이득 0 — G-SHUFFLE FAIL, 기각).
  첫 후보 변동 29.4%는 주 기인물 선별(rows[0]) 리스크로 잔존
- confidence(언어화): 저확신(<70) 2장 모두 오답(G-CONF PASS)이나 모델 과신 — 확인 유도는 보조 수단
- 잔여 진짜 오인식 7건(석면3·그라인더2·화기1·접지1) = 카탈로그 판별 단서 보강 대상
- 러너: `scripts/measure_resolve_shuffle.py`(자체 캐시, 프롬프트·스키마·카탈로그 SHA 자기무효화)

## 앵커(기인물) 인식 정확도 — 시간축 구조의 단일 실패점 (2026-08-02, 카탈로그 수정 후)

스냅샷→시간축 재정의로 **기인물 하나에 흐름 6단계가 전부 걸린다.** 앵커가 틀리면 계획·점검·작업·종료가
통째로 틀리므로(현행은 조문마다 따로 틀림) 이 값이 새 구조의 단일 실패점이다.
측정: 감독관 gold v2의 정답 조문 → (편,장,절,관) 역산 → RESOLVE `group_keys`와 대조. **라벨 추가 0.**

| 지표 | 값 | CI95 |
|---|---|---|
| 관 단위 정확 일치 | **0.600** | [0.467, 0.717] |
| 절 단위 일치(상위 흐름 공유) | **0.617** | [0.500, 0.733] |
| 완전 오인식(절도 불일치) | **38.3%** (23/60) | |
| 예측 자체가 빈 사진 | 0장 | |

> ⚠️ **직전 값 0.711은 채점 대상이 좁아서 나온 과대평가였다.** 비계 사진 15장이 통째로 빠져 있었다.
> 측정이 `편1이면 정답에서 제외`로 하드코딩돼 있었는데, 비계는 편1 장7이다.
> 그 15장은 정답이 비계뿐이라 **채점 자체가 안 됐다**(45장 → 60장).
>
> 원인은 앵커 카탈로그였다. `cross_cutting`(=RESOLVE 카탈로그 제외 목록)에 **장7 비계가 통째로**
> 들어 있어 비계 6종이 카탈로그에서 빠졌고, 항상-후보인 `CROSS` 16개 조문에도 비계는 없었다.
> **사진에 비계가 찍혀도 앵커로 도달할 경로가 아예 없었다.** RESOLVE의 자유 텍스트는
> '비계(발판)'이라고 정확히 말하고 있었는데 group_key로 옮기지 못한 것이다.
>
> 조치: ① `CROSS_CUTTING_JANG`에서 장7 비계 제거(카탈로그 99 → 105종)
> ② 측정의 정답 필터를 **카탈로그에서 역산**하도록 변경(앞으로 카탈로그를 바꾸면 측정이 따라온다)
> ③ 새 카탈로그로 **RESOLVE 재실행**(`rerun_resolve_cache.py` → `rank_ab_resolve_cache_v2.json`.
>    원본은 RANK A/B 실측 구성요소라 보존). 129장 중 **39장이 비계를 앵커로 지목**하기 시작했다
> ④ LLM이 카탈로그 줄 전체(`… ::기인물=… (N조)`)를 복사하는 경우 정규화(5장 회복, 빈 예측 1 → 0)

| 같은 60장 기준 | 관 일치 | 완전 오인식 |
|---|---|---|
| 옛 카탈로그(99종) + 옛 캐시 | 0.533 | 45.0% |
| **새 카탈로그(105종) + 재실행** | **0.600** | **38.3%** |

> ⚠️ **초판 수치(관 0.778 · 절 0.800 · 완전 오인식 20%)는 좌표 비교 버그로 부풀려진 값이었다.**
> `measure_anchor_accuracy.py`가 좌표를 `(절, 관)`으로만 비교하고 **편·장을 버렸다.** 규칙에는
> `절1`이라는 이름의 절이 20곳 있어(편2장1 기계 일반기준 / 편2장3 전기 / 편3 각 장 통칙 …)
> 서로 다른 절이 같은 좌표로 뭉개졌다. (편,장,절,관) 4튜플 비교로 고친 값이 위 표다. 부풀림 **+0.067**.
> 재발 감지를 위해 산출물에 `legacy_exact_match`(구 방식)를 함께 남긴다.
>
> **서빙 경로는 이 버그의 영향을 받지 않았다** — `cue_article_service`는 `group_keys` 문자열로 직접
> 조회하고 좌표 비교를 하지 않는다. 영향 범위는 측정 스크립트와 그 산출물뿐이다.

**caveat**: gold 129장 중 **60장만 채점**된다(나머지 69장은 정답 조문이 카탈로그 밖 그룹뿐이라 역산 불가 —
작업장·통로·보호구·추락 같은 횡단과 정의뿐인 통칙). gold가 감독건 인용이라 사진의 모든 기인물을
담지 않으므로 recall은 과소평가된다.

> ★ **채점 대상이 늘면 점수는 대체로 내려간다.** 0.778 → 0.711은 좌표 버그, 0.711 → 0.600은 채점 범위였다.
> 두 번 다 "숫자가 예상보다 좋으면 측정 자체를 의심하라"는 같은 교훈이다.
> 남은 69장도 언젠가 채점 대상이 되면 값이 또 움직인다.

측정 스크립트: `serving-team/08-app/backend/scripts/measure_anchor_accuracy.py`
raw: `data-team/05-enrichment/runtime-artifacts/anchor_accuracy.json`

## Track A RANK A/B **v2** — 라벨 복구 후 재실행: union 유의 개선 확정 (2026-07-31 ⭐)

라벨 2차 검수(사람 1,051쌍 판정 + 1차 수정 15건 → gold v2, top1 판정율 31%→**100%**) 후 사전등록 재실행.
arm A·B 4-rep 실측(1,032콜) + **arm D promote-1**(B top1이 A후보 밖 신규코드일 때만 채택 — A·B 랭킹에서 결정론 유도).
게이트 5종 전부 PASS(실패 0 · order max 0.019 · 후보구성 재현 · 상수랭커 초과 · 전체랭킹 저장).

| arm | P@1 | Hit@3 | Hit@5 | R@5 | MRR | (v1-gold P@1) |
|---|---|---|---|---|---|---|
| A baseline | 0.475 | 0.663 | 0.723 | 0.625 | 0.577 | 0.419 |
| **B union** | **0.521** | **0.734** | **0.814** | **0.704** | **0.638** | 0.455 |
| D promote-1 | 0.523 | 0.723 | 0.783 | 0.680 | 0.630 | 0.459 |
| (const_제43조) | 0.326 | 0.326 | 0.403 | — | — | — |

- **★A→B: P@1 Δ+0.046 CI[+0.002,+0.095] · Hit@3 Δ+0.072 CI[+0.019,+0.128] · Hit@5 Δ+0.091 CI[+0.039,+0.147] — 전부 CI가 0을 배제.**
  v1 실행의 "비열등, 이득 검출 불가"는 **top1의 40%가 미판정이라 B의 정답을 오답으로 세던 과소평가**였음이 판명.
  페어드 비교는 공정(라벨 확장이 A·B 양쪽 top3를 모두 판정). 층화: gold∩CROSS=∅ 50장 Δ+0.150 / CROSS안 79장 Δ-0.019(v1의 -0.051에서 해소).
- **D promote-1은 사전등록 계층판정에서 기각**: H1 비headroom A→D Δ-0.013 CI[-0.028,-0.002]가 마진 -0.02를 초과 → FAIL
  (H2 headroom Δ+0.596은 전제 미충족으로 미판정). B→D Hit@5 -0.031 — **union 단독이 우세해 하이브리드 불필요**. 좋은 의미의 기각.
- 채택 갱신: cue-pool union = 연구트랙 후보생성 기본값(v1 결정 유지) + **이제 근거가 "비열등"이 아니라 "유의 개선"**.
  잔여 전제: 서빙 배선 전 후보-밖 코드 필터(환각 A 31·B 28/516랭킹) · 오탐 비용 사실상 미측정(⚠"음성 102장"은 과대 집계 — 실제 음성 9장뿐+EXCLUDED 93, 9장 스모크는 neg_fp_results.json, 정식 측정은 정상 현장 사진 신규 수집 필요) · v2 gold의 모델-top3 노출 편향(형제 10종 전수로 완화).
- raw: `rank_ab_results_v2.json/.md`(전체 랭킹 rep별 저장 — 사후 fusion 시뮬 가능) · 하네스 `scripts/rank_ab_v2.py`.

## ⭐ 정식 오탐(FP) 측정 — 현 구성은 프로덕션에 못 올린다 (2026-08-01)

`no_label_photo` 648장(label_photo와 교집합 0)에서 업체당 1장·seed 고정 **80장** 사전등록 표본 →
파이프라인 실행(실패 0) → **블라인드 사람 이진 판정**(위반없음 67 · 위반있음 7 · 모호 6) → 채점.

| 지표 | 값 |
|---|---|
| **주지표 top1 FP율** | **0.948** CI[0.903, 0.985] → 사전등록 밴드 **≥0.50 = 프로덕션 노출 부적합** |
| 판별력 | 음성 주장률 0.948 vs 양성 1.000 → **Δ 0.052** |
| 사진당 노출 · abstain | 5.2건 · 0.052 |

- **위반이 없는 현장에서도 95%가 조문을 받는다.** 위반 유무와 거의 무관하게 주장한다 —
  정확도 문제가 아니라 **판단을 하지 않는** 구조다.
- 음성 top1 분포: 제3조(전도의 방지) 33회 · 제22조 18회 · 제20조 13회 · 제315조 11회 — 전부 포괄 의무.
  RANK 프롬프트에 "포괄 의무 강등" 지시가 있는데도 그렇다(프롬프트 주입 실패 패턴의 연장).
- **사후 탐색(탐색적 — 판정 불변)**: CROSS16 제외 0.799 · top1만 제한 0.799 · 빈출 2종 제외 0.910.
  **목록에서 무엇을 빼도 0.80 밑으로 안 내려간다** → 후보를 좁히는 방향(pruning·shortlist·표기 보완)으로는
  해결되지 않는다. 필요한 것은 **위반 유무 판단 단계**(없으면 목록을 내지 않는 경로)다.
- 라벨 잡음에 강건: 주장률이 사진 종류와 거의 무관하므로 음성 판정 일부가 틀렸어도 결론이 뒤집히지 않는다.
- **`OHS_ENABLE_CUE_ARTICLES`는 계속 off.** 이 게이트를 통과하기 전에는 프로덕션 반영 없음.
- **★게이트 탐색(사후·탐색적)에서 지렛대 발견 — 모델은 이미 판단하고 있었다**: 음성 노출의 applies 분포가
  **no 1,110 · maybe 510 · yes 153**인데 `do_rank`/`filter_to_candidates`가 **yes와 maybe를 합쳐** 내보낸다.
  `yes만 노출` → 음성 0.978→**0.672**(판별력 0.022→0.186), `yes + CROSS16 제외` → **0.306**(밴드 진입).
  CROSS16 단독 제거는 무력(0.955). 결여신호 정규식 게이트의 추가 기여는 미미(0.306→0.291).
  ⚠ 양성 표본 7장에서 주장률 1.000→0.500(위반 절반 놓침) · 같은 80장 사후 탐색 → **남은 568장에서 사전등록 재측정 필수**.
- **기인물 등급화는 지렛대 없음(검증됨)**: 음성 67장에 기인물 **186종**·최다 빈출 **2/67장(3%)**·양성과 겹침 1종(4%).
  막을 공통 기인물이 없다. 문제는 식별이 아니라 **"기인물 존재 → 그 조문이 후보"** 매핑이다.
  cue-pool 115종 중 결여 표현을 담은 cue는 **2종(1.7%)** — 입구가 통째로 '존재' 기반이다.
- **채택(2026-08-01): A안 yes만 노출 + C안 포괄조문 분리.** 노출 기준을 `applies=="yes"`로 좁히고
  (env `CUE_EXPOSE_MAYBE=1`로 복원), SSOT §6.2 전역강등 대상 **제3·4·22조**를 `group="common"`으로 분리해
  '위반 후보'가 아니라 '모든 현장 공통 점검'으로 낸다. 시뮬(같은 80장): 정상 0.948→**0.373** / 위반 1.000→0.429.
  위반 쪽 하락이 실제 손실이 아닌 근거 — 감독관 gold에서 **제3조는 52장 판정 중 실제 위반 1장(2%)**,
  제22조 14%(5/35). 즉 분리로 잃는 건 탐지가 아니라 오답이다(비교: 제43조 42%·제13조 17%).
  **조건부 C(SSOT 원문 "특정조문 있을 때만 강등")는 효과 0으로 기각** — 정상 사진은 포괄조문이 단독 yes라 미발동.
  ⚠ 정책을 고른 그 80장에서 잰 수치 → **남은 568장에서 사전등록 재측정 필요**. 플래그는 계속 off.
- **★Round 2 재측정(A+C 켠 채, 손대지 않은 새 80장 + gold 129장 두 축)**:
  | 정책 | 정상 위반목록 | 위반 위반목록 | gold P@1 | gold 완전침묵 |
  |---|---|---|---|---|
  | 현행 | 0.945 [0.897,0.986] | 1.000 | 0.515 | 0.008 |
  | A만 | 0.630 | 0.900 | 0.492 | 0.050 |
  | **A+C** | **0.308** [0.205,0.411] | 0.900 | 0.488 | **0.155** |
  **재현성이 핵심**: 현행 0.948(R1) → 0.945(R2)로 독립 표본에서 사실상 동일, A+C 개선도 정책을 고르지 않은
  표본에서 그대로 나왔다(CI가 R1 시뮬 0.373 포함) → 과적합 우려 미실현.
  **누락 정본은 축 2**(gold 129장, 침묵률 0.155 < 기각선 0.30, P@1 -0.027) — 축 1의 위반 표본은 5~7장이라
  판별력 추정이 불안정(R1 0.429 vs R2 0.900).
  ⚠ 사전 예측(0.40~0.55)은 **틀렸다**(실측 0.308) — 사후에 기준을 옮기지 않기 위해 기록으로 남김.
  **판정: A+C는 코드 유지, 플래그는 계속 off**(정상 3곳 중 1곳에 여전히 후보가 뜸 — 노출 기준 <0.20 미달).
  남은 오탐은 포괄조문이 아니라 **구체조문**(제43조 12회·제20조 11회·제14조 10회)이고 제43조는 gold 정답률 42%라
  뺄 수 없다 → **조문 제거 방향은 종료, 다음은 결여 신호 구조화**(존재가 아니라 '있어야 할 것이 없음'을 요구).
- raw: `fp_results.json/.md` · `fp_posthoc_variants.json` · `fp_gate_variants.json` · `fp_simulate_ac.json` · `fp_round2_results.json/.md` · `fp_recall_gold.json` · 사전등록·해석 [../dev-notes/fp-measurement-2026-08-01.md](../dev-notes/fp-measurement-2026-08-01.md)

## 변별 프로브 **v2** — 형제조문 변별은 병목이 아니었다 (2026-08-01)

v1 프로브(gold v1, 판정쌍 299)는 형제 JPA 0.719를 냈지만 **형제쌍이 65개뿐이라 탐색적 관찰**이었다.
gold v2로 검출력을 확보해 재실행: 129장 · 판정쌍 **1,878** · 형제쌍 **665**(확장 924) · 4-rep · 1,548콜 · 실패 0.
설계 불변(큐레이터가 y/n을 실제로 매긴 코드만 후보로 제시 → 후보생성 품질을 배제한 **순수 변별력**).

| arm | JPA | CI95 | 형제 JPA(665쌍/74장) | 형제확장(924쌍/76장) |
|---|---|---|---|---|
| P0 현행 | 0.810 | [+0.772,+0.842] | **0.875** | 0.875 |
| P1 +정보배관 | 0.816 | [+0.781,+0.847] | 0.881 | 0.882 |
| P2 +근거렌더 | 0.824 | [+0.786,+0.858] | 0.879 | 0.877 |

- **★형제 JPA 0.875 > 전체 0.810 — 형제조문에서 오히려 더 잘 구분한다.** v1의 0.719는 65쌍 소표본 아티팩트였다.
- **프롬프트 정보 보강은 이번에도 무효**: P0→P1 +0.007 CI[-0.002,+0.016] · P0→P2 +0.014 CI[-0.002,+0.030] ·
  형제쌍만 보면 P1→P2 **-0.002** — 전부 non_inferior(유의 이득 없음). 조건부 규칙 주입 실패에 이은 **4번째 확인**.
- **⚠ 앞 절 "다음 병목은 랭킹 변별"의 정정**: 같은 랭커가 rank_ab(후보 중앙값 46개)에서는 gold 제43조 39장 P@1 0.635·
  제13조 15장 top1 0장인데, 후보를 판정코드(평균 **11.3개**)로 좁히면 형제 JPA 0.875다. 병목은 "형제를 구분하는 능력"이
  아니라 **후보 잡음 아래에서의 순위 안정성** — 두 측정의 차이는 후보 집합 크기·잡음뿐이다.
- **쌍별 분해**(rep0 기술통계, `scripts/analyze_sibling_pairs.py`): 형제쌍 실패 112/924(12.1%). 오답인데 정답 위로
  올라온 조문은 **제13조 25%**(28건) · 제42조 17% · 제24조 12%로, SSOT §5.1(제13조는 단독 1차 아님)·포괄 조문 문제와 일치.
  약한 쌍: 제24조↔제13조 0.33 · 제56조↔제43조 0.33 · 제44조↔제13조 0.33 · 제56조↔제13조 0.40.
  다만 **1위 오염은 작다**(제13조 4/80장 · 제42조 4/87장) → 결정론 후처리로 제13조를 강등해도 **P@1 기대이득은 소폭**.
- raw: `probe_discrimination_v2.json/.md`(v1 산출물 `probe_discrimination.json`은 보존) ·
  하네스 `scripts/probe_discrimination.py --gold v2`(Vision `intake_vision_gold.json` 재사용).

## Track A RANK A/B — cue-pool union 후보확장의 최종 랭킹 영향 (2026-07-29, P@1 비열등 확정 · 정확도 상승 주장 불가 — **v2 재실행으로 갱신됨, 위 절 참조**)

후보천장 A/B 이후 남은 질문 = **후보 +15.6개(distractor)가 최종 순위를 해치는가**.
paired 3-arm(같은 사진·Vision·RESOLVE 공유), 실제 감독관 gold **129장 · y-코드 162**, reps 4, RANK=gpt-5.4.

| arm | P@1 | Hit@3 | Hit@5 | Hit@10 | R@5 | MRR | 천장(cand_any) | 평균후보 |
|---|---|---|---|---|---|---|---|---|
| A base_plain | 0.432 | 0.609 | 0.680 | 0.725 | 0.611 | 0.531 | 0.837 | 30.5 |
| **B union_plain** | **0.438** | **0.655** | **0.713** | **0.779** | **0.654** | **0.557** | **0.930** | 46.1 |
| C union_expert (누출·상한추정, 채택 판단 미사용) | 0.444 | 0.638 | 0.700 | 0.754 | 0.645 | 0.551 | 0.930 | 46.1 |

- **주지표 A→B P@1 Δ+0.006 CI95[-0.039,+0.052] → `non_inferior`**(사전지정 마진 -0.05). 유효성 게이트 전부 PASS
  (G1 실패 0 / G2 order_sensitivity max 0.0426 ≤0.05 / G3 천장 재현 / G4 상수랭커 0.302 초과).
- **⚠ 이 결과는 '정확도가 올랐다'의 근거가 아니다.** 이득경로(headroom)가 12장뿐이라 P@1 이론상한 +0.093,
  실현 gross +0.050 < **MDE80 0.066** → **이득은 원리적으로 검출 불가, 해악만 검출 가능한 설계**.
  부지표 Hit@3 +0.047 · Hit@5 +0.033 · R@5 +0.043 · MRR +0.026은 전부 양의 방향이나 **95% CI가 0을 포함**
  (재부트스트랩 B=20000: Hit@3 [-0.002,+0.099]). **CI가 0을 배제한 유일 지표 = Hit@10 Δ+0.054 CI[+0.002,+0.111]**.
- **이득/손실 완전 분리**: headroom 12장(A후보가 gold를 아예 못 담고 B는 담은 사진)에서
  P@1 0.000→0.542 · Hit@3 0.000→0.729 · Hit@5 0.000→0.812, 나머지 117장에서 P@1 0.4765→0.4274(**-0.049,
  CI[-0.079,-0.024]로 0 배제**) · Hit@3 -0.024 · Hit@5 -0.047.
  P@1 사진승패 = B승 7(전부 headroom) · A승 14(전부 비headroom) · 동률 108(불일치 14쌍이 14-0, 부호검정 p=0.00012).
- **진짜 층화축은 headroom이 아니라 CROSS16**: headroom 12장은 **12/12 전부 `gold ∩ CROSS16 = ∅`**.
  gold∩CROSS=∅ 56장 ΔP@1 **+0.080**/ΔHit@3 **+0.134**/ΔHit@5 **+0.143**, gold∩CROSS≠∅ 73장 -0.051/-0.021/-0.051.
  → 이득은 횡단 일반의무 **밖** 롱테일(제68조·제122조·제87조·제302조 등) 도달, 손실은 이미 잘 맞히던 횡단 사진의 순위 흔들림.
  (사후 층화 = 탐색적. 다음 측정에서 사전등록 층화변수로 승격할 것.)
- **다건 제시 환산(129장)**: Hit@3 78.5장→**84.5장(+6.0장)**, Hit@5 87.8→92.0(+4.3장), Hit@10 93.5→100.5(+7.0장).
  4/4 rep 전원일치 기준 top-3 신규 전환 8장 vs 이탈 0장. 단 +6.0장 = headroom +8.8장 − 비headroom 2.8장의 **순액**.
- **천장→실현 갭이 오히려 벌어졌다**: 천장 +12.0장(108→120장) 대비 Hit@5 실현 +4.3장(**실현율 35%**, Hit@3 기준 50%).
  미실현 갭 A 20.2장 → **B 28.0장(21.7%p)**. → **다음 병목은 후보생성이 아니라 랭킹 변별.**
- **최대 단일 손실원 = 추락 형제조문 변별**: gold 제43조 39장(gold y의 24.1%) P@1 A 0.705 → B 0.635 → C 0.481.
  gold 제13조 15장(2위 빈도)은 3 arm 모두 top1 정답 **0장**(제13조는 CROSS 상수로 129/129 후보에 이미 포함 —
  도달성이 아니라 변별 문제).
- **arm C(감독관 SSOT 프롬프트 힌트)는 상한추정 — 채택 판단 미사용.** gold 129장 노출 후 작성된 규칙
  (홀드아웃 분할 없음, 커밋 `9c322b4`). 누출을 안고도 순이득 ≈0(headroom P@1 +0.042·Hit@3 +0.062 /
  비headroom +0.002·**-0.026**). 실제로 힌트가 바꾼 것은 의도한 제13조 분기가 아니라 제43조→제56조 오스왑
  (gold 제43조 39장 P@1 0.635→0.481) → **프롬프트 힌트 방향 폐기**, SSOT는 후보생성/온톨로지 제약으로만 형식화.
- **부작용**: 후보-밖 코드(환각) 출력이 A 16건 → **B 24건(+50%)**(각 arm 129×4=516 랭킹, 하네스가 걸러 지표엔 미반영).
  서빙 배선 시 후보-밖 필터 구현이 **채택 전제조건**.
- **천장 수치 정합 주의**: 본 하네스 실측 A cand_any **0.837**·recall 0.814 / B **0.930**·recall 0.922.
  아래 「후보천장 A/B」 절의 0.845/0.821 · 0.930/0.914와 미세 상이(G3 tolerance 내 PASS, A는 Δ0.008로 상한 근접).
  **두 절 수치를 섞어 인용하지 말 것.**
- **채택 범위**: 서빙 코드(`serving-team/08-app/backend/app/`)에 cue-pool 참조 **0건**(grep 확인) —
  이번 채택은 **연구트랙 후보생성 기본값 전환**이지 배포 서빙 정확도 개선이 아니다.
- raw: `data-team/05-enrichment/runtime-artifacts/rank_ab_results.json` ·
  하네스 `serving-team/08-app/backend/scripts/rank_ab_gold.py`
  (Vision `intake_vision_gold.json` / RESOLVE `rank_ab_resolve_cache.json` 재사용).

상세·재현·오독 방지 12항: [../dev-notes/rank-ab-cuepool-union-2026-07-29.md](../dev-notes/rank-ab-cuepool-union-2026-07-29.md).

## Track A cue-pool 후보천장 A/B — 실제 감독관 gold 129장 (2026-07-13, cand_any 84.5%→93.0% ⭐)

관찰단서(cue-pool 115종, RULE 100% 커버)를 baseline 후보생성(gimulmul 기인물 앵커)에 **additive union**으로 얹었을 때 후보천장(cand_any) 측정. **실제 감독관 gold 129장·y-라벨 162** (합성 아님, `label_curation_gold.csv` match=y). baseline photo_any 0.845가 문서화된 후보천장 84.5%를 **재현**.

| arm | recall | photo_any(천장) | photo_all | 평균후보 |
|---|---|---|---|---|
| baseline(gimulmul) | 0.821 | 0.845 | 0.798 | 29.8 |
| cue_entry | 0.722 | 0.729 | 0.698 | 19.2 |
| cue_entry+flow | 0.765 | 0.783 | 0.752 | 26.8 |
| **union(base∪cue)** | **0.914** | **0.930** | **0.915** | 45.3 |

- **union +8.5pt(0.845→0.930)** = plan P1 게이트(cand_any ≥0.93) 달성. cue-pool 단독 < baseline(**상보재**, 대체재 아님). 이득 = 환경조건(분진·조도)·위험장소구조(안전난간·사다리)·기인물 보강(회전축·전기) — 기인물-only 사각 정확히 보완.
- 남은 7% 갭 = 석면 표지 미부착(제490·492) 지배 = 사진 검출 본질적 불가(도메인 한계).
- 비용 +15.5 후보/사진(RANK 부담). **⚠️ 천장 ≠ P@1** — 다음 관문 = union RANK로 P@1/Hit@5 A/B.
- Vision(gpt-4.1) 영구저장 `intake_vision_gold.json`(한글명 키) · 스크립트 `measure_cuepool_gold.py` · raw `cuepool_ab_results.json`.

상세·재현: [../dev-notes/cuepool-candidate-ceiling-ab-2026-07-13.md](../dev-notes/cuepool-candidate-ceiling-ab-2026-07-13.md).

## guide-accuracy Sprint — Guide 추천 정확도 (2026-05-28, 8-photo Guide mapping 80%→100% ⭐)

실 서비스에서 CI 추천은 정확하나 Guide가 엉뚱하게 추천되는 문제(boilerplate CI fan-out + CI 개수 단독 랭킹) 근본 해결.

- **P1 CI 변별력**: `checklist_items.guide_frequency` backfill (**3,953 CI, max 130**). `ci_weight = 1/log2(1+gf)`.
- **P0 Guide 랭킹**: `get_guides_from_srs()` CI 개수 → Σ(ci_weight) 변별력 가중합.
- **P2 직접 위험 매핑**: `guide_entity_feature_candidates(entity_type='GUIDE', method='guide_hazard_weighted_majority')` **2,115행 / 659 Guide** + 신규 `get_guides_by_hazard_features()` (CI 경유 없음).
- **P3 온톨로지**: `guide:addressesHazard`/`guideAddressesAgent`/`guideAppliesToContext` + `kosha-instances-guide-hazard.ttl` (659 Guide, 2,115 triple). ⚠️ **2026-06-20**: 이 ABox는 이후 `archive/kosha-instances-guide-hazard.ttl`로 이동(manifest `arc-old-inversion`, 활성 프로파일 없음) → fine-tagging 산출 `kosha-instances-guide-fine.ttl`(957 guide / 9,415 triple)이 대체. 위 659/2,115는 PG `guide_entity_feature_candidates(method='guide_hazard_weighted_majority')`로 라이브 보존.

8-photo Guide eval:

| 지표 | before | after |
|---|---|---|
| mapping rate | 80% | **100% (27/27)** |
| guide_hazard_direct mapping | — | **85%** |
| boilerplate Guide 출현 | 발생 | **0** |

> ⚠️ **측정 caveat (WS-OBS-2)**: 위 'mapping rate 100% (27/27)'은 hazard→code **매핑 커버리지**이며 scene-correctness 정확도가 **아니다**(사람-라벨 gold set 부재·n=8 비통계·work_context 미측정). 폐지예정 `standard_procedures` lane은 무관 guide를 高confidence로 내보내는 사례가 있다(`claude_vision_8photo_eval.json`). 안전 품질 주장은 gold set(WS-EVAL-2) 인용 후에만.

Gate 3 regression (replay 2,360, tolerance 0.02): synthetic metric 회귀 없음 (Guide 추천은 synthetic corpus 채점 대상 외 → 8-photo로 측정). she 0.5758 / sr 0.7581 / penalty 0.4551 / overall 0.3258 유지.

Runbook: [../dev-notes/guide-recommendation-accuracy.md](../dev-notes/guide-recommendation-accuracy.md).

## axiom-100% Sprint — Ontology 공리 100% (2026-05-20~27, SWRL→SHACL CONSTRUCT)

SWRL 의사코드 30개를 정형 추론 facts로 전환. Pellet NEXPTIME blowup 회피 위해 R-14~R-30은 SHACL CONSTRUCT.

- v4 TBox 패치 9종 (deps/alethic/bridge/deontic/violation/penalty-extra/restrictions/hazard-direct/asymmetric). **owl:Restriction 35, owl:AsymmetricProperty 1, NaturalLanguageHazardCategory 21, sh:NodeShape 1,964**. ⚠️ **2026-06-20 실측**: owl:Restriction는 현재 **37**(v4-restrictions 33 + v3-guide-profile 4; 문서 35는 v4-only 집계). sh:NodeShape **1,964**는 axiom-100% 어셈블리 스코프 — 전체 48 TTL raw grep은 4,407(kb-candidates 2,192 + vetted-disjoint-shapes 2,161 후보 KB 포함, 측정 스코프 밖).
- R-1/R-3 SWRL native 유지 (Pellet: 107 + 3,579 inferred). R-14~R-30 → `kosha-rules-r14-r30-shacl-construct.ttl` (12 sh:rule CONSTRUCT, Java sources 4 SWRL 주석).
- K-general SHACL: `core:dependsOn` 36,949 + `core:coApplicable` 16,429 = **53,378 pair**.
- Gate 3 PASS (ontology-layer 변경, serving replay 회귀 없음). 검증: `scripts/verify_axiom_100pct.py` Overall OK.

Runbook: [../workplans/ontology-axiom-100pct.md](../workplans/ontology-axiom-100pct.md), [../dev-notes/axiom-100pct-phase-c-j.md](../dev-notes/axiom-100pct-phase-c-j.md).

## Phase G.3 penalty_rule_index PG materialization — 2026-05-19 (penalty_accuracy +27.16%p ⭐)

Phase G Sprint G.3에서 신규 PG table `penalty_rule_index` 도입 + `hazard_rule_engine._load_penalty_index()` PG primary 전환. TTL parse 우회 + 더 완전한 mapping으로 인한 metric 대폭 개선.

Input:
- Source: `ontology-team/06-reasoning/ontology/kosha-instances.ttl` (TTL ABox, 1.06M lines)
- Target: PG `penalty_rule_index` (14 cols + 4 indexes, ORM `PgPenaltyRuleIndex`)
- 적재 script: `import_penalty_to_pg.py` (rdflib parse → UPSERT)
- Result: **4,076 unique (sr_id, penalty_rule_id) pairs** (100% CriminalSanction; AdministrativeFine는 design intent로 0건)

Gate 3 결과 (vs `replay_baseline_v3.json`):

| metric | baseline_v3 | Phase G.3 PG | delta | verdict |
|---|---|---|---|---|
| she_accuracy | 0.5771 | 0.5758 | -0.0013 | ok (noise) |
| sr_accuracy | 0.7581 | 0.7581 | 0.0000 | ok |
| **penalty_accuracy** | **0.1835** | **0.4551** | **+0.2716 (+27.16%p) ⭐** | ok |
| **overall_accuracy** | **0.1377** | **0.3258** | **+0.1881 (+18.81%p) ⭐** | ok |
| false_positive_rate | 0.8696 | 0.8696 | 0.0000 | ok |
| false_negative_rate | 0.0625 | 0.0436 | -0.0189 | ok (개선) |

**효과 설명**: 기존 backend는 `_load_penalty_index()`가 `kosha-instances.ttl` parse (시작 시간 ~25초, lazy materialization으로 일부 사실 누락). PG 전환 후 4,076 mappings 모두 즉시 query 가능 → backend가 정확한 SR→penalty 경로 더 많이 발견.

Phase G.3 runbook: [phase-g.3-penalty-rule-index-pg.md](../dev-notes/phase-g.3-penalty-rule-index-pg.md).

## Tier 4 #3 SWRL Pellet 실행 검증 — 2026-05-19 (R-1: 107 + R-3: 3,579 inferred ⭐)

기존 `kosha-rules-v2.swrl` (22+8 pseudo-code rules, 의사코드 문서)를 OWL/RDF SWRL serialization으로 변환 (`kosha-rules-r1-r3-swrl.ttl`, R-1 + R-3 우선). Pellet/Openllet native SWRL 실행 검증.

Input:
- `kosha-rules-r1-r3-swrl.ttl` (+76 triples, R-1 ExemptedByRule + R-3 HighSeverityRule)
- KoshaFusekiServer.java sources에 추가 → docker rebuild → container recreate
- Fuseki 부팅 시 자동 로드 (총 981,485 triples, 이전 981,409 + 76)

SPARQL 검증 결과:

| SWRL Rule | 추론 결과 | Sanity check |
|---|---|---|
| **R-1 exemptedBy** | `?s core:exemptedBy ?o` → **107 inferred triples** | NormStatement modifies + Exemption modality 매칭 |
| **R-3 HighSeverityPenalty** | `?s a penalty:HighSeverityPenalty` → **3,579 inferred** | `severityScore >= 5` count도 정확히 **3,579** (Pellet swrlb:greaterThanOrEqual 100% 정확) |

**의미**: Pellet의 SWRL built-in support 입증. 의사코드 문서가 실제 추론 가능 facts로 변환됨. 후속 sprint에서 R-2~R-30 일괄 변환 가능.

Tier 4 #3 runbook: [t4-swrl-pellet-integration.md](../dev-notes/t4-swrl-pellet-integration.md).

**Track A ② — PG 물질화 + 서빙 소비 (2026-06-14, COMMITTED+PUSHED `87d9e63`/`7c50304`/`e6140bb`)**:
위 추론 산출을 서빙이 Fuseki 없이 소비하도록 물질화. 신규 PG 테이블 `sr_inferred_relations`
**= 총 103,295행** (`rule_id`로 strict R-1 vs relaxed K-R2/K-R4 구분):
- **R-1 exemptedBy** (`87d9e63`): 107 NS-edge를 SR 단위로 확장 **107행 / 95 distinct SR** (strict DL) →
  `/api/v1/sparql/sr/{id}/exemptions`·`/article/{}/inferred-graph` 가 PG SELECT로 응답(F7/F8 "추론이 서빙 하중을 받음").
- **K-R2 coApplicable** (`7c50304`): same-Chapter relaxation **16,429 distinct pair → 32,858행**(양방향).
  ⚠️ 이전 본 항목이 표기한 "미적재/별도 프로파일"은 **정정** — 이제 **PG 물질화 완료**.
- **K-R4 dependsOn** (`e6140bb`): same-Hazard relaxation **35,165 distinct pair → 70,330행**(양방향) →
  신규 엔드포인트 `/api/v1/sparql/sr/{id}/depends-on`.

R-2 strict coApplicable은 현 ABox에서 **0건**(SR↔Article 1:1로 same-article cross-pair 없음). R-3
HighSeverityPenalty(3,579)는 `penalty_rule_index.severity_score>=5` SQL 동치로 재현(reasoner 불요,
`sr_inferred_relations` 미저장). 출처 TTL: `kosha-inferred-relations.ttl`·`kosha-coapplicable-chapter.ttl`·
`kosha-dependson-hazard.ttl`(emit_inferred_relations.py `--mode strict|chapter|hazard`). PROV:
`materialization_runs`(git rev + TTL sha256, 행 단위 run_id, runs #1-4). 게이트: `make phase-g5/g5b/g5c-verify`.
분석 경로 무변경 → f1-regression all-metric delta **0.0000**(3 slice) · latency 무회귀.

> ⚠️ **수치 정합**: 위 axiom-100% Sprint 섹션의 "K-general `core:dependsOn` 36,949"는 **on-demand SHACL count**로,
> 이제 PG에 물질화된 **K-R4 dependsOn = 35,165 distinct pair**(same-Hazard relaxation 재집계)와는 **다른 수치**다.
> coApplicable 16,429쌍 역시 같은 섹션에선 on-demand였으나 이제 K-R2로 PG 적재(32,858행). 서빙은 PG를 읽는다(Fuseki 요청경로 아님).

## T2.D F.3.2 vetted promotion — 2026-05-18 (8/8 candidates 1-by-1 PASS)

T2.D sprint에서 8 F.3.2 candidate를 1-by-1 vetted 승격. 각 promote 직후 full
replay (2,360 cases) + regression_gate (tolerance 0.02) 실행, FAIL 시 자동 rollback.

Input (initial state):
- KB vetted_count = 0, candidate_count = 8 (source=f32_axiom_miner)
- Baseline: `replay_baseline_v3.json`

Per-candidate verdict:

| idx | domain_a | domain_b | conf | replay valid | Gate 3 | verdict |
|---|---|---|---|---|---|---|
| 1 | BUTCHER_MEAT_RETAIL | CONSTRUCTION | 0.86 | 2,360 / 0 errored | PASS | vetted |
| 2 | CONSTRUCTION | METAL_MACHINING | 0.86 | 2,360 / 0 errored | PASS | vetted |
| 3 | MANUFACTURING | ELECTRICAL_CONSTRUCTION | 0.72 | 2,360 / 0 errored | PASS | vetted |
| 4 | BUTCHER_MEAT_RETAIL | LANDSCAPING_GREENSPACE | 0.82 | 2,360 / 0 errored | PASS | vetted |
| 5 | GAS_PIPING_INSTALLATION | CHEMICAL_INDUSTRY | 0.84 | 2,360 / 0 errored | PASS | vetted |
| 6 | 편의점 | METAL_MACHINING | 0.78 | 2,360 / 0 errored | PASS | vetted |
| 7 | GAS_PIPING_INSTALLATION | CONSTRUCTION | 0.74 | 2,360 / 0 errored | PASS | vetted |
| 8 | FIRE_PROTECTION_INSTALLATION | CHEMICAL_INDUSTRY | 0.74 | 2,360 / 0 errored | PASS | vetted |

Final state: KB vetted_count = 8, candidate_count = 0 (source=f32_axiom_miner).
Total KB incompatibilities: 2,232 vetted + 8 = 2,240 (KO→EN cleanup 후 동일).

**PASS** — 예상 5-6 PASS 대비 8/8 (100%) 달성. F.3.2 mining quality 매우 우수.
T2.D 1차 실행 시 promote_f32_per_candidate.py `✓✗→—` unicode chars가 Windows
cp949 codec encoding 불가 → 모든 unicode를 ASCII로 교체 + PYTHONIOENCODING=utf-8
+ python -u 로 재실행 성공. 1차 시도에서 CONSTRUCTION×METAL_MACHINING이 vetted
state로 stuck (rollback 실패) → manual rollback 후 클린 재실행으로 8/8 검증.

보고서: [t2d-per-candidate-promotion-2026-05-18.md](t2d-per-candidate-promotion-2026-05-18.md).

## Tier 3.A Closed Vocab Schema Enum — 2026-05-18 (free-create 94.7% 감소)

Hybrid Day 3의 partial 효과 (schema axis 5 + prompt enum만, text는 free string
잔존)를 본격 schema-level enum constraint로 해결. `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text`에 catalog 529 codes enum 강제.

Implementation:
- `openai_client.py:_load_catalog_codes()` — `risk_feature_catalog.json` axes의 모든 코드를 단일 set으로 수집 (529 codes)
- Module-level lazy load (`_ALL_CATALOG_CODES`, backend restart로 갱신)
- Schema JSON 크기: 12.6KB (OpenAI strict mode 한도 내, 100KB ≪)
- `analyze_image` + `analyze_text` 둘 다 동일 schema 사용 → 양쪽 enum 강제

Pre/Post analysis_log normalizer_unknown_codes 통계:

| 측정 | rows | with_unknown | unknown_terms | rate |
|---|---|---|---|---|
| Pre-3A (전체 history) | 26,524 | 54 | 76 | 0.2% |
| Post-3A (T3.A replay 2,360 cases) | 2,360 | 3 | 4 | 0.1% |

**76 → 4 (-94.7% 감소)**.

Top 10 pre-3A free-creates (3A 적용 후 모두 0건):

| count | text | axis |
|---|---|---|
| 10 | MACHINERY | work_context |
| 10 | THF | hazardous_agent |
| 10 | CO | hazardous_agent |
| 6 | machinery | work_context |
| 4 | WAREHOUSE | work_context |
| 3 | FORKLIFT | work_context |
| 2 | cooking | work_context |
| 2 | ELEVATED_WORK | work_context |
| 2 | STEEL_STRUCTURE | hazardous_agent |
| 2 | CONSTRUCTION_SITE | work_context |

잔존 4건 (post-3A):

| text | axis | scene_hash (16-char) | timestamp |
|---|---|---|---|
| THF | hazardous_agent | 74016445d8182014 | 2026-05-18T09:03:20 |
| CO | hazardous_agent | 3530bfec867698dd | 2026-05-18T09:05:31 |
| MOBILE_EQUIPMENT | hazardous_agent | (3-row analysis 누락) | - |
| WAREHOUSE | work_context | (3-row analysis 누락) | - |

→ OpenAI strict mode enum의 edge-case 누락 (강제력 ~99.6%). 별도 분석 또는
normalizer step에서 hard reject 가능.

Gate 3 결과 (replay_baseline_v3 vs /tmp/replay_3a_full.json):

| metric | baseline_v3 | T3.A | delta | verdict |
|---|---|---|---|---|
| she_accuracy | 0.5771 | 0.5758 | -0.0013 | ok (noise) |
| sr_accuracy | 0.7581 | 0.7581 | 0.0000 | ok |
| penalty_accuracy | 0.1835 | 0.1835 | 0.0000 | ok |
| overall_accuracy | 0.1377 | 0.1377 | 0.0000 | ok |
| false_positive_rate | 0.8696 | 0.8696 | 0.0000 | ok |
| false_negative_rate | 0.0625 | 0.0639 | +0.0014 | ok (within tolerance) |

**PASS** — 모든 metric delta 0 또는 noise. enum 강제가 정확도 회귀 없이 free-create만 95% 차단.

보고서: [t3a-closed-vocab-schema-enum-2026-05-18.md](t3a-closed-vocab-schema-enum-2026-05-18.md).

## F.3.3 Gate 3 Regression — 2026-05-17 (F.3.2 first batch 영향 측정)

Plan agent의 4-Gate 중 Gate 3 (counter-example regression). F.3.2 sprint에서 KB
머지된 8 candidate disjoint axiom이 production 회귀를 일으키지 않는지 측정.

Input:
- Baseline: `data-team/05-enrichment/runtime-artifacts/replay_baseline_v3.json` (Phase 3D 후)
- Current run: `data-team/05-enrichment/runtime-artifacts/replay_post_f32.json`
- 평가 corpus: 2,360 synthetic observations (v1~v10 EN transform 후)
- KB 상태: 2,232 vetted + 8 F.3.2 candidate = **2,240** incompat

Result (regression_gate.py tolerance 0.02):

| metric | baseline_v3 | post-F.3.2 | delta | verdict |
|---|---|---|---|---|
| she_accuracy | 0.5771 | 0.5758 | -0.0013 | ok (noise) |
| sr_accuracy | 0.7581 | 0.7581 | 0.0000 | ok |
| penalty_accuracy | 0.1835 | 0.1835 | 0.0000 | ok |
| overall_accuracy | 0.1377 | 0.1377 | 0.0000 | ok |
| false_positive_rate | 0.8696 | 0.8696 | 0.0000 | ok |
| false_negative_rate | 0.0625 | 0.0625 | 0.0000 | ok |
| valid / total | n/a | 2,360 / 2,360 | — | 0 errored ✅ |

**PASS** — 8 candidate 모두 Gate 3 통과. asymmetric trust 본래 의도대로
`promote_incompatibilities.py`가 50회 사용 후 자동 vetted 승격 유지.

Hot-fix 노트 (commit `a841a0b` → main `d0b2262`): 첫 replay에서 1,700/2,360 errored
발견 — A 변경 (commit `ebe1011`)의 `raw_vision_features=dict(...)`가 list 입력에
`ValueError: dictionary update sequence element #0 has length 4; 2 is required`
발생. `list` 타입으로 수정 후 0 errored 회복.

보고서: [f33-gate3-regression-2026-05-17.md](f33-gate3-regression-2026-05-17.md).

## Phase 3 reasoning catch (누적, 2026-05-17)

ontology reasoning이 LLM 환각/과대추정 **1,902건 자동 차단**. 자세히는
[reasoning-catch-effectiveness-2026-05-17.md](reasoning-catch-effectiveness-2026-05-17.md).

| catch 메커니즘 | 차단 건수 |
|---|---|
| Ensemble disagreement (Phase 3A HUMAN queue) | 228 |
| Freq threshold (1007 NEW → 170) | 837 |
| Catalog validation mapping | 813 |
| SHACL enum validation (Phase 3 Step 2) | 24 |
| Disjoint axioms (preventive) | ∞ |
| **합계** | **1,902** |

## F.3.0 reject reason distribution (2026-05-17)

`docs/status/f30-reject-reason-classification-2026-05-17.md` 정본.

2,525 excluded entries 5 카테고리:
- domain_mismatch 1,136 (44.99%) — KB axiom 작동 중
- axiom_missing 920 (36.44%) — F.3.2 input pool (210 unique pair)
- ambiguous 466 (18.46%)
- data_quality 3 (0.12%)
- normalizer_gap 0 (별도 신호 채널 필요)
- **F.3 recommendation: PROCEED_F3** (≥5% 임계의 7배)

## CI Cross Guide Broad Only Guard 1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_cross_guide_broad_only_guard1.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_cross_guide_broad_only_guard1_pg.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_ci_cross_guide_broad_only_guard1_report_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_ci_cross_guide_broad_only_guard1.*
data-team/05-enrichment/eval-data/reports/ci_boundary_mismatch_triage_ci_cross_guide_broad_only_guard1.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_ci_cross_guide_broad_only_guard1.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_actionability_ci_cross_guide_broad_only_guard1.*
data-team/05-enrichment/eval-data/reports/ci_no_action_triage_ci_cross_guide_broad_only_guard1.*
data-team/05-enrichment/eval-data/reports/ci_mapping_review_semantic_ci_cross_guide_broad_only_guard1.*
data-team/05-enrichment/eval-data/reports/ci_sr_mapping_candidate_review_ci_cross_guide_broad_only_guard1.*
data-team/05-enrichment/eval-data/reports/pg_ci_sr_link_candidates_ci_cross_guide_broad_only_guard1_apply.*
data-team/05-enrichment/eval-data/reports/ci_sr_candidate_promotion_ci_cross_guide_broad_only_guard1.*
ontology-team/06-reasoning/ontology/serving-snapshot-ci_cross_guide_broad_only_guard1.ttl
ontology-team/06-reasoning/ontology/serving-validation-report-ci_cross_guide_broad_only_guard1.*
ontology-team/06-reasoning/ontology/serving-workprocess-alignment-ci_cross_guide_broad_only_guard1.*
```

Summary:

```text
previous accepted baseline: ci_unrelated_action_filter1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5 -> 5
NO_TOP: 88 -> 88
NO_TOP actionability: accepted empty top 31 / source-taxonomy review 57 / runtime repair candidates 0
industry_boundary_gap: 0 -> 0
workprocess_mismatch: 5 -> 5
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 16
CI no_action: 494 -> 495
CI context_mismatch: 0 -> 0
CI broad_sr_only: 0 -> 0
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 2 -> 1
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: this pass keeps status/penalty/SHE/SR, Guide top selection, NO_TOP, WorkProcess, photo policy, and ontology validation stable. It only adds a narrow final immediate-action gate: if an immediate-action CI comes from a non-primary standard-procedure Guide and its only SR evidence is broad secondary SR, suppress it. This removes the H-117 broad-SR cross-Guide action in the manhole/confined-space case and lets the C-54 local CI surface instead. The remaining mismatch is `SYN-V5-0201`, where gas-station vapor exposure still borrows an H-115 hydrogen-cyanide tank purge CI; treat it as source/profile/taxonomy review, not a broad alias target.

PG candidate review refresh on 2026-05-16:

```text
CI no_action triage total: 495
upstream_stage2_3_review: 356
ci_mapping_review: 68
source_or_taxonomy_review: 45
accepted_empty_top: 23
runtime_repair_candidate: 3

semantic CI mapping review:
  source rows: 68
  reviewed rows: 67
  missing manual review: SYN-V5-0203
  true_ci_mapping_candidate: 19
  guide_selection_mismatch: 21
  corpus_gap_or_near_analogy: 22
  safe_or_followup_no_immediate: 5
  needs_manual_review: 1

guide_sr_link_candidates method ci_candidate_review_v1:
  imported review rows: 50
  serving candidate rows: 17
  needs_review rows: 33
  asserted rows: 0
  ci_sr_mapping inserts: 0
```

Interpretation: the additional CI no-action case is not automatically promoted. It is `SYN-V5-0203`, a gas-station enclosed car-wash exhaust/vapor case that now needs manual semantic review before any CI/SR candidate work. The safe candidate set remains 19 cases and 50 review rows; 17 narrow rows are serving `candidate`, 33 remain `needs_review`.

## CI Unrelated Action Filter 1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_unrelated_action_filter1.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_ci_unrelated_action_filter1_report_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_ci_unrelated_action_filter1.*
data-team/05-enrichment/eval-data/reports/ci_boundary_mismatch_triage_ci_unrelated_action_filter1.*
data-team/05-enrichment/eval-data/reports/ci_no_action_triage_ci_unrelated_action_filter1_current.*
data-team/05-enrichment/eval-data/reports/ci_mapping_review_semantic_ci_unrelated_action_filter1.*
data-team/05-enrichment/eval-data/reports/ci_sr_mapping_candidate_review_ci_unrelated_action_filter1_current.*
data-team/05-enrichment/eval-data/reports/pg_ci_sr_link_candidates_ci_unrelated_action_filter1_current_apply.*
data-team/05-enrichment/eval-data/reports/ci_sr_candidate_promotion_ci_unrelated_action_filter1_current.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_candidate_review_current_pg.*
ontology-team/06-reasoning/ontology/serving-snapshot-ci_unrelated_action_filter1.ttl
ontology-team/06-reasoning/ontology/serving-validation-report-ci_unrelated_action_filter1.*
ontology-team/06-reasoning/ontology/serving-workprocess-alignment-ci_unrelated_action_filter1.*
```

Summary:

```text
previous accepted baseline: ci_preferred_guide_ci1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5 -> 5
NO_TOP: 88 -> 88
industry_boundary_gap: 0 -> 0
workprocess_mismatch: 5 -> 5
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 16
CI no_action: 491 -> 494
CI context_mismatch: 0 -> 0
CI broad_sr_only: 0 -> 0
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 8 -> 2
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: this pass keeps status/penalty/SHE/SR, Guide top selection, NO_TOP, WorkProcess, photo policy, and ontology validation stable. It only changes immediate-action filtering after preferred top-Guide CI ordering: direct SHE checklist cues stay eligible, selected top-Guide CIs stay eligible, and generic CIs from unrelated Guides are suppressed. This reduces `CI guide_boundary_mismatch` from 8 to 2, with a small `CI no_action` increase from 491 to 494. The stricter primary-Guide-only trial was rejected because it reduced mismatch to 0 but regressed CI no_action to 551.

Residual `CI guide_boundary_mismatch` triage:

```text
total: 2
top Guide source_ci_ids present: 0
top Guide source_ci_ids absent: 2
top_guide_local_ci_gap: 1
guide_or_source_gap: 1
remaining top Guides: E-13, C-54
remaining top action source Guides: H-115, H-117
```

Interpretation: the remaining 2 cases are source/profile/taxonomy review tails, not broad alias candidates. Do not solve them by allowing unrelated generic CI fallback.

PG candidate review refresh on 2026-05-16:

```text
source reports:
  data-team/05-enrichment/eval-data/reports/ci_no_action_triage_ci_unrelated_action_filter1_current.*
  data-team/05-enrichment/eval-data/reports/ci_mapping_review_semantic_ci_unrelated_action_filter1.*
  data-team/05-enrichment/eval-data/reports/ci_sr_mapping_candidate_review_ci_unrelated_action_filter1_current.*
  data-team/05-enrichment/eval-data/reports/pg_ci_sr_link_candidates_ci_unrelated_action_filter1_current_apply.*
  data-team/05-enrichment/eval-data/reports/ci_sr_candidate_promotion_ci_unrelated_action_filter1_current.*
  data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_candidate_review_current_pg.*

CI no_action triage total: 494
upstream_stage2_3_review: 356
ci_mapping_review: 67
source_or_taxonomy_review: 45
accepted_empty_top: 23
runtime_repair_candidate: 3

semantic CI mapping review:
  source rows: 67
  true_ci_mapping_candidate: 19
  guide_selection_mismatch: 21
  corpus_gap_or_near_analogy: 22
  safe_or_followup_no_immediate: 5

guide_sr_link_candidates method ci_candidate_review_v1:
  imported review rows: 50
  serving candidate rows: 17
  needs_review rows: 33
  asserted rows: 0
  ci_sr_mapping inserts: 0
```

Interpretation: this refresh updates PostgreSQL review material only. The 17 narrowly promoted serving candidates remain the same policy class, while the extra 8 rows stay `needs_review` and cannot serve. Verification report `pipeline_quality_v1_v10_ci_candidate_review_current_pg` exactly preserves the accepted `ci_unrelated_action_filter1` metrics: Guide mismatch 5, NO_TOP 88, CI no_action 494, CI guide-boundary mismatch 2, CI needs_review_used 0.

## CI Preferred Guide CI1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_preferred_guide_ci1.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_ci_preferred_guide_ci1_report_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_ci_preferred_guide_ci1.*
data-team/05-enrichment/eval-data/reports/ci_boundary_mismatch_triage_ci_candidate_promotion_v1.*
ontology-team/06-reasoning/ontology/serving-snapshot-ci_preferred_guide_ci1.ttl
ontology-team/06-reasoning/ontology/serving-validation-report-ci_preferred_guide_ci1.*
ontology-team/06-reasoning/ontology/serving-workprocess-alignment-ci_preferred_guide_ci1.*
```

Summary:

```text
previous accepted baseline: ci_candidate_promotion_v1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5 -> 5
NO_TOP: 88 -> 88
industry_boundary_gap: 0 -> 0
workprocess_mismatch: 5 -> 5
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 16
CI no_action: 491 -> 491
CI context_mismatch: 0 -> 0
CI broad_sr_only: 0 -> 0
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 20 -> 8
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: this pass keeps status/penalty/SHE/SR, Guide top selection, NO_TOP, WorkProcess, photo policy, and ontology validation stable. It only changes immediate-action ordering: when the top standard-procedure Guide already has context-matched local CI candidates, those CIs are preferred over generic CI rows from unrelated Guides. This reduces `CI guide_boundary_mismatch` from 20 to 8 without increasing `CI no_action` or allowing broad-SR/needs-review leaks.

## CI Candidate Promotion v1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/ci_sr_candidate_promotion_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_candidate_promotion_v1.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_ci_candidate_promotion_v1_report_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_ci_candidate_promotion_v1.*
data-team/05-enrichment/eval-data/reports/ci_boundary_mismatch_triage_ci_candidate_promotion_v1.*
ontology-team/06-reasoning/ontology/serving-snapshot-ci_candidate_promotion_v1.ttl
ontology-team/06-reasoning/ontology/serving-validation-report-ci_candidate_promotion_v1.*
ontology-team/06-reasoning/ontology/serving-workprocess-alignment-ci_candidate_promotion_v1.*
```

Summary:

```text
previous accepted baseline: ci_broad_sr_guard4
candidate review method: ci_candidate_review_v1
review rows: 42
serving candidate rows: 17
kept needs_review rows: 25
asserted mapping update: 0
ci_sr_mapping update: 0
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5 -> 5
NO_TOP: 88 -> 88
industry_boundary_gap: 0 -> 0
workprocess_mismatch: 5 -> 5
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 16
CI no_action: 492 -> 491
CI context_mismatch: 0 -> 0
CI broad_sr_only: 0 -> 0
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 21 -> 20
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: this pass accepts the smallest safe part of the CI no-action mapping review queue. It promotes only direct, reviewed CI/SR pairs such as conveyor guarding, hot-work fire prevention, winter ice slip control, dry-cleaning ventilation, and ergonomic standing-work controls. Broad/generic PPE, near-analogy SRs, and weak corpus-gap rows remain `needs_review`. The runtime still blocks `needs_review/rejected` candidates, broad SR-only top actions, and asserted legal mapping changes.

Residual `CI guide_boundary_mismatch` triage:

```text
total: 20
top Guide source_ci_ids present: 6
top Guide source_ci_ids absent: 14
top_guide_local_ci_gap: 6
preferred_guide_ci_rank_gap: 5
source_or_taxonomy_gap: 4
ambiguous_or_source_gap: 3
guide_or_source_gap: 2
top action source Guide category: industry_boundary_gap 19, broad_sr_overreach 1
```

Interpretation: the remaining 20 cases are not broad alias candidates. In all 20, the top standard-procedure Guide is currently evaluated as acceptable, but the first immediate-action CI comes from a different Guide. The next safe repair is therefore CI/WorkProcess relevance, not risk-feature alias expansion: first prefer existing top-Guide `source_ci_ids` where they already exist, then review local CI support for Guides such as `B-M-36`, `D-C-7`, `G-11`, `A-G-18`, `G-67`, `E-13`, and `P-76`.

## CI Broad SR Guard v4

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_actionability_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_ci_broad_sr_guard4_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/pg_guide_usage_profiles_sync_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/ci_no_action_triage_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/ci_mapping_review_semantic_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/ci_sr_mapping_candidate_review_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/pg_ci_sr_link_candidates_ci_broad_sr_guard4.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_candidate_review_v1.*
ontology-team/06-reasoning/ontology/serving-validation-report-ci_broad_sr_guard4.*
ontology-team/06-reasoning/ontology/serving-workprocess-alignment-ci_broad_sr_guard4.*
```

Summary:

```text
previous accepted baseline: ci_wp_relevance_guard1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5 -> 5
NO_TOP: 88 -> 88
industry_boundary_gap: 0 -> 0
workprocess_mismatch: 5 -> 5
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 16
CI no_action: 497 -> 492
CI context_mismatch: 0 -> 0
CI broad_sr_only: 13 -> 0
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 23 -> 22
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
accepted photo-actionable role overrides: 10
PG guide_usage_profiles sync: PASS, 1,038 rows
PG primary WorkProcess check: missing 0 / cross-guide 0
```

Policy change:

```text
active artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v21.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v21.jsonl
runtime gate:
  immediate-action CI is suppressed for explicit normal/completed/stored/education scenes
  broad SRs and needs_review candidates remain blocked from serving
profile boundary tightened:
  G-91 patient-transfer hoist is exclusive and no longer matches general lifting/crane scenes
  C-C-85 inert-gas purging excludes public indoor CO2 ventilation scenes
  G-44 hand-tool and M-51 noise-control require their own usage terms
status/penalty/SHE/SR/legal asserted mapping/public API impact: none
```

NO_TOP actionability:

```text
total NO_TOP: 88
accepted empty top: 31
source/taxonomy review: 57
runtime repair candidate: 0
manual review: 0
```

Ontology validation result:

```text
snapshot: ontology-team/06-reasoning/ontology/serving-snapshot-ci_broad_sr_guard4.ttl
validation report: ontology-team/06-reasoning/ontology/serving-validation-report-ci_broad_sr_guard4.*
WorkProcess alignment report: ontology-team/06-reasoning/ontology/serving-workprocess-alignment-ci_broad_sr_guard4.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
PG guide_usage_profiles sync: PASS, 1,038 rows
PG photo_actionable / conditional / unmatchable: 631 / 39 / 368
PG primary WorkProcess check: missing 0 / cross-guide 0
```

Interpretation: this pass accepts that some photos still have no scene-relevant KOSHA top Guide. NO_TOP stays at 88 and runtime repair candidates remain 0. Guide mismatch, industry boundary, WorkProcess mismatch, and ontology validation stay stable; CI broad-only, no_action, and boundary queues improve while v10 smoke and actual 240 status behavior remain stable. The next quality target is remaining CI no_action, CI guide-boundary mismatch, and generic CI overreach.

CI no-action triage:

```text
source report: data-team/05-enrichment/eval-data/reports/ci_no_action_triage_ci_broad_sr_guard4.*
total CI no_action: 492
upstream_stage2_3_review: 357
ci_mapping_review: 63
source_or_taxonomy_review: 45
accepted_empty_top: 24
runtime_repair_candidate: 3

triage categories:
  upstream_she_not_actionable_no_sr: 194
  upstream_she_not_actionable_with_sr: 163
  no_top_source_or_taxonomy_review: 45
  top_guide_ci_sr_mapping_gap: 36
  top_guide_ci_has_no_sr_mapping: 27
  no_top_accepted_empty_top: 24
  top_guide_ci_relevance_gate_gap: 3
```

Semantic review of the 63 `ci_mapping_review` rows:

```text
source report: data-team/05-enrichment/eval-data/reports/ci_mapping_review_semantic_ci_broad_sr_guard4.*
guide_selection_mismatch: 21
corpus_gap_or_near_analogy: 21
true_ci_mapping_candidate: 16
safe_or_followup_no_immediate: 5
```

Interpretation: `CI no_action 492` is mostly not a direct CI ranking bug. The immediate runtime repair tail is only 3 cases (`E-31`, `A-G-18`), while the apparent 63-case CI mapping queue shrinks to 16 true CI-SR/candidate mapping candidates after semantic review. The other 47 should be handled as Guide selection/profile issues, source/taxonomy gaps, or accepted safe/follow-up no-action scenes. The largest bucket, 357 cases, still belongs upstream in Stage 2/3 because SHE is not actionable enough to create immediate actions.

CI/SR mapping candidate review for the 16 true candidates:

```text
source report: data-team/05-enrichment/eval-data/reports/ci_sr_mapping_candidate_review_ci_broad_sr_guard4.*
review cases: 16
manual-seeded CI candidates: 16
best candidate still needs mapping review: 16
top Guides: A-G-12 7, B-M-37 2, A-G-11/A-G-6/C-113/D-28/E-G-1/G-11/P-22 1 each
```

Interpretation: the 16 rows now have concrete ChecklistItem review seeds, but they are not asserted PG mappings. Examples include `CI-AG6-006` for knife/cutting, `CI-BM37-140` for conveyor guarding/emergency stop, `CI-C113-130` for icy surfaces, and `CI-P22-027` for dry-cleaning ventilation. Any PG update should import these as candidate/review rows first or apply a tightly reviewed `ci_sr_mapping` patch, then rerun v1~v10 and actual 240.

PG review-only candidate import:

```text
source report: data-team/05-enrichment/eval-data/reports/pg_ci_sr_link_candidates_ci_broad_sr_guard4.*
table: guide_sr_link_candidates
method: ci_candidate_review_v1
mode: apply
raw candidate rows: 62
pre-aggregated rows inserted: 42
distinct CI / SR: 19 / 19
review_status: needs_review
asserted: false
serving-eligible rows: 0
missing Guide/CI/SR refs: 0
ci_sr_mapping inserts: 0
```

Interpretation: the review candidates now exist in PostgreSQL for ontology/audit review, but they cannot affect OHS runtime because `needs_review` is excluded from serving gates. The next step is not to rerank immediately; it is to review these 42 candidate rows, promote only validated rows to a serving-eligible candidate or asserted mapping policy if justified, and then rerun synthetic v1~v10 plus actual 240.

Post-import Stage 2~5 validation:

```text
source report: data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_candidate_review_v1.*
total: 2,360
SHE: TP 1,107 / FN 909 / FP 82
SR: TP 1,414 / FN 270 / FP 211
Guide mismatch: 5
NO_TOP: 88
industry boundary gap: 0
WorkProcess mismatch: 5
CI no_action: 492
CI broad_sr_only: 0
CI needs_review_used: 0
CI guide_boundary_mismatch: 21
```

Interpretation: PG now contains review-only CI/SR candidates, but the runtime-facing evaluation remains stable. The candidate import did not create `ci_needs_review_used` leakage.

## NO TOP Serving Bridge v4

Historical accepted baseline before `ci_wp_relevance_guard1`.

## No Forced Hotwork Gate v1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_no_forced_hotwork_gate1.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_no_forced_hotwork_gate1_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_no_forced_hotwork_gate1.*
ontology-team/06-reasoning/ontology/serving-validation-report-no_forced_hotwork_gate1.*
ontology-team/06-reasoning/ontology/serving-workprocess-alignment-no_forced_hotwork_gate1.*
```

Summary:

```text
previous accepted baseline: context_safe_gate1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 15 -> 8
NO_TOP: 85 -> 90
industry_boundary_gap: 1 -> 1
workprocess_mismatch: 14 -> 7
broad_sr_overreach: 0 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 15
CI no_action: 482 -> 482
CI context_mismatch: 12 -> 12
CI broad_sr_only: 14 -> 14
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 26 -> 26
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 0
accepted photo-actionable role overrides: 10
```

Policy change:

```text
context-required Guide families added on top of context_safe_gate1:
  air_jacket_gas_manifold_welding_support
  small_tank_drum_hot_work
principle:
  현장 사진에 맞는 Guide가 없으면 broad hot-work Guide를 억지로 올리지 않고 NO_TOP으로 남길 수 있다.
status/penalty/SHE/SR/legal asserted mapping/public API impact: none
```

Ontology validation result:

```text
snapshot: ontology-team/06-reasoning/ontology/serving-snapshot-no_forced_hotwork_gate1.ttl
validation report: ontology-team/06-reasoning/ontology/serving-validation-report-no_forced_hotwork_gate1.*
WorkProcess alignment report: ontology-team/06-reasoning/ontology/serving-workprocess-alignment-no_forced_hotwork_gate1.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: `G-76-2011` no longer appears as a repeated WorkProcess mismatch warning. Some chemical/lab cases now correctly remain `NO_TOP` when the current Guide corpus lacks a scene-specific procedure.

## Context Safe Gate v1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_context_safe_gate1.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_context_safe_gate1_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_context_safe_gate1.*
ontology-team/06-reasoning/ontology/serving-validation-report-context_safe_gate1.*
ontology-team/06-reasoning/ontology/serving-workprocess-alignment-context_safe_gate1.*
```

Summary:

```text
previous accepted baseline: corpus_gap_guard1
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 22 -> 15
NO_TOP: 85 -> 85
industry_boundary_gap: 1 -> 1
workprocess_mismatch: 20 -> 14
broad_sr_overreach: 1 -> 0
photo_unmatchable_top_count: 0 -> 0
followup_only_retained_count: 15
CI no_action: 482 -> 482
CI context_mismatch: 11 -> 12
CI broad_sr_only: 14 -> 14
CI needs_review_used: 0 -> 0
CI guide_boundary_mismatch: 26 -> 26
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive / positive_missed / ambiguous_over_promoted: 10 / 2 / 5
serving ontology validation: PASS, hard violations 0, warnings 1
accepted photo-actionable role overrides: 10
```

Policy change:

```text
context-required Guide families added:
  pipe_support_installation_welding
  airborne_infectious_disease_workplace_prevention
safe welding block phrases added:
  착용 완비 / 차광 커튼 / 차광막 / 국소 배기 가동 / 국소 배기 장치가 가동 / 자동 차광 헬멧
status/penalty/SHE/SR/legal asserted mapping/public API impact: none
```

Ontology validation result:

```text
snapshot: ontology-team/06-reasoning/ontology/serving-snapshot-context_safe_gate1.ttl
validation report: ontology-team/06-reasoning/ontology/serving-validation-report-context_safe_gate1.*
WorkProcess alignment report: ontology-team/06-reasoning/ontology/serving-workprocess-alignment-context_safe_gate1.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 1
remaining warning: G-76-2011 repeated workprocess_mismatch 7 cases
primary WorkProcess alignment: 4,715 / 4,715 same Guide
```

Interpretation: `B-M-20-2026`, `H-186-2016`, and `A-G-14-2026` warning queues were resolved without broadening status-level inference. The remaining issue is a narrower `G-76-2011` WorkProcess relevance queue, so the next work should refine Guide/WorkProcess matching rather than add broad aliases.

## SituationFrame Support v2

Source reports:

```text
data-team/05-enrichment/eval-data/reports/situation_frame_artifact_build.v2.*
data-team/05-enrichment/eval-data/reports/situation_frame_eval_report.v2_child_gate1.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_situation_frame_support7.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_situation_frame_support7.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_situation_frame_support7_report.*
```

Artifact build summary:

```text
Stage 3 candidate input: 230
classified candidates: 230
runtime SHE approved update: 0
asserted mapping update: 0
child contexts: 86
Guide support candidates v2 historical: 1
support Guide review:
  accept: 1
  reject: 190
reject reasons:
  manual_child_guide_boundary: 187
  domain_excluded: 2
  domain_mismatch: 1
classification labels:
  taxonomy_gap: 230
  guide_support_only: 112
  ambiguous_confirmation: 117
  true_new_she: 60
  sr_review_needed: 98
```

Frame extraction summary on synthetic v1~v10:

```text
total samples: 2,360
match policy:
  confirmation_required: 880
  guide_support_only: 1,351
  status_safe: 129
collapse queues:
  child_context_available: 528
  broad_parent_without_child: 241
  no_broad_parent: 1,591
Guide support hit samples: 8
```

## Guide Photo Matchability v1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/guide_photo_matchability_audit_v1.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_photo_matchability1.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_photo_matchability1.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_photo_matchability1_report.*
```

Artifact:

```text
serving-team/08-app/backend/app/data/guide_photo_matchability.v1.json
serving-team/08-app/backend/app/data/guide_domain_profiles.json
```

Classification summary:

```text
Guide profiles: 1,038
photo_actionable: 631
photo_conditional_followup: 39
photo_unmatchable: 368
non-field role overrides: 10 field-action Guides retained as photo_actionable
asserted mapping update: 0
SHE/SR/status/penalty impact: none
```

Serving policy:

```text
photo_actionable: can appear as photo-based top standard procedure
photo_conditional_followup: cannot be top; allowed as at most one lower follow-up with explicit management/document context
photo_unmatchable: cannot be photo top; explicit document/measurement/test/health/method context is required for any follow-up
scope: standard_procedures top lane only
not applied to: immediate_actions, SHE status, SR evidence, penalty path
```

## Stage 2~5 Integrated Quality

Source report:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_no_forced_hotwork_gate1.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_no_forced_hotwork_gate1.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_actionability_no_forced_hotwork_gate1.*
```

Summary:

```text
total samples: 2,360
Stage failure counts:
  stage2: 775
  stage3: 1,288
  stage4: 612
  stage5: 564
SHE TP/FN/FP: 1,107 / 909 / 82
SHE recall: 54.9%
SR TP/FN/FP: 1,414 / 270 / 211
SR recall: 84.0%
Guide mismatch: 8
Stage 2~5 NO_TOP: 90
industry_boundary_gap: 1
workprocess_mismatch: 7
broad_sr_overreach: 0
photo_unmatchable_top_count: 0
followup_only_retained_count: 15
CI no_action: 482
CI context_mismatch: 12
CI broad_sr_only: 14
CI needs_review_used: 0
CI guide_boundary_mismatch: 26
```

NO_TOP actionability audit:

```text
total NO_TOP reviewed: 90
accepted empty top: 29
source/taxonomy review: 54
runtime repair candidates: 7
manual review required: 0

actionability groups:
  source_or_taxonomy_review 54
  accepted_empty_top 29
  runtime_repair_candidate 7

runtime repair candidate types:
  situation_frame_support_repair_candidate 5
  guide_usage_profile_repair_candidate 2
runtime repair candidate case ids:
  SYN-V10-0023, SYN-V2-0073, SYN-V3-0061, SYN-V5-0001, SYN-V9-0128, SYN-V9-0181, SYN-V9-0216
```

Interpretation: `NO_TOP` is not automatically a failure. For 29 cases, the safer product behavior is to leave `standard_procedures` empty because the scene is safe-controlled, outside the KOSHA photo-top scope, follow-up/document-only, or known wrong-support territory. For 54 cases, the next step is source/taxonomy review rather than a scoring tweak. Only 7 cases are immediate runtime repair candidates, and those must be handled through Guide usage profile or SituationFrame support evidence.

Synthetic SHE smoke by version:

| Version | Samples | positive / ambiguous / negative | SHE recall | SHE FN | SHE FP | negative specificity | confirmed-risk recall | ambiguous over-promoted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v1 | 120 | 60 / 40 / 20 | 100.0% | 0 | 28 | 42.9% | 48.3% | 6 |
| v2 | 100 | 55 / 25 / 20 | 100.0% | 0 | 10 | 66.7% | 60.0% | 5 |
| v3 | 200 | 120 / 60 / 20 | 100.0% | 0 | 25 | 44.4% | 55.0% | 2 |
| v4 | 80 | 48 / 24 / 8 | 100.0% | 0 | 0 | 100.0% | 52.1% | 1 |
| v5 | 210 | 126 / 63 / 21 | 100.0% | 0 | 0 | 100.0% | 66.7% | 1 |
| v6 | 330 | 198 / 99 / 33 | 100.0% | 0 | 0 | 100.0% | 70.2% | 37 |
| v7 | 330 | 198 / 99 / 33 | 100.0% | 0 | 1 | 97.1% | 68.7% | 7 |
| v8 | 330 | 198 / 99 / 33 | 100.0% | 0 | 3 | 91.7% | 68.7% | 17 |
| v9 | 330 | 187 / 99 / 44 | 100.0% | 0 | 0 | 100.0% | 65.8% | 7 |
| v10 | 330 | 187 / 99 / 44 | 100.0% | 0 | 0 | 100.0% | 42.8% | 0 |
| v1~v9 | 2,030 | 1,190 / 608 / 232 | 100.0% | 0 | 67 | 71.1% | 64.8% | 83 |
| v1~v10 | 2,360 | 1,377 / 707 / 276 | 100.0% | 0 | 67 | 75.7% | 61.8% | 83 |

## Serving Ontology Validation Snapshot

Source artifacts:

```text
serving-team/08-app/backend/app/data/guide_domain_profiles.json
serving-team/08-app/backend/app/data/guide_photo_matchability.v1.json
serving-team/08-app/backend/app/data/broad_sr_policy.json
serving-team/08-app/backend/app/data/situation_context_taxonomy.v21.json
serving-team/08-app/backend/app/data/guide_support_candidates.v21.jsonl
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_ci_broad_sr_guard4.json
data-team/05-enrichment/eval-data/reports/pg_guide_usage_profiles_sync_ci_broad_sr_guard4.json
```

Generated ontology files:

```text
ontology-team/06-reasoning/ontology/serving-policy.ttl
ontology-team/06-reasoning/ontology/serving-snapshot-ci_broad_sr_guard4.ttl
ontology-team/06-reasoning/ontology/serving-validation-shapes.ttl
ontology-team/06-reasoning/ontology/serving-validation-report-ci_broad_sr_guard4.*
ontology-team/06-reasoning/ontology/serving-workprocess-alignment-ci_broad_sr_guard4.*
```

Validation summary:

```text
GuideUsageProfile: 1,038
photo_actionable: 631
photo_conditional_followup: 39
photo_unmatchable: 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 0
accepted photo-actionable role overrides: 10
```

Warning queue:

```text
none
```

Core A-Box sync:

```text
kosha-instances.ttl regenerated from PostgreSQL on 2026-05-14
KoshaGuide: 1,038
ChecklistItem: 54,631
DomainTerm: 7,726
WorkProcess: 9,316
EquipmentSpec: 8,103
DocumentRequirement: 3,435
serving profile primary WorkProcess links: 4,715 / 4,715 aligned
primary_workprocess_not_in_base_ttl: 1,220 -> 0
guide_usage_profiles PG sync: 1,038 / 1,038, missing Guide 0, missing primary WorkProcess 0, cross-guide primary WorkProcess 0
```

## Stage3 Remaining Gap Support v20 Actionable

`stage3_remaining_gap_support_v20_actionable` keeps the `stage3_remaining_gap_support_v19_dropped_tool` status/penalty/SHE/SR boundary and adds two narrow Guide-support-only contexts: `GREENHOUSE_STRUCTURE_FALL` and `DRY_CLEANING_STEAM_PIPE_HOT_SURFACE`. `SYN-V8-0022` now routes to `C-49-2012` safety harness use for greenhouse-frame high-place fall risk. `SYN-V8-0167` now routes to `P-22-2012` dry-cleaning process safety for exposed hot steam-pipe contact-burn risk. Both rows are trigger-backed support only; status, penalty, SHE approval, asserted mapping, and legal SR evidence remain unchanged.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage3_remaining_gap_support_v20_artifacts.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v20_actionable.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_remaining_gap_support_v20_actionable_report_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_remaining_gap_support_v20_actionable.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v20_actionable.*
```

Runtime artifacts:

```text
serving-team/08-app/backend/app/data/situation_context_taxonomy.v20.json
serving-team/08-app/backend/app/data/guide_support_candidates.v20.jsonl
serving-team/08-app/backend/app/services/situation_frame_service.py
```

Remaining `NO_TOP` root-cause audit:

```text
total_no_top: 17
stage2_taxonomy_or_normalization_gap: 11
stage3_she_to_sr_gap: 2
synthetic_fixture_or_safe_controlled_positive: 2
situation_frame_child_context_gap: 1
stage3_she_gap_but_sr_available: 1
```

## Stage3 Remaining Gap Support v19 Dropped Tool

`stage3_remaining_gap_support_v19_dropped_tool` keeps the `stage3_safe_cue_negation_fix2` status/penalty/SHE/SR boundary and adds one narrow Guide-support-only context: `MAINTENANCE_HEIGHT_DROPPED_TOOL`. This fixes `SYN-V8-0323`, a hospital/building high-place maintenance scene with dropped-tool risk, by routing support to `G-60-2012` building management work and `G-44-2011` hand-tool safety instead of exterior-wall painting. Status, penalty, SHE approval, asserted mapping, and legal SR evidence remain unchanged.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage3_remaining_gap_support_v19_artifacts.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v19_dropped_tool.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_remaining_gap_support_v19_dropped_tool_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_remaining_gap_support_v19_dropped_tool.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v19_dropped_tool.*
```

Runtime artifacts:

```text
serving-team/08-app/backend/app/data/situation_context_taxonomy.v19.json
serving-team/08-app/backend/app/data/guide_support_candidates.v19.jsonl
serving-team/08-app/backend/app/services/situation_frame_service.py
```

## Stage3 Safe Cue Negation Fix2

`stage3_safe_cue_negation_fix2` keeps the `stage3_remaining_gap_support_v18_narrow10` status/penalty/SHE/SR boundary and fixes a SituationFrame safe-cue parsing problem. Safe terms such as `LOTO` and `정상` are no longer treated as safe when they appear in negated or contrastive phrases such as `LOTO 미적용`, `밀착 미흡`, or `동료 정상 착용과 대비`. Conversely, trigger-only Guide support is suppressed in safe procedure contexts such as `압력 게이지 0`, `잔압 완전 방출`, `방열 장갑 착용`, and `안면 보호대 착용`.

Resolved NO_TOP cases include silica-dust respirator misuse, binding-machine jam clearing without LOTO, and lab eyewash/shower inspection. The remaining 20 NO_TOP cases are now dominated by Stage 2 taxonomy/normalization gaps in service/healthcare and small-facility domains. Two CI no-action regressions remain in welding samples, so the next algorithm pass should focus on CI fallback/WorkProcess relevance rather than widening status-level risk inference.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_safe_cue_negation_fix2.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_safe_cue_negation_fix2_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_safe_cue_negation_fix2.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_safe_cue_negation_fix2.*
```

Runtime code:

```text
serving-team/08-app/backend/app/services/situation_frame_service.py
```

## Stage3 Remaining Gap Support v18 Narrow10

`stage3_remaining_gap_support_v18_narrow10` keeps the `stage3_remaining_gap_support_v17b_narrow9b` status/penalty/SHE/SR boundary and adds 4 narrow Stage 3 remaining-gap support contexts: industrial washer vibration/crush, garment sharp-object puncture, EV high-voltage battery PPE gap, and cold-room emergency-release failure. It also tightens the existing binding-machine LOTO support row so actual `기계 미정지` and `용지 걸림 제거` wording can match. One resolved industrial washer case moved from `NO_TOP` to `workprocess_mismatch`, so it remains a WorkProcess-quality follow-up instead of being treated as fully solved.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage3_remaining_gap_support_v18_artifacts_narrow10.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v18_narrow10.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_remaining_gap_support_v18_narrow10_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_remaining_gap_support_v18_narrow10.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v18_narrow10.*
```

Runtime artifacts:

```text
serving-team/08-app/backend/app/data/situation_context_taxonomy.v18.json
serving-team/08-app/backend/app/data/guide_support_candidates.v18.jsonl
```

## Stage3 Remaining Gap Support v17b Narrow9b

`stage3_remaining_gap_support_v17b_narrow9b` keeps the `stage3_remaining_gap_support_v16c_narrow8c` status/penalty/SHE/SR boundary and adds 8 narrow Stage 3 remaining-gap support contexts: hair chemical eye exposure, hair-wash neck ergonomics, cashier prolonged standing, pet grooming bite/table fall, binding-machine LOTO, truck-coupling pretrip check, and steam-gun face burn PPE. A broader v17 trial was held back because generic `안전핀` wording overmatched a safe rack-inspection scene and an engine-overhaul waste support row produced a weak waste-collection Guide.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage3_remaining_gap_support_v17b_artifacts_narrow9b.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v17b_narrow9b.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_remaining_gap_support_v17b_narrow9b_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_remaining_gap_support_v17b_narrow9b.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v17b_narrow9b.*
```

Runtime artifacts:

```text
serving-team/08-app/backend/app/data/situation_context_taxonomy.v17b.json
serving-team/08-app/backend/app/data/guide_support_candidates.v17b.jsonl
```

## Stage3 Remaining Gap Support v16c Narrow8c

`stage3_remaining_gap_support_v16c_narrow8c` keeps the `stage2_taxonomy_gap_support_v15_narrow7b` status/penalty/SHE/SR boundary and adds 6 narrow Stage 3 remaining-gap support contexts: wafer-transfer robot sensor bypass, UV sterilizer PPE, silica-dust respirator misuse, yarn-winding hand entry, harvest squatting ergonomics, and adhesive splash eye/face PPE. A v16b EV battery support row was held back because it fixed one NO_TOP case but moved an existing EV battery positive case from an electrical-work Guide to an unrelated welding-fire-blanket Guide.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage3_remaining_gap_support_v16c_artifacts_narrow8c.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v16c_narrow8c.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_remaining_gap_support_v16c_narrow8c_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_remaining_gap_support_v16c_narrow8c.*
```

Runtime artifacts:

```text
serving-team/08-app/backend/app/data/situation_context_taxonomy.v16c.json
serving-team/08-app/backend/app/data/guide_support_candidates.v16c.jsonl
```

## Stage2 Taxonomy Gap Support v15 Narrow7b

`stage2_taxonomy_gap_support_v15_narrow7b` keeps the `stage3_sr_gap_support_v14_narrow6b` status/penalty/SHE/SR boundary and adds 5 narrow Stage 2 taxonomy-gap support contexts: night/lone-worker care monitoring, client aggression emergency response, chemical cleaner PPE/ventilation, lab eyewash/shower inspection, and glutaraldehyde disinfection PPE/ventilation. The first v15 trial overmatched generic PPE wording (`방진마스크`, `니트릴 장갑`, `고글`) in safe/non-related scenes, so accepted `narrow7b` keeps substance/task-specific child aliases and leaves PPE terms only as profile-alignment/trigger evidence.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage2_taxonomy_gap_support_v15_artifacts_narrow7b.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage2_taxonomy_gap_support_v15_narrow7b.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage2_taxonomy_gap_support_v15_narrow7b.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage2_taxonomy_gap_support_v15_narrow7b_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage2_taxonomy_gap_support_v15_narrow7b.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v15.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v15.jsonl
runtime artifacts at v14 acceptance:
  situation_context_taxonomy.v15.json
  guide_support_candidates.v15.jsonl
added support rows: 5
support candidate count: 201 -> 206
child context count: 156 -> 161
Guide mismatch: 136 -> 136
NO_TOP: 52 -> 42
stage2_taxonomy_or_normalization_gap: 20 -> 12
stage3_she_gap_but_sr_available: 11 -> 9
stage3_she_to_sr_gap: 10 -> 10
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 64 -> 64
CI no_action: 487 -> 487
CI guide_boundary_mismatch: 64 -> 64
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 SR Gap Support v14 Narrow6b

`stage3_sr_gap_support_v14_narrow6b` keeps the `stage2_taxonomy_support_v13_narrow5` status/penalty/SHE/SR boundary and adds 13 narrow Stage 3 SHE-to-SR gap support contexts: indoor welding fume respirator gap, sharp metal edge handling, reflow oven residual heat PPE, FOUP stair carrying, excavator slope/signaler gap, confined tank attendant gap, ship heavy-lift sling inspection, vehicle exposed wiring fire gap, scalding tank fall/burn, binding machine jam LOTO, binding machine hotmelt PPE, plate-making chemical PPE, and UV plate-making shielding/PPE. The first v14 trial overmatched short trigger terms (`발판 없이`, generic `슬링/인양`, generic `용접 흄`, generic `보호 장갑 미착용`), so accepted `narrow6b` keeps compound/object-specific triggers. It also marks 2 stale `SOLDERING_ASSEMBLY` rows as `review_only/rejected` because they pointed reflow-oven scenes to explosives/explosion-proof electrical Guides.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage3_sr_gap_support_v14_artifacts_narrow6b.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_sr_gap_support_v14_narrow6b.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_sr_gap_support_v14_narrow6b.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_sr_gap_support_v14_narrow6b_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_sr_gap_support_v14_narrow6b.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v14.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v14.jsonl
default runtime artifacts:
  situation_context_taxonomy.v14.json
  guide_support_candidates.v14.jsonl
added support rows: 13
rejected stale support rows: 2
support candidate count: 188 -> 201
child context count: 143 -> 156
Guide mismatch: 136 -> 136
NO_TOP: 64 -> 52
stage3_she_to_sr_gap: 22 -> 10
stage2_taxonomy_or_normalization_gap: 20 -> 20
stage3_she_gap_but_sr_available: 11 -> 11
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 64 -> 64
CI no_action: 487 -> 487
CI guide_boundary_mismatch: 64 -> 64
status/penalty/SHE approval/asserted mapping update: 0
```

`stage2_3_support_v10_narrow2` keeps the `stage2_3_support_v9_narrow4` status/penalty/SHE/SR boundary and adds six trigger-backed support-only contexts: powered food-slicer cleaning, bakery oven/hot-tray burn, small-server electrical overload, elevated welding fall control, automotive tire/wheel service, and silica-dust blasting. The first v10 trial overmatched high-pressure washing/electrical-panel and safe elevated-welding scenes, so the accepted narrow2 pass removed that seed and tightened food-slicer, elevated-welding, and silica triggers. It reduced NO_TOP by 11 and CI no_action by 1 while keeping Guide mismatch, industry boundary gap, workprocess mismatch, broad SR overreach, photo top gating, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage2_3_support_v9_narrow4` keeps the `stage2_3_support_v8_narrow2` status/penalty/SHE/SR boundary and adds five trigger-backed support-only contexts: sports-facility slip/trip, powered cardio-equipment maintenance, needlestick/sharps disposal, blood-contaminated waste handling, and flammable-chemical smoking. Earlier v9 trials overmatched generic `전원을 끄지 않고`, generic medical-waste wording, and `담배꽁초`, so the accepted narrow4 pass requires specific child context plus unsafe/observable trigger phrases. It reduced NO_TOP by 8 while keeping Guide mismatch, industry boundary gap, workprocess mismatch, broad SR overreach, CI queues, photo top gating, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage2_3_support_v8_narrow2` keeps the `stage2_service_support_v7_narrow1` status/penalty/SHE/SR boundary and adds six trigger-backed support-only contexts: X-ray radiation control, blasting operation, hot-work permit deviation, shipyard/internal welding, soldering assembly, and solvent-waste fire. The first v8 trial overmatched broad `방사선`, `허가서`, `용접 흄`, and `용제` wording, so the accepted narrow2 pass keeps only specific visual/unsafe phrases. It reduced NO_TOP by 11, improved Guide mismatch by 1, industry boundary gap by 1, and CI no_action by 1 while keeping broad SR overreach, workprocess mismatch, photo top gating, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage2_service_support_v7_narrow1` keeps the `stage3_domain_support2_confirmation_gate2` status/penalty/SHE/SR boundary and adds only two trigger-backed support-only service contexts: display/wiring-device electrical maintenance and floor-polisher/stair-cleaner building cleaning. Broad terms such as `DISPLAY_SETUP`, `형광등`, `청소기`, and `출입 통제` were removed after an overmatch trial. The accepted narrow pass reduced NO_TOP by 7 and CI no_action by 3 while keeping Guide mismatch, industry boundary, workprocess mismatch, broad SR overreach, CI queues, photo top gating, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage3_domain_support2_confirmation_gate2` keeps the `stage3_domain_support1_tight1` status/penalty/SHE/SR boundary and only changes Guide usage/domain gating. `confirmation_required` SituationFrame support can satisfy the gate at score `0.54` instead of `0.78` only when it is trigger-backed, backed by a non-broad SR, and child-context/profile-aligned. This reduced NO_TOP by 9 additional cases and reduced `stage3_she_to_sr_gap` from 46 to 37 while keeping Guide mismatch, industry boundary, workprocess mismatch, broad SR overreach, CI queues, v10 SHE smoke, and actual 240 status behavior unchanged.

`stage3_domain_support1_tight1` adds three narrow `guide_support_only` rows to `guide_support_candidates.v6.jsonl`: spray painting fire/explosion, dry-cleaning solvent ignition, and pesticide/greenhouse re-entry. Each row requires a child context plus trigger evidence and stays outside status, penalty, SHE approval, asserted mapping, and legal SR evidence. The pass reduced NO_TOP by 8 additional cases and improved obvious Guide mismatch by 1 while keeping broad SR overreach at 1. CI no_action increased from 492 to 494 but remains under the current gate and did not affect actual 240 status/penalty behavior.

`stage2_support_usage_gate3_safe_lock1` keeps the `stage2_support_usage_gate2b` status/penalty/SHE/SR boundary and narrows SituationFrame safe-cue detection: generic `잠금` is no longer treated as a safe lockout cue for external-lock/entrapment wording. This allows existing `COLD_ROOM_ACCESS` support rows to create cold-room procedures in unsafe lock-in scenes. It reduced NO_TOP by 5 additional cases without increasing industry boundary gap, broad SR overreach, or actual 240 status drift. It does not approve new SHE patterns, insert asserted mappings, or create legal SR evidence.

## Stage2 Taxonomy Support v13 Narrow5

`stage2_taxonomy_support_v13_narrow5` keeps the `stage3_gap_support_v12_narrow4` status/penalty/SHE/SR boundary and adds seven narrow Stage 2 taxonomy-gap support contexts: high-pressure waterjet PPE, UV lamp eye PPE, UV coating ozone respirator, formalin contact PPE, cold-room PPE, crematorium hot-surface PPE, and sharp-fragment hand PPE. The broad trial overmatched cold-room wording, and a global short-token matching guard regressed Guide quality; the accepted pass keeps object-specific triggers and only blocks the confirmed `P-55-2012` single-character `황` false match against words like `상황`.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage2_taxonomy_support_v13_artifacts_narrow5.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage2_taxonomy_support_v13_narrow5.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage2_taxonomy_support_v13_narrow5.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage2_taxonomy_support_v13_narrow5_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage2_taxonomy_support_v13_narrow5.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v13.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v13.jsonl
then-default runtime artifacts:
  situation_context_taxonomy.v13.json
  guide_support_candidates.v13.jsonl
added support rows: 7
support candidate count: 181 -> 188
child context count: 136 -> 143
Guide mismatch: 136 -> 136
NO_TOP: 74 -> 64
stage2_taxonomy_or_normalization_gap: 28 -> 20
stage3_she_gap_but_sr_available: 11 -> 11
stage3_she_to_sr_gap: 24 -> 22
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 64 -> 64
CI no_action: 487 -> 487
CI guide_boundary_mismatch: 64 -> 64
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 Gap Support v12 Narrow4

`stage3_gap_support_v12_narrow4` keeps the `stage2_3_support_v11_narrow3` status/penalty/SHE/SR boundary and adds 13 narrow Stage 3 SHE-gap support contexts for cases where non-broad SRs already exist but no Guide anchor was available. The first v12 trial overmatched safe PPE, high-heat, stair, and electrical-control scenes, so accepted narrow4 keeps only unsafe/object-specific trigger phrases and drops the EV battery seed that moved one case from CI no-action to CI boundary mismatch.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage3_gap_support_v12_artifacts_narrow4.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_gap_support_v12_narrow4.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_gap_support_v12_narrow4.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_gap_support_v12_narrow4_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_gap_support_v12_narrow4.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v12.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v12.jsonl
default runtime artifacts:
  situation_context_taxonomy.v12.json
  guide_support_candidates.v12.jsonl
added support rows: 13
support candidate count: 168 -> 181
child context count: 123 -> 136
Guide mismatch: 137 -> 136
NO_TOP: 94 -> 74
stage2_taxonomy_or_normalization_gap: 28 -> 28
stage3_she_gap_but_sr_available: 28 -> 11
stage3_she_to_sr_gap: 25 -> 24
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 65 -> 64
CI no_action: 489 -> 487
CI guide_boundary_mismatch: 64 -> 64
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2/3 Support v11 Narrow3

`stage2_3_support_v11_narrow3` keeps the `stage2_3_support_v10_narrow2` status/penalty/SHE/SR boundary and adds five narrow Stage 2 taxonomy-gap support contexts: sharp glass manual handling, lead-paint grinding dust, ice-pick fragment eye exposure, climbing-wall fall surface, and chair-stack manual carry. Earlier v11 trials overmatched PPE-only, generic fall-risk, and generic blocked-visibility wording, so accepted narrow3 requires object-specific triggers such as `판유리`, `전동 그라인더`, `아이스픽`, `클라이밍 월`, or `무거운 의자`.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage2_3_support_v11_artifacts_stage2_narrow3.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage2_3_support_v11_narrow3.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage2_3_support_v11_narrow3.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage2_3_support_v11_narrow3_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage2_3_support_v11_narrow3.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v11.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v11.jsonl
default runtime artifacts:
  situation_context_taxonomy.v11.json
  guide_support_candidates.v11.jsonl
added support rows: 5
support candidate count: 163 -> 168
child context count: 118 -> 123
Guide mismatch: 137 -> 137
NO_TOP: 100 -> 94
stage2_taxonomy_or_normalization_gap: 33 -> 28
stage3_she_gap_but_sr_available: 29 -> 28
stage3_she_to_sr_gap: 25 -> 25
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 65 -> 65
CI no_action: 489 -> 489
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2/3 Support v10 Narrow2

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage2_3_support_v10_artifacts_narrow2.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage2_3_support_v10_narrow2.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage2_3_support_v10_narrow2.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage2_3_support_v10_narrow2_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage2_3_support_v10_narrow2.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v10.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v10.jsonl
default runtime artifacts:
  situation_context_taxonomy.v10.json
  guide_support_candidates.v10.jsonl
added support rows: 6
support candidate count: 157 -> 163
child context count: 112 -> 118
Guide mismatch: 137 -> 137
NO_TOP: 111 -> 100
stage2_taxonomy_or_normalization_gap: 35 -> 33
stage3_she_gap_but_sr_available: 34 -> 29
stage3_she_to_sr_gap: 28 -> 25
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 65 -> 65
CI no_action: 490 -> 489
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2/3 Support v9 Narrow4

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage2_3_support_v9_artifacts_narrow4.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage2_3_support_v9_narrow4.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage2_3_support_v9_narrow4.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage2_3_support_v9_narrow4_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage2_3_support_v9_narrow4.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v9.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v9.jsonl
default runtime artifacts:
  situation_context_taxonomy.v9.json
  guide_support_candidates.v9.jsonl
added support rows: 5
support candidate count: 152 -> 157
child context count: 110 -> 112
Guide mismatch: 137 -> 137
NO_TOP: 119 -> 111
stage2_taxonomy_or_normalization_gap: 39 -> 35
stage3_she_gap_but_sr_available: 36 -> 34
stage3_she_to_sr_gap: 30 -> 28
industry_boundary_gap: 71 -> 71
workprocess_mismatch: 65 -> 65
CI no_action: 490 -> 490
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2/3 Support v8 Narrow2

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage2_3_support_v8_artifacts_narrow2.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage2_3_support_v8_narrow2.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage2_3_support_v8_narrow2.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage2_3_support_v10_narrow2_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage2_3_support_v10_narrow2.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v8.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v8.jsonl
default runtime artifacts:
  situation_context_taxonomy.v8.json
  guide_support_candidates.v8.jsonl
added support rows: 6
support candidate count: 146 -> 152
child context count: 104 -> 110
Guide mismatch: 138 -> 137
NO_TOP: 130 -> 119
stage2_taxonomy_or_normalization_gap: 42 -> 39
stage3_she_gap_but_sr_available: 37 -> 36
stage3_she_to_sr_gap: 37 -> 30
industry_boundary_gap: 72 -> 71
workprocess_mismatch: 65 -> 65
CI no_action: 491 -> 490
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2 Service Support v7 Narrow1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage2_service_support_v7_artifacts_narrow1.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage2_service_support_v7_narrow1.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage2_service_support_v7_narrow1.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage2_service_support_v7_narrow1_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage2_service_support_v7_narrow1.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v7.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v7.jsonl
then-default runtime artifacts:
  situation_context_taxonomy.v7.json
  guide_support_candidates.v7.jsonl
added support rows: 2
support candidate count: 144 -> 146
child context count: 102 -> 104
covered Stage2 NO_TOP cases: 5
Guide mismatch: 138 -> 138
NO_TOP: 137 -> 130
stage2_taxonomy_or_normalization_gap: 47 -> 42
industry_boundary_gap: 72 -> 72
workprocess_mismatch: 65 -> 65
CI no_action: 494 -> 491
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 Confirmation Gate v2

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_domain_support2_confirmation_gate2.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_domain_support2_confirmation_gate2.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_domain_support2_confirmation_gate2_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_domain_support2_confirmation_gate2.*
```

Patch summary:

```text
changed files:
  serving-team/08-app/backend/app/services/situation_frame_service.py
  serving-team/08-app/backend/app/services/guide_recommendation_service.py
policy: confirmation_required support can pass Guide usage/domain gates only when trigger-backed, non-broad-SR-backed, and child/profile-aligned
default support threshold: 0.78
confirmation_required support threshold: 0.54
Guide mismatch: 138 -> 138
NO_TOP: 146 -> 137
stage3_she_to_sr_gap: 46 -> 37
industry_boundary_gap: 72 -> 72
workprocess_mismatch: 65 -> 65
CI no_action: 494 -> 494
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 Domain Support v1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage3_domain_support_v6_artifacts_tight1.*
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage3_domain_support1_tight1.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_domain_support1_tight1.*
```

Patch summary:

```text
generated artifacts:
  serving-team/08-app/backend/app/data/situation_context_taxonomy.v6.json
  serving-team/08-app/backend/app/data/guide_support_candidates.v6.jsonl
default runtime artifacts:
  situation_context_taxonomy.v6.json
  guide_support_candidates.v6.jsonl
added support rows: 3
support candidate count: 141 -> 144
child context count: 100 -> 102
asserted mapping update: 0
status/penalty/SHE approval update: 0
```

## SituationFrame Safe-Lock Fix v1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_stage2_support_usage_gate3_safe_lock1.*
data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage2_support_usage_gate3_safe_lock1.*
```

Patch summary:

```text
changed file: serving-team/08-app/backend/app/services/situation_frame_service.py
safe-cue change: generic `잠금` removed from SAFE_TERMS
lockout control cue remains: 잠금표지, 잠금 표지, LOTO, lockout, tagout, 잠근 뒤, 전원 잠금
resolved missing_usage_profile cases: 5
resolved workprocess_mismatch cases: 1
new regressions in diff: 0
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage2 Support Usage Gate v2b

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage2_support_usage_gate_artifacts_v2.*
serving-team/08-app/backend/app/data/situation_context_taxonomy.v5.json
serving-team/08-app/backend/app/data/guide_support_candidates.v5.jsonl
```

Artifact summary:

```text
existing context updates: 6
new support rows: 2
covered Stage2 NO_TOP cases by new seeds: 4
merged support rows: 141
taxonomy child contexts: 102
trigger-only support rows: 5
runtime use: guide_support_only
safe trigger-only suppression: enabled
resolved missing_usage_profile cases in replay: 10
status/penalty/SHE approval/asserted mapping update: 0
```

Rejected sibling experiment:

```text
stage2_support_usage_gate1 reduced NO_TOP more aggressively but regressed Guide mismatch, industry boundary quality, workprocess quality, and broad SR overreach.
Rejected trigger-only rows included display lighting, child outlet, and high-pressure wash style overmatches.
gate2b keeps only narrow support rows that passed v1~v10, v10 smoke, and actual 240 regression.
```

## Stage2 NO_TOP Support v3

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage2_no_top_support_candidates_v3.*
serving-team/08-app/backend/app/data/situation_context_taxonomy.v3.json
serving-team/08-app/backend/app/data/guide_support_candidates.v4.jsonl
```

Artifact summary:

```text
curated Stage2 contexts: 12
added support rows: 12
covered Stage2 NO_TOP cases: 20
merged support rows: 139
taxonomy child contexts: 98
runtime use: guide_support_only
new Stage2 rows require trigger hit: true
status/penalty/SHE approval/asserted mapping update: 0
```

## Stage3 Support Profile Alignment v2

Source reports:

```text
data-team/05-enrichment/eval-data/reports/stage3_support_alignment_aliases_v2.*
serving-team/08-app/backend/app/data/situation_context_taxonomy.v4.json
serving-team/08-app/backend/app/data/guide_support_candidates.v4.jsonl
```

Artifact summary:

```text
seed child contexts: 7
accepted profile-alignment aliases: 18
affected support rows: 15
affected NO_TOP cases: 15
taxonomy child contexts: 98
runtime use: guide_support_only
aliases stored as profile_alignment_aliases: true
runtime extraction alias update: 0
status/penalty/SHE approval/asserted mapping update: 0
```

## NO_TOP Guide Support v1

Source reports:

```text
data-team/05-enrichment/eval-data/reports/no_top_guide_support_candidates_v1.*
serving-team/08-app/backend/app/data/guide_support_candidates.v3.jsonl
serving-team/08-app/backend/app/data/guide_support_candidates.v3.preview.jsonl
```

Artifact summary:

```text
input NO_TOP Stage3 rows: 213
Stage3 candidate input: 230
support candidate rows: 127
covered NO_TOP cases: 136
distinct child contexts: 71
distinct Guide codes: 69
runtime use: guide_support_only
status/penalty/SHE approval/asserted mapping update: 0
parent-only match: blocked
generic term-only match: blocked
```

NO_TOP root-cause audit:

```text
report: data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage2_taxonomy_support_v13_narrow5.*
total_no_top: 64
primary_root_cause:
  stage2_taxonomy_or_normalization_gap: 20
  stage3_she_to_sr_gap: 22
  stage3_she_gap_but_sr_available: 11
  situation_frame_child_context_gap: 7
  synthetic_fixture_or_safe_controlled_positive: 2
  situation_frame_child_support_gap: 2
domain_bucket:
  service_healthcare_people_gap: 21
  chemical_profile_gap: 16
  other_taxonomy_gap: 9
  machine_profile_gap: 7
  construction_fall_profile_gap: 4
  material_handling_profile_gap: 3
  burn_heat_profile_gap: 2
  electrical_profile_gap: 2
situation_frame:
  child_context_available: 26
  broad_parent_without_child: 27
  support_hit_cases: 9
```

Current NO_TOP root-cause audit:

```text
report: data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v19_dropped_tool.*
total_no_top: 19
primary root causes:
  stage2_taxonomy_or_normalization_gap: 11
  stage3_she_gap_but_sr_available: 3
  stage3_she_to_sr_gap: 2
  synthetic_fixture_or_safe_controlled_positive: 2
  situation_frame_child_context_gap: 1
domain buckets:
  service_healthcare_people_gap: 7
  chemical_profile_gap: 4
  other_taxonomy_gap: 4
  construction_fall_profile_gap: 2
  machine_profile_gap: 1
  material_handling_profile_gap: 1
```

## v10 Smoke

Source report:

```text
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_stage3_remaining_gap_support_v18_narrow10_report.*
```

Summary:

```text
v10 cases: 330
SHE recall: 100.0%
SHE false negative: 0
SHE false positive: 0
normal suppression: 100.0%
```

## Actual Response 240 Regression

Source report:

```text
data-team/05-enrichment/eval-data/reports/actual_response_samples_stage3_remaining_gap_support_v18_narrow10.*
```

Summary:

```text
total samples: 240
status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
attention cases: 74
penalty counts:
  conditional: 96
  no_penalty: 94
  direct: 50
```

## Historical Guide Recommendation Baseline

`usage_profile11` remains the historical Guide-only comparison baseline.

```text
synthetic Guide v1~v10 total samples: 2,360
legacy obvious top Guide mismatch: 1,145
usage_profile11 obvious top Guide mismatch: 165
reduction count: 980
reduction ratio: 85.59%
Guide-only NO_TOP: 395
Guide-only attention cases: 560
```

## Operating Note

Broadening status-level risk inference or adding generic text aliases was rejected because it changed actual 240 status boundaries. Broad `UNSAFE_TERMS` widening was also rejected because it reduced NO_TOP only slightly while regressing Guide mismatch and industry boundary quality. Trigger-only domain override was rejected because it reduced NO_TOP but reintroduced broad SR overreach. A broad Stage 2 support attempt also regressed Guide mismatch; accepted support rows are trigger-backed, support-only, and blocked in safe checklist-style contexts. Stage 3 profile-alignment aliases are accepted only because they are not extraction aliases. v14 confirmed the same rule again: short terms like `발판 없이`, `슬링`, `용접 흄`, and `보호 장갑 미착용` overmatch safe or unrelated scenes unless tied to object-specific context. Remaining quality work should use SituationFrame child contexts, Guide usage profiles, visual triggers, review-only SHE/SR support candidates, and WorkProcess relevance. The 230 Stage 3 candidates stay review-controlled; automatic approved SHE promotion and asserted mapping updates remain `0`.


## Corpus Gap Guard v1

Accepted runtime baseline: `corpus_gap_guard1`

Previous accepted baseline: `safe_scene_phrase_gate2`

This pass keeps the status/penalty/SHE/SR boundary unchanged and changes only Stage 5 standard-procedure ranking. It preserves `safe_scene_phrase_gate2` safe-scene suppression and adds compound corpus-gap top-procedure guards so lab exit checklist, medication preparation/disposal, and recycling glass-shard walking scenes are not filled by unrelated broad Guides. Rejected follow-up trials tried to force high-pressure gas-cylinder normal transport into the current Guide layer, but they moved cases to other broad Guides; that topic is deferred to WorkProcess/Guide relevance.

Source reports:

```text
data-team/05-enrichment/eval-data/reports/pipeline_quality_v1_v10_corpus_gap_guard1.*
data-team/05-enrichment/eval-data/reports/industry_boundary_gap_triage_corpus_gap_guard1.*
data-team/05-enrichment/eval-data/reports/synthetic_observations_v10_corpus_gap_guard1_report.*
data-team/05-enrichment/eval-data/reports/actual_response_samples_corpus_gap_guard1.*
```

Summary:

```text
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 22
NO_TOP: 85
industry_boundary_gap: 1
workprocess_mismatch: 20
broad_sr_overreach: 1
photo_unmatchable_top_count: 0
photo_unmatchable_suppressed_count: 29
followup_only_retained_count: 15
top_replaced_by_photo_actionable_count: 27
CI no_action: 482
CI context_mismatch: 11
CI broad_sr_only: 14
CI needs_review_used: 0
CI guide_boundary_mismatch: 26
v10 SHE recall: 100.0%, FN 0, FP 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
remaining industry_boundary_gap triage: C_corpus_or_followup_gap 1
backend compileall: OK
```

NO_TOP root-cause audit for corpus_gap_guard1:

```text
report: data-team/05-enrichment/eval-data/reports/stage2_5_no_top_root_cause_corpus_gap_guard1.*
total_no_top: 85
primary root causes:
  stage2_taxonomy_or_normalization_gap: 39
  situation_frame_child_context_gap: 22
  stage3_she_gap_but_sr_available: 10
  situation_frame_child_support_gap: 5
  stage3_she_to_sr_gap: 4
  synthetic_fixture_or_safe_controlled_positive: 3
  guide_usage_profile_context_gap: 2
```
