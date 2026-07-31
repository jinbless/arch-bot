# Track A 조문 후보 — 스테이징 플래그 on 실증 + 프론트 후보 패널 (2026-07-31)

배선 자체는 [`cf325ce`](../../serving-team/08-app/backend/app/services/cue_article_service.py)에서 끝났고(기본 off), 이 문서는 **실제로 켜서 사진을 통과시킨 결과**와 **화면 노출**을 기록한다.
검증 근거 정본은 [evaluation-baseline](../status/evaluation-baseline.md) 최상단(RANK A/B v2), 경위는 [rank-ab-cuepool-union](rank-ab-cuepool-union-2026-07-29.md).

> **이 문서의 강도**: 아래는 "기능이 서빙 경로에서 동작한다"는 **스모크 수준의 확인**이다. 사진 3장(개발용 데모 사진, 위반 없는 사진 0장)이므로 정확도·오탐에 대한 어떤 수치 주장도 여기서 하지 않는다. 연구 v2의 P@1·Hit@5는 **연구 하네스 구성**(고정 Vision 캐시, 연구 intake 프롬프트)에서 나온 값이라 서빙 파이프라인(다른 Vision 프롬프트·스키마)으로 그대로 전이된다는 근거는 아직 없다.

## 1. 실증 방법 — 기존 스택 불침습

로컬 compose 스택(`ohs-backend` :8000)은 **건드리지 않고**, 같은 이미지에 소스만 마운트한 임시 컨테이너를 띄워 on/off를 나란히 돌렸다.

```bash
docker inspect ohs-backend --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -v '^$' > /tmp/cue_env
docker run -d --name ohs-backend-cue --network ohs_ohs-network -p 127.0.0.1:8010:8000 \
  --env-file /tmp/cue_env -e CUE_ARTICLES=1 -e CUE_ARTICLE_RANK=1 \
  -v /mnt/c/project/arch-bot/serving-team/08-app/backend:/app \
  -v /mnt/c/project/arch-bot/shared/reference:/app/shared/reference:ro \
  ohs-backend:airgap
rm -f /tmp/cue_env
```

- env를 **원본 컨테이너에서 승계**하므로 사람이 DATABASE_URL/OPENAI_API_KEY를 열어볼 일이 없다(값은 파일로 잠깐 존재했다가 삭제 — 절차상 노출을 없앤 것이지 시크릿이 디스크에 안 닿았다는 뜻은 아니다).
- 소스 bind-mount → 이미지 재빌드 없이 최신 코드로 검증. 대조군은 같은 명령에 `CUE_ARTICLES=0`(포트 8011), RANK만 끈 구성은 `CUE_ARTICLE_RANK=0`(포트 8012).
- 요청: `POST /api/v1/analysis/image` (multipart `image`), 사진은 `real-test-photo/`.

## 2. 결과 — 사진 3장 전부 200, 후보가 실제로 붙는다

| 사진 | e2e | 노출 후보 | 상위 3 (applies · 출처) |
|---|---|---|---|
| 지게차 | 61.4s | 10 | 제172조 접촉의 방지(yes·큐레이션) · 제22조 통로의 설치(yes·횡단) · 제3조 전도의 방지(yes·횡단) |
| 고소작업대 | 31.0s | 4 | 제186조 고소작업대 설치 등의 조치(maybe·기인물) · 제44조 안전대의 부착설비 등(maybe·횡단) · 제14조 낙하물(maybe·횡단) |
| 프레스 | 34.1s | 9 | 제93조 방호장치의 해체 금지(yes·기인물) · 제87조 원동기·회전축(yes·기인물) · 제91조 고장난 기계의 정비(maybe·기인물) |

기인물이 곧바로 상위 조문으로 이어졌다. 다만 **상위 조문의 출처는 대부분 기인물 앵커(큐레이션/기인물) 경로**이지 cue-pool 매칭이 아니다 — 이 3장만으로 "cue-pool이 상위 정확도를 만들었다"고 말할 수 없다. cue 기여도 분리는 연구 하네스(A/B)의 몫이다.

