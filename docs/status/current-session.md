# 현재 세션 / 다음 세션 시작 지침

> ⚠️ 이 문서는 2026-06-14 이후 갱신이 끊겼고, 그 뒤 작업은 `docs/dev-notes/`와 메모리에만 있었다.
> **최신 상태는 아래 '2026-08-09~12' 절부터** 읽는다.

## ⭐⭐ 2026-08-09~12 — 앵커 0.647→0.961(흐름) + 3단계 UI + 텍스트 트랙 개통 (전부 push·prod 배포)

**HEAD `6fbdec3`, 전부 push + moellab.info 배포 완료.** 지표 정본 = [evaluation-baseline.md](evaluation-baseline.md) 앵커 절.

**+2026-08-12 추가: 앵커 정정 시 '지금 당장' 재선별 + SR 순위 신호 부활(버그 9호)** —
정본 [recalc-actnow-on-correction-2026-08-12.md](../dev-notes/recalc-actnow-on-correction-2026-08-12.md).
GET /flow가 재선별을 싣고(accident_code 승계), 대안 칩·직접 검색 정정 모두 그 기인물의 '지금 당장'을
받는다(LLM 0). SR 히트는 canonical∪레거시 두 컬럼 합집합 — canonical 단독은 ELECTRIC_SHOCK류 회귀
(리뷰 적발). ⚠ FIRE_EXPLOSION 계열은 SR canonical 데이터 미이관으로 여전히 순위 미적용(데이터 과제).

**+2026-08-12 추가 2: prod 실사용 개선 2트랙** (사용자 발견: 앵커 뭉개짐 + 소화기 미부각):
- **Track B(소화기 부각) 완료·배포**: 화재 어휘 정합(사진 hazard 합류+SR legacy 별칭
  FIRE_EXPLOSION→{EXPLOSION,FIRE_INJURY}) + align matched 순위 부스트((ref,text) 쌍 —
  별표 항목 ref 공유 함정) + 별표3 항목 모집단 구제 + ref 안정 식별자·evidence quote fallback
  (966건 채움). prod 화면 실증: "소화기 비치" 제안 → 제243조 matched·immediate·원문 인용.
  정본 [fire-actnow-visibility] = recalc 노트와 같은 흐름, 커밋 402096d·92f6f24.
- **Track A(장소성 라우팅)**: A-1 판별단서 4종 완료·배포(함정 4호: '허가대상 유해물질' ㆍ분리 →
  별표2 오부착, 공백 융합 우회) · A-2 프롬프트 개입 기각(재추첨 변동과 구분 불가 — 선우개발
  경계 사례) · A-3 judge+basics 라우팅 코드 완성(**플래그 CUE_ANCHOR_JUDGE off**, 게이트 미통과:
  진짜 FP 2장·미니 6/8) — 정본 [place-routing-judge-2026-08-12.md](../dev-notes/place-routing-judge-2026-08-12.md).
  **다음 = 미니 gold 라벨 사용자 검수 → 재계측 → 통과 시 A-4 on.**

**현재 수치(감독관 gold 51장)**: 앵커 exact **0.784** [0.667,0.882] · **흐름 유효율 0.961** [0.902,1.000] ·
예측 빈 0장. 경로: 0.647 → 비계 상속(A안) → 판별단서 → Vision v2 → 키 정규화 0.784/0.941 → miss11 레버 0.961.

**단계별 정본(dev-notes)**:
- [ui-consulting-redesign-2026-08-09.md](../dev-notes/ui-consulting-redesign-2026-08-09.md) — 3단계 컨설팅 UI·ALIGN·불비 원장
- [anchor-a0-metrics-2026-08-09.md](../dev-notes/anchor-a0-metrics-2026-08-09.md) — A0 계측(오류 절반=데이터 구조)
- [terra-opus-experiment-2026-08-10.md](../dev-notes/terra-opus-experiment-2026-08-10.md) — gpt-5.6-terra 전환 **비권고**·Claude Opus 5 검수자 유효(판가름 3/3)
- [miss11-decompose-2026-08-10.md](../dev-notes/miss11-decompose-2026-08-10.md) — 완전 오인식 11장 분해: **8장=지표 정의 잔여물**(흐름은 정답 포함), 진짜 결함 3장
- [text-track-flow-2026-08-12.md](../dev-notes/text-track-flow-2026-08-12.md) — **텍스트 분석 트랙도 앵커→흐름 개통**(image 게이트 해제 + 문구 분기). ⚠ 텍스트 gold 계측 없음

**이번 구간에 실측된 함정(재발 주의)**:
- **이름 매칭 함정 3번째**: 라벨 토큰 '국소배기장치'가 law3 제42조 부착을 절3에서 빼앗음(`resolve_machines` 최구체 1개 선택) → '배기 후드'로 우회. **라벨 변경 시 gimulmul diff + flow diff 0 검사 필수**
- **gold Vision 재생성 = 전 사진 재추첨**: 한 장 고치려 129장 재판독하면 경계 사진이 뒤집힘(한솔2: v2 '이동식 비계'→v3 '고소 작업대'). `regen_vision_gold.py`는 태그 백업·프롬프트 sha 게이트 내장
- gpt-4.1은 소형 흡연 물체(재떨이 깡통·라이터)를 프롬프트를 줘도 미서술(**지각 한계**, Opus/Fable은 봄) — 텍스트 트랙이 이 클래스의 우회로
- 텍스트 분석 엔드포인트는 **JSON 본문**(멀티파트 422) · rows[0] 주 기인물 선별 변동은 prod E2E에서도 재현
- RESOLVE가 카탈로그에 없는 변형 키를 내면 조용히 버려짐 → **prefix 정규화**가 측정(`measure_anchor_accuracy.norm_gk`)·서빙(`cue_article_service._norm_gk`) 동일 적용됨

**다음 후보(미착수, 사용자 결정)**:
1. 잔여 진짜 결함 3장: 제니알테크(4.1 지각 한계 — Vision 모델 실험 또는 수용) · 한솔2(rows[0]·형태 서술) · IMG_3166(라벨 재검토)
2. 제43조(개구부) 감독건 인용 사진들 라벨 재검토 세션 · 텍스트 트랙 gold 구축 여부
3. 주 기인물 선별(rows[0], 첫 키 변동 29.4%) · B1 confidence 확인 유도 · A0-d ALIGN gold(사용자 검수 시간)
4. ops 스키마 구현(설계 완료, prod ALTER 포함 — 지시 대기) · 즉시성 태그 빌드타임 승격 · 불비 원장 배치 검토(prod에 실사용 원장 쌓이는 중 — records 90·gaps 11, **update-ohs.sh는 볼륨 wipe라 원장 소실 주의**)

배포 절차·함정은 메모리 `deploy_moellab_droplet` 참조(코드 배포=update-ohs-code.sh, frontend 빌드 Git Bash 금지, 번들 'Program Files' 검사).

## ⭐⭐ 2026-08-02 — 조문 시점을 제목이 아니라 원문으로 판정

**상세 정본: [../dev-notes/article-phase-relabel-2026-08-02.md](../dev-notes/article-phase-relabel-2026-08-02.md)** ⭐
(compact 후 여기부터 읽고 재개. 그 앞 단계는 아래 2026-08-01 절)

커밋 17개(`8417169` → `84013ac`, main, **push 안 함**).

- 흐름 6칸의 시점 라벨을 조문 **제목** 정규식으로 정하고 있었다 → **669조 중 642조(96%)가 '작업 중'**에 몰림.
  원문(fullText)으로 다시 판정. 계획 2→32 · 인적 4→50 · 작업전 7→58 · 종료 14→29 · 정기 0→19
- (중간값) 실질 채움 계획 31% · 인적 46% · 작업전 49% · 항목 2,210 — **아래 제38·39조 수정 후 값이 최종이다**
- 판정은 LLM이 하되 **양방향 검증**: 1차 → 2·3차 반박/재심 → 역방향 탐색 → 역검증 → 3인 최종판정 →
  **인용문 원문 대조(결정론, 실패 0건)**. 한 방향만 검증하면 편향된 래칫이 된다
- ⚠️ **정의·목적·적용제외 조문 30종이 '작업 중' 칸에 떠 있었다**(제1조 목적, 제2조 정의까지). 뺐다
  → 그 결과 **빈 흐름 13종**(통칙 그룹)이 생겼다. 앵커가 여기로 떨어지면 보여줄 게 없다
- ⚠️ **적용범위 자기한정 조문 상속 — 같은 버그 6번째.** 제98조(제한속도)가 프레스·보일러·로봇 등
  16종에, 제86조(탑승 제한)가 건설기계 포함 11종에 붙어 있었다
- **안전검사 scope·cycle을 법령 원문과 글자 단위 대조** — 67건 일치, 1건 수정(`(kN)`→`(KN)`).
  시행령·시행규칙은 **밖에서 받아올 게 아니라 `article-texts.json`에 있었다**(미확보라고 적어 둔 게 틀렸다).
  혼합기·파쇄기 적용 제외 범위는 **시행령에 없다** — 제2항이 위임한 별도 고시가 유일한 출처(미확보).
  ⚠ 시행규칙 제125조 **면제 사유 11개가 미반영** — 화면이 '법정 N년마다'만 보여주면 면제가 숨는다
- **재료 범위를 규칙 → 법 전체로 넓혔다.** 흐름 6칸의 재료가 산업안전보건기준규칙뿐이었다.
  법·시행령·시행규칙 554조를 훑어 **기인물 단위 의무 43건 전부 배선**.
  새 별표 4종 파싱(시행령 별표 20·21, 시행규칙 별표 4·**5 특별교육 대상작업 39종**)
- **검수 항목 2,295** (2,658에서 내려갔다 — 아래 제38·39조 오부착 제거)
- ⚠️ **제38·39조가 126개 그룹에 무조건 주입되고 있었다 — 버그 8번째, 가장 컸다.**
  제38조제1항은 13개 작업만 열거하는 닫힌 목록인데 92%가 오부착.
  **계획·인적·작업전의 '겉보기 100%'가 순전히 이 때문이었다.** 이제 겉보기 = 실질:
  계획 39% · 인적 67% · 작업전 49% · 작업중 93% · 종료 35% · 정기 25%
- **사진 앵커 적격 분류** — 기인물 52 · 장소 22 · 환경 19 · **부적격 34**(통칙·보호구·관리·상위 개념).
  지우지 않고 표시한다. 앵커가 부적격이면 화면이 "목록에서 직접 찾기"를 안내
- ⚠️ **제52조 — 사람 검수가 3인 다수결을 뒤집었다.** 조건부 발동 의무인데 계획 칸으로 채택됐었다.
  `human_review.json`이 다른 모든 판정을 덮어쓴다. **갈린 3건 중 첫 번째에서 다수결이 틀렸다**
- ⚠️ **앵커 정확도 0.711 → 0.600** (채점 45 → 60장). 비계가 `cross_cutting`에 묶여
  **앵커로 도달할 경로가 아예 없었고**, 측정도 편1을 통째로 빼서 비계 사진 15장을 안 세고 있었다.
  카탈로그 99 → 105종 + RESOLVE 재실행으로 +0.067 회복. 정본 = [evaluation-baseline.md](evaluation-baseline.md)
- **'기본 안전수칙' 카테고리 47건** — 사진과 무관하게 늘 지켜야 하는 것(`/basics`).
  **앵커 정확도와 무관하게 항상 맞는 유일한 화면**
- **검수 뷰어에 우선순위** — '의심스러운 것만' 버튼이 116건만 남긴다(판정 갈림 22 + 이름매칭 94)
- ⚠ **적용범위 무시 버그 7번째**(안전검사 주기: 이동식 크레인에 크레인 주기). 그리고 좌표를
  눈대중으로 적어 8번째가 될 뻔했다(석면·화학설비·비계 전부 틀림 → 대조해 수정)
- **라벨 검수 0/2,295** — ⭐ 다음 작업. 뷰어 `http://localhost:8920/flow_review_viewer.html`,
  '의심스러운 것만' 버튼이 116건만 남긴다. ⚠ **검수 CSV → 데이터 반영 경로가 아직 없다**

---

## ⭐ 2026-08-01 — 기인물 앵커 → 작업 흐름: 데이터 확보부터 서빙까지

**상세 정본: [../dev-notes/anchor-flow-serving-2026-08-01.md](../dev-notes/anchor-flow-serving-2026-08-01.md)** ⭐
(compact 후 여기부터 읽고 재개. 제품 전제는
[flow-skeleton-gap-2026-08-01.md](../dev-notes/flow-skeleton-gap-2026-08-01.md))

커밋 7개(`7e3eea7` → `dde9cb6`, main, **push 안 함**). 사진 → 기인물 앵커 → 작업 흐름 6칸 → 화면까지 연결.

- **안전검사 고시 15종 확보**(13종 아님 — 혼합기·파쇄기 신설, 시행 2026.6.26.). 별표 14종·499행·1,906항목
- **흐름 인덱스를 별표 3 19행 → 기인물 그룹 127종으로 확대**. 커버리지 57.8% → 100%(gold 45장 기준)
- ⚠️ **앵커 정확도 정정: 0.778 → 0.711**(좌표를 (절,관)으로만 비교하고 편·장을 버린 버그).
  완전 오인식 20% → **26.7%**. 정본 = [evaluation-baseline.md](evaluation-baseline.md) '앵커 인식 정확도'
- ⚠️ **'칸이 찼다'를 믿지 말 것** — 총칙 주입 제외한 **실질** 채움은 계획 13%·인적 17%·작업전 20%·
  작업중 99%·종료 25%·정기 10%. 실질 1칸짜리가 68종
- **서빙 배선 + 앵커 정정 UI**. `OHS_ENABLE_WORK_FLOW`(env `CUE_FLOW`) **기본 off**, kill switch 실측 완료
- **라벨 검수 0/1,989** — 화면이 '검수 전' 경고를 띄우는 상태. 다음 세션 1순위

**같은 좌표 뭉갬 버그가 5번 재발했다.** 좌표는 항상 (편,장,절,관) 4튜플로 다룰 것.
증상이 매번 같다 — 숫자는 좋아 보이는데 내용이 틀린다.

---

