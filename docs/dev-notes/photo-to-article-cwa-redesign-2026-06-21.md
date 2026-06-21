# 사진→산업안전보건규칙 조문 매핑 — 백지 재설계 (OWA→CWA) · 2026-06-21

> compact 후 **ultracode 재실행용 자기완결 스펙.** 사용자 지시로 기존 CLAUDE.md/SHE/facet/온톨로지 접근은 이 하위문제(사진→조문)에 한해 **무시·대체**. KOSHA guide/CI 연결은 **별도 트랙(후순위)**.

## 목표
사진 → GPT가 (1) 위험요소 + 해결 체크리스트 추출, (2) 그 위험이 **산업안전보건규칙 조문 몇 조 위반**인지 연결. 지금은 **(2) 조문 연결만** 해결.

## 비싸게 얻은 교훈 (반복 금지)
- **facet 매핑 = 1.9% (사망).** 거친 코드(accident_type=FALL)는 article 변별 불가. ≥2축 게이팅·top-N 절단·자석 prune 다 무효(precision@1 천장 6%, recall 반토막).
- **배포된 semantic(hybrid_search 'sr', config ON) = P@1 18%.** 내 초기 "1.9% 고장" 주장은 facet 경로 측정 착오였음(정정됨). 실제 서빙은 18% 수준.
- **gold-reuse(scene→이웃 kNN) = 합성벤치 58%지만 실제 사진 8장에선 배포(18%)와 wash.** 합성에선 쌍둥이 이웃 베끼기, 실제(이웃sim 0.56~0.75)에선 generic 조(제3 전도·제32 보호구·제42 추락)로 후퇴. 배포 semantic은 도리어 특정조(제186 고소작업대·제380 철골·제342 굴착기계)를 집음 → **상보적, 어느 쪽도 단독 승자 아님.**
- **retrieve→LLM rerank = 합성 76%지만 실제선 과보수**(화재사진에 화재조 전부 드롭, 추락사진에 제42 드롭하고 제32만 남김). rerank 기준도 합성에 overfit.
- **∴ 합성+LLM라벨 수치는 전부 신기루.** 신뢰 지표는 **실제 사진 + 사람 확정 라벨**에서만.

## 새 아키텍처 — 조문 분류체계로의 OWA→CWA (사용자 통찰)
**핵심:** 산업안전보건규칙 674조 = 수십 년 산재 경험으로 다져진 "사람이 다치는 방식"의 **완전한 닫힌 카테고리**. 사진의 복합위험 = 그 카테고리들의 **조합**. 문제 = 열린세계(사진)→닫힌세계(조문) **다중라벨 분류**. 합성장면 대리 폐기, 기준점은 **조문 자체**.

실패의 근본 = 사진 *관찰언어* ↔ 조문 *법조문체* 간극. 해법 = 조문을 관찰언어로 변환해 같은 언어에서 매칭.

### 파이프라인
1. **674조 관찰가능/비관찰 분류.** 관찰가능 조문(시각 탐지 가능)만 타깃. 비관찰(안전교육·작업계획서·자격·기록보존 등)은 사진→조문 대상에서 제외(정밀도↑, 과거 miss 일부 설명).
2. **닫힌세계 인덱스 = 조문별 "관찰 시그니처"** (합성 장면 아님). 예:
   ```
   제42조 원문(법조문체): "근로자 추락위험 … 작업발판·안전난간·추락방호망·안전대 …"
     → 시그니처: {맥락: 2m↑ 고소작업(비계·지붕·개구부·고소작업대),
                  시각징후: 단부 안전난간 없음/안전대 미연결/추락방호망 없음,
                  결여조치: [안전난간, 추락방호망, 안전대]}
   ```
   LLM batch 생성 + 사람 전수 spot-check(674는 유한 → 검수 현실적). KB가 규칙북에서 나오니 합성→실제 전이문제 KB쪽 소멸.