## 3. 무회귀 대조군 — 그리고 trace 비교가 왜 근거가 못 되는가

flag off(8011)에서 동일 사진: `article_candidates = []`(키는 존재), **응답 키 집합 차이 없음**, e2e 58.1s.

`reasoning_trace.articles`는 on/off 모두 30개인데 집합이 달랐다. 이걸 회귀로 읽으면 안 된다 — **flag off끼리 두 번 돌려도 교집합 15/30**이다. 매 요청 Vision을 다시 부르므로 관찰 자체가 매번 달라진다. 따라서:

- ❌ 무회귀 근거로 쓸 수 없는 것: on/off의 trace.articles·guides 개수 일치 여부
- ✅ 실제 근거: ① 후보 계산이 `run_input.result`만 읽고 `article_ids`/`knowledge`를 **바꾸지 않음** ② 응답 키 집합 동일 ③ flag off → 빈 배열 ④ 단위 테스트 4종(`tests/unit/test_cue_article_service.py`)
- ⚠️ 단, **PG 세션은 공유한다**(RANK 프롬프트용 조문 전문 조회). 초기 구현은 그 쿼리가 실패하면 세션이 오염된 채 분석 저장까지 500이 될 수 있었다 → 예외 경로에 `db.rollback()` 추가로 격리(§7).

## 4. 한계비용 — Vision과 분리해 계측 (하한선)

e2e 차분(61.4 vs 58.1s)은 Vision 변동(29~61s)에 묻혀 의미가 없다. 컨테이너 안에서 후보 경로만 3회 계측:

| | rep1 | rep2 | rep3 |
|---|---|---|---|
| RESOLVE | 2.27s | 1.91s | 1.92s |
| RESOLVE+RANK 전체 | 5.08s | 3.45s | 3.52s |

**+3.5~5.1초 · LLM +2회.** 단 이 측정은 **후보 4개짜리 최소 케이스(고소작업대) 1장**이라 하한선이다 — 후보 50개짜리 사진의 RANK 프롬프트는 훨씬 길다. 후보 집합은 3회 모두 동일(제186·44·3·14조), 상위 2개 순서만 흔들렸다.

## 5. "제42조가 왜 없지?" — 후보에는 있었고 랭커가 뺐다

고소작업 사진에서 hazards에 추락이 있는데 제42조(추락의 방지)가 안 보였다.

- 결정론 후보(RESOLVE 제외)만 44개, **제42조 포함** → 랭커가 `applies=no`로 판정해 노출에서 빠진 것
- 단, 제42조는 CROSS 상수라 **모든 사진에 무조건 들어간다** — "후보에 있었다"는 사실이 후보생성의 정상성을 증명하진 않는다
- 배제가 타당해 보이는 정황: Vision 관찰문에 난간·안전모·안전벨트 착용이 기술돼 있다. 다만 랭커의 `no`는 "의무를 충족했다"가 아니라 "무관하다"는 출력이므로, 이걸 **정당한 판단으로 확정할 수는 없다**(사람 판정 없음)
- 이 사진의 노출 4개는 전부 `maybe`, yes 0건이었다. 이걸 "기권 문제가 완화됐다"로 읽으면 안 된다 — ① 표본은 양성 사진 1장인데 기권 리스크는 음성 사진의 문제고 ② 음성 9장 실측(`neg_fp_results.json`)은 abstain 0.0·사진당 평균 7.1건 노출·top1 확정오탐 27.8%로 반대 방향이며 ③ 화면은 `maybe`도 목록에 그대로 올리므로(배지 강도만 다름) yes 억제가 노출량을 줄이지 않는다. 같은 관측은 "위반 가능성 있는 사진에서 yes를 하나도 못 냈다(리콜 실패)"로도 읽힌다

## 6. RANK off 구성은 검증 대상이 아니다

`CUE_ARTICLES=1, CUE_ARTICLE_RANK=0`(포트 8012)로 실측: 후보 **52개**가 조문 번호 순으로 그대로 나온다(출처 분포 횡단 15·기인물 14·단서 11·큐레이션 6·흐름 6). CROSS 16조가 항상 주입되므로 **후보가 비는 일은 없다**.