최신 갱신일(이하 구 본문): **2026-06-14** — ⭐ **Track A ② 추론 수직 슬라이스**(신규 PG `sr_inferred_relations` **103,295행** = R-1 exemptedBy 107행/95SR + K-R2 coApplicable 16,429쌍→32,858행 + K-R4 dependsOn 35,165쌍→70,330행; 서빙 Fuseki→PG 전환 + 신규 `/depends-on`; PROV `materialization_runs`; 커밋 `87d9e63`/`7c50304`/`e6140bb`, f1-regression delta 0) **+ A4/A5 거버넌스**(dual license Apache-2.0+CC-BY-4.0, 릴리스 버전 **2.0.0**, VoID triples 1,049,862/classes 625/properties 164, A5 SKOS 3 scheme/504 concept/2,659 triple — DONE·미커밋). 직전 = ⭐ **facet 구조 audit(18 findings) + 구조 수정 Fix A/B·B1·B2·B3a·B4·B5(F4) + B3a 정정**. 신규 도구 inspect_node·gen_catalog/CATALOG.md·**derive_property_domain_range**·**check_disjoint_consistency** + findings 문서. **Fix A**(`ba11895`) floating 480→0, **Fix B**(`ac327a8`) UPPER_SNAKE 12 제거, **B1**(`1f32a61`) ctx/agent 라벨, **B2+정정**(`b81436a`/`678a7d1`) dead/alias 정리+오제거 복원, **B3a**(`0a82546`) facet disjoint, **B4**(`523465a`) guide/core property domain·range **25 코퍼스-aware 보강**(F10/F15), **B3a 정정**(`c5919af`) **haz:Hazard를 disjoint에서 제외(10→9축)로 KB 일관 복구** — ⚠️ B4 Openllet 게이트(owl:Nothing 실쿼리)가 사전-존재 비일관 적발(haz:AccidentType⊥haz:Hazard 7개체; B3a가 lazy `prepare()` 거짓양성 오신뢰), **B5/F4** **haz:Hazard 클래스 폐지**(`bb76d1f` (a)AccidentType⊑Hazard가 축 계층 비대칭 유발해 반려 → (c) 클래스 삭제; 4 range·3 제약·SWRL→AccidentType repoint, v2.owl 선언 삭제. AccidentType RiskFeature 직속 복귀, class 628→627, 잔여참조 0, Openllet 일관). **+ SHE ABox 통합(F5 해결)**: F5 추적으로 데이터팀 `she-instances-v1.ttl`(965 패턴×6축 맥락)이 **온톨로지 미적재 + KOSHA-22 이전 legacy 어휘** 발견 → canonical **forward 마이그레이션**(신규 `gen_she_abox.py`→`kosha-instances-she.ttl` 49,689 triple) + manifest 편입 + `she:triggerText` range xsd:string→rdfs:Literal(datatype 비일관 수정) → **she:has* 0→965, F5 5축 실채움, Openllet 일관**(⚠️ 965는 **2026-06-12 CAT-4 `68cc76b`**에서 `kosha-instances-she-full.ttl` **1,675**로 단일화·퇴역, PG 활성과 정합). **직전 세션** = Phase 3 facet taxonomy + B-트랙(아래, `1dab81a`). **남은 것**: B3b(저가치)/B6(BFO grounding, 高)/**F20 sr속성 hard merge ✅**/(선택)F5 다축 prune·~~**F21**(F4c잔재 r14-r30 haz:Hazard 본문)~~ ✅(WS-GATE-7 repoint 완료). **+ empty-class/dormant-property detector ✅**(`scripts/check_data_coverage.py`·`make data-coverage` — F5/SHE형 미적재 상시 탐지: 빈 클래스/dormant property를 app·rule-head·facet-fine 분리해 triage). — 상세 정본 `docs/backlog/ontology-structural-findings.md`.

## ⭐ 2026-06-20 — SR→조 매핑 검증 (정확도 향상 1단계, compact 전 체크포인트)

**상세 정본: [../dev-notes/sr-article-mapping-verification-2026-06-20.md](../dev-notes/sr-article-mapping-verification-2026-06-20.md)** ⭐ (compact 후 여기부터 읽고 재개)

목적: "GPT 인식 위험 → 산업안전보건규칙 몇 조 위반" 매핑이 잘 되는지 전수 검증.
- **방법**: 시스템 예측(`dump_synthetic_sr_articles.py` → focused/broad SR+조) **vs 독립 gold(장章 기반 LLM 태깅)** 채점(`score_sr_article_mapping.py`). gold = **Claude**(Workflow 에이전트, $0, batch4) + **gpt-5.4**(Batch 2-round, `build_gpt_chapter_gold.py`) 2개 독립 annotator.
- **핵심 발견**: 시스템 조-매핑 **심하게 오정렬** — consensus gold(두 LLM 동의 722건)에서도 focused **3.4%**/broad ~51%(정밀도 **1.4%**)만 일치. 근본원인(`diagnose_focused_mismatch.py`) = **자석 SR**(제390 하역·제312 전기 등 도메인 무관 오부착 7-12%)·**facet-collision SHE→SR 큐레이션**(FALL로 추락↔하역)·**느슨한 2축 SHE 매칭**(밀폐↔굴착).
- **gold 신뢰**: Claude↔gpt Jaccard 0.45·**disagreement 59%(770)** → 사람 adjudication 미완(WS-EVAL-2 미확정). negative/ambiguous는 둘 다 ~zero(정상).
- **산출물**: `claude_gold_v2.jsonl`(2,360)·`gpt_gold.jsonl`(1,292) 추적; dump·batch·derived는 gitignore(재생성). 신규 scripts 7개 + `_mapping_review_common.py`(조 컬럼).
- **다음**: ① gold 확정(disagreement 770 adjudication 또는 3rd 모델 tiebreak) ② **정확도 개선 실수정** — 자석 SR `she_sr_mapping` cross-domain 링크 정리 + SHE 매칭 도메인 게이팅.

## ⭐ 2026-06-14 — Track A ② 추론 수직 슬라이스 + A4/A5 거버넌스

승인 plan `docs/workplans/llm-accelerated-ontology-engineering.md` Track A. **추론 산출을 서빙이 Fuseki 없이 PG에서 소비**하도록 물질화 + 오픈소스 공개용 거버넌스(라이선스/SKOS) 정비.

### Track A ② — 추론 수직 슬라이스 (push 완료, 커밋 `87d9e63`/`7c50304`/`e6140bb`)

- ✅ **신규 PG 테이블 `sr_inferred_relations` = 총 103,295행** (`rule_id`로 strict R-1 vs relaxed K-R2/K-R4 구분):
  - **R-1 exemptedBy**: 107행 / **95 distinct SR** (`87d9e63`). strict DL — NS→exempt-NS edge를 SR 단위로 확장, SR별 서빙.
  - **K-R2 coApplicable**: 16,429 distinct pair → **32,858행** (same-Chapter relaxation, 양방향) (`7c50304`).
  - **K-R4 dependsOn**: 35,165 distinct pair → **70,330행** (same-Hazard relaxation, 양방향) (`e6140bb`).
  - **R-2 strict coApplicable = 0** (SR↔Article 1:1로 same-article cross-pair 없음). R-3 HighSeverityPenalty(3,579)는 `penalty_rule_index.severity_score>=5` SQL 동치로 재현(`sr_inferred_relations` 미저장).
- ✅ **신규 PG 테이블 `materialization_runs`** — PROV run-tracking(`run_id`, `rule_set`, `ontology_commit`=git rev, `source_ttl_sha256`=content-hash, `triple_count`, `status`). runs #1-4.
- ✅ **서빙 Fuseki→PG 전환** (`serving-team/08-app/backend`): `/api/v1/sparql/sr/{id}/exemptions`·`/co-applicable`·`/article/{code}/inferred-graph` 가 PG SELECT로 응답 + **신규 `/api/v1/sparql/sr/{id}/depends-on`**. 신규 `app/services/sr_inferred_service.py`. dead `enrich_sr_with_sparql`(hazard_rule_engine) → PG-backed `enrich_sr_with_pg` 교체.
- **신규 스크립트**: `ontology-team/06-reasoning/ontology/scripts/emit_inferred_relations.py`(`--mode strict|chapter|hazard`) / `serving-team/07-materialization/pg-sync-scripts/import_sr_inferred_relations_to_pg.py` / `serving-team/08-app/backend/scripts/verify_inferred_relations.py`. **신규 TTL**: `kosha-inferred-relations.ttl`·`kosha-coapplicable-chapter.ttl`·`kosha-dependson-hazard.ttl`. **신규 Makefile target**: `reasoning-emit{,-chapter,-hazard}`·`phase-g5{,b,c}-{schema,import,verify}`.
- **게이트**: f1-regression all-metric delta **0.0000**(분석 hot-path 무변경, 3 slice 전부) · latency-gate PASS · verify-baseline PASS · phase-g5/g5b/g5c-verify PASS.
- ⚠️ **OLD 수치 정합**: ① 구 "K-general dependsOn 36,949"(on-demand SHACL count)는 **이제 물질화된 K-R4 = 35,165 pair와 다른 수치**(별개 집계). ② coApplicable 16,429는 이전에 "미적재/on-demand/gitignore"였으나 **이제 PG 물질화 완료**(K-R2). 이들 reasoner 산출은 더 이상 Fuseki 요청경로 아님 — 서빙은 PG를 읽는다.

### A4/A5 거버넌스 — DONE(아직 미커밋, 본 문서 갱신 직후 커밋 예정)

- ✅ **A4 dual license**: `LICENSE`(Apache-2.0, 코드) + `LICENSE-ontology.md`(CC-BY-4.0, 온톨로지/데이터) + README license 섹션 + `CITATION.cff`(CFF 1.2.0) + `kosha-ontology-metadata.ttl`. **온톨로지 릴리스 버전 = 2.0.0**(`owl:versionIRI .../ontology/2.0.0`·`owl:versionInfo "2.0.0"`, kosha-ontology-v2.owl lineage 정렬; CITATION 2.0.0 — 1.0.0 아님).
- ✅ **VoID**(`kosha-ontology-metadata.ttl`, full consistency assembly scope): `void:triples` **1,049,862** · `void:classes` **625**(named owl:Class, facet fine 포함; core conceptual TBox ~62) · `void:properties` **164**(ObjectProperty 119 + DatatypeProperty 45).
- ✅ **A5 SKOS**: `gen_skos_scheme.py` → `kosha-codes-skos.ttl` = **3 SKOS ConceptScheme**(축별: accident-type/hazardous-agent/work-context), **504 concept / 2,659 triple**. 관계: `skos:broader` 418(같은 축 rollup→canonical) · `skos:relatedMatch` 21(cross-axis agent→accident-type associative) · `rdfs:seeAlso` 62(canonical→OWL class haz:/agent:/ctx:). ⚠️ `broadMatch`/`exactMatch`가 아니라 `relatedMatch`+`seeAlso` 사용(전자는 계층/punning 오선언). `make gen-skos`. `validate_prefixes.py`에 code-accident-type/code-hazardous-agent/code-work-context 네임스페이스 등록.
- ℹ️ 네임스페이스는 **여전히 cashtoss.info** (w3id.org/ohs-kr 마이그레이션은 FUTURE step A2 — IRI 미변경).

## ⭐ 2026-05-31 (이어서) — facet 구조 top-down audit + 구조 수정 (push 완료)

Fuseki(Openllet) 전체 적재 후 class/predicate를 대화형 top-down 점검 → 18 structural findings 수집·정본화 → 고가치 batch 수정. 정본 추적: **`docs/backlog/ontology-structural-findings.md`**.

**신규 진단 도구** (재사용):
- `scripts/inspect_node.py` (`8670c6a`): 한 IRI의 전체 triple(주어/목적어 양방향) + **출처 파일**(수정 위치) 카드. `--list <prefix>` scope 개요.
- `scripts/gen_catalog.py`→`CATALOG.md` (`d99da77`,`756f778`): 전체 class 계층 트리 + property + **자동 이상징후**(floating/label/dead/dup/dom-rng/punning). ⚠️ ref/dead는 대용량 코퍼스 제외 집계 → guide/core/app 클래스엔 caveat(코퍼스 포함 재확인 필수).

**구조 수정 (batch)**:
- **Fix A** (`ba11895`): `gen_facet_taxonomy.py`에 canonical⊑axis emit 추가 — canonical의 기존 rdf:type 축을 데이터로 읽어 rdfs:subClassOf 승격. **floating 480→0**(haz 181+agent 84+ctx 215이 risk:RiskFeature까지 연결). compare_graphs +62, Openllet DL 일관, 라이브 `haz:Fall⊑risk:RiskFeature`=true.
- **Fix B** (`ac327a8`): haz:Hazard UPPER_SNAKE 레거시 개체 12(haz:FALL 등) 제거 — CamelCase canonical로의 마이그레이션 잔재, live 참조 0. haz:Hazard *클래스*는 property range로 유지. graph_diff −36.
- **B1** (`1f32a61`): ctx canonical 16 + agent:UnknownAgent 한글 라벨(F6/F7). 신규 `shared/reference/facet-ko-labels.json` SSOT + gen_kosha22_vocab_patch @ko emit. graph-diff +17.
- **B2** (`b81436a`) + **정정** (`678a7d1`): 8 haz alias 축-레벨 개체 제거(코퍼스 haz: 참조 0=정확, facet fine 클래스로 보존) + core:Relation 선언(dangling 0). ⚠️ **B2가 core:Worker·guide:DocumentRequirement/DomainTerm를 dead 오판 제거→복원**(코퍼스 55/3435/7726회 live; ref-check 코퍼스제외+IRI형grep 이중실수). F13/F16 오탐 정정.
- **B3a** (`0a82546`): `kosha-facet-axis-disjoint.ttl` 신규 — risk:RiskFeature 10축 owl:AllDisjointClasses(F2). ⚠️ 아래 정정으로 **9축**(haz:Hazard 제외).
- **B4** (`523465a`): guide/core property **domain·range 25 코퍼스-aware 보강**(F10/F15). 신규 `kosha-ontology-v4-domain-range-patch.ttl`(+36 triple) + 도출기 `scripts/derive_property_domain_range.py`(956K ABox 포함 full union 1.48M triple 전수집계). 주어·목적어 100% 해당 type(untyped 0) → domain/range 추론 NO-OP·range 전부 비-facet → **단일변수 토글로 B3a 충돌 비유발 입증**. CON union +36 정확·중복 0, catalog (e) 59→34, verify-manifest/prefixes 통과. **bridge appliesTo/observedIn·core hasViolation·sourceGuide/Section·identifier/text/title 8은 의도적 multi-signature/cross-cutting → 제외(by-design, F17 오탐).**
- ⚠️ **B3a 정정** (`c5919af`): B4 Openllet 게이트(owl:Nothing 실쿼리)가 **사전-존재 KB 비일관 적발** — `haz:Fall` 등 **7 canonical 코드가 haz:AccidentType이자 haz:Hazard**(같은 코드가 `addressesAccidentType`/`addressesHazard` 양쪽 목적어)인데 B3a가 둘을 disjoint 선언. `kosha-facet-axis-disjoint.ttl`에서 **haz:Hazard 제외(10→9축)** → 재적재 **owl:Nothing HTTP 200 count 0**(전 HTTP 500), 추론 liveness OK. **교훈: Openllet lazy `prepare()`의 "Server Started"는 일관성 증거 아님 — 실제 추론 쿼리(owl:Nothing) 필수. disjoint pre-check는 domain/range 주입까지 포함**(신규 `scripts/check_disjoint_consistency.py`). haz:Hazard는 하위 0 빈 축(F4)이라 AccidentType와 통합 대상(B5).
- ✅ **B5/F4** (`bb76d1f` → 이 커밋): 최초 (a) `AccidentType ⊑ Hazard`(`bb76d1f`)는 AccidentType만 2-level로 내려 **축 계층 비대칭**(타 축은 RiskFeature 직속)을 만들어 사용자 반려 → **(c) haz:Hazard 클래스 폐지**로 전환. 4 Hazard-range 속성 객체가 코퍼스 **100% AccidentType**(738/2484/8/8, agent/ctx 0)이라 Hazard은 빈·중복 클래스. **repoint**: 4 range + 3 allValuesFrom 제약(v4-restrictions) + R-11 SWRL classPredicate + demo fixture → `haz:AccidentType`, **haz:Hazard 선언 삭제(v2.owl)**. 서빙 무영향(serving-team .py 참조 0). **결과**: AccidentType이 RiskFeature 직속 단일 부모로 복귀(균일 평탄), class 628→627, **haz:Hazard 잔여 참조 0**. 게이트: compare_graphs(전부 Hazard→AccidentType repoint·facet-disjoint 동치), check_disjoint 0, verify-manifest/prefixes, Openllet 재적재 일관(owl:Nothing 0). **F5(ctx 5 빈 sub축) 잔여.**