3. **추출(Stage1, Vision):** 위험을 조문 형태로 — `{설비/작업맥락, 관찰된 위험상태, 결여된 안전조치(법정어휘), 위치, checklist}`. 프롬프트 3원칙: (a) "설비+결여조치" 쌍 분해, (b) 규칙 통제어휘(작업발판·안전난간·방호장치·추락방호망…) 주입해 단어 정렬, (c) "결여 조치" 강제 출력.
4. **매핑(Stage2):** 추출 ↔ 674 시그니처 **전수 매칭**(닫힌세계라 유한·열거가능 → recall 천장 소멸) + **편/장/절/관 계층 boost**(같은 관=복합위험 조합 자연복원) → 후보 → LLM 확정.
5. **검증:** 실제 사진 + 사람 라벨. `real-test-photo/` 8장(+30~50 확보). LLM은 후보만, **최종 판정 사람**(순환 차단).

### #3 답 (프롬프트 vs RDB)
**LLM 주력(조문 전문 직접 읽음) + RDB는 캐시.** 순수 RDB는 위험을 키로 환원 → 변별정보(미묘한 조문 텍스트) 소실 = facet 1.9% 재현. 미세 RDB 손큐레이션은 브리틀. **"LLM이 매칭, RDB가 기억"**(확정 매핑 적재 → 흔한 위험 점점 결정적 처리, LLM은 꼬리).

### #4 답 (모델)
이론으로 못 정함 → **8장 모델 스윕 실측**: Stage1 추출에 4.1 vs gpt-5-mini/nano vs gpt-5.4-mini/nano 비교(위험 누락률·결여조치/설비 용어 정확도). Stage2 매핑은 추론이라 강한 모델(gpt-5.4급) 유리. 추출 완전성=매핑 상한이라 Stage1 절약은 신중.

## 기존 자산
- **실제 사진 8장 Vision 출력:** `data-team/05-enrichment/runtime-artifacts/claude_vision_8photo_input.json` ({photos:[{photo,industry,result:{visual_observations,visual_cues,hazards[]}}]}). 사진 원본 `real-test-photo/`(gitignore).
- **합성 gold(dev-eval 전용, 실측 무효):** `claude_gold_v2.jsonl`(2360)·`gpt_gold.jsonl`(1292)·`final_gold.jsonl`(core∪tiebreak-yes). 장(章) 기반 라벨링 *방법*은 재사용 가능(규칙북 기반).
- **배포 semantic 인프라(ON):** `app/services/hybrid_search.py`(BM25+dense, 컬렉션 'sr'/'guide'/'guide_section'), `hazard_to_guide_service.py`(semantic+rerank+continual cache), `guide_embedding_filter.py`. config `OHS_ENABLE_HYBRID_SEARCH/SEMANTIC_RERANK=True`.
- **이번 세션 스크립트(serving-team/08-app/backend/scripts/):** sim_broad_gating·prototype_semantic_rerank·eval_knn_generalization·eval_rerank_ceiling·eval_recall_boost·eval_final_gold·eval_deployed_vs_goldreuse·real_photo_transfer·real_photo_hybrid·adjudicate_gold·tiebreak_gold_gpt·build_semantic_article_index·draft_magnet_pruning. + `app/services/semantic_article_service.py`(프로토타입). 임베딩 캐시 semantic_proto_emb.npz / semantic_kb.*.
- PG: `docker exec kosha-pg`(mcp__postgres 아님). RULE 조문 674(full_text 653). DATABASE_URL=postgresql://kosha:1229@localhost:5432/kosha. venv .venv/bin/python. WSL은 /mnt/c/.

## ultracode 첫 실행 순서 (제안)
1. **674조 관찰가능/비관찰 분류** (LLM batch + 규칙) → 타깃 부분집합.
2. **관찰가능 조문 → 관찰 시그니처 생성** (LLM batch) + 사람 spot-check 샘플.
3. **8장 실제 라벨 시트** (장 후보+조문 전문 묶음) → 사람 확정 = 첫 실제 gold.
4. **시그니처-전수매칭을 8장에 측정** vs 배포 semantic 18% — 향상 가설 검증.
5. (가설 성립 시) Stage1 모델 스윕 + RDB 캐시 + 실서빙 통합 검토.