연구 v2가 검증한 것은 **RANK on 구성**이다. RANK off는 비용 절감용 축소 모드일 뿐 근거가 없으므로, 켠다면 RANK까지 켜는 것이 기본이다.

조문 번호 순 = 총칙 포괄조항 순이라, 미정렬 목록의 앞부분은 사진과 무관하게 거의 같아진다. 리뷰가 gold 129장의 union 후보(19~85개·중앙값 46)로 정량화한 결과: **1행은 129/129가 제3조**, 첫 6줄에 제22조보다 큰 번호가 나온 사진 **0장**, gold 정답이 첫 6줄에 드는 비율 **13.7%**(사진의 81.1%는 첫 6줄에 정답이 하나도 없음). 지게차 사진의 제172조는 43개 중 24번째다. 그래서 **프론트에서 출처 우선순위로 재정렬**한다(§7) — 백엔드 반환 순서(측정 조건)는 건드리지 않는다.

## 7. 적대 리뷰가 잡은 것 — 반영 완료

4개 렌즈(프론트 정확성/안전 프레이밍/문서 주장/배포 통합)로 리뷰 후 각 지적을 반증 시도. 살아남아 고친 것:

| 지적 | 조치 |
|---|---|
| RANK 경로 DB 예외를 rollback 없이 삼켜 세션 오염 → 분석 전체 500 | 예외 경로에 `db.rollback()` |
| 요청 경로 LLM 호출 timeout 미지정(기본 600초) | `AsyncOpenAI(timeout=45, max_retries=1)`, env `CUE_LLM_TIMEOUT` |
| `lru_cache`가 None을 영구 캐시 → 1회 로드 실패가 프로세스 수명 내내 고착 | 성공만 캐시 |
| 텍스트 분석에도 무조건 실행(프롬프트·UI 문구는 사진 전제) | `analysis_type == "image"` 게이트 |
| 플래그를 off로 되돌려도 저장된 기록은 계속 후보를 렌더 | GET 응답에서 flag off면 후보 제거(**kill switch** — 저장 데이터는 보존) |
| 후보-밖(환각) 필터 카운트가 `logger.info`라 실효 레벨 WARNING에서 영영 안 보임 | `logger.warning`으로 승격 |
| 랭커가 같은 코드를 두 번 뱉으면 두 줄로 노출 | 백엔드 dedupe + 프론트 dedupe |
| RANK off 미리보기 6칸이 전 사진 동일(총칙 포괄조항) | 프론트에서 출처 우선순위 정렬 |
| "점검관이 먼저 지적할 순서" 문구 = 단속 예측처럼 읽힘 | "구체적으로 드러난 정도 순 · 순서는 참고용" |
| `frontend/.dockerignore`에 `.env.local` 누락 | 추가 |

기각된 지적(근거와 함께): 제13조/제30조 병렬 나열은 SSOT §5.1이 "후보엔 둘 다, 판정은 분기"로 **명시 허용** · 완충 문구가 tooltip에만 있다는 전제는 사실과 다름(고정 문구 존재) · 제40조(신호)는 애초에 후보 경로에 도달하지 못함(cue·기인물 어디에도 없음).

## 8. 프론트 후보 패널

- 신규 [ArticleCandidatesPanel.tsx](../../serving-team/08-app/frontend/src/components/results/ArticleCandidatesPanel.tsx), 타입 `ArticleCandidate` + `AnalysisResponse.article_candidates`, [ResultPage](../../serving-team/08-app/frontend/src/pages/ResultPage.tsx) 배선
- **배치**: 벌칙 3경로 **뒤**, 추론 근거 앞 — 확정 성격 패널(즉시조치·벌칙)과 붙여 놓으면 "확정 위반"으로 오독될 여지가 커서 근거·참고 구역에 둔다
- **색**: 위험등급 색(amber/red)을 배지에 쓰지 않는다. 같은 페이지의 '중간 위험' 칩과 같은 색이면 후보 강도가 위험 판정으로 읽힌다 → 중립 slate 계열로만 강약
- **문구는 tooltip에 숨기지 않는다**(폰 스크린샷 전달이 주 경로): 고정 렌더되는 고지 2줄 + `finding_status`가 확정이 아니면 그 사실을 패널 안에서 먼저 말한다
- applies 배지: yes=**우선 확인** / maybe=**추가 확인** / unranked=미정렬. 출처 칩은 사람 말로(관찰단서·기인물 매핑·기인물·판단흐름·**일반의무**), '일반의무'가 있으면 "이 사진의 핵심 위반이 아닐 수 있음" 한 줄을 본문에 렌더
- 기본 6개 + "나머지 n개 보기". `article_candidates`가 비면 **패널 자체가 렌더되지 않음**