- 🔍 **F5/중복label/속성중복 triage** (코드 변경 0): 정밀조사로 셋 다 단순 결함 아님 — **F5** ctx 5축은 개체 보유+she:range라 구조 결함 아님(she:has* used=0=SHE/data 갭), **중복label**(F19) 정당한 homonym, **속성중복**(F20) sr:addressesHazard~addressesAccidentType는 둘 다 활성(다른 룰 서브시스템)이라 통합=별도 refactor. 백로그 정밀화.
- ✅ **SHE ABox 온톨로지 통합** (이 커밋, **F5 해결**): F5의 진짜 원인 = SHE 패턴 ABox(**965패턴×6축 맥락**)가 데이터팀 `she-instances-v1.ttl`에만 있고 온톨로지 미적재 + 2026-04 생성이라 **KOSHA-22 이전 legacy 어휘**. 신규 `scripts/gen_she_abox.py`가 `migrate_vocab_to_kosha22` 결정적 치환으로 **forward 마이그레이션**(롤백 아님 — 데이터 100% 재활용, 코드 155 전수 resolve·gap 0) → `kosha-instances-she.ttl`(49,689 triple) + manifest(SRV/CON/MAT/FAC). ⚠️ Openllet 1차가 **she:triggerText datatype 비일관**(@ko langString vs range xsd:string, 1,623건) 적발 → v2.owl range **xsd:string→rdfs:Literal** 완화 → 재적재 **owl:Nothing 0·일관**, **she:hasPPEState 0→965, SHE 패턴 965, F5 5축 실채움**. orphan-TTL 스윕으로 "또 있는지" 확인 = SHE 외 큰 누락 없음(pipe-A pilot fixture만). ('온톨로지가 정본, data-team 산출물 migrate' 원칙.) ⚠️ **2026-06-12 CAT-4 후속(`68cc76b`)**: 이 965 ABox(`kosha-instances-she.ttl`)는 **퇴역** — PG `she_catalog` 활성 전량을 `export_she_catalog_to_abox.py --scope active`로 emit한 **`kosha-instances-she-full.ttl`(1,675패턴, status approved_auto/manual)**가 manifest 활성 프로파일(SRV/CON/MAT/FAC)에서 대체(full ⊇ 965, diff 0). 현행 온톨로지 SHE = PG 활성 1,675 정합.
- ✅ **facet fine 한글 라벨 완결** (이 커밋, F6/F7·nolabel 339→0): facet-taxonomy fine 클래스 418개 라벨 전무 → `gen_facet_taxonomy.py`가 `risk_feature_catalog.json` 한글 label emit(412) + catalog 미보유 6은 `facet-ko-labels.json` 보충 = **418/418 @ko**. 번역 아닌 **데이터팀 catalog 한글 재활용**. compare_graphs -0/+418(전부 라벨), catalog nolabel 339→0. 라벨=annotation이라 reasoner 게이트 불요.

## ⭐ 2026-06-01 — fine granularity 보존+활용 graded matching (WC-C, push 완료)

승인 plan `~/.claude/plans/jiggly-shimmying-starlight.md`. 목표: Vision이 fine 코드 인식해도 fold(fine→canonical)로 변별 손실 → 엉뚱 CI/Guide 추천을 graded matching(fine-first)으로 보정.

- 🔬 **경험 재조정(중요)**: accident_type 파일럿 착수 전 PG 확인 → **엔티티(SR/CI/Guide)에 진짜 fine accident/agent 태그 없음**(CRUSH/CUT/FALLING_OBJECT 등 legacy 별칭만; `FALL_FROM_HEIGHT` 보유 guide=0). graded match는 양쪽(관찰+엔티티) fine 필요 → accident/agent는 **entity fine-tagging enrichment 선행 필요**(별도·큰 작업). **work_context만 GF(`guide_entity_feature_candidates`)에 진짜 fine 51종**(FORKLIFT_OPERATION 48guide·HEAVY_LIFTING 93·WELDING 28…) → 사용자 결정 **work_context로 파일럿 전환**.
- ✅ **WC-C 서빙 fine-first (기본 경로)**: `query_guide_for_facets`(Three-Worlds=기본 추천)에 GF 기반 fine work_context 매칭 추가 + `match_fusion_service` 정렬 관통. **fine-first 결정적**(관찰 fine wc를 GF 보유 guide가 fold-only 항상 상회). `FINE_GRADED_MATCH` flag(호출시점, default **off=무회귀**). 신규 헬퍼 `_fine_wc_match_guides`(690-744 hazard-direct boost 패턴 일반화) + `scripts/verify_fine_graded_wc.py`.
- **검증**(forklift, FORKLIFT_OPERATION): OFF/ON **197/197 후보 동일(recall 불변)**·OFF순서=기존, **43 fine guide 결정적 상위**(last fine rank 42 < first non-fine 43). 무회귀+승격 입증.
- ✅ **WC-D eval + flag 기본 ON**: `scripts/eval_fine_graded_wc.py`(synthetic 330→204 고유 입력, expected_features 주입·LLM 0). **recall/within-order/fine-first/canonical-control 204/204 무회귀 입증** → `_fine_graded_enabled` **default ON**(env로 비활성). 단 합성셋(제빵/주방)은 GF fine(산업 위주)과 겹침 적어 보정 발동 5/204(forklift 수동 43). 더 큰 효과 = GF fine 태그 확장.
- 🔧 **COV 커버리지 확장 인프라 준비**(키 대기): WC-D 5/204 발동의 병목=GF fine 태그 부족. **재사용 판정**(SHE/라벨 원칙): 엔티티→fine 매핑은 기존 산출물에 **없어 생성 필수**, 단 입력은 재사용(guide_llm_domains 1038 도메인힌트·synthetic_obs 검증셋·fine 한글어휘·71 UNKNOWN+라벨). 신규(mock plumbing 전부 검증·키 불요): `llm-scripts/llm_client.py`(OpenAI+Anthropic+mock 통일, enum=allowlist 환각차단)·`curate_wc_rollup.py`(rollup 71 UNKNOWN→canonical, wrong_facet 플래그)·`tag_guides_wc_fine.py`(guide→fine wc→GF insert `method=llm_enriched_wc/candidate`). **키 설정 후**: `curate_wc_rollup --run --apply`(rollup 패치) + `tag_guides_wc_fine --run --limit N --apply`(GF) → `eval_fine_graded_wc` 재실행 lift 측정. 모델 하이브리드(curate strong, tag cheap).
- ✅ **COV 실행/적용**(2026-06-01, 키 .env 자동로드 OPENAI+ANTHROPIC): **curate**(Claude sonnet-4-6) 71→51배정, **21건 ≥0.7 rollup 적용**(OVEN_OPERATION→HEAT_COLD_WORK·EV_BATTERY→ELECTRICAL_WORK 등) — `shared/reference/wc_rollup_overrides.json` + `build_canonical_vocabulary` override 병합 wiring으로 **regen-safe**(직접 패치 아님). **tag**(gpt-4.1-mini) 파일럿 30→131 GF행 적재, **루프 검증**(CHEMICAL_MIXING 관찰→23 guide fine_match·top promotion). **전체 943 guide 태깅 완료** → GF `llm_enriched_wc` 3424행/938guide/**149 fine 코드**(기존 51→149, +192%; proposal 파일 기록 후 dedup·멱등 적재, UNIQUE 위반 dedup 버그 수정). **WC-D lift: fine 보유 입력 5/204→125/209(60%)·top-1 보정 107/125** — 보정 25배 확장(OVEN→오븐guide P-123 등). 안전: **canonical_control 209/209**(무신호 0변화)·fine_first_partition 209/209. recall_identical 147/209 하락=top-300 truncation(광범위 코드 풀>300, fine promotion이 top-N 재구성=의도된 보정; WHERE/canonical 풀 불변).
- ✅ **#1 실효 수치화**(`scripts/eval_fine_effectiveness.py`, synthetic v1~v10 998관찰 다양업종): **fine_precision@6 OFF 0.059→ON 0.383(+0.324, 6.5배)** — canonical-only가 묻은 맥락-특화 guide를 fine-first가 top-6에 끌어올림. coverage 76.2%(태깅 도달), activation 46.4%. (라벨/사진 없어 correctness 아닌 specificity proxy.)
- ✅ **#2 전 축 확장 완료**: 서빙 fine-first **3축 일반화**(`_fine_match_guides`). accident_type(917 guide/132 fine)·hazardous_agent(786 guide/86 fine) LLM 태깅(gpt-4.1-mini, file→GF dedup·멱등, method `llm_enriched_acc/agt`). tag_guides `--axis` parametrize. **3축 효과 eval: coverage 76%→92.4%, fine_precision@6 OFF 0.414→ON 0.782(+0.367)** — 추천 top-6의 78%가 맥락-특화 guide(canonical-only 41%). GF LLM 태그: accident 4857행/work_context 3424/agent 1765. ⚠️ **2026-06-20 갱신**: 이후 cross-axis 631건 재분류로 현재 PG `guide_entity_feature_candidates`(GUIDE) = accident **4,226**/work_context 3,424/agent **2,396**(합 6,622 보존).
- ✅ **WC-A/B 온톨로지 정합**: PG GF의 LLM fine 태그를 **온톨로지 ABox로 emit** → `kosha-instances-guide-fine.ttl`(957 guide / **9415 fine triple**: guide:addressesHazard/guideAddressesAgent/guideAppliesToContext + fine 코드, fold 안 함). 신규 `gen_guide_fine_abox.py` + 공통 SSOT `code_iri_mapper.fine_iri_fragment`·`canonical_vocab.same_axis_fine`(taxonomy·allowlist·emit 동일 기준). taxonomy 재생성(rollup 21 override 재부모화: CashierArea→GeneralWorkplace·EvBattery→ElectricalWork 등) + allowlist 69→487 + manifest(SRV/CON/MAT/FAC). 게이트: **check_disjoint 충돌 0**·validate_canonical_codes PASS·prefixes/manifest OK·미선언 클래스 0·Fuseki owl:Nothing(진행). same-axis만(cross-axis/UNKNOWN 631 skip → rollup 큐레이션 대상). **온톨로지가 fine 지식 정본 보유 = PG 정합**(서빙=PG 불변). 잔여: accident/agent rollup 큐레이션·서빙앱 재시작.
- ⚠️ **도메인 캐비엇**: WC-D 합성셋=제빵/주방, KOSHA guide=산업/기술 → synthetic lift는 제한적일 수 있음(산업 관찰엔 실효). 더 정밀한 측정은 산업 시나리오 eval 필요.
- **잔여**: (백그라운드 후) WC-D lift 측정·전 guide GF 반영 / CI fine(canonical_ci↔GF 링크)·WC-A/B(온톨로지 fine wc 물질화)·accident/agent entity fine-tagging(findings F22).

## ⭐ 2026-05-31 (이어서2) — F20 sr 속성 hard merge (push 완료)

- ✅ **F20 `sr:addressesHazard` → `sr:addressesAccidentType` hard merge**: F4c로 둘 다 domain(SR)·range(AccidentType) 동일 동의어가 됐고 데이터가 두 술어로 분산(addressesHazard 738트리플/626행, addressesAccidentType 284행; **both 284·H_only 342·A_only 0**). 객체는 양쪽 모두 canonical 사고유형(fine 0)이나 addressesHazard만 6종(ChemicalExposure/ElectricShock/FireInjury/OtherAccident/OxygenDeficiency/TempExtremeContact) 보유 → "addressesHazard 버리기"는 **342 SR 손실**이라 **union 흡수** 방향.
  - **방식**: ⚠️ rdflib parse→serialize round-trip이 law:fullText 등 **여러 줄 리터럴 공백을 정규화**(~1052 무관 트리플 변형, 단일변수 위반) → 폐기하고 **바이트 토큰 치환**(`scripts/migrate_f20_addresses_hazard.py`) — turtle 반복술어=union, RDF set 중복제거, 리터럴/줄끝 무손실. 생성기 fix: `export_owl.py` L271(addresses_hazard 컬럼→addressesAccidentType emit) + `gen_canonical_code_shape.py`(targetObjectsOf 제거). TBox 선언삭제(v2.owl)·restriction onProperty·SWRL R-4·SHACL K-R4/R-15/16/30·demo-chain·CATALOG 재생성.
  - **게이트**: **compare_graphs -738/+417 단일변수**(전부 addressesHazard↔addressesAccidentType, 타 술어 0), verify-prefixes 0·verify-manifest 정합, **Fuseki Openllet 재적재 owl:Nothing 0**(restriction onProperty 이동·SWRL 변경 후 일관 유지 — 객체 이미 AccidentType라 신규 type 추론 NO-OP).
  - ⚠️ **부수 발견**: ① kosha-instances.ttl이 현 PG보다 **+23K 드리프트**(guide:ciInWorkContext 등) — 전체 재export는 무관변경을 끌어들여 타깃 rewrite 채택(생성기 수정으로 미래 export는 일관). ② **F21 신규**(F4c 잔재): `kosha-rules-r14-r30-shacl-construct.ttl` R-15/16 본문에 폐지된 `?hazd a haz:Hazard`(L66·84) 잔존 → 해당 bridge 룰 dead. F20 단일변수 유지 위해 미수정, 별도 정리 대상. ✅ **2026-06-20 정정**: 이후 WS-GATE-7(owa-cwa)에서 R-14/R-15 본문을 `haz:AccidentType`로 repoint 완료 — 현재 shape 본문 라이브 `haz:Hazard` **0건**(L55/56/76 주석만 잔존), R-24 cascade revive.

**남은 batch** (findings 문서 B3b/B6 + 선택 refactor): B3b 축내 disjoint(저가치) / B6 BFO grounding(risk:RiskFeature=Quality인데 자식 Object/Process 혼재, top·고위험) / ~~**F21**(F4c 잔재 r14-r30 haz:Hazard 본문)~~ → ✅ **2026-06-20 WS-GATE-7 repoint 완료** / (선택) F5 다축 ctx prune·fine 코드 prune. (~~F20 sr 속성 통합~~ → **hard merge 완료**, 위.) **권고: 구조 변경은 코퍼스-aware + 실추론쿼리(owl:Nothing) 게이트로.**

## ⭐ 2026-05-31 — Phase 3 facet taxonomy(궁극 목표 달성) + P1.6b archive 정리 (push 완료)

origin/main HEAD `1dab81a`. 재설계 Phase 3(facet 리모델) 온톨로지 레벨 완료 + B-트랙 위생(B1 archive / B2 restructure 화석 / A 포맷중복 / B3 SWRL 은퇴) 완료. 승인 plan: `~/.claude/plans/calm-hugging-pond.md`.

**Step 0 — serve_facets cp949 버그픽스** (`5ed927b`): serve_facets_sparql.py가 부팅 마지막 print의 em-dash(—)를 Windows cp949 콘솔이 인코딩 못 해 백그라운드 런치 시 크래시(UnicodeEncodeError). `sys.stdout/stderr.reconfigure(utf-8)` 영구 수정(validate_prefixes 패턴).