## 불변 원칙
- 모든 핵심 수치는 **실제 사진 + 사람 라벨**에서만 신뢰. 합성은 dev-loop 전용.
- LLM은 후보 생성/매칭, **ground truth·최종 gold는 사람.**
- 닫힌세계(674조)는 유한 → 전수·검수가 닫힘(무한 사진 라벨링 회피).

---

## 진행 현황 (2026-06-21 실행)

### ①+② 완료 — 닫힌세계 인덱스 구축
- **build_article_signatures.py** (batch `batch_6a378503...`, 653/653 성공). 조문 → 관찰 시그니처
  {observable, context, equipment, visual_cues, required_measures, **violation_scene**}.
  - 관찰성 분포: **yes=64, partial=472, no=117**. no(117)=목적·정의·교육주지·점검주기·압력설정 등 행정/측정 → 사진 타깃서 제외.
  - 편 분포: 편2 안전기준 관찰최다(yes54/par245), 편3 보건 no78(분진·화학·소음 사진불가) — 합리적.
  - 산출 `article_signatures.jsonl`(653). 모델 gpt-5.4.
- **embed_article_signatures.py** → 관찰가능 536개 `violation_scene`+context+cues+measures 임베딩
  `article_sig_emb.npz`(536×3072, text-embedding-3-large) + `_meta.json`. = 닫힌세계 retrieve 인덱스.

### 8장 정성 비교 (라벨 전, plausibility만 — 측정 아님)
- **match_photos_to_articles.py** → `match_compare.md` + `label_sheet.csv`(174행) + `label_sheet_meta.json`.
- 시그니처 매칭이 **배포 semantic의 off-domain 치명오답 제거**: 고소대작업→배포는 제545 스쿠버잠수·제561 환기·제523 공기부피(오답), SIG는 제186 고소작업대·제42 추락. 영세제조→배포 제121 사출성형기 누락+제495 석면해체(오답), SIG 제121 #1. 포크레인→SIG 제200접촉방지·제375/344유도자.
- 배포 우세: 안전대길이(철골)→배포 제380 철골조립·제42, SIG는 일반추락(가설통로/계단) 후퇴 ← 계층 boost 후보(--knn-boost 미검증).
- 양쪽 약함: 음식점주방(규칙에 주방 조문 부재, 둘 다 가스용접 유사조로 후퇴 = 정직한 도메인갭).
- **주의: 위는 전부 내 타당성 판단. 신뢰 수치 아님.**