검증(실 브라우저, 8010/8012 백엔드): 랭킹 결과 렌더·펼침, **미정렬 결과에서 관찰단서 출처가 미리보기 상단**(제4·8·18·24·27·173조 — 재정렬 전에는 제3·5·13·14·20·22조 고정), flag off 기록에서 미렌더, kill switch(같은 기록이 8010=9건 / 8011=0건), 모바일 375px 가로 오버플로 0, 콘솔 에러 0, `tsc --noEmit`·`vite build` 통과, 백엔드 단위 테스트 4종 통과.

## 9. 남은 것

- **조문 내용이 화면에 없다** — "현장 확인 후 판단하세요"라고 하면서 조번호·제목만 준다. 백엔드는 RANK 프롬프트를 만들며 `violation_scene`·PG 전문을 이미 로드하지만 응답에 싣지 않는다
- **[A]가시 / [B]절차 구분 미표기** — SSOT는 절차조문을 Track A 채점에서 빼는데 화면엔 구분이 없다
- **랭커의 `no` 판정이 응답·로그에 안 남는다** — "왜 빠졌나"를 사후 재현할 수 없다
- 정확도·오탐 주장은 여전히 연구 하네스 몫. 서빙 Vision 구성에서의 재측정은 미실시

## 10. 프로덕션 반영 시 체크리스트 (아직 안 함)

1. ✅ **데이터는 이미지에 굽힌다 — 실측 확인**: 재빌드 후 `/app/app/data/trackA/`에 5개 파일 전부 존재(1.5MB), `/app/data`(chromadb 등 런타임)는 `.dockerignore`의 `data/`로 제외. `data/`는 **컨텍스트 루트만** 매칭하므로 `app/data/trackA`는 살아남는다
2. 코드 변경분이 이미지에 들어가야 한다(현 검증은 bind-mount) → **backend·frontend 둘 다 재빌드**. 번들 경로는 [`deploy/server/build_bundle.sh`](../../serving-team/08-app/deploy/server/build_bundle.sh)
3. env: `CUE_ARTICLES=1` + `CUE_ARTICLE_RANK=1`(RANK off는 §6대로 검증 구성이 아님). 모델은 `CUE_RESOLVE_MODEL`/`CUE_RANK_MODEL`(기본 gpt-5.4), 타임아웃 `CUE_LLM_TIMEOUT`(기본 45초)
4. 비용/지연: 분석당 LLM +2회, +3.5초 이상
5. cue-pool·signature 재생성 시 `backend/app/data/trackA/` **동기화 필수**(연구본과 서빙본 두 벌)
6. **정식 FP 측정 선행** — 오탐 비용은 아직 사실상 미측정이다([evaluation-baseline](../status/evaluation-baseline.md) 잔여 전제). 위반 없는 정상 현장 사진을 새로 모아 측정하기 전에는, 이 기능을 켜는 것이 "후보를 보여주는 이득 > 없는 위반을 보여주는 손해"인지 확인되지 않았다
7. 기동 시 지식 로드 워밍업이 없다 — `app/data/trackA` 동기화가 어긋나면 첫 요청 때 조용히 빈 후보가 되고 응답만으로는 flag off와 구별되지 않는다(로그 WARNING 한 줄이 유일한 신호)

관련: [[rank-ab-result]] · [rank-ab-cuepool-union](rank-ab-cuepool-union-2026-07-29.md) · [[cue-centric-architecture]]