**Phase 3 — facet taxonomy (vocab 단일 SSOT)** (`8adb79a`):
- **진단** `scripts/diff_facet_sources.py`: catalog `sub`(구 생성기 입력)와 vocab `rollup`이 같은 fine→canonical 지식 **중복 보유·구조 상이**. 계산 결과 = **vocab rollup이 완전·정본 상위집합**(catalog는 79/69/186 dangling=canonical 미도달, work_context 계층 통째 부재). ∴ "합집합"=vocab 채택.
- **신 생성기** `scripts/gen_facet_taxonomy.py`(vocab rollup SSOT): ① canonical owl:Class **punning** 62 ② fine⊑canonical 418(same-axis) ③ ctx 계층(rollup 자동, `ForkliftOperation⊑Vehicle`). **cross-axis 21건 제외**(agent→haz; Python `canonical_vocab.to_canonical`가 서빙/물질화 시점 재라우팅 — 온톨로지 subClassOf 불필요, `to_prefixed`가 None 반환해 자동 제외). 교차검증 게이트(생성 canonical IRI ⊆ 기존 NamedIndividual)로 casing 드리프트 차단.
- `kosha-facet-taxonomy.ttl`이 구 `kosha-ontology-v3-subclass-patch.ttl` **대체**(manifest swap, profiles SRV/CON/MAT/FAC 동일), 구 patch archive, 구 생성기 `regenerate_subclass_patch.py` deprecate(footgun guard). 검증기 `scripts/verify_facet_taxonomy.py`(explained-delta 게이트) 신규.
- **검증(단일변수)**: explained-delta `+836/-281`(부모변경 7 = GasolineVapor/RadiationExposure→Toxic/Radiation 의도된 평탄화), verify-manifest green, SHACL conforms, **functional(serve_facets 3031): ctx owl:Class 6→221 / haz 137→183 / agent 37→85, `forklift⊑vehicle`=True, total Δ+555 = patch diff와 정확 일치**(전체 1.44M 그래프 그외 무변경 입증), verify-prefixes 0위반.
- **A1 Openllet DL 일관성** ✅: Fuseki(REASONER_MODE=openllet, `-Xmx30g`) 재기동 → 981,995 base 분류 **모순 없이 완료**(prepare() 통과→Server Started). 라이브 쿼리: `ctx:ForkliftOperation`의 추론 상위클래스 = {Vehicle(asserted), owl:Thing(**추론**)} → DL 추론 작동 + forklift→Vehicle 인식 확인.

**서빙 forklift 변별 — 조사 결론(중요)**: 3개 read-only 조사 일치. 서빙은 `canonical_vocab.to_canonical`(하드코딩 JSON rollup) + 하드코딩 cross-inference 규칙으로 FORKLIFT_OPERATION→VEHICLE 변환, **Fuseki/온톨로지 계층을 work_context 매칭에 안 씀**(복합축 enrichment에만 선택적). CLAUDE.md "온톨로지≠서빙"과 일치. ∴ **온톨로지 재물질화로는 서빙 forklift 변별이 안 생김** — gap = `kosha_guides`/`canonical_checklist_items`가 canonical-only(SR/CI엔 fine 컬럼+fine 매칭/부스트 이미 존재). → **서빙팀 백로그로 scope 확정**(guide/CI에 fine work_contexts 컬럼 + import 확장 + query_guide_for_facets fine 부스트 + 8-photo eval에 work_context 측정 추가). 8-photo eval은 현재 work_context를 아예 측정 안 함(mapped_codes=accident_type만).

**B1 — P1.6b archive 물리이동 + snapshot 삭제** (`9b0e51b`): archive 10 ttl/owl/swrl → `archive/`(git mv, history 보존), serving-snapshot 8개 **74MB git rm**(PG materialize 재생성 가능·비추적 정책). manifest_source archive 경로 `archive/<name>`, snapshot 엔트리 제거(60→52 files), `validate_prefixes` archive/ subtree skip 추가. **verify-manifest GREEN**(dir 52=SSOT 52, silent-orphan 0), verify-prefixes 0위반, active profile 카운트 전부 불변(archive=소비자 0). (full active-layering tbox/rules/abox는 `_dir_files`·Fuseki 경로 변경 필요 = cosmetic·고위험 → B1b 보류.)

**B-트랙 위생 완료** (2026-05-31): **B2** restructure-patch 화석 archive(의도 이미 v2.owl에 — 3축⊑RiskFeature/CriminalSanction⊑SanctionType, patch는 오타+파싱실패) `17b51c1` / **cleanup** 삭제 snapshot의 stale 리포트 48개(validation-report+workprocess-alignment × json/md/csv) 제거 `6846b76` / **A** v2.formatted.ttl 포맷중복 제거(=v2.owl 동치 triple diff 0, facet-explorer→v2.owl 통합) `e78fe29` / **B3** SWRL-RDF→SPARQL 충실변환 vs pyshacl로 **SWRL≡SHACL parity 입증**(demo-chain 15 triple, 차이 0) → R-14~R-30 SWRL 4파일 은퇴(R-1~13 Pellet+R-27 SHACL-only 유지, CON 27→23, conforms 회귀0) `af6840a`·`1dab81a`. 신규 진단/harness: `diff_facet_sources`/`verify_facet_taxonomy`/`verify_rule_parity`.

**남은 것**: B1b 디렉토리 layer화(생성기 ~10개 출력경로 갱신 동반 = 보류) / 서빙 백로그(forklift fine 변별·catalog sub 마이그레이션 — 둘 다 runtime 의존, 서빙팀) / 구 Three-Worlds #10·#11 재평가. 상세 scope: plan `~/.claude/plans/calm-hugging-pond.md` 「## 남은 작업」.

## ⭐ 2026-05-30 (오후) — prefix 표준화 + manifest 단일정본 재설계 Phase 1 (push 완료)

**승인 plan**: `~/.claude/plans/calm-hugging-pond.md`(이제 **온톨로지 체계 재설계** — Phase 1 manifest / Phase 2 구조심화 / Phase 3 facet 리모델). 동기: 버전·패치 난립 + 6 로더 제각각 하드코딩 → "무엇이 온톨로지인가" 단일 정본 부재.

**A. prefix/namespace 표준화** (`1aa0743`): cashtoss.info 네임스페이스마다 정본 짧은이름1+IRI1.
- `agent:` 의미 과부하 → `agent:Worker`(행위자) **`actor:` 분리**. 별칭 통일(context→ctx/hazard→haz/sit→she/penalty→pen). 화석 `kosha-instances.original.ttl` 삭제(레거시 28k). guide-profile-patch orphan 수정(`kosha:KoshaGuide`→`guide:KoshaGuide`). 생성기 `regenerate_subclass_patch.py` axis casing(accident=UPPER, agent/ctx=Pascal). pipe-A pilot `ontology/hazard#`→`risk/hazard#`.
- **신규 가드레일**: `validate_prefixes.py`(+`make verify-prefixes`), `compare_graphs.py`(그래프 동치 오라클). 검증: 위반 0 / 레거시 0 / 리즈너 conforms=626.
- v3 G-patch(incompat/guide-profile/penalty-relations/restructure)는 **Phase G TBox SoT라 유지**(삭제 안 함). ⚠️ restructure-patch는 파싱실패(`<>` 누락 3줄) — Phase 2 수리 대상.

**B. manifest 단일정본** (`f751397`) — 평탄화(merge) 아니라 명명:
- `assembly/manifest_source.py`(SSOT 59파일·6 profile) → `gen_manifest.py` → `assembly-manifest.json`. `assembly/manifest.py`(소비자 `load_profile`). `validate_manifest.py`+`make verify-manifest`(silent orphan 0+freshness 게이트).
- **6 소비자 repoint**: Python 5(run_shacl/local_consistency/serve_facets/run_inference/run_guide_hazard) + **Java Fuseki**(번들 `org.apache.jena.atlas.json`, 추가 의존성 0, bind-mount라 이후 파일집합 변경 시 Java 재빌드 불필요).
- **base v1→v2 정정 = facet 버그 해결**: serve_facets/run_inference가 v1 base 로드+subclass 누락 → v2+subclass/disjoint → **facet-explorer haz 2→137 / agent 1→37 owl:Class** 정상.
- 검증(no-op): 6 profile==기존 하드코딩(set-equality), run_shacl conforms=626 불변, Fuseki 21파일·base 981,440, local_consistency merged 26 동일. **serving/consistency/shacl 그래프 불변**.

**핵심 발견(Phase 3 동기)**: facet 코드 class/individual 비정합 — haz/agent: fine=class·canonical=individual, **ctx: 전부 individual·subClassOf 0**(107 정의 중 29만 facet 사용, `ctx:ForkliftOperation` 등 78 잠금 → forklift 변별 상실의 근원). 데이터 개체(SR/CI/Guide/관찰)는 individual 유지가 정답.

**다음 (우선순위)**: **Phase 3 facet 리모델**(haz/agent/ctx→일관 owl:Class+subClassOf taxonomy, canonical도 class화, ctx 계층 신설, **punning으로 기존 facet assertion 51,776 보존**, 데이터 개체는 individual 유지 → forklift fine 변별 복원 → PG 재물질화) = **궁극 목표**. / (선택) P1.6b 물리 archive 이동(17파일 archive/) + serving-snapshot 78MB 삭제 / Phase 2 구조심화(layer 디렉토리 + SWRL→SHACL parity-gated + restructure 수리). **serve_facets(3031)는 재시작해야 고쳐진 explorer(haz=137) 반영**.

## ⭐ 2026-05-30 — Three-Worlds CI/Guide 매칭 재설계 S1 (Phase 0/1/3a, working tree)

**메인 작업.** 사용자 재정의: open-world(사진 hazard) → closed-world(SR/CI/Guide) 매핑, **온톨로지=SoT + 업데이트 메커니즘, PG=특정시점 스냅샷**. 문제: 실사진에서 SR은 매칭되나 **CI/Guide 안 됨**. 근본 원리(사용자 합의): **CI는 고유 control 세계, Guide는 분야별로 control을 묶는 bundle 계층. open-world O는 CI·Guide와 각각 독립 facet 매칭, 구조(Guide-bundles-CI)는 랭킹 corroboration.** boilerplate=canonical CI의 guide-degree(구조). PG-side 인버전(derive_guide_hazard_features+export_guide_hazard_to_abox) 폐기 → 온톨로지 유도 → PG 물질화. 승인 plan: `~/.claude/plans/calm-hugging-pond.md`.

**Phase 0 — Canonical-CI 레이어** ✅: `kosha-ontology-v4-canonical-ci-patch.ttl`(`CanonicalChecklistItem ⊑ ChecklistItem` + `realizesControl`/`bundlesControl`/`controlBundledBy`). `derive_canonical_ci.py`(정규화-텍스트 NFKC 군집): **54,631 instance → 51,263 canonical**(축소 6.2% — 정확-텍스트는 literal boilerplate만; 큰 dedup은 semantic merge=Phase 3b gated), degree=guide_frequency(max 130), boilerplate 71(degree≥10). PG staging: `canonical_checklist_items`/`guide_control_bundle`/`checklist_items.canonical_ci_id`. `export_canonical_ci_abox.py` → `kosha-instances-canonical-ci.ttl`(466k triple, facet/degree/basedOnSR 집계 직접 부여 → inverse 링크 불요).

**Phase 1 — facet 유도(ontology SHACL)** ✅: `kosha-rules-guide-hazard-shacl.ttl`(6 CONSTRUCT: CI-SR 상속 3 + non-boilerplate Guide rollup 3) + `run_guide_hazard_rules.py`(rdflib fast-path, fixpoint) → `kosha-instances-ci-guide-hazard-derived.ttl`. **Guide rollup 10,423**(addressesHazard 2484 / guideAddressesAgent 3227 / guideAppliesToContext 4712, boilerplate 제외). **CI-SR 상속=0**(pipe-B step6가 이미 SR-enrich → CI accident 희소(27%)는 SR로 못 메움, **Phase 2 orphan 재태깅이 유일 lever**).

**Phase 3a — ontology→PG 물질화** ✅: `import_guide_facets_to_pg.py`(IRI→code SSOT 역변환 + wc_meta) → `kosha_guides` facet 컬럼(addresses_hazard **832 guide**>구 인버전 659 / agent 986 / context 979). `make verify-codes-shape` 대상(derived) **conforms=True**. ⚠️ **2026-06-20**: 이후 2dd19b2 accident 큐레이션 재물질화로 현재 addresses_hazard = **996 guide**(agent 986 / context 979 불변).

**검증 데모**(지게차 facets accident=CAUGHT_IN/COLLISION/CRUSHED_OVERTURNED, ctx=VEHICLE, PG 직접쿼리): **O↔CI 독립 매칭 = 좌석안전띠·포크삽입·차량브레이크·통로보호 등 정확 + boilerplate 71 억제 ✅**. O↔Guide = 항만하역 등 관련 + 광범위 VEHICLE 오매칭(오토바이배달) 잔존 → **Phase 4 fusion(corroboration 랭킹)이 sharpen 예정**.

**Phase 4 — 서빙 엔진** ✅ (구현+검증, **wiring ⏳**): `models.py`(PgCanonicalChecklistItem/PgGuideControlBundle + PgKoshaGuide facet 컬럼 + PgChecklistItem.canonical_ci_id), `hazard_rule_engine.query_ci_for_facets`/`query_guide_for_facets`(query_sr_for_facets 미러, CI 특이도=1/log2(2+guide_degree)), `match_fusion_service.fuse_matches`(O↔CI/Guide 독립 + **Guide corroboration boost**: 매칭 CI를 bundle한 Guide 가산). **WSL venv 실검증**(`scripts/verify_fusion_matching.py`): 지게차 → **B-M-11 지게차 안전작업 + A-G-18 항만하역이 corroboration으로 top, 오토바이배달 top-8 탈락** ⭐. O↔CI = 좌석안전띠·포크삽입 등 정확. (화학 시나리오: corroboration 미발화(분석 guide가 안전 CI 미bundle) → CI→guide recall 채널 추가가 후속 튜닝 후보.)

**Phase 4 wiring** ✅ (2026-05-30): `analysis_pipeline`이 `get_immediate_checklist_items`/`get_standard_guides`(무순위 junction/CI-count 전이 경로) 대신 `match_fusion_service.build_recommendation_rows`(계약형 CI/Guide row 어댑터 — 대표 instance + work_process_steps 보강) 호출로 교체. SR과 동일 게이트(`actionable_matches or observable_violation_signal`)로 negative-case false positive 방지. **검증**: WSL venv로 import OK → **Gate 3 PASS**(2,360 replay, false_positive_rate 0.87 유지·SR/SHE/penalty 회귀 0) → **8-photo eval**(Vision, parallel): 8/8 100% mapping, 48 procedures, 크래시 0.
- ⚠️ **정직한 한계**: 지게차 photo의 fusion procedures가 canonical `VEHICLE` 매칭 → 항만하역·컨베이어·이동식크레인 등 **광범위 vehicle/material-handling guide**(합리적이나 핀포인트 아님). **2026-05-29 ctx_boost의 fine `FORKLIFT_OPERATION` 변별 상실**(canonicalization이 FORKLIFT→VEHICLE 뭉갬). corroboration은 작동하나 소수 forklift CI가 다수 generic CI guide에 밀림. → **task: Phase 4 튜닝(fine work_context 보존·매칭 + corroboration을 CI 특이도 합으로 가중)**.

