# Track A 조문 후보 — 스테이징 플래그 on 실증 + 프론트 후보 패널 (2026-07-31)

배선 자체는 [`cf325ce`](../../serving-team/08-app/backend/app/services/cue_article_service.py)에서 끝났고(기본 off), 이 문서는 **실제로 켜서 사진을 통과시킨 결과**와 **화면 노출**을 기록한다.
검증 근거 정본은 [evaluation-baseline](../status/evaluation-baseline.md) 최상단(RANK A/B v2), 경위는 [rank-ab-cuepool-union](rank-ab-cuepool-union-2026-07-29.md).

## 1. 실증 방법 — 기존 스택 불침습

로컬 compose 스택(`ohs-backend` :8000)은 **건드리지 않고**, 같은 이미지에 소스만 마운트한 임시 컨테이너 2개를 띄워 on/off를 나란히 돌렸다.

```bash
docker inspect ohs-backend --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -v '^$' > /tmp/cue_env
docker run -d --name ohs-backend-cue --network ohs_ohs-network -p 127.0.0.1:8010:8000 \
  --env-file /tmp/cue_env -e CUE_ARTICLES=1 -e CUE_ARTICLE_RANK=1 \
  -v /mnt/c/project/arch-bot/serving-team/08-app/backend:/app \
  -v /mnt/c/project/arch-bot/shared/reference:/app/shared/reference:ro \
  ohs-backend:airgap
rm -f /tmp/cue_env   # 시크릿은 파일로 남기지 않는다
```

- env를 **원본 컨테이너에서 승계**하므로 DATABASE_URL/OPENAI_API_KEY를 사람이 만질 일이 없다(값 노출 0).
- 소스 bind-mount → 이미지 재빌드 없이 최신 코드로 검증. 대조군은 같은 명령에서 `CUE_ARTICLES=0`, 포트 8011.
- 요청: `POST /api/v1/analysis/image` (multipart `image`), 사진은 `real-test-photo/`.

## 2. 결과 — 사진 3장 전부 200, 후보가 실제로 붙는다

| 사진 | e2e | 노출 후보 | 상위 3 (applies) |
|---|---|---|---|
| 지게차 | 61.4s | 10 | 제172조 접촉의 방지(yes) · 제22조 통로의 설치(yes) · 제3조 전도의 방지(yes) |
| 고소작업대 | 31.0s | 4 | 제186조 고소작업대 설치 등의 조치(maybe) · 제44조 안전대의 부착설비 등(maybe) · 제14조 낙하물에 의한 위험의 방지(maybe) |
| 프레스 | 34.1s | 9 | 제93조 방호장치의 해체 금지(yes) · 제87조 원동기·회전축 등의 위험 방지(yes) · 제91조 고장난 기계의 정비 등(maybe) |

기인물이 곧바로 1위 조문으로 이어졌다(지게차→제172조, 프레스→제93·87조, 고소작업대→제186조). `evidence`에 매칭된 관찰단서(`지게차`, `미끄러운/오염 바닥` 등)가 붙어 근거 추적이 된다.

## 3. 무회귀 대조군 — 그리고 trace 비교가 왜 근거가 못 되는가

flag off(8011)에서 동일 사진: `article_candidates = []`(키는 존재), **응답 키 집합 차이 없음**, e2e 58.1s.

`reasoning_trace.articles`는 on/off 모두 30개인데 집합이 달랐다. 이걸 회귀로 읽으면 안 된다 — **flag off끼리 두 번 돌려도 교집합 15/30**이다. 매 요청 Vision을 다시 부르므로 관찰 자체가 매번 달라진다. 따라서:

- ❌ 무회귀 근거로 쓸 수 없는 것: on/off의 trace.articles·guides 개수 일치 여부
- ✅ 실제 근거: ① 후보 계산이 `run_input.result`만 읽고 `article_ids`/`knowledge`를 **쓰지 않음**(예외는 삼켜 기존 경로 유지) ② 응답 키 집합 동일 ③ flag off → 빈 배열 ④ 단위 테스트 4종(`tests/unit/test_cue_article_service.py`)

## 4. 한계비용 — Vision과 분리해 계측

e2e 차분(61.4 vs 58.1s)은 Vision 변동(29~61s)에 묻혀 의미가 없다. 컨테이너 안에서 후보 경로만 3회 계측:

| | rep1 | rep2 | rep3 |
|---|---|---|---|
| RESOLVE | 2.27s | 1.91s | 1.92s |
| RESOLVE+RANK 전체 | 5.08s | 3.45s | 3.52s |

**분석당 +3.5~5.1초, LLM +2회.** 후보 집합은 3회 모두 동일(제186·44·3·14조), 상위 2개 순서만 흔들렸다.

## 5. "제42조가 왜 없지?" — 버그 아님, 랭커가 거른 것

고소작업 사진에서 hazards에 추락이 있는데 제42조(추락의 방지)가 안 보였다. 진단 결과:

- 결정론 후보(RESOLVE 제외)만 44개, **제42조 포함**(cue entry + CROSS 양쪽) → 후보생성은 정상
- 랭커가 `applies=no`로 판정 → 노출 4개로 축소. 사진은 **난간 있는 고소작업대 + 안전모·안전벨트 착용** 상태라 타당한 배제
- 부수 관찰: 이 사진의 노출 4개는 전부 `maybe`, **yes 0건** — 오탐 스모크에서 지적된 "기권 경로 없음"이 실제로는 yes 억제로 완화되는 사례

**관측 가능성 공백(후속 과제)**: 랭커가 `no`로 버린 조문과 후보-밖 필터 카운트는 로그에만 남고 응답에 없다. 큐레이션 중 "왜 빠졌나"를 사후 재현할 수 없으므로, 디버그 필드나 구조화 로깅이 필요하다.

## 6. 프론트 후보 패널

- 신규 [ArticleCandidatesPanel.tsx](../../serving-team/08-app/frontend/src/components/results/ArticleCandidatesPanel.tsx), 타입 `ArticleCandidate` + `AnalysisResponse.article_candidates`, [ResultPage](../../serving-team/08-app/frontend/src/pages/ResultPage.tsx) 배선
- **배치**: 벌칙 3경로 **뒤**, 추론 근거 앞 — 확정 성격 패널(즉시조치·벌칙)과 붙여 놓으면 "확정 위반"으로 오독될 여지가 커서 근거·참고 구역에 둔다. 색도 빨강 계열 회피(amber)
- **표기 정책**(backend docstring과 동일): 제목 "조문 후보 (확정 아님 · 검토 대상)" + 상단 고정 문구 — *"후보 목록은 해당 없음을 반환하지 않으므로, 실제로 위반이 없는 현장에서도 조문이 표시될 수 있습니다"*
- applies 배지: yes=가시 단서 있음 / maybe=정황·미확인 / unranked=미정렬(RANK off). source 칩(큐레이션·기인물·단서·흐름·횡단)은 tooltip으로 의미 제공
- 기본 6개 + "나머지 n개 보기"(RANK off면 수십 개가 오므로 접기 필수). `article_candidates`가 비면 **패널 자체가 렌더되지 않음** → flag off 무회귀

검증(실 브라우저, 8010 백엔드): 지게차 결과에서 패널 렌더·10개 중 6개 표시·펼침 동작 확인, 프레스 결과에서 9개 전체 펼침, **flag off로 만든 분석 기록에서는 패널 미렌더**, 콘솔 에러 0, `tsc --noEmit` 통과.

## 7. 프로덕션 반영 시 체크리스트 (아직 안 함)

1. ✅ **데이터는 이미지에 굽힌다 — 실측 확인**: 재빌드(`docker build -t ohs-backend:cue-verify .`) 후 `/app/app/data/trackA/`에 5개 파일 전부 존재(1.5MB), `/app/data`(chromadb 등 런타임)는 `.dockerignore`의 `data/`로 제외됨. `data/`는 **컨텍스트 루트만** 매칭하므로 `app/data/trackA`는 살아남는다
2. 코드 변경분이 이미지에 들어가야 한다(현 검증은 bind-mount) → 재빌드 필요
3. env: `CUE_ARTICLES=1`, RANK까지 켜려면 `CUE_ARTICLE_RANK=1`. 모델은 `CUE_RESOLVE_MODEL`/`CUE_RANK_MODEL`(기본 gpt-5.4)
4. 비용/지연: 분석당 LLM +2회, +3.5~5.1초
5. cue-pool·signature 재생성 시 `backend/app/data/trackA/` **동기화 필수**(연구본과 서빙본 두 벌)

관련: [[rank-ab-result]] · [rank-ab-cuepool-union](rank-ab-cuepool-union-2026-07-29.md) · [[cue-centric-architecture]]