### 다음 관문 = ③ 사람 라벨 (HITL, 진행 대기)
- `label_sheet.csv`: photo·article_code·title·section·observable·sources(SIG#/DEPL#)·sig_sim·violation_scene·full_excerpt·**LABEL(빈칸)**. UTF-8-BOM(Excel 한글 OK).
- 사람이 `real-test-photo/` 사진 보며 LABEL=y(위반성립)/n(무관)/m(애매) 기입 + 놓친 조문은 행 추가(y). = 첫 실제 gold.
- → **score_label_sheet.py** 로 SIG vs DEPL 동일-gold 채점(P@1/Hit@k/R@k). 이게 18% 대비 진짜 비교.

### 신규 스크립트(이번 실행, 미커밋)
build_article_signatures · embed_article_signatures · match_photos_to_articles · score_label_sheet (serving-team/08-app/backend/scripts/).
산출물 article_signatures.jsonl / article_sig_emb.npz / label_sheet.csv 등은 runtime-artifacts.

---

## ★ 기인물(起因物) 앵커 — 사용자 통찰 검증 (2026-06-21, 실제 라벨 측정)

사용자가 8장 라벨링 중 도출: "가장 먼저 사고를 일으킬 **기인물**을 찾으면, 산업안전보건규칙에서
그 기인물을 정의하는 조문을 찾기 쉽다." → 규칙의 편/장/절/관이 대부분 **기인물별 분류체계**
(절8 사출성형기, 절10관2 지게차, 절12관1 차량계건설기계, 절9관2 크레인 …)이기 때문.

**첫 실제 측정(8장, 사람 gold y=20). 4-way 비교:**

| 지표 | DEPL(배포 hybrid 'sr') | SIG(자유 의미매칭) | **GIMULMUL(기인물앵커)** |
|---|---|---|---|
| P@1 | 12.5% | 25.0% | **62.5%** |
| Hit@3 | ~50% | ~75% | **100%** |
| Hit@5 | 62.5% | 87.5% | 100% |
| R@5 | 33.3% | 40.6% | **72.9%** |
| R@10 | 39.6% | 57.3% | 72.9% |

- 합성 아님 — **실제 사진 + 사람 라벨**. SIG 대비 P@1 2.5배, Hit@3 100%(전 사진 top-3 내 정답).
- gold 패턴 확정: ①기인물-정의 조문(기인물 전용 절/관) + ②횡단 일반의무(제32 보호구·제42~44 추락·제3 전도·제20 출입금지). 제186 고소작업대·제183 지게차 좌석안전띠·제121 사출성형기·제103 프레스 = 전형적 기인물조문.
- 파이프라인: 사진→기인물 식별(RESOLVE)→절/관 group_key→후보(그룹 관찰조문 ∪ 횡단)→LLM 랭킹(RANK). 536조→25~40 후보로 국소화 = recall 천장 소멸 + P@1 급등.
- 정밀화 2레버(효과 확인): (a) **기인물 전용 조 > 횡단 일반의무** 우선, (b) **기인물 식별 후 그 설비 전체 의무 점검**(시각 미강조여도 maybe) → 제183 좌석안전띠 회수, Hit@3 87.5%→100%, R@5 62.5%→72.9%.
- 남은 P@1 미스(지게차·화재·음식점): 횡단조문(제3 전도·제22 통로)이 rank1 — 오답 아니라 시각적으로 더 확실한 케이스(gold는 기인물조문 우선). 음식점=도메인갭(규칙에 주방 조문 없음, 제232/245가 최근접).
- **주의: 8장/20라벨 = 소표본. 방향성 확정이지 정밀수치 아님. 견고화엔 라벨 사진 확충 필요.**

### #3 답 갱신 (프롬프트 vs RDB)
**RDB가 핵심 역할로 부상.** 기인물→절/관 매핑은 규칙 구조 자체라 **결정적 RDB 조회**(gimulmul_index.json).
LLM은 (1)사진→기인물 식별, (2)좁혀진 후보 내 랭킹만. = "RDB가 기인물 국소화, LLM이 식별·확정". 순수 facet-RDB(1.9%)와 다른 점=기인물 절/관이 이미 사고경험 카테고리라 변별력 보존.

### 기인물 신규 스크립트(미커밋)
build_gimulmul_index.py (절/관→기인물 인덱스) · gimulmul_match.py (RESOLVE→ASSEMBLE→RANK→채점).
산출 gimulmul_index.json / gimulmul_match.md.

### 다음 후보
1. **Stage1 기인물-first 재추출 + 모델 스윕(#4)**: 실제 8장 사진을 기인물-first 프롬프트로 4.1 vs gpt-5-mini/nano vs 5.4-mini/nano 재추출 → 앵커매칭 → 추출완전성·P@1 비교 (= 병렬 fan-out, Workflow 적합).
2. **violation_scene 과대추론 수정**: 사람 가정 서술 → 설비-상태 기준 재생성(기인물앵커가 의존 낮추나 인덱스 품질 개선).
3. **라벨 사진 확충**: 8→30~50장 (정밀수치 병목).
4. 서빙 통합(기인물 RESOLVE+RANK를 hazard_to_guide 경로에).

---

## ★ #4 모델 스윕 결과 (2026-06-21, 8장·매칭단 고정 gpt-5.4)

8장을 기인물-first 프롬프트로 6모델 재추출(`model_sweep_extract.py`)→매칭(`model_sweep_score.py`, RESOLVE+RANK gpt-5.4 고정). gpt-5-nano는 reasoning_effort=low+16k 토큰 필요(기본 4k는 빈응답).

| Stage1 모델 | P@1 | Hit@3 | Hit@5 | R@5 | 평균기인물 |
|---|---|---|---|---|---|
| gpt-4.1 | 37.5% | 62.5% | 75.0% | 35.4% | 2.0 |
| gpt-5-mini | 37.5% | 50.0% | 62.5% | 30.2% | 4.6(장황) |
| gpt-5-nano | 50.0% | 62.5% | 87.5% | 38.5% | 3.1 |
| gpt-5.4-mini | 25.0% | 37.5% | 87.5% | 53.1% | 3.1 |
| gpt-5.4-nano | 25.0% | 37.5% | 37.5% | 19.8% | 3.4(불안정) |
| gpt-5.4 | 37.5% | 50.0% | 100% | 59.4% | 3.4 |

**#4 답 (8장, 변동성 큼):**
- **Stage1 모델은 병목 아님.** P@1 성공은 거의 전 모델 공통(고소대작업·영세제조 전원✓, 포크레인 4모델). gpt-5-nano의 50%는 **프레스 1장**(프레스↔사출 구분 유일 성공)이 전부 = 1장 노이즈.
- gpt-5.4-nano만 명확히 불가(기인물 오인 전파: 포크레인→컨베이어, 지게차→크레인 / Hit@5 37.5%). 나머지는 8장 내 구분 불가.
- **4.1 대체 가능성: gpt-5-nano(저렴·동급)·gpt-5.4-mini(Hit@5 87.5%·R@5 53%) 후보지만 8장으론 확정 불가.** 모델 교체 결정엔 30~50장 필요.
- **부가발견: 모든 GPT 기인물-first 재추출이 기존 Claude rich 추출(P@1 62.5%/Hit@3 100%)을 못 넘음.** Claude가 안전대길이(제44 rank1)·프레스(제103 rank1)를 잡은 걸 GPT들은 놓침. → 추출 *풍부함/정확도*가 모델tier보다 중요. 기인물-first 터스 포맷 + 프레스↔사출 혼동이 GPT 발목.
- **진짜 병목 = Stage2 "절-내 변별".** 4장(지게차·안전대길이·화재·음식점) 전 모델 P@1 0인데 Hit@5는 높음 → 정답이 top-5엔 있으나 형제조문(제42/43/44, 제243/244/245, 제232/227) 중 정확한 1위 선택 실패. + gold 8장 소표본.

### #4 확장 — Claude 모델 추가 (사용자 요청: haiku/sonnet 키 보유)
같은 기인물-first 프롬프트·스키마로 Claude 3모델 재추출(`claude_sweep_extract.py`, tool-forcing). 9모델 일괄 채점(LLM 비결정성으로 GPT 수치 ±소폭 변동).

| Stage1 모델 | P@1 | Hit@3 | Hit@5 | R@5 | R@10 |
|---|---|---|---|---|---|
| gpt-4.1 | 37.5% | 62.5% | 75.0% | 35.4% | 61.5% |
| gpt-5-mini | 37.5% | 50.0% | 75.0% | 36.5% | 49.0% |
| gpt-5-nano | 50.0% | 50.0% | 87.5% | 38.5% | 65.6% |
| gpt-5.4-mini | 25.0% | 62.5% | 75.0% | 40.6% | 59.4% |
| gpt-5.4-nano | 25.0% | 37.5% | 50.0% | 26.0% | 40.6% |
| gpt-5.4 | 37.5% | 50.0% | 100% | 63.5% | 66.7% |
| claude-haiku-4-5 | 25.0% | 50.0% | 75.0% | 42.7% | 53.1% |
| claude-sonnet-4-6 | 50.0% | 62.5% | 75.0% | 42.7% | 55.2% |
| claude-opus-4-8 | 37.5% | 75.0% | 87.5% | 47.9% | 52.1% |

**★ 핵심 disentanglement: 모델/제공자는 병목 아님, 추출 포맷이 변수.**
- Claude 기인물-first도 GPT와 같은 밴드(P@1 25~50%). sonnet 50%(공동1위)·opus Hit@3 75%(최고)지만 GPT 대비 결정적 우위 없음.
- 앞서 기존 Claude rich 추출 62.5%는 **모델이 아니라 rich 포맷 덕**: 같은 Claude라도 터스 기인물-first면 ≤50%. → Claude-rich(62.5%) vs Claude-터스(sonnet50/opus37.5/haiku25) = 포맷 효과 모델내부 분리 확인.
- **처방: 기인물 구조 + 풍부한 장면묘사(visual_observations/cues) 둘 다 유지.** 터스 기인물-only가 matcher 입력 신호를 깎음.
- 안전대길이+opus = 기인물 0개(퇴화) 1건.

### #4 신규 스크립트(미커밋)
model_sweep_extract.py · model_sweep_score.py · claude_sweep_extract.py. 산출 model_sweep_extractions.json / model_sweep.md / model_sweep_results.json.

### 재정렬된 다음 레버 (우선순위 수정)
1. **Stage2 절-내 변별 강화** ← 진짜 병목. 형제조문 discriminator(제42 작업발판 vs 제43 개구부 vs 제44 안전대 vs 제45 지붕; 제243 소화 vs 제244 방화 vs 제245 화기사용). RANK에 형제 대조 단계 추가.
2. **라벨 사진 확충 8→30~50** ← 모든 수치의 변동성 병목.
3. 서빙 통합 / violation_scene 수정(후순위).

---

## ★ A 최적 파이프라인 시도 = NEGATIVE RESULT (2026-06-21)

처방(rich+기인물 추출 + 결여조치↔요구조치 measure-aware RANK)을 구현·측정. **기존 62.5%를 못 넘고 후퇴.**

| 파이프라인 | P@1 | Hit@3 | Hit@5 | R@5 |
|---|---|---|---|---|
| **기존: claude_vision 추출 + 기인물앵커 + plain RANK** | **62.5%** | **100%** | 87.5% | 72.9% |
| 신규 rich+기인물(sonnet) + plain RANK | 37.5% | 62.5% | 75.0% | 42.7% |
| 신규 rich+기인물(sonnet) + measure-aware RANK | 37.5% | 75.0% | 87.5% | 44.8% |
| 신규 rich+기인물(gpt-5.4) + measure-aware | 37.5% | 50.0% | 62.5% | 32.3% |

**진단(ablation으로 분리):**
- plain≈measure-aware(둘 다 37.5%) → **RANK 변경은 중립**. measure-aware는 틀린 기인물 식별을 못 고침(추출이 "사출"이면 절8로 직행).
- **후퇴 원인 = 추출.** 내 재추출(GPT·Claude, 터스든 rich+기인물이든)이 기존 claude_vision 추출보다 못함. 잃은 2장: 프레스(재추출이 사출성형기로 오인→제121, 기존은 제103 rank1) + 안전대길이(제44 안전대를 1위 못잡음, 기존은 제44 rank1).
- 프레스↔사출 혼동은 대부분 모델 공통(gpt-5-nano만 예외). 기존 claude_vision 추출은 프레스 정확(파일명 힌트 가능성 or 더 나은 프롬프트).

**결론: 기존 추출 + 기인물 앵커(62.5%/Hit@3 100%)가 검증된 최선.** 재추출·RANK 엔지니어링은 8장에서 이득 없음(오히려 손해). 진짜 레버는 ①라벨 사진 확충(노이즈 탈출) ②추출의 confusable 설비 변별(프레스/사출, 안전대 granularity) — 단 둘 다 더 많은 라벨 데이터로만 검증 가능. **8장에서의 추가 프롬프트 튜닝은 과적합이므로 중단.**

### A 신규 스크립트(미커밋)
optimal_extract.py (rich+기인물) · optimal_match.py (measure-aware + --plain ablation). 산출 optimal_extractions.json / optimal_match.md.

### 서빙 가능 상태
검증된 파이프라인 = 기존 Vision 추출 → build_gimulmul_index(절/관=기인물) → RESOLVE(gpt-5.4)→ASSEMBLE(절/관∪횡단)→RANK(gpt-5.4). P@1 62.5%·Hit@3 100%. 서빙은 top-3 제시 형태가 적합(Hit@3 100%).