**다음**: Phase 4 튜닝(fine work_context 변별) → Phase 2(orphan 재태깅) → Phase 3b(hard-cut 인버전 삭제 + semantic merge). 재현 파이프라인: `derive_canonical_ci.py --apply` → `export_canonical_ci_abox.py` → `run_guide_hazard_rules.py` → `import_guide_facets_to_pg.py --apply` → (서빙) `verify_fusion_matching.py` / 8-photo eval.

## 2026-05-30 — Phase 5 incremental 가드레일 (Deferred #2 일부, working tree 미커밋)

2026-05-29 Deferred 후속 #2(Phase 5 incremental) 중 **자기완결·저위험 2건** 구현. 둘 다 SSOT(`canonical-code-vocabulary.json`) 파생 — 하드코딩/ PG re-tag 무영향. 자세히: [../dev-notes/phase5-incremental-guardrails.md](../dev-notes/phase5-incremental-guardrails.md).

**2a — SHACL codes∈canonical 가드레일** (선언적; `make verify-codes` regex 게이트의 보완재):
- `ontology-team/06-reasoning/ontology/scripts/gen_canonical_code_shape.py` → `kosha-canonical-code-shape.ttl` (자동 생성, NodeShape 4 = 축별 3 + feature union). 각 shape `sh:targetObjectsOf <코드 술어> + sh:in <정본 IRI> + sh:Violation`.
- 허용 = `canonical_set ∪ meta_set` = accident 23 / agent 10 / **work_context 36(=29+7 wc_meta)** = **69 IRI**. `canonical_vocab.meta_set(axis)` 공개 접근자 신설(additive — wc_meta=SAFETY_MGMT 등 rollup 항등 정당 축값).
- `validate_canonical_codes.py`(pyshacl) + `make verify-codes-shape` / `make gen-canonical-shape`.
- 검증: 전체 ABox **958,666 triple → conforms=True** (Phase 4-B "구어휘 잔여 0"을 SHACL allowlist로 독립 재확인). 음성 테스트(`haz:Crush`/`CAUGHT_IN`/`agent:ArcFlash`/`ctx:Forklift`) **4건 적발 + exit 1**, 정본 통과.

**2c — Layer 4.7 Continual pending 승격 추적** (gate WARN → 정식 태스크):
- `data-team/05-enrichment/llm-scripts/continual_pending_promotion.py` + `make continual-pending`. live PG(SR+CI+GUIDE) 빈도로 pending 코드 랭킹 + tier(PROMOTE≥8 / WATCH≥3 / NOISE). **읽기전용**(mutate 금지), queue 산출(gitignored).
- 현재 스냅샷: accident/agent 0건. **work_context 7건**(전부 GUIDE) — PROMOTE=`WET_FLOOR_WORK`(11), WATCH=`NIGHT_SOLO_WORK`(6), NOISE 5. 승격 결정은 사용자 몫(→ `build_canonical_vocabulary.py` 룰 보강 후 재생성).

**회귀 0**: `audit --gate` CRITICAL=0/WARN=7 PASS, `canonical_vocab`+`code_iri_mapper`(62) self-test PASS.

**신규**: gen_canonical_code_shape.py, validate_canonical_codes.py, kosha-canonical-code-shape.ttl, continual_pending_promotion.py, phase5-incremental-guardrails.md. **수정**: canonical_vocab.py(+meta_set), Makefile(+3 target), .gitignore. **⚠️ 미커밋 — 다음 세션에서 검토 후 commit.**

## ⭐ Canonicalization + KOSHA-22 Sprint — 단일 세션 완주 (2026-05-29) ⭐

지게차 사진 실측에서 정규화(risk_features)는 정확한데 SHE/Guide/즉시조치/표준절차가 엉뚱하게 나온 문제의 **근본 원인 = 단일 정본(canonical) 코드 어휘 미강제(4세대 어휘 공존: catalog 세밀 / PG 거친 / GUIDE seed / 온톨로지 dual-URI)**를 전 surface 정합 + 재발 방지로 해결. 커밋 `bbc9b8c`~`5fdd8a0` (+ merge `f4f078a`), 8커밋 origin/main 반영.

**Phase 1-3 — 정본 SSOT + PG canonical + 서빙 연결** (`bbc9b8c`, `7a465b0`):
- ⭐ 신규 SSOT: `shared/reference/canonical-code-vocabulary.json` (accident 23=**KOSHA-22 공식** / agent 10 / work_context 29) + 단일 소비자 모듈 `shared/reference/canonical_vocab.py` (`to_canonical(axis,code)`, 교차축 인지, self-test PASS). 빌더 `data-team/05-enrichment/llm-scripts/build_canonical_vocabulary.py`.
- **Additive 듀얼 태깅**(덮어쓰기 금지 — fine 코드 보존, SHE 1,616 패턴 무변경): SR/CI에 `*_canonical` jsonb + GUIDE에 `canonical_code`/`canonical_axis` 컬럼 신규, populate (SR 626 / CI 54,631 / GUIDE 70,296). schema `serving-team/07-materialization/pg-sync-scripts/schema_canonical_columns.sql` + `apply_canonical_tags.py`.
- 서빙: `hazard_rule_engine.query_sr_for_facets`/`get_guides_by_hazard_features` canonical 컬럼 조회 → 끼임(CAUGHT_IN)/전도(FALL)/지게차(VEHICLE) SR 커버리지 **0→76**.

**#95 지게차 충돌 잔존 fix** (`64a2a96`): 광범위 COLLISION/ERGONOMIC에서 '오토바이 배달' guide 오매칭 → `get_guides_by_hazard_features` **2-tier ctx_boost**(scene 구체 fine work_context(FORKLIFT_OPERATION) 보유 guide 강부스트 +0.30 [entity_type 무관 하위행 fine 활용], generic VEHICLE만 공유 약부스트 +0.05) + `_merge_guide_paths` CI-only −0.06. **실제 Vision 재실행 bad-hit 0** (오토바이 소멸, '지게차 운전자 교육' 표준절차 등장).

**Phase 4-B — 온톨로지 KOSHA-22 전면 마이그레이션** (`94bcdbb`): 3 공존 어휘 → KOSHA-22 단일 CamelCase **62개**.
- `serving-team/08-app/backend/app/integrations/code_iri_mapper.py`: 하드코딩 8/11/13 테이블 폐지 → **SSOT 파생 + 결정적 `_camel()`** + 구→KOSHA22 LEGACY 매핑 (sparql_queries 백워드 호환 유지).
- `ontology-team/06-reasoning/ontology/scripts/migrate_vocab_to_kosha22.py`: 50 TTL 결정적 fragment 치환 **~20,820건** (Crush→CaughtIn, Cut→CutLaceration, FallingObject→StruckBy, agent ArcFlash→Electricity, agent/ctx UPPER→CamelCase 등). `kosha-instances.original.ttl` 백업 제외.
- `kosha-ontology-v4-kosha22-vocab-patch.ttl` (62 NamedIndividual, `gen_kosha22_vocab_patch.py` 생성) + `kosha-accident22-disjoint.ttl` KOSHA-22 CamelCase 재작성.
- 검증(`validate_kosha22_migration.py`): 활성 TTL 구어휘 잔여 **0**, rdflib 파싱 OK(ABox 956k triples), disjoint rdf:type 위반 **0**, Gate 3 2,360 PASS.

**Phase 5 — 재발 방지 가드레일** (`c5e3bac`, `012b845`, `5fdd8a0`):
- ⭐ `scripts/audit_code_consistency.py --gate` — 온톨로지 UPPER/dual-URI 재발 시 **exit 1** (SSOT 인지; PG fine 코드의 pending(UNKNOWN) orphan은 WARN, open-class 허용). **`make verify-codes`** 등록. **게이트가 실제로 Phase 4-B의 agent/ctx UPPER 25종 누락을 적발 → 1,856건 자동 수정 → PASS** (재발방지 메커니즘 작동 입증).
- exporter 3종(`export_owl`/`export_guide_hazard_to_abox`/`export_8photo_to_abox`) → `code_iri_mapper` SSOT 일원화 (향후 PG 재생성 dual-URI 재발 차단).

**검증 수치**: 전 단계 회귀 0 — 현행 수치는 정본 [evaluation-baseline.md](evaluation-baseline.md)의 **Gate Baseline 거버넌스 anchor** 참조(직기재 금지, CLAUDE.md 규칙; `make verify-baseline`이 정본↔게이트 일치를 기계 검증).

**⏸️ Deferred 후속 (라이브 영향 없음 — 온톨로지 offline, 서빙은 PG 기반이라 forklift fix 이미 live)**:
1. **Fuseki Openllet reload** (~30분 warmup, 선택적 SPARQL enrichment만 영향): WSL `cd ontology-team/06-reasoning/ontology/docker && docker compose restart fuseki`. ⚠️ **2026-05-30 발견**: `KoshaFusekiServer.java`의 sources 목록이 in-place 마이그레이션된 `kosha-instances.ttl`(volume-mount, restart로 반영)은 로드하나 `kosha-ontology-v4-kosha22-vocab-patch.ttl`(62 NamedIndividual)은 **미포함** → 단순 restart론 정본 개체 선언이 안 됨. 결정 필요: (a) patch를 sources에 추가 + Java image rebuild, 또는 (b) 서빙층 patch 불요 확인.
2. **Phase 5 incremental** (저우선, 게이트 1차 방어):
   - ✅ **2a SHACL codes∈canonical** + ✅ **2c Layer 4.7 continual** — 2026-05-30 완료 (위 §2026-05-30, 미커밋).
   - ⏳ **catalog 죽은코드 deprecated + WRONG_AXIS work_context 정리** — 사용자 판단 + PG re-tag blast radius. 주의: `INTERLOCK_BYPASS`/`LOTO_NOT_APPLIED`/`SAFETY_DEVICE_BYPASS`는 이미 work_context 소속(→UNKNOWN_CONTEXT, catalog L2007–2034) — "WRONG_AXIS 18" 정확 목록 미보존 + "분리" 의도 불명확(meta-condition 별도 분리? 4/5번째 축에서 이동?). curation 의도 확인 필요. 2c가 pending 빈도 정량화(PROMOTE-tier=`WET_FLOOR_WORK` 1개뿐) → 긴급도 낮음.
3. **HTTP 서버 기동**: WSL `cd /mnt/c/project/arch-bot && make dev-up` (PRIMARY는 WSL venv 전용 → Git Bash에서 미기동). 기동 시 지게차 분석이 새 로직으로 LIVE.
4. **LFS**: `kosha-instances.ttl` 58MB(>GitHub 권장 50MB) → git-lfs 후보. 계획: [../dev-notes/large-file-management-plan.md](../dev-notes/large-file-management-plan.md). git history 영향 → 사용자 명시 승인 후 진행.

**다음 세션 재현/검증 (WSL, /mnt/c/project/arch-bot)**:
```bash
make verify-codes        # 코드 어휘 하드게이트 (드리프트 시 exit 1)
serving-team/08-app/backend/.venv/bin/python ontology-team/06-reasoning/ontology/scripts/validate_kosha22_migration.py  # disjoint 0 + 구어휘 0
python shared/reference/canonical_vocab.py   # SSOT self-test
```

## ⭐ axiom-100% Sprint — Phase A~K 완주 (2026-05-20~27)

온톨로지 공리 커버리지 100% 목표. SWRL 의사코드 30개를 정형 추론 가능 facts로 전환.

- **v4 TBox 패치 9종** (Phase A~J): `kosha-ontology-v4-{deps,alethic,bridge,deontic,violation,penalty-extra,restrictions,hazard-direct,asymmetric}-patch.ttl`. owl:Restriction **35** (allValuesFrom ABox-safe), owl:AsymmetricProperty **1** (`law:modifiesAsymmetric`, inverseOf 충돌 회피), NaturalLanguageHazardCategory **21**. ⚠️ **2026-06-20 실측**: owl:Restriction 현재 **37**(v4-restrictions 33 + v3-guide-profile 4).
- **SWRL R-14~R-30 → SHACL CONSTRUCT 전환** ⭐ (Phase C~F): Pellet이 12개 SWRL 조합에서 **NEXPTIME blowup**(22분 무한 재시작) → `kosha-rules-r14-r30-shacl-construct.ttl` (12 sh:rule CONSTRUCT). Java sources에서 4개 SWRL ttl 주석 처리. R-1/R-3만 SWRL native 유지 (Pellet 정상: R-1 107 + R-3 3,579 inferred).
- **K-general SHACL** (Phase K): `kosha-rules-k-general-shacl.ttl` — 같은 Hazard → `core:dependsOn` **36,949** + 같은 Chapter → `core:coApplicable` **16,429** = **53,378 pair** (on-demand materialization, gitignore).
  - ⚠️ **정합(2026-06-14, Track A ②)**: 위 on-demand 수치는 이제 **PG 물질화로 대체**됐다 — coApplicable 16,429쌍은 K-R2로 PG `sr_inferred_relations`에 적재(32,858행), dependsOn은 same-Hazard relaxation 재집계 결과 **K-R4 = 35,165쌍**(70,330행)으로 위 on-demand 36,949와 **다른 수치**다. 서빙은 더 이상 on-demand Fuseki가 아니라 PG를 읽는다(상단 2026-06-14 섹션).
- **production ABox enrichment**: 8-photo eval → `kosha-instances-production-8photo.ttl` (R-10~R-30 fire 입증). sh:NodeShape 총 **1,964**.
- 검증: `scripts/verify_axiom_100pct.py` (5-step) Overall OK. Gate 3 regression PASS.
- Plan/Runbook: [../workplans/ontology-axiom-100pct.md](../workplans/ontology-axiom-100pct.md), [../dev-notes/axiom-100pct-phase-a.md](../dev-notes/axiom-100pct-phase-a.md) / [-b](../dev-notes/axiom-100pct-phase-b.md) / [-c-j](../dev-notes/axiom-100pct-phase-c-j.md).

## ⭐ guide-accuracy Sprint — P0~P3 완주 (2026-05-28)

실 서비스에서 CI 추천은 정확하나 Guide가 엉뚱하게 추천되는 문제 근본 해결 (boilerplate CI fan-out + CI 개수 단독 랭킹).

- **P1 CI 변별력**: `checklist_items.guide_frequency` 컬럼 (동일 텍스트 CI의 distinct source_guide 수) backfill **3,953 CI 갱신, max 130**. `ci_weight = 1/log2(1+gf)` (gf=130 → 0.14).
- **P0 Guide 랭킹 교체**: `hazard_rule_engine.get_guides_from_srs()` CI **개수** → **Σ(ci_weight) 변별력 가중합** + 정규화 + 산업 일치. boilerplate 자동 억제.
- **P2 Guide 직접 위험 매핑 레이어** ⭐: `derive_guide_hazard_features.py` → `guide_entity_feature_candidates(entity_type='GUIDE', method='guide_hazard_weighted_majority')` **2,115행 / 659 Guide**. 신규 `get_guides_by_hazard_features()` (CI 경유 없는 직접 조회) + `_merge_guide_paths()` (직접 우선 + CI union, 교집합 bonus +0.15).
- **P3 온톨로지 정합**: `kosha-ontology-v4-guide-hazard-patch.ttl` (`guide:addressesHazard`/`guideAddressesAgent`/`guideAppliesToContext` + `ciGuideFrequency`/`isBoilerplate`) + `kosha-instances-guide-hazard.ttl` (659 Guide, 2,115 triple). ⚠️ **2026-06-20**: 이 ABox는 이후 `archive/`로 이동 → 현행 fine ABox `kosha-instances-guide-fine.ttl`(957 guide / 9,415 triple)이 대체(PG GF 라이브 보존).
- **8-photo guide eval**: mapping rate 80% → **100%** (27/27), guide_hazard_direct mapping **85%**, boilerplate Guide 출현 **0**. Gate 3 regression PASS (synthetic 회귀 없음).
- Runbook: [../dev-notes/guide-recommendation-accuracy.md](../dev-notes/guide-recommendation-accuracy.md).

## 🎯 Hazard-Direct Pivot — 단일 세션 완주 (2026-05-19) ⭐

본 세션의 핵심 성과. 23일 plan을 단일 세션에서 완주:

- **Phase 1 Day 1**: `ONTOLOGY_OBSERVATION_SCHEMA`에 `hazards[]` 추가 + 14개 표준 라벨 prompt (commit `acd2303`)
- **Phase 2 Day 1**: `generate_hazard_name_seed.py` (Sonnet 4.6 자동 seed) (commit `7a17b47`)
- **Phase 2-5 통합** (commit `7c97118`):
  - Phase 2 Day 2-7: Sonnet 19/21 accepted + 2 manual override → 21 vetted alias 등재
  - Phase 2 Day 3-4: `normalize_hazards_array()` 신규 함수 (hazard_normalizer.py)
  - Phase 3 Day 1-3: `hazard_to_guide_service.py` + analysis_pipeline `HAZARD_DIRECT_MODE` 통합
  - Phase 4 Day 1: `HazardItem` + `GuideRef` + `HazardGuideRelation` Pydantic + AnalysisResponse 확장
  - **Phase 5 Day 1**: 8 real-test-photo 실호출 → **25/25 (100%) 매핑** ⭐ (AC-2 ≥85% **PASS**)
- **Phase 4 Day 2** (commit `5256573`): Frontend `RiskOverviewPanel` 확장 + `HazardGuideRelationsPanel` 신규

8 photo eval 핵심 수치:
- 8/8 photos analyzed
- 25 hazards / **25 mapped (100%)** / 25 relations
- 48 standard_procedures (legacy 병행, 호환성 OK)
- 14 penalty paths (Phase G.3 차별점 보존)
- moellab overlap 18/37 (자연어 표현 차이)

Sprint plan + 결과: [../workplans/hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md)
효과성 raw 데이터: [../../data-team/05-enrichment/runtime-artifacts/hazard_direct_8photo_eval.json](../../data-team/05-enrichment/runtime-artifacts/hazard_direct_8photo_eval.json)

이전 갱신:
- 2026-05-18 (저녁): Tier 1 재포함 + Tier 2 F.3 closing (T2.A-D) + Tier 3.A enum
- 2026-05-18 (오전): F.3 first batch + F.1 sprint (5 vetted aliases) + F.2 sprint (catalog v3.3, 5 axes × 481 codes)

이 문서는 다른 Claude/Codex/LLM 세션이 현재 상태를 빠르게 이어받기 위한 시작점이다.

불변 메타 규칙(팀 구조, 9단계 작업 모델, 폐기 용어, 절대 금지)은 루트 [../../CLAUDE.md](../../CLAUDE.md) 참고.

## 🚀 다음 세션 시작 시 먼저 읽을 문서 순서

### 즉시 (5분 내 컨텍스트 파악)
1. **[../../CLAUDE.md](../../CLAUDE.md)** — 자동 로드 (불변 규칙 + 팀 구조)
2. **이 문서** (status/current-session.md) — 현재 상태 + 다음 작업
3. **[../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)** ⭐ — **메인 plan, 이번 두 세션의 핵심 성과**

### 깊이 (필요 시)
4. [../architecture/4-layer-architecture.md](../architecture/4-layer-architecture.md) — Layer 0-4 전체 구조
5. [../architecture/ontology-learning-layer.md](../architecture/ontology-learning-layer.md) — Layer 4 7-module 정밀 설계
6. [../architecture/llm-dependency-evolution.md](../architecture/llm-dependency-evolution.md) — LLM 의존 폐지 path
7. [../governance/ontology-learning-references.md](../governance/ontology-learning-references.md) — 9 학계 paper 요약

### 기존 baseline / 디렉토리 구조
8. [evaluation-baseline.md](evaluation-baseline.md) — 5번 enrichment baseline (변화 없음)
9. [../architecture/team-structure.md](../architecture/team-structure.md), [stage-mapping.md](../architecture/stage-mapping.md)
10. [../governance/repositories.md](../governance/repositories.md), [data-governance.md](../governance/data-governance.md)

## 📍 현재 상태 한 문장 요약

> "**(2026-06-14) Track A ② 추론 수직 슬라이스 — 신규 PG `sr_inferred_relations` 103,295행(R-1 107행/95SR + K-R2 coApplicable 32,858행 + K-R4 dependsOn 70,330행), 서빙 Fuseki→PG 전환 + 신규 `/depends-on`, PROV `materialization_runs`, f1-regression delta 0 ⭐ + A4/A5 거버넌스(dual license, 릴리스 2.0.0, VoID 1,049,862 triples, SKOS 504 concept) DONE·미커밋.** 누적: Phase 0/B/A/C + E-prep + E.2 + Phase 3 + F.3 first batch + F.1 + F.2 (이전) + Tier 1-3.A + **Phase G PG materialization (G.1: guide_domain_incompatibilities 2,016 rows + G.2: guide_usage_profiles 1,038 PG primary + G.3: penalty_rule_index 4,076 rows → penalty_accuracy +27.16%p ⭐ + G.4: she_patterns_reasoner_derived view)** + **Tier 4 후속 (AsymmetricProperty 패치로 Openllet 정상화 + SWRL Pellet 실행기 통합 → R-1: 107 + R-3: 3,579 inferred ⭐ + Pellet reporting 명시화)** + **T4 #1 후속 sprint (approve 57 / modify 19 / defer 1, batch promote -10.17%p VETOED → matcher refactor sprint plan 작성) + moellab.info/ohs 위험요소 비교 (37/37 합리적, architecture pivot 후보 식별: hazard-direct)**. 사용자 구조 step 4 본격 입증. 다음 1순위: hazard-direct architecture pivot (sprint plan 작성 TBD)."

## 🎯 핵심 성과

### Phase G PG materialization + Tier 4 후속 (2026-05-19)

**사용자 구조 step 4 본격 입증**: "온톨로지화된 KB → PG 적재 → 실 서비스 자동 반영" 완성.

- **Phase G.1** (commit `d6b4589`) — `core:Incompatibility` ontology TBox 보강 + `guide_domain_incompatibilities` PG (2,016 rows: 8 vetted + 2,008 candidate, T2.D 8/8 PASS 자동 반영) + `shadow_reasoner.py` PG primary + JSON fallback. 10/10 sample equality. PG p50 0.4μs (cache warm).
- **Phase G.2** (commit `2f7ef92`) — `guide:GuideUsageProfile` OWL class **전체 신규 정의** (14 properties, ontology 가장 큰 갭 해결: SHACL shape는 있었으나 OWL class 부재) + 기존 PG `guide_usage_profiles` (1,038 rows) ontology backed + `guide_domain_profile.py` PG primary. Gate 3 PASS, `false_negative_rate -0.0189` 개선.
- **Phase G.3** (commit `8ddc2c7`) — `penalty:appliesTo/penaltyType/maxFine/maxPrisonYears` ontology 보강 + 신규 PG `penalty_rule_index` (**4,076 SR→PenaltyRule mappings**, kosha-instances.ttl → PG 자동 추출) + `hazard_rule_engine._load_penalty_index` PG primary. **penalty_accuracy +27.16%p ⭐, overall_accuracy +18.81%p ⭐** (TTL parse 우회 + 더 완전한 mapping).
- **Phase G.4** (commit `434f35f`) — 신규 PG view `she_patterns_reasoner_derived` (77 F.2 v3.1 link SHE 노출, read-only architectural layer) + Openllet `inferred=0` 근본 원인 분석 (law:modifies AsymmetricProperty + inverseOf 충돌 = FunInv 경고).
- **Tier 4 AsymmetricProperty 패치** (commit `5edae0b`) — `kosha-ontology-v2.owl` + `.formatted.ttl`에서 `law:modifies`의 `owl:AsymmetricProperty` 제거 + Fuseki rebuild + container recreate. **FunInv 경고 사라짐 + SPARQL 추론 작동 검증** (`hazard:FALL_FROM_HEIGHT rdfs:subClassOf+ ?super` → `owl:Thing` + `hazard:FALL`).
- **Tier 4 #4 Pellet reporting** (commit `1bacd44`) — `KoshaFusekiServer.java`에 `getDeductionsModel()` 명시 호출 + lazy materialization 안내 부연.
- **Tier 4 #2 AdministrativeFine** (commit `70d2862` 일부) — Decision Skip: `withAdministrativeFine: 0`은 design intent (RULE 조문은 OSHA 제38/39 위임으로 criminal-only). OSHA 제175조 admin은 별도 Pipe-A 확장 sprint. 문서: `docs/dev-notes/t4-administrative-fine-scope-decision.md`.
- **Tier 4 #1 77 SHE matcher 통합** (commit `70d2862` 일부) — 5 SHE batch 시도 → she_accuracy -7.07%p VETOED (~1.4%p/SHE), rollback 정상 작동 + utf-8 fix. 근본 원인: matcher의 broadness 처리 (promote만으로 해결 불가). 별도 sprint 이관. 문서: `docs/dev-notes/t4-77-she-matcher-integration-decision.md`.
- **Tier 4 #3 SWRL Pellet 실행기 통합** (commit `448a8d0`) ⭐ — 신규 `kosha-rules-r1-r3-swrl.ttl` (R-1 exemptedBy + R-3 HighSeverityPenalty, OWL/RDF SWRL serialization) + KoshaFusekiServer.java sources + docker rebuild. **SPARQL 검증**: R-1 `?s core:exemptedBy ?o` → **107 inferred**, R-3 `?s a penalty:HighSeverityPenalty` → **3,579 inferred** (severityScore ≥ 5와 100% 일치, swrlb:greaterThanOrEqual built-in 정상 평가).

**4-Layer 흐름 완전 입증** (Phase G + T4 후):
```
Vision LLM (T3.A enum) → normalizer → PG (G.1-3 materialized) → 답변
                                       ↑
       Fuseki + Pellet ← TTL ← Ontology TBox (G.1-3 patches) ← Mining (F.3.0/3.2)
                                                              + SWRL rules R-1/R-3 (T4 #3)
                                                              + SHACL shapes (T2.B)
```

main HEAD: `3502eff` (T4 #1 후속 + moellab 비교 후). origin/main 동기화 완료.

### T4 #1 후속 sprint + moellab 위험요소 비교 (2026-05-19)

**T4 #1 후속 sprint** (commits `a26c888` → main `1bfd6b8`) — 77 pending_review SHE matcher 통합의 별도 sprint 전 단계 1차 정리:
- 77 SHE manual review (사용자 1차 분류, single-file HTML UI 도구):
  - **approve 57 / modify 19 / defer 1 / reject 0** (사용자가 패턴 폐기할 만큼 비현실적인 것은 없다 판정)
  - modify 19 → 5개 테마 자동 분류 (PPE 과도 8 + 사진불가 3 + 좁은조건 4 + 비현실 3 + 도메인불일치 1)
- Step 2 approve 57 batch promote 재시도: **Batch 1 (5 SHE) → she_accuracy -10.17%p VETOED, rollback 자동**. 5회 audit history 모두 동일 패턴 (-7~-10%p) → **matcher 자체 로직 문제 입증**
- Step 3 patch proposal 자동 생성 (19/19 PG-only patch, ontology 영향 없음)
- 다음 sprint plan: [`she-matcher-broadness-refactor.md`](../workplans/she-matcher-broadness-refactor.md) — 7-day plan (broadness-aware ranking + PPE state weakening + `approved_derived` 신규 + SHACL shape + PG→TTL export)
- Runbook: [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md)

**moellab.info/ohs 위험요소 비교 분석** (commit `833dcd7` → main `3502eff`) — 우리 프로젝트의 초안과 dev server 비교:
- 비교 범위: GPT 직접 출력 `hazards[]` 만 (외부 시스템 부속 legal_reference / related_guides / checklist / resources 제외)
- 8개 사진 / **37 hazards 식별 모두 합리적** (false positive 없음, 자연어 카테고리 직관적: "끼임/협착", "전도/미끄럼", "추락" 등)
- `preventive_measures` 평균 3-4개 / hazard, 사진 context 반영
- **architecture pivot 후보 식별** ⭐:
  - Vision LLM HAZARD_DIRECT_SCHEMA → hazards[] 그대로 표시 (moellab 스타일)
  - hazard.name → catalog 529 codes 매핑 (T1.C alias 활용)
  - 우리 ontology reasoning으로 Guide 추천 (moellab title_match 한계 회피)
  - Guide procedure + GPT preventive 병기 (사용자 화면)
  - SHE matcher 회귀 부담 본질적 감소 (Step 2 -10.17%p 우회)
- 다음 sprint plan: `docs/workplans/hazard-direct-architecture-pivot.md` (TBD, 별도 plan)
- Runbook: [moellab-vs-devserver-comparison.md](../dev-notes/moellab-vs-devserver-comparison.md)

### Tier 1 재포함 + Tier 2 F.3 closing + Tier 3.A (2026-05-18 저녁)

- **Tier 1 재포함** (commit `93c49fe`): 직전 `b66fa36` commit이 T1.B npz 바이너리 + 마이그레이션 스크립트만 staged하고 T1.A/T1.C 코드 working tree만 잔존했던 누락 발견 + 재포함:
  - T1.A `promote_she_review.py` — `rollback_batch` `result.rowcount` + 사후 verification + `stuck_ids` 검출 (5 stuck SHE bug 재발 방지)
  - T1.B `auto_register_aliases.py` + `recover_catalog_mismatch.py` — numpy `load/save_embedding_cache` (~87% 크기 축소 적용)
  - T1.C `hazard_normalizer.py` step 4.5 `_log_alias_usage()` + `promote_aliases.load_meta_latest` 'used' action 집계 (`promote_aliases --auto` production-ready)
- **T2.A F.3.1 pyshacl reasoner shadow channel** (commit `93c49fe`): 신규 `pyshacl_shadow_validator.py` (offline batch CLI) + `shadow_reasoner.py` (serving runtime, lazy module cache, ~50μs/photo) + `analysis_pipeline.py` `_append_analysis_log`에 `reasoner_rejects` kwarg 추가. **2580 analysis_log rows → 859 reasoner_rejects** (62.8% processable rows). Gate 3 PASS.
- **T2.B F.3.4 KB compile + Fuseki reload** (commit `78886b3` + `ac98d4c`): 신규 `compile_kb_to_ttl.py` → `kb-candidates.ttl` (2200 → 2192 shapes after T2.D, sh:Info severity). `KoshaFusekiServer.java` sources array에 kb-candidates.ttl 추가. docker image rebuild (`docker-fuseki:latest` sha256 `08837972`). container `docker compose up -d --force-recreate fuseki` 완료. **SPARQL 검증**: `SELECT COUNT(?s) WHERE { ?s a sh:NodeShape }` → **2216 NodeShapes** (kb-candidates 2192 + serving 24). Fuseki Java v2 read-only blocker 해결 (rebuild + recreate 패턴).
- **T2.C F.3.5 drift detection + Makefile f3-* 통합** (commit `78886b3`): 신규 `f3_drift_check.py` (6 metric 추적, exit code 0/1/2). `Makefile` f3-help/shadow-validator/promote-candidates/compile-kb/drift-check/weekly-cycle targets. cron 권장: `0 2 * * 0 cd /path && make f3-weekly-cycle`.
- **T2.D 8 F.3.2 candidates 1-by-1 vetted promotion** (commit `ac98d4c` → main `325ad37`): 신규 `promote_f32_per_candidate.py` (1-by-1 + full replay + Gate 3 wrap + 자동 rollback). **8/8 candidate PASS** (예상 5-6 PASS 대비 100% 통과). 모든 F.3.2 axiom vetted 승격 (vetted_count 0 → 8). 1차 실행 시 cp949 unicode bug 발견 → 모든 ✓✗→— 를 ASCII로 교체 후 PYTHONIOENCODING=utf-8 + python -u 로 재실행 성공.
- **Tier 3.A Closed Vocab Schema Enum** (commit `606b91f` → main `b237e78`): `openai_client.py` `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text`에 catalog 529 codes enum. `_load_catalog_codes()` lazy module-level load (12.6KB schema JSON, OpenAI strict mode 한도 내). Gate 3 PASS (delta noise 수준). **analysis_log normalizer_unknown_codes 76 → 4 (−94.7%)**. 잔존 4건 (THF, CO, MOBILE_EQUIPMENT, WAREHOUSE) — OpenAI strict mode enum의 edge-case 누락 (강제력 ~99.6%).

**효과 정리** (Layer 4 Module 4.4 closed loop 완성):
```
mining (F.3.0/3.2)   →   verify (F.3.3 Gate 3)   →   compile (T2.B compile_kb_to_ttl.py)
                                                     ↓
monitor (T2.C f3_drift_check.py)   ←   deploy (Fuseki container restart + SPARQL endpoint)
```

main HEAD: `b237e78` (Tier 3.A merge), 직전 `325ad37` (Tier 2 merge).

## 🎯 핵심 성과 (2026-05-16 ~ 17)

### Phase 0/B/A/C (LLM 자율 도메인 보강) — 완료
- **baseline_v2**: she_accuracy 55.81% → **60.72%** (+4.9%p), overall 13.31% → **15.25%** (+1.94%p)
- **active_v2**: positive avg_procedures 3.07 → **2.26** (−26.4%) — LLM rerank 효과
- **8 real-test-photo**: 4/5 over-promote 차단 확인 (지게차/영세제조/포크레인/음식점)
- **Phase C 자율 학습**: 2,528 analysis_log + 31개 신규 incompatibility 자율 채택

### Phase E-prep + E.2 (Openllet 통합) — 완료
- **Step 1**: 50 CQ + 55 class layer (B 26/A 20/Bridge 9) + 7 reuse scorecard
- **Step 2**: kosha-ontology-v2.owl (BFO + LKIF imports + 64 subClassOf)
- **Step 3**: kosha-disjoint-axioms.ttl (84 industries, 2,192 disjoint) + 22 SWRL + 26 SHACL
- **Step 4**: OntoClean 13 violations → **1** (92% 자동 수정)
- **E.2**: Fuseki Java가 v2 ontology + disjoint + SHACL + 172 subClassOf 로드 (commit `3520cab`)
- **Verification**: SHACL Conforms: True ✅, Openllet inference 정상

### Phase 3 (catalog v4 + SHE patterns + reasoning catch) — 완료
- **Phase 3A audit**: 1,914 synthetic codes hybrid ensemble 검증
- **Phase 3B catalog v4**: +170 신규 codes + 169 sub + 193 aliases
- **Phase 3C direct LLM SHE patterns**: 498 신규 → validation 후 누적 **1,616** PG she_patterns
- **Phase 3D**: synthetic v1~v10 EN enum transform + baseline_v3
- **Phase 3 validation**: ontology reasoning이 LLM 환각/과대추정 **1,902건 catch** (보고서 `docs/status/reasoning-catch-effectiveness-2026-05-17.md`)
- **8 real-test-photo 라이브**: 평균 사진당 1건 부적절 추천을 reasoning이 사용자 앞에서 reject

### Phase F.3 자율 axiom learning loop — 첫 정식 단계 완료 ⭐
- **F.3.0 (commit `8ff40d7`)**: 2,525 excluded entries 5 카테고리 분류 — `axiom_missing 36.44%` (920건, **210 unique pair**) → PROCEED_F3
- **F.3.5-prep (commit `ebe1011`)**: `analysis_log.jsonl`에 Runtime 4번 환류 채널 3 신규 필드 (`normalizer_unknown_codes`, `she_match_count`, `raw_vision_features`)
- **C cleanup (commit `2ea800d`)**: `guide_domain_incompatibilities.json` 2,232 entries 100% KO→EN translated (mining 정확도 normalize)
- **F.3.2 first batch (commit `9219c7c`)**: 49 LLM verify → **8 accepted candidate axiom** (incompatible_count 2,232 → 2,240)
- **Merge `11e46c6`** + GitHub push 완료
- **A hot-fix (commit `a841a0b` → main `d0b2262`)**: `raw_vision_features` 타입을 `dict` → `list`로 수정. ebe1011에서 dict() 변환 시 `risk_feature_candidates`(array)를 받아 `ValueError: dictionary update sequence element #0 has length 4; 2 is required` 발생. 2,360 synthetic replay에서 1,700 errored 원인. 3-case quick test로 0 errored 검증 후 push.
- **F.3.3 Gate 3 regression PASS (commit `eb7843f` → main `5b10980`)**: 2,360 synthetic replay 전체 valid, 0 errored. she_accuracy delta `-0.0013` (노이즈 범위), 모든 metric 회귀 없음. 8 candidate axiom **production-safe 검증 완료** — 수동 vetted 승격 가능 (50회 대기 불필요). 보고서 `docs/status/f33-gate3-regression-2026-05-17.md`.
- **14-docs sweep (commit `af26e13` → main `f5bde60`, HEAD)**: F.3 first batch + hot-fix + F.3.3을 14개 docs 전 영역(README/architecture/status/workplans/governance/backlog) 반영. 메타 일관성(current-session ↔ evaluation-baseline ↔ workplans) cross-check 완료.

### 학계 reference 통합 — 완료
- 9 paper 분석 (`ontology-team/reference-article/`)
- Layer 4 = 7 module 정밀 구성
- 우리 차별점: deontic 도메인 + 한국어 + asymmetric trust + Task C SOTA + Task D 학계 미답

## 📦 신규 산출물 (2026-05-19 Phase G + T4 — origin/main push 완료)

**Phase G 신규 산출**:
- Ontology TBox 4 patches:
  - `ontology-team/06-reasoning/ontology/kosha-ontology-v3-incompat-patch.ttl` (G.1: `core:Incompatibility` class + 5 metadata properties)
  - `ontology-team/06-reasoning/ontology/kosha-ontology-v3-guide-profile-patch.ttl` (G.2: `guide:GuideUsageProfile` class + 14 properties + cardinality restrictions)
  - `ontology-team/06-reasoning/ontology/kosha-ontology-v3-penalty-relations-patch.ttl` (G.3: 4 relation/datatype properties)
  - `ontology-team/06-reasoning/ontology/kosha-rules-r1-r3-swrl.ttl` (T4 #3: R-1 exemptedBy + R-3 HighSeverityPenalty SWRL OWL serialization)
- Ontology TBox 1 수정: `kosha-ontology-v2.owl` + `.formatted.ttl` (`law:modifies`의 `owl:AsymmetricProperty` 제거, T4 fix)
- PG schema 3 신규:
  - `serving-team/07-materialization/pg-sync-scripts/schema_guide_domain_incompatibilities.sql`
  - `serving-team/07-materialization/pg-sync-scripts/schema_penalty_rule_index.sql`
  - `serving-team/07-materialization/pg-sync-scripts/schema_she_patterns_reasoner_derived.sql`
- PG import scripts 2 신규:
  - `serving-team/07-materialization/pg-sync-scripts/import_domain_incompatibilities_to_pg.py`
  - `serving-team/07-materialization/pg-sync-scripts/import_penalty_to_pg.py`
- Validation scripts 1 신규: `serving-team/07-materialization/validation-scripts/sample_query_equality.py`
- Bench script 1 신규: `serving-team/08-app/backend/scripts/bench_shadow_reasoner.py`
- PG ORM 3 신규 (`app/db/models.py`): `PgGuideDomainIncompatibility`, `PgPenaltyRoute`, `PgPenaltyRuleIndex`
- Backend code 4 수정 (PG primary):
  - `app/services/shadow_reasoner.py` (G.1, JSON fallback 유지)
  - `app/services/guide_domain_profile.py` (G.2)
  - `app/services/hazard_rule_engine.py` (G.3, `_load_penalty_index_from_pg()`)
  - `app/services/openai_client.py` (T3.A enum, 이전 sprint)
- Fuseki Java 수정: `KoshaFusekiServer.java` (kb-candidates + SWRL TTL sources 추가 + Pellet reporting 명시화)
- Makefile: `phase-g-help/phase-g1-schema/import/verify/phase-g-verify` targets
- Manual review 자산: `data-team/05-enrichment/runtime-artifacts/pending_review_she_for_manual_review.json` (77 SHE 8-axis + visual_triggers)

**신규 dev-notes (이번 세션, 7 runbooks/decisions)**:
- [phase-g.1-domain-incompatibilities-pg.md](../dev-notes/phase-g.1-domain-incompatibilities-pg.md)
- [phase-g.2-guide-usage-profiles-pg.md](../dev-notes/phase-g.2-guide-usage-profiles-pg.md)
- [phase-g.3-penalty-rule-index-pg.md](../dev-notes/phase-g.3-penalty-rule-index-pg.md)
- [phase-g.4-she-patterns-reasoner-derived.md](../dev-notes/phase-g.4-she-patterns-reasoner-derived.md)
- [t4-administrative-fine-scope-decision.md](../dev-notes/t4-administrative-fine-scope-decision.md)
- [t4-77-she-matcher-integration-decision.md](../dev-notes/t4-77-she-matcher-integration-decision.md)
- [t4-swrl-pellet-integration.md](../dev-notes/t4-swrl-pellet-integration.md)

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

---

## 📦 신규 산출물 (2026-05-19 T4 #1 후속 + moellab 비교 — origin/main push 완료)

**T4 #1 후속 산출 (commit `a26c888` → main `1bfd6b8`)**:
- 신규 dev-note: [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md)
- 신규 sprint plan: [she-matcher-broadness-refactor.md](../workplans/she-matcher-broadness-refactor.md) (7-day, hazard-direct pivot 후 보조 track으로 통합 또는 후행)
- 신규 script 2개:
  - `data-team/05-enrichment/llm-scripts/patch_she_visual_triggers.py` (Step 3 patch proposal 생성)
  - `data-team/05-enrichment/runtime-artifacts/she_review_ui.html` (94KB single-file 검토 UI)
- 신규 정본 자산:
  - `data-team/05-enrichment/runtime-artifacts/pending_review_she_REVIEWED.json` (77/77 사용자 검토 결과)
  - `data-team/05-enrichment/runtime-artifacts/pending_review_she_PATCH_PROPOSAL.json` (19/19 자동 patch)
- 수정: `data-team/05-enrichment/llm-scripts/promote_she_review.py` (`--only-from-review-json` 옵션)

**moellab 비교 산출 (commit `833dcd7` → main `3502eff`)**:
- 신규 dev-note: [moellab-vs-devserver-comparison.md](../dev-notes/moellab-vs-devserver-comparison.md)
- 보조 (git 미추적, 다음 세션 재현 자산): `.compare_moellab/*.json` (8개 사진 raw API 응답)
- 수정 1개: `.gitignore` (외부 raw 캡처 + manual review 보조 파일 + auto-gen logs 추가)

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

---

## 📦 신규 산출물 (2026-05-18 저녁 Tier 1-3.A — main에 push 완료)

**신규 파일**:
- `data-team/05-enrichment/llm-scripts/pyshacl_shadow_validator.py` (T2.A offline batch)
- `data-team/05-enrichment/llm-scripts/compile_kb_to_ttl.py` (T2.B)
- `data-team/05-enrichment/llm-scripts/f3_drift_check.py` (T2.C)
- `data-team/05-enrichment/llm-scripts/promote_f32_per_candidate.py` (T2.D)
- `data-team/05-enrichment/llm-scripts/_migrate_embedding_cache_to_npz.py` (T1.B 1회성)
- `serving-team/08-app/backend/app/services/shadow_reasoner.py` (T2.A serving runtime)
- `ontology-team/06-reasoning/ontology/kb-candidates.ttl` (T2.B output, 2192 SHACL shapes)
- `data-team/05-enrichment/runtime-artifacts/f32_per_candidate_promotion_results.json` (T2.D summary)
- `data-team/05-enrichment/runtime-artifacts/f3_drift_log.jsonl` (T2.C 시계열)
- `data-team/05-enrichment/runtime-artifacts/kb_candidates_compile_audit.json` (T2.B audit)

**수정 파일**:
- `serving-team/08-app/backend/app/services/analysis_pipeline.py` (T2.A: happy + skipped path 모두 `shadow_validate` + `reasoner_rejects` kwarg)
- `serving-team/08-app/backend/app/services/hazard_normalizer.py` (T1.C: step 4.5 `_log_alias_usage`)
- `serving-team/08-app/backend/app/integrations/openai_client.py` (T3.A: 529 codes enum + `_load_catalog_codes()`)
- `ontology-team/06-reasoning/ontology/docker/fuseki/src/main/java/kr/or/kosha/KoshaFusekiServer.java` (T2.B: sources array + kb-candidates.ttl)
- `data-team/05-enrichment/llm-scripts/promote_she_review.py` (T1.A: rollback verification + stuck_ids)
- `data-team/05-enrichment/llm-scripts/auto_register_aliases.py` (T1.B: npz load/save)
- `data-team/05-enrichment/llm-scripts/recover_catalog_mismatch.py` (T1.B: npz load/save)
- `data-team/05-enrichment/llm-scripts/promote_aliases.py` (T1.C: 'used' action 집계)
- `Makefile` (T2.A-D: f3-help/shadow-validator/promote-candidates/compile-kb/drift-check/weekly-cycle)

**신규 docs (이번 세션 저녁)**:
- [F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md) — T2.A/B/C/D 통합 runbook
- [T3.A-closed-vocab-schema-enum.md](../dev-notes/T3.A-closed-vocab-schema-enum.md) — T3.A runbook
- [t2d-per-candidate-promotion-2026-05-18.md](t2d-per-candidate-promotion-2026-05-18.md) — T2.D 8/8 PASS 보고
- [t3a-closed-vocab-schema-enum-2026-05-18.md](t3a-closed-vocab-schema-enum-2026-05-18.md) — T3.A 76→4 분석

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

---

## 📦 신규 산출물 (오늘 후반 — main에 push 완료, 2026-05-17~18 오전)

오늘 후반 (F.3 sprint + F.3.3 + sweep) commits + merge:
- `classify_reject_reasons.py` + 산출 jsonl/json + sample_100 (F.3.0)
- `analysis_pipeline.py` 수정 (Runtime 4번 hook 3 필드, A) + hot-fix (`raw_vision_features` list)
- `translate_incompat_industries.py` + KB 변환 (C)
- `mine_missing_axioms.py` + 8 candidate (B)
- `data-team/05-enrichment/runtime-artifacts/replay_post_f32.json` (F.3.3 replay)
- `docs/status/f30-reject-reason-classification-2026-05-17.md` (F.3.0 보고서)
- `docs/status/f33-gate3-regression-2026-05-17.md` (F.3.3 PASS 보고서)
- `docs/` 전반 14 docs sweep (`af26e13`): README/architecture/status/workplans/governance/backlog

## ⚠️ 다음 세션 시작 시 주의사항

1. **현재 작업 worktree**: `.claude/worktrees/trusting-chandrasekhar-7b2041/` (claude/trusting-chandrasekhar-7b2041 branch). **origin/main + PRIMARY 동기화 완료** (`f4f078a`, 2026-05-29 canonicalization sprint). PRIMARY(`C:/project/arch-bot`) = origin/main 동일 SHA. 정리 시 worktree 제거 가능 (모든 작업 커밋·푸시·배포됨).
2. **PG materialization runtime path**: shadow_reasoner (G.1) + guide_domain_profile (G.2) + hazard_rule_engine._load_penalty_index (G.3) 모두 **PG primary + JSON/TTL fallback** 패턴. PG cache 갱신 = backend restart 필요. PG row 변경 시 `_load_*_from_pg()` 캐시 reset 또는 service 재시작.
3. **Fuseki container 상태**: `kosha-fuseki` 신규 image (`docker-fuseki:latest`, 981,485 triples 로드, kb-candidates.ttl + kosha-rules-r1-r3-swrl.ttl 포함). SWRL R-1: 107 + R-3: 3,579 inferred triples 검증됨. 다음 docker compose 시 동일 image 자동 사용.
4. **Pellet inferred count log "0"은 정상**: `infModel.size()` lazy materialization quirk. 실제 추론은 SPARQL query 시 on-demand 실행 (검증 완료). 로그 메시지에 안내 포함.
2. **API 키**: `serving-team/08-app/backend/.env`에 OPENAI_API_KEY 설정됨. 정상 작동 확인 (T2.D 8회 replay 모두 성공)
3. **8 F.3.2 candidate axiom 모두 vetted 승격 완료** (T2.D 8/8 PASS). vetted_count 0 → 8. 잔여 candidate-only 진행 시 동일 `promote_f32_per_candidate.py --apply` 패턴.
4. **Fuseki container 새 image 적용 중**: `docker-fuseki:latest` sha256 `08837972` (kb-candidates.ttl 17,618 triples 로드, 총 981,409 triples). `docker compose up -d`에 동일 image 자동 사용. 다음 TTL 추가 시 동일 (Java sources 수정 + rebuild + recreate).
5. **T2.D 1차 cp949 unicode bug 처리됨**: `promote_f32_per_candidate.py` 모든 ✓✗→— → ASCII 교체. 재실행 시 `PYTHONIOENCODING=utf-8 python -u` 권장.
6. **T3.A 잔존 4 free-creates**: THF, CO, MOBILE_EQUIPMENT, WAREHOUSE — OpenAI strict mode enum의 edge-case (~99.6% 강제력, 0.4% 누락). 별도 분석 후보 (또는 normalizer step에서 hard reject 가능).
7. **편의점 KO unmapped** (이전 sprint에서 발견): `industry_ko_to_en_map.json`에 `편의점 → CONVENIENCE_STORE` 매핑 추가됨 (Quick Win Task 3). T2.D 후보 [6/8] 편의점×METAL_MACHINING가 vetted 통과 확인.
8. **A hook 항상 실행됨** (Quick Win Task 2 + T2.A): `_apply_llm_rerank`의 early-return 3 경로 모두 `_log_skipped_analysis` 호출 → analysis_log에 `mode=off_skipped_*` 기록. T2.A `reasoner_rejects` field도 happy + skipped path 모두 추가됨.
9. **stash@{0}**: `WIP on main: ca55ac6` (이전 세션 8 real-test-photo PNG/JPG untracked). 무관함, 보존

## 🛣️ 다음 작업 우선순위

### ✅ 완료: Phase G — PG 재물질화 (G.1-4, 2026-05-19)
- G.1: `guide_domain_incompatibilities` PG (2,016 rows, ontology `core:Incompatibility`)
- G.2: `guide_usage_profiles` PG + `guide:GuideUsageProfile` 신규 OWL class (ontology 가장 큰 갭 해결)
- G.3: `penalty_rule_index` PG (4,076 rules) — **penalty_accuracy +27.16%p ⭐**
- G.4: `she_patterns_reasoner_derived` view + Openllet root cause 분석
- Runbooks: `docs/dev-notes/phase-g.{1,2,3,4}-*.md`

### ✅ 완료: Tier 4 후속 (2026-05-19)
- AsymmetricProperty 패치 (Openllet SPARQL 추론 검증)
- T4 #4 Pellet reporting 명시화
- T4 #2 AdministrativeFine: Skip (design intent)
- T4 #1 77 SHE: 별도 sprint 이관
- T4 #3 SWRL Pellet 실행기 통합 (R-1: 107 + R-3: 3,579 inferred) ⭐
- Runbooks: `docs/dev-notes/t4-{administrative-fine,77-she-matcher,swrl-pellet}-*.md`

### ✅ 완료: Tier 1 재포함 (T1.A/B/C, 2026-05-18 저녁)
- T1.A promote_she_review rollback verification + stuck_ids 검출
- T1.B npz cache load/save (95MB → 12MB, 87% 축소)
- T1.C hazard_normalizer step 4.5 alias usage tracking + promote_aliases 'used' 집계

### ✅ 완료: Tier 2 F.3 closing (T2.A/B/C/D, 2026-05-18 저녁, Module 4.4 closed loop)
- T2.A pyshacl reasoner shadow channel (offline batch + serving runtime)
- T2.B KB compile to TTL + Fuseki Java edit + docker rebuild + container restart + **SPARQL 2216 NodeShapes 검증**
- T2.C drift detection + Makefile f3-* 통합
- T2.D 8/8 F.3.2 candidates vetted (예상 5-6 대비 100% 통과)
- Runbook: [../dev-notes/F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md)
- Makefile: `make f3-help` 참고

### ✅ 완료: Tier 3.A Closed Vocab Schema Enum (2026-05-18 저녁)
- `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text`에 catalog 529 codes enum
- **free-creates 76 → 4 (-94.7%)** (Hybrid Day 3 partial → 본격 schema-level enum)
- Gate 3 PASS (delta noise 수준)
- Runbook: [../dev-notes/T3.A-closed-vocab-schema-enum.md](../dev-notes/T3.A-closed-vocab-schema-enum.md)

### ✅ 완료: Phase F.1 — Vocabulary auto-registration (Day 1-7, 2026-05-18 오전)
- 5 vetted aliases (FALL_FROM_HEIGHT, FINGER_AMPUTATION 등) + 1 candidate
- 4-Gate closed loop: embedding + LLM verify + regression + asymmetric trust
- Runbook: [docs/dev-notes/F.1-auto-register-aliases.md](../dev-notes/F.1-auto-register-aliases.md)
- Makefile: `make f1-help` 참고

### ✅ 완료: Phase F.2 — Taxonomy Discovery (Day 1-7, 2026-05-18 오전)
- catalog v3.1 (404 codes, 3 axes) → **v3.3 (481 codes, 5 axes)**
- 신규 axis: ppe_state (50 codes), environmental (18 codes)
- 790 SHE OTHER → specific (Sonnet 4.6, Gate 3 PASS)
- 79 v3.1-link SHE (status=pending_review, 수동 승격 대기)
- Runbook: [../dev-notes/F.2-taxonomy-discovery.md](../dev-notes/F.2-taxonomy-discovery.md)
- Makefile: `make f2-help` 참고

### 다음 작업 우선순위 (T4 #1 후속 + moellab 비교 완료 후):

**1순위: hazard-direct architecture pivot** ⭐ (sprint plan 작성 완료, Phase 1 즉시 시작 가능):
- 📄 **Plan: [docs/workplans/hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md)** (3주, 5 Phase × 평균 5일)
- 핵심 가설: Vision LLM이 위험요소(hazards) 자연어로 직접 출력 → 우리 ontology로 Guide 추천 → SHE matcher 의존도 본질 감소
- moellab(우리 초안)의 GPT 직접 hazard 식별이 8/8 사진 / 37/37 합리적 (Step 2 SHE matcher -10.17%p VETOED와 대조)
- Phase 1: HAZARD_DIRECT_SCHEMA + GPT prompt 갱신 (~3일)
- Phase 2: hazard.name → catalog 529 codes alias 매핑 (T1.C 확장 + Sonnet 4.6 seed, ~1주, ~$0.20)
- Phase 3: hazards-based Guide 추천 layer + A/B 검증 (parallel/primary/off mode, ~1주)
- Phase 4: 응답 schema 확장 + Frontend `RiskOverviewPanel`/`HazardGuideRelationsPanel` (~3일)
- Phase 5: Gate 3 통합 + 정본 문서 + Architectural debt 3가지 해소 (~3일)
- 결정 완료: seed = Sonnet 4.6 자동 + 사용자 vetted / SHE matcher refactor = 후행 별도 sprint

**2순위: SHE matcher broadness-aware refactor** (T4 #1 후속, 보조 track):
- [she-matcher-broadness-refactor.md](../workplans/she-matcher-broadness-refactor.md) (7-day plan)
- hazard-direct pivot의 Phase 3 보조 track으로 통합 또는 후행 (SHE matcher 의존도는 본질적으로 감소하지만 fallback으로 유지)

**3순위: OSHA admin penalty Pipe-A 확장** (T4 #2 후속, 4-6h):
- 제175조 administrative fines (6단계, 5천만원~300만원) 추출. `step1_extract_penalties.py` 확장. 결과 → penalty_rule_index에 sanction_type='AdministrativeFine' rows 추가.

**4순위: SWRL 확장 + 학계 작업**:
- ✅ **완료 (axiom-100% Sprint)**: R-4~R-30은 SWRL serialization 대신 **SHACL CONSTRUCT로 변환** (Pellet NEXPTIME 회피). `kosha-rules-r14-r30-shacl-construct.ttl` (12 rules) + `kosha-rules-k-general-shacl.ttl` (R-2/R-4 일반화, 53,378 pair). R-1/R-3만 SWRL native 유지.
- **8-photo real-test eval** (`make f1-eval`, ~$0.40 + 8분): Phase G + T4 효과 실제 사진 검증.

**3순위 (Tier 4 중장기, 1-3개월) — 별도 plan**:
- F.5 GraphRAG (Module 4.6, 2주)
- F.4 CQ Reverse + Photo persist (Module 4.5, 3-4주)
- Phase J OBO Foundry 등재 (1-3개월) — **사용자 명시: 나중에 별도 계획**
- Two-way CoT prompt 전환 (1일, +0.2 F1 기대)
- OOPS! Pitfall Scanner 통합 (2-3h)

**T3.A 잔존 4건** (THF/CO/MOBILE_EQUIPMENT/WAREHOUSE): 별도 sprint 또는 normalizer hard reject로 점진 보강.

**비채택** (도메인 부적합 — 2026-05-17 결정):
- **OntoGPT 통합** — F.1 alias mining에 자체 LLM verify(`mine_missing_axioms.py` 패턴)로 충분, 추가 가치 없음
- **OntoClean 메타-validation** — 170 atomic codes / 498 SHE patterns에 비용 비대칭. BFO+LKIF 62-class TBox 통합(Phase E-prep)에서만 유효했으며 이미 13→1 완료. F.1은 taxonomy 변경 없는 alias 등재 작업이므로 적용 영역 외

## 🔧 OHS 실행 (시연용)

PG + Fuseki 컨테이너 (이미 동작 중):
```bash
docker ps | grep -E 'kosha-pg|kosha-fuseki'
```

backend + frontend dev-up (WSL):
```bash
cd /mnt/c/project/arch-bot
# baseline 시연 (LLM rerank off, 비용 0)
make dev-up
# 또는 LLM rerank 활성 시연 (Phase B+A.4 효과 시각화)
LLM_RERANK_MODE=active make dev-up
make dev-check
```

브라우저: http://127.0.0.1:5173/ohs/

8 real-test-photo: `C:\project\arch-bot\real-test-photo\`

## 📊 검증 명령 (회귀 확인)

```bash
# rdflib parse + Local consistency check
cd /mnt/c/project/arch-bot
/mnt/c/project/arch-bot/serving-team/08-app/backend/.venv/bin/python \
  data-team/05-enrichment/llm-scripts/local_consistency_check.py --skip-instances --skip-sparql

# 2,360 synthetic replay (baseline 측정)
cd /mnt/c/project/arch-bot/serving-team/08-app/backend
DATABASE_URL='postgresql://kosha:1229@localhost:5432/kosha' \
.venv/bin/python -u scripts/replay_synthetic_observations.py \
  --output /tmp/replay_check.json

# regression gate (baseline vs current)
.venv/bin/python scripts/regression_gate.py /tmp/replay_check.json
```

## 🌟 핵심 통찰 (다음 세션 결정 기준)

1. **현재 SHE 부족분 = LLM 보강 JSON으로 메꿈** → 정형 OWL/SWRL/SHACL로 점진 대체
2. **Vision LLM만 영구 유지** (인식 영역). Semantic reasoning은 reasoner로 이전
3. **Layer 4 (Ontology Learning) 별도 layer 필수** — long-tail 도메인 자율 적응
4. **closed vocabulary 기각** (사용자 결정) — 학계 SOTA와 일치
5. **자율 등재 위험성** — 4-gate 검증 (embedding + multi-LLM + counter-example + asymmetric trust)
6. **우리 시스템의 학계 차별점** = LKIF-Core × BFO + 한국어 + asymmetric trust + Task C SOTA + Task D 미답
7. **7단계 PG 재물질화** = reasoner 추론 결과 → PG → 서빙 ms 응답

## 5단계/6단계 전환 시각화

```
[현재 5단계] LLM 의존 hybrid
   Vision LLM → Normalizer → SHE 매칭 → LLM enrichment lookup → Phase B LLM rerank → dynamic KB

[Phase E.2 후 6단계] declarative reasoning
   Vision LLM → BFO Photo instance → Openllet OWL DL → SWRL/SHACL → 정형 추론

[Phase F+ Layer 4] cross-cutting 자율 학습
   Layer 1-3 데이터 → 7 module → vocabulary/class/rule 자동 등재 → asymmetric trust

[Phase G 7단계] PG materialize
   reasoner 결과 → PG table → 서빙 PG SELECT only (ms, LLM 0회)
```
