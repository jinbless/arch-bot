# OWA→CWA 파이프라인 보완 실행계획

> 작성: 2026-06-06 · 다중에이전트 워크플로(7 워크스트림 정밀작성 → 시퀀싱 → 완전성 비평) 산출.
> 근거: 두 차례 감사(전체 파이프라인 12 + 벡터DB 매칭 10 = **22 리스크**, air-gap 발견 1건 정정 제외).
> 대상: `serving-team/08-app`(backend/frontend), `ontology-team/06-reasoning`, `data-team/05-enrichment`(eval).
> 원칙: 생성물 손수정 금지(생성기 수정) · 온톨로지=SoT/PG=스냅샷 · provenance/version=표시전용(scoring 무관) · 변경은 replay(2,360)+regression_gate(tol 0.02), 온톨로지는 owl:Nothing 실쿼리 게이트 통과 · **안전 도메인: FN(미탐지) 방향 회귀를 최우선 차단**.

---

## 1. 개요 (Executive Summary)

접근 원칙은 "5개 근본 원인을 한 번씩만 고친다(fix 5 roots once)"이며, 안전 도메인 특성상 FN(미탐지)을 절대 늘리지 않는 비대칭 보수성을 모든 단계의 채택 게이트로 강제한다. 5개 근본은 (1) OWA→CWA 경계의 silent green-collapse(WS-SAFETY, A1/A2), (2) soft-match를 fact로 굳히는 검증 부재(WS-GATE, B1/A6/A10/B5), (3) 조용한 고장의 무신호(WS-OBS, A3/A5/B3/B10), (4) 약한 근거의 무표시(WS-PROV, A7/A12/B7), (5) 원본↔DB/색인 드리프트(WS-DRIFT, A4/B2/B4/B9)이고, WS-EVAL과 WS-DEEP는 이 5개의 측정·근본모델 보강이다.\n\n실행은 3단계: Phase0=가시화(visibility). 사용자 대면에서 '미탐지=안전'으로 보이는 치명 결함(SAFETY-1/3/4)을 소스에서 차단하고, 측정 인프라의 진실(EVAL-4 baseline v3, EVAL-5/OBS-2 caveat 문서)과 truth-in-docstring(GATE-1), 그리고 런타임 무변경·표시전용 출처 스캐폴드(PROV-1/3, DRIFT-5/6)를 깐다. Phase0의 핵심은 회귀게이트가 진짜 v3 baseline을 밟게 만들어 이후 모든 변경을 측정 가능·안전하게 만드는 것이다.\n\nPhase1=차단·결속(blocking & binding). FN-방향 1급 veto 키(OBS-1)를 먼저 세운 뒤, recall을 올리는 방향(SAFETY-2/5, GATE-2/3, DEEP-1)과 게이트를 hard-wire(GATE-4/5/6/7/8), 드리프트 자동탐지(DRIFT-1~4), 관측 attribution(OBS-3~7), 근거 discount(PROV-2/4)를 배치한다. recall을 올릴 수 있는 모든 변경은 OBS-1(FN-direction metric)이 존재한 뒤에만 진입한다.\n\nPhase2=정밀·평가(precision & evaluation). gold-set 의존 항목(EVAL-2)과 그것에 의존하는 promote 게이트(GATE-9), drop-ratio active 승격 전제(OBS-8)를 마지막에 둔다. 이들은 데이터(gold/PR곡선)가 선행 단계에서 축적된 뒤에만 임계값을 확정할 수 있기 때문이다.

## 2. ⚠️ 사용자 결정 필요 (착수 전 확정)

### D1. assessed_safe(평가했고 안전) 상태를 finding_status 에 지금 신설할지, 후속으로 미룰지

- **왜 필요한가:** 녹색 low 허용 여부를 결정 — 지금 신설하면 silent green-collapse 차단과 동시에 정당한 안전 표시가 가능하나 FN 위험(잘못된 안전 표시) 도입; 미루면 FN-보수적이나 모든 미판정이 unknown 으로만 표기
- **옵션:** (a, 권장·FN보수) 지금은 not_determined/needs_clarification→unknown 만, assessed_safe 는 후속 / (b) 동시에 assessed_safe 신설해 녹색 low 허용
- **블로킹 항목:** WS-SAFETY-1, WS-SAFETY-3, WS-SAFETY-4, WS-SAFETY-5

### D2. ppe/env 유래 unsafe_state 의 confirmed-vs-candidate 라우팅, 및 match_she early-return(L815)을 ppe/env 포함으로 확장할지

- **왜 필요한가:** GPT-단정 ppe/env 가 unsafe_state→confirmed 직행 시 is_direct_penalty_match→photo_based penalty fire → 오탐 시 벌칙 오신호(법적 load-bearing FP). early-return 확장은 recall↑ 이나 FP risk
- **옵션:** (a, 권장) ppe/env-only 유래 unsafe_state 는 candidate(confirmation_required)로만 라우팅; early-return 미확장 / (b) 시각 score 충족 시 confirmed 허용 + early-return 을 ppe/env 포함으로 확장(recall↑)
- **블로킹 항목:** WS-SAFETY-2, WS-SAFETY-5, WS-GATE-9

### D3. high-concern(미분류 위험) 승격 판정 기준

- **왜 필요한가:** chemical/electrical/high-severity 미해석을 needs_clarification 으로 과대/과소 승격하면 각각 노이즈/미탐지 발생
- **옵션:** (a, 권장·단순보수) 축 기반: hazardous_agent 축 미해석 + hazard risk_level=='high' 만 승격 / (b) 키워드 사전(THF/CO/전기 패밀리) 추가(정밀하나 미등재 위험·유지보수 부담)
- **블로킹 항목:** WS-SAFETY-5

### D4. semantic attach calibrated cosine floor 시작값(text-embedding-3-small)

- **왜 필요한가:** floor 가 높으면 FP 억제·관련 guide 드롭(FN) 위험, 낮으면 FN 보수적이나 noise 통과. 안전도메인은 FN 보수 우선
- **옵션:** (a) FP 억제 우선 0.25 / (b, 권장·안전도메인) FN 보수 우선 0.20 후 judge set 으로 점진 상향
- **블로킹 항목:** WS-GATE-2

### D5. shadow_reasoner hard-reject 운영 기본값(opt-in vs default-on)

- **왜 필요한가:** vetted&conf>=0.9 reject 를 default-on 하면 도메인-모순 부착 억제(FP↓)하나 관련 guide 과다 드롭 위험(FN); confirmed-vs-candidate 라우팅 철학과 정합 필요
- **옵션:** (a, 보수) 영구 opt-in(off) 로 ship / (b) vetted&conf>=0.9 만 eval 통과 시 default-on(FP 억제)
- **블로킹 항목:** WS-GATE-3, WS-GATE-9

### D6. consistency-gate 의 G.3(penalty_rule_index)/G.4(she_patterns) 적재 타깃 적용 순서

- **왜 필요한가:** 블라스트 반경 큰 사용자대면 타깃 우선 적용 vs 전 타깃 일괄 — 사용자대면 우선이 리스크 노출 최소화
- **옵션:** (권장) G.3/G.4(사용자대면) 우선 / (b) 전 적재 타깃 일괄 적용
- **블로킹 항목:** WS-GATE-6

### D7. OHS_ENABLE_ATTACH_CACHE read-path 를 enable 할지/언제(현재 의도적 dormant·데모 stale 캐시), 및 PROMOTE_K(현 2) 상향

- **왜 필요한가:** enable 안 하면 LLM 점진 폐지 미달성; enable 하면 stale/저품질 promoted link 서빙 위험 → full-corpus 재누적+게이트+사람검토 전제 필요
- **옵션:** (a) 영구 off 유지(보수, LLM 폐지 미달성) / (b) full-corpus 재누적 + 본 게이트 통과 + 19 promoted link 사람 검토 후 enable + PROMOTE_K 안전도메인용 상향
- **블로킹 항목:** WS-GATE-9

### D8. positive-only SHE recall_tolerance 값

- **왜 필요한가:** 0 이면 어떤 미세 recall 회귀도 hard-veto(안전 최대화이나 false-alarm 위험), 0.005 면 ε 여유. 합성 replay 는 결정적이라 둘 다 가능
- **옵션:** (A) 0 — 미세 회귀도 hard-veto / (B, 권장) 0.005 — ε 여유
- **블로킹 항목:** WS-OBS-1, WS-EVAL-1

### D9. analysis_log 프로덕션 집계 알람 채널

- **왜 필요한가:** 운영 통합 방식 결정 — 기존 f3 패턴 재사용이 즉시 가능하고 저비용
- **옵션:** (A, 권장) exit-code + JSON 산출(cron, 기존 f3 패턴) / (B) slack webhook(후속)
- **블로킹 항목:** WS-OBS-3, WS-OBS-8

### D10. penalty PG-load 실패 처리 정책(법적 load-bearing 출력)

- **왜 필요한가:** 틀린 법적 답 vs 무답의 방어가능성 — 저정확도 TTL fallback 계속 서빙 vs penalty 패널 hard-fail
- **옵션:** (A) 저정확도(0.1835) TTL fallback 계속 서빙 + degraded 표식 / (B, 권장·FN보수) penalty 패널만 '산출 불가+provenance' hard-fail, 다른 패널은 계속 서빙
- **블로킹 항목:** WS-OBS-5, WS-OBS-6

### D11. evidence_confidence 저신뢰 floor 값 + numeric discount 활성 여부(라우팅 영향)

- **왜 필요한가:** discount 는 suspected→needs_clarification 라우팅에 영향 → 켤지/표시만 할지 product 결정. floor 높을수록 격하 빈번(FN 안전·노이즈↓)
- **옵션:** (a, 권장) floor=0.5 + discount on / (b) floor=0.4 + discount on(격하 드뭄) / (c) badge-only / discount off(가장 안전하나 lexical blind-spot 미보완)
- **블로킹 항목:** WS-PROV-2, WS-PROV-4

### D12. penalty import prune 방식(legal 감사성)

- **왜 필요한가:** DELETE 즉시삭제는 스냅샷 동등·단순하나 감사추적 소실; soft-deprecate 는 감사추적 보존하나 서빙쿼리 1곳 수정
- **옵션:** (A) DELETE 즉시삭제(스냅샷 동등·단순) / (B, 권장·legal 감사성) deprecated_at soft-deprecate + 서빙 필터
- **블로킹 항목:** WS-DRIFT-3

### D13. 신규 guide-level veto 를 즉시 hard veto 로 승격할지 2주 observe-only(WARN) 후 hard 화할지

- **왜 필요한가:** 즉시 hard 는 ON-flip 즉각 보호하나 noisy baseline 으로 false-veto 위험; WARN→hard 는 안전하나 그 사이 ON 경로 회귀 무방비
- **옵션:** (A) 즉시 hard veto(exit 1) / (B, 권장) WARN→hard(2주 observe-only 후)
- **블로킹 항목:** WS-EVAL-1

### D14. gold 라벨링 주체/SoT 및 expected_guide 정의

- **왜 필요한가:** 평가 신뢰성의 근간 — 라벨 출처와 정답 정의(단일 vs 집합)가 recall@k/precision 산식과 LLM-judge proxy 신뢰도를 좌우
- **옵션:** 라벨 주체: (A) 사용자 본인(도메인 전문가) / (B) KOSHA guide 원문 근거 별도 검수자 / 정답 정의: (권장) 관련 guide 집합(recall@k) + top-1 적합(precision@1)
- **블로킹 항목:** WS-EVAL-2, WS-EVAL-3

### D15. cross-vendor judge Claude 모델 선택 + 누설 제거 후 rerank 기본 ON 유지 여부

- **왜 필요한가:** 비용 vs 품질; 누설 제거 후 delta 가 유의하게 줄면 self-agreement 였다는 의미 → rerank 승급 근거 재평가(EVAL-1 ON-flip 연동)
- **옵션:** judge 모델: 비용 vs 품질 Claude 모델 선택 / rerank: (A) 유지하되 게이트로만 정당화 / (B) flag-gated 강등
- **블로킹 항목:** WS-EVAL-3, WS-EVAL-1

### D16. over-drop mode-mean 임계(placeholder 0.3)

- **왜 필요한가:** gold-set 기반 PR 곡선 없이 확정 불가 → 임시값 착수 후 곡선 확보 시 재튜닝(gold-set 의존이라 phase2)
- **옵션:** (임시) placeholder 0.3 으로 착수 / (확정) WS-EVAL gold-set PR 곡선으로 재튜닝
- **블로킹 항목:** WS-OBS-8

### D17. recall_tolerance / guide-level veto 의 pool 상향 값(oracle-rank 곡선 평탄점)

- **왜 필요한가:** 측정 전 임의 상향 금지 — oracle-rank recall@k 곡선의 평탄점(예 100/200)으로 결정. 임베딩 query 1회/scene 이라 FN-보수적으로 넉넉히 가능
- **옵션:** recall@k 곡선 평탄점 100 / 평탄점 200(FN-보수적으로 넉넉)
- **블로킹 항목:** WS-EVAL-4, WS-EVAL-1

### D18. B6 — ctx:WorkContext/WorkActivity/TemporalStage 의 BFO 축 재배치 모델 결정(B6-ontology 백로그로 라우팅)

- **왜 필요한가:** WS-DEEP-2 의 detector+CON-strict 격리는 이 결정 없이 안전 선행 가능하나, 근본 재모델링은 별도 모델 결정 필요. RiskFeature 의 Quality vs Occurrent 축 정합
- **옵션:** (A) RiskFeature(Quality) 하위에서 분리, Process/Occurrent 유지 / (B) grounding 을 Quality 로 변경해 RiskFeature 하위 유지 / (C) RiskFeature 의 BFO 상위를 Quality→BFO_0000001(entity) 상향
- **블로킹 항목:** WS-DEEP-2

## 3. 단계 계획 (Phased Plan)

| 단계 | 목표 | 항목 | 진입 게이트 | 종료 게이트 | 노력 |
|---|---|---|---|---|---|
| **Phase 0** | 가시화(visibility) — 사용자 대면 green-collapse를 소스에서 차단하고, 측정 인프라의 진실(real v3 baseline + caveat 문서)과 런타임 무변경 표시전용 스캐폴드를 깔아 이후 모든 변경을 측정 가능·안전하게 만든다. recall을 올리거나 FN을 움직일 수 있는 변경은 이 단계에 두지 않는다(순수 라벨/표시/문서/baseline만). | WS-EVAL-4, WS-OBS-2, WS-GATE-1, WS-SAFETY-1, WS-SAFETY-3, WS-SAFETY-4, WS-PROV-1, WS-PROV-3, WS-DRIFT-5 | 세션 시작 git status clean 확인. 작업 전 baseline 캡처: python scripts/replay_synthetic_observations.py --save current.json 가 현행 코드에서 결정적으로 재현되는지 확인(합성 replay는 LLM 미호출 → byte-identical 기대). | Phase0 회귀게이트 통과: (1) regression_gate.py 의 DEFAULT_BASELINE 가 replay_baseline_v3.json 으로 전환되고 v3 baseline 파일이 캡처/커밋되어 'baseline:' 라인이 v3 출력. (2) SAFETY-1/3/4 적용 후 make f1-regression(replay 2,360 + regression_gate --tolerance 0.02) PASS, 특히 false_negative_rate delta≈0(라벨/표시 변경이므로 FN 불변 증명) + no-green-on-unknown.test.tsx 통과(unknown/high 존재 시 risk-low 녹색 클래스 부재). (3) PROV-1/3·DRIFT-5/6 는 표시전용/startup-only → make f1-regression delta≈0 + npm run build(tsc) 0 에러. (4) docs grep: '100% 정확도'류 0건, hybrid_search docstring overclaim 문자열 0건. | S×6 (EVAL-4, OBS-2, EVAL-5, GATE-1, DRIFT-5, DRIFT-6, PROV-3) + M×4 (SAFETY-1, SAFETY-4, PROV-1) — 정정: S 7항목 + M 4항목(SAFETY-1 M, SAFETY-4 M, PROV-1 M, SAFETY-3 S). 합계 약 S7+M4, 가장 가벼운 차단성 단계. |
| **Phase 1** | 차단·결속(blocking & binding) — FN-방향 1급 veto 키를 먼저 세우고, recall을 올리는 방향(unsafe_state 배선, semantic floor/도메인 reject, dual-path merge), 일관성/드리프트 게이트 hard-wire, 관측 attribution, 근거 discount를 배치. recall/FN을 움직일 수 있는 변경은 모두 WS-OBS-1 존재 후에만 진입. | WS-OBS-1, WS-EVAL-1, WS-SAFETY-2, WS-SAFETY-5, WS-GATE-2, WS-GATE-3, WS-GATE-7, WS-GATE-8, WS-GATE-4, WS-GATE-5, WS-GATE-6, WS-DRIFT-1, WS-DRIFT-2, WS-DRIFT-3, WS-DRIFT-4, WS-OBS-4, WS-OBS-3, WS-OBS-5, WS-OBS-6, WS-OBS-7, WS-PROV-2, WS-PROV-4, WS-DEEP-1, WS-DEEP-3, WS-DEEP-2, WS-DRIFT-6 | Phase0 회귀게이트 통과 후 진입. 추가 entry 조건: WS-OBS-1(positive-only SHE recall + she_recall_miss_rate 가 regression_gate 의 1급 veto 키로 등록)과 WS-EVAL-1(replay 에 hazards[] 주입 → ON 경로 실제 실행 + guide_recall@K/top1 veto)이 이 단계 최우선으로 머지되어, 이후 recall 상향 항목이 FN-방향 metric 위에서만 채택되도록 보장. | Phase1 결속게이트 통과: (1) FN 비대칭 veto 실증 — she_matcher 패턴 비활성 mutation·_rerank_guides_llm 0-점 drop mutant 주입 시 positive_she_recall/she_recall_miss_rate/guide_recall_at3 단독 exit 1; mutation 없으면 delta≈0 PASS. (2) 모든 recall 상향 항목(SAFETY-2/5, GATE-2/3, DEEP-1)이 off/floor=0 기본값에서 byte-identical 무회귀 + 활성 시 false_negative_rate delta ≤ +0.02, false_positive_rate 상승 ≤ tol. (3) consistency-gate(GATE-4) + local_consistency_check --gate(GATE-5)가 GATE-6 으로 phase-g3/g4 import prerequisite 에 hard-wire 되고 의도적 비일관 .ttl 음성테스트가 exit 1. (4) GATE-7 repoint 후 GATE-8 per-rule fire-coverage 전 룰 green(0-fire 없음). (5) ontology_pg_drift_check(DRIFT-2) symmetric-diff=0(동기) + 의도 삭제/추가 후 exit 1. (6) PROV-4 harness 가 PROV-1/2/3 적용 전후 scoring 키 byte-identity + 표시필드 존재 동시 통과. (7) OBS-5/6/7 health degraded 신호 정상. | S×6 (OBS-1, GATE-5, GATE-6, GATE-7, OBS-6, OBS-7) + M×15 (EVAL-1, SAFETY-2, SAFETY-5, GATE-2, GATE-3, GATE-8, GATE-4, DRIFT-1~4, OBS-4, OBS-3, OBS-5, PROV-4, DEEP-2, EVAL-3) + L×4 (PROV-2, DEEP-1, DEEP-3) — 가장 무거운 단계, 결속·차단의 본체. |
| **Phase 2** | 정밀·평가(precision & evaluation) — gold-set/PR곡선 등 선행 단계에서 축적되는 데이터에 임계값이 의존하는 항목과, 그 데이터 위에서만 정당화 가능한 promote/active 승격 게이트를 마지막에 확정한다. | WS-EVAL-2, WS-EVAL-3, WS-EVAL-5, WS-GATE-9, WS-OBS-8 | Phase1 결속게이트 통과 후 진입. 추가: WS-OBS-1 FN veto + WS-EVAL-1 ON-경로 replay + WS-GATE-3 shadow_validate 도메인 reject + WS-GATE-4 consistency-gate 가 운영 중이어야 promote/active 승격을 안전하게 평가 가능. | Phase2 평가게이트 통과: (1) EVAL-2 — gold-truth-v1.jsonl 30→100 (NEGATIVE 포함, Vision-FN 별도 카운트) 라벨링 + eval_real_photo_e2e.py 가 precision@1/recall@3 산출, NEGATIVE 케이스 guide=0 보호 실증, LLM-judge↔human κ≥0.4. (2) GATE-9 — promote()/record_link() 가 generic 단일축 code_sig 를 promoted 0건 유지 + cache_enabled on 시뮬레이션에서 regression_gate false_negative_rate delta ≤ +0.02; OHS_ENABLE_ATTACH_CACHE read-path enable 결정은 사용자 승인 + 19 promoted link 사람 검토 후. (3) OBS-8 — drop-ratio over/degenerate 이중 알람 + npz dim mismatch fail-loud; over-drop 임계는 EVAL gold-set PR곡선으로 확정 후 재튜닝. 이 monitor 존재가 LLM_RERANK_MODE=active 승격 PR 의 dependsOn 으로 문서화. | M×2 (GATE-9, OBS-8) + L×1 (EVAL-2) — 데이터 축적 의존으로 마지막, 임계값 확정 중심. |

**Critical path (강제 순서):** WS-EVAL-4 → WS-SAFETY-1 → WS-OBS-1 → WS-EVAL-1 → WS-SAFETY-2 → WS-SAFETY-5 → WS-EVAL-2 → WS-GATE-9

**시퀀싱 근거:** 순서는 세 가지 강제 제약을 동시에 만족하도록 위상정렬했다. (1) 측정 우선성: 안전 도메인에서 'recall/FN 을 움직일 수 있는 변경은 FN-방향 metric 이 존재한 뒤에만 진입'이 하드 룰이다. 따라서 WS-EVAL-4(real v3 baseline — 현재 replay_baseline*.json 부재 확인됨)와 WS-OBS-1(positive-only SHE recall + she_recall_miss_rate veto), WS-EVAL-1(hazards[] 주입으로 ON 경로 실제 실행 + guide_recall@K veto)을 recall 상향 작업(SAFETY-2/5, GATE-2/3, DEEP-1) 앞에 강제 배치했다. v3 baseline 이 없으면 게이트가 거짓 baseline 을 밟아 모든 후속 측정이 무의미해진다.\n\n(2) 안전 가시성 우선성: SAFETY-1/3/4 는 '미탐지=녹색 안전'으로 보이는 치명 결함을 소스에서 차단하는데, 이는 라벨/표시/문서 변경이라 FN 을 움직이지 않으므로 Phase0 에 안전하게 둘 수 있고(요청의 'A1/A2/A3 earliest' 충족), 동시에 후속 모든 SAFETY 항목의 enum/타입 토대다(SAFETY-1 이 RiskLevel.UNKNOWN 과 finding_status 분기를 도입 → 3/4/5 가 이를 소비).\n\n(3) 데이터 축적 의존성: gold-set(EVAL-2)과 PR곡선이 있어야 임계값을 확정할 수 있는 항목(GATE-9 promote 임계·OBS-8 over-drop 임계)은 Phase2 로 미뤘다. 이들을 앞당기면 placeholder 임계로 false-veto/false-pass 가 발생한다.\n\nSAFETY-2↔SAFETY-5 의 명시적 순환 의존(SAFETY-5 dependsOn[1,2], SAFETY-2 dependsOn[5])은 co-design 으로 해소했다: 둘 다 Phase1 에 두되, critical path 에서는 SAFETY-5(surfacing 모델·needs_clarification 승격)를 SAFETY-2(ppe/env 런타임 배선) 앞에 놓아 SAFETY-2 가 surfacing 대상 축을 생산하고 SAFETY-5 가 그것을 소비하는 단방향으로 정렬했다. GATE 워크스트림 내부는 GATE-7(dead clause repoint)→GATE-8(per-rule fire-coverage, GATE-7 의 fire 를 검증), GATE-4+GATE-5(두 게이트)→GATE-6(import prerequisite hard-wire)의 명시 의존을 따랐다. DRIFT-2(symmetric-diff 게이트)→DRIFT-3(prune 은 게이트가 동기 상태를 보증한 뒤에만 안전)도 동일. PROV-1/3 은 표시전용 스캐폴드라 Phase0, PROV-2(라우팅 영향 discount)와 PROV-4(byte-identity harness)는 측정게이트가 선 Phase1. DEEP-2 의 detector+CON-strict 격리는 B6 모델 결정 없이 선행 가능하므로 Phase1 에 두고 재모델링만 백로그로 분리했다.

## 4. 항목 인덱스 (전체)

| ID | 제목 | 단계 | 노력 | 심각도 | 닫는 리스크 | 의존 |
|---|---|:--:|:--:|:--:|---|---|
| `WS-SAFETY-1` | 백엔드 UNKNOWN/not_assessed 위험 상태 도입 (소스에서 녹색-붕괴 차단) | 0 | M | critical | A1 | — |
| `WS-SAFETY-2` | ppe_state/environmental 런타임 배선 (사문화된 unsafe_state 승격 경로 활성화) | 1 | M | high | A2 | WS-SAFETY-1, WS-OBS-1 |
| `WS-SAFETY-3` | 상단 배지 hazards[] OR-in (CWA 상단 vs OWA hazards 모순 제거) | 0 | S | high | A1 | WS-SAFETY-1, WS-EVAL-1 |
| `WS-SAFETY-4` | 프론트엔드 UNKNOWN 중립 렌더 + '미탐지 ≠ 안전' disclaimer | 0 | M | critical | A1 | WS-SAFETY-1, WS-SAFETY-3 |
| `WS-SAFETY-5` | 미분류 위험/unmapped_safety_terms 응답 surfacing + 고위험 미해석 needs_clarification 승격 | 1 | M | high | A2 | WS-SAFETY-1, WS-SAFETY-2, WS-OBS-1 |
| `WS-GATE-1` | hybrid_search docstring overclaim 제거 (truth-in-docstring) | 0 | S | medium | B1 | — |
| `WS-GATE-2` | semantic attach 절대 cosine floor surface + no-match sentinel | 1 | M | high | B1 | WS-EVAL-1 |
| `WS-GATE-3` | shadow_reasoner를 log-only → opt-in hard reject로 승격 (domain-incompat 게이트) | 1 | M | high | B1 | WS-OBS-1, WS-EVAL-1 |
| `WS-GATE-4` | make consistency-gate (check_disjoint_consistency + Fuseki Openllet owl:Nothing live ASK) | 1 | M | high | A6 | — |
| `WS-GATE-5` | local_consistency_check.py --gate 버그 수정 (SHACL non-conform → exit 1) | 1 | S | medium | A6 | — |
| `WS-GATE-6` | consistency-gate를 phase-g3/g4 import Makefile prerequisite로 hard-wire | 1 | S | high | A6 | WS-GATE-4, WS-GATE-5 |
| `WS-GATE-7` | R-14/R-15 dead clause 수정 (haz:Hazard → haz:AccidentType), R-24 cascade revive | 1 | S | medium | A10 | — |
| `WS-GATE-8` | per-rule fire-coverage detector + TBox-liveness 게이트 | 1 | M | medium | A10 | WS-GATE-7 |
| `WS-GATE-9` | learned.json promote 게이트 (domain-guard + reasoner + single-axis 배제) — 캐시 flag-on 전제 | 2 | M | medium | B5 | WS-GATE-3, WS-GATE-4, WS-EVAL-1 |
| `WS-OBS-1` | 회귀 게이트에 positive-only SHE recall을 FN-비대칭 1급 veto 키로 추가 | 1 | S | high | A3 | — |
| `WS-OBS-2` | baseline.md에 'Layer1-3 metric, Vision FN excluded' 캐비엇 명시 | 0 | S | medium | A3 | — |
| `WS-OBS-3` | analysis_log.jsonl 경량 프로덕션 집계기 + 추세-델타 알람 | 1 | M | high | A3 | WS-OBS-4 |
| `WS-OBS-4` | _append_analysis_log에 per-stage drop attribution 필드 추가 | 1 | M | medium | A3 | — |
| `WS-OBS-5` | penalty/profile/incompat 로더에 responding-source 스탬프 + fallback WARNING/metric | 1 | M | high | A5 | — |
| `WS-OBS-6` | startup/health active probe: penalty_index/profile/axiom의 PG 로드 성공 능동 확인 | 1 | S | high | A5 | WS-OBS-5 |
| `WS-OBS-7` | 벡터 recall degrade 가시화: health 카운트 + startup probe + facet(hybrid_unavailable) 표식 | 1 | M | medium | B3 | WS-OBS-6 |
| `WS-OBS-8` | embedding pre-filter drop-ratio 모니터(over-drop/degenerate 이중 알람) — active 승격 전제조건 | 2 | M | medium | B10, B3 | WS-OBS-3 |
| `WS-PROV-1` | RiskFeature origin(gpt_observed vs rule_derived) + ReasoningTrace 추론/정규화 분리 | 0 | M | medium | A7, A3-05 | — |
| `WS-PROV-2` | evidence_confidence on PenaltyPath/Finding + 저신뢰 근거 badge + numeric→needs_clarification discount | 1 | L | medium | A12, A7 | WS-PROV-1 |
| `WS-PROV-3` | StandardProcedure mapping_type/provenance 전파 + 임베딩 후보(미검증) vs 규칙 검증 badge | 0 | S | medium | B7, A7 | — |
| `WS-PROV-4` | Display-only 불변성 증명 harness (scoring byte-identity + 위장-금지 smoke) | 1 | M | medium | A7, A12, B7 | WS-PROV-1, WS-PROV-2, WS-PROV-3 |
| `WS-DRIFT-1` | materialization_runs 출처 테이블 + run_id 스탬프(legal-critical 우선) 🟡 **부분완료(2026-06-14, `87d9e63`)** | 1 | M | high | A7-version | — |
| `WS-DRIFT-2` | ontology_pg_drift_check.py 양방향 symmetric-diff 게이트 + strict 승격 + 주간 CI | 1 | M | high | A4 | — |
| `WS-DRIFT-3` | penalty import reconcile/prune (TTL-absent PG 행 in-txn 제거) | 1 | M | high | A4 | WS-DRIFT-2 |
| `WS-DRIFT-4` | 빌드→서빙 PG baseline 결속(Chroma/npz 스탬프 + 첫 로드 비교 + 번들 manifest) | 1 | M | medium | B2, B4 | — |
| `WS-DRIFT-5` | embedding model/dim 중앙화 + 스탬프 + startup 비교 + 캐시 키에 모델 포함 | 0 | S | medium | B9 | — |
| `WS-DRIFT-6` | startup 벡터 인덱스 health probe + /health degrade 신호 | 1 | S | medium | B2 | WS-DRIFT-4, WS-DRIFT-5 |
| `WS-EVAL-1` | replay에 hazards 주입 + guide_recall@K / top1-relevance FN veto (게이트가 ON 경로를 실제로 밟게) | 1 | M | high | B6, A3, B4 | WS-EVAL-4, WS-OBS-1 |
| `WS-EVAL-2` | 고아 human-gold 인프라 부활 + industrial gold set 30→100 (NEGATIVE 포함, Vision 포함 full pipeline) | 2 | L | high | A9, B8 | — |
| `WS-EVAL-3` | judge 정답누설(expected_corrective_direction) 제거 + cross-vendor(Claude) judge로 순환 평가 차단 | 2 | M | medium | B8 | WS-EVAL-2 |
| `WS-EVAL-4` | DEFAULT_BASELINE v1→v3 + hybrid_search pool forward 버그 수정 + oracle-rank recall@k 계측 | 0 | S | medium | B4, B6, B2 | — |
| `WS-EVAL-5` | evaluation-baseline.md에 ON-flip 통과 + 측정 caveat 문서화 (defensibility) | 2 | S | medium | A9, B6, B8 | WS-EVAL-1, WS-EVAL-2 |
| `WS-DEEP-1` | 이중경로 guide overwrite를 corroboration-보존 MERGE로 전환 + disagreement(she_only/hazard_direct_only/both) 가시화 + per-path agreement 메트릭 | 1 | L | high | A8 | WS-OBS-1, WS-EVAL-1 |
| `WS-DEEP-2` | BFO 축 모순 grounding을 격리된 CON-strict profile + static class-level detector로 가시화 (B6 재모델링은 모델 결정으로 분리) | 1 | M | medium | A11 | — |
| `WS-DEEP-3` | ReasoningTrace를 평면 node-list에서 edge graph로 승격 + applied_rules/reasoner_rejects forward + 추론파생 RiskFeature [추론] 배지 | 1 | L | medium | A7, A3-05 | WS-PROV-1 |

## 5. 완전성 비평 (Completeness Critique)

**커버리지 전부 충족:** ✅ 예

**빠지거나 약한 검증 게이트:**

- WS-DEEP-2 (A11): detector verification asserts exactly 3 BFO-axis-clash classes fire, but there is NO replay/regression_gate run and NO FN-direction check at all. A new disjoint stub TTL (Quality⊥Process, Continuant⊥Occurrent) is loaded into a 'consistency-strict' profile — the item claims SRV/MAT/FAC profiles are unaffected, but nothing in the verification proves the stub cannot leak into the serving manifest beyond a graph-diff. Add: explicit assertion that consistency-strict TTL is NOT in any import/materialization target's source set, and a make verify-manifest exit-0 on serving profile as a hard gate, not prose.
- WS-OBS-2 / WS-EVAL-5 / WS-GATE-1 (A3/A9/B1 docs): pure-docs items have no executable regression at all (correctly), but they are the ONLY closers that touch the 'measurement-truth' risk surface for their grep checks. The grep assertions ('100% 정확도' 0건, overclaim string 0건) are not wired into any make target / CI gate, so they are one-shot manual checks that will silently rot. Add a make verify-docs-claims target that greps and exits 1, referenced by an exitGate.
- WS-DRIFT-1 (A7-version): verification proves run_id IS NULL count == 0 and that scoring code does not reference run_id (Grep), but provides NO FN-direction or serving-path regression beyond 'display-only'. Since import_penalty_to_pg upsert is modified (a serving-data-producing path), a byte-identical PG-content diff (pre/post run_id column add) should be required, not just a NULL-count check — schema migration on a legal-load-bearing table needs a content-equality gate.
- WS-SAFETY-3 (A1): _overall_risk_level signature change adds a hazards param, but verification only unit-tests the OR-in branch and asserts 'replay (hazards 미주입) → unchanged'. Because replay never injects hazards (verified: build_fake_result L91-144 has no hazards key), the OR-in branch is NEVER exercised by any automated gate until WS-EVAL-1 lands. The only coverage is a unit test. Add: WS-SAFETY-3 must depend on WS-EVAL-1 (hazards injection) OR ship a dedicated fixture replay that injects hazards, otherwise the live A1 fix is unmeasured in the regression suite.
- WS-GATE-9 (B5): cache_enabled-on simulation runs regression_gate with false_negative_rate delta<=+0.02, but the replay's false_negative_rate is computed as (procedures==0 AND actions==0) over positives (verified L186-191). The attach-cache promote path raises procedure recall, so a regression there is invisible to false_negative_rate. The correct guard is guide_recall@K (WS-EVAL-1), which GATE-9 does NOT list as a dependency. Add WS-EVAL-1 to WS-GATE-9.dependsOn.

**의존성 이슈:**

- CYCLE (hard deadlock): WS-SAFETY-2.dependsOn=[WS-SAFETY-5] and WS-SAFETY-5.dependsOn=[WS-SAFETY-1, WS-SAFETY-2]. SAFETY-2↔SAFETY-5 are mutually dependent — neither can be merged first, the graph is unschedulable. One edge must be cut.
- DANGLING DEP: WS-DEEP-3.dependsOn=['WS-PROV/A3-02'] is not a valid item id (no such item exists; looks like a placeholder for WS-PROV-1, which owns the RiskFeature.origin + ReasoningTrace.applied_rules fields WS-DEEP-3 forwards). The dep is unresolvable as written.
- PHASE REVERSAL: WS-DRIFT-6 (phase 0) dependsOn WS-DRIFT-4 (phase 1) and WS-DRIFT-5 (phase 0). DRIFT-6 reads hybrid_search._INDEX_HEALTH (produced by DRIFT-4) and the embedding model flag (DRIFT-5). DRIFT-4 is phase 1, so the phase-0 health probe would ship before the index-stamp it consumes exists — the probe would have nothing to read.
- PHASE REVERSAL: WS-EVAL-5 (phase 0) dependsOn WS-EVAL-1 (phase 1) and WS-EVAL-2 (phase 2). A phase-0 docs item cannot document 'ON-flip 통과' and 'real-photo end-to-end recall' numbers that are only produced in phase 1/2. EVAL-5 must move to phase 2 (after EVAL-1 and EVAL-2 produce the three distinct numbers it is supposed to record).
- PHASE REVERSAL: WS-EVAL-1 (phase 1) dependsOn WS-EVAL-2 (phase 2) and WS-EVAL-3 (phase 1) dependsOn WS-EVAL-2 (phase 2). The gold set (EVAL-2) is intentionally last (data-accumulation), but EVAL-1's guide_recall@K veto and EVAL-3's judge-leakage fix are phase-1. Either the EVAL-2 dep is spurious (EVAL-1 truly needs only EVAL-4 hazards-injection + WS-OBS-1, not the human gold set) and should be dropped, or EVAL-1 must move to phase 2 — which would leave the entire phase-1 recall-raising block (SAFETY-2/5, GATE-2/3, DEEP-1) with NO guide-level FN veto, the opposite of the plan's stated safety order.
- MISSING CROSS-WORKSTREAM DEP (the plan's core safety invariant is unenforced): the phase-1 entryGate asserts WS-OBS-1 (positive-only SHE recall veto) and WS-EVAL-1 (guide_recall@K veto) must merge BEFORE any recall-raising item — but NOT ONE recall-raising item (WS-SAFETY-2, WS-SAFETY-5, WS-GATE-2, WS-GATE-3, WS-DEEP-1, WS-GATE-9) lists WS-OBS-1 or WS-EVAL-1 in dependsOn. The ordering lives only in phasing prose; the dependency graph permits a recall change to merge before its veto exists.
- MISSING DEP: WS-SAFETY-3 (live A1 OR-in on overall_risk_level) is only exercised when hazards[] are injected, which is WS-EVAL-1. SAFETY-3 has no dep on EVAL-1, so its production behavior is uncovered by the regression suite until EVAL-1 lands (and EVAL-1 is a later phase).

**회귀(FN/서빙) 위험 + 보강책:**

- WS-SAFETY-2 (unsafe_state wiring) can RAISE false-positives: GPT-asserted ppe/env → unsafe_state → confirmed → is_direct_penalty_match → photo_based penalty fires (legal-load-bearing false alarm). Safeguard already named in decisionNeeded (route ppe/env-only unsafe_state to candidate/confirmation_required, do NOT extend match_she early-return L815). This MUST be locked to option (a) before merge, and the regression must assert false_positive_rate delta<=tol AND that no photo_based penalty fires from ppe/env-only origin — the current verification only checks she/overall accuracy and FP rate generically.
- WS-DEEP-1 (dual-path overwrite → MERGE) can RAISE false-negatives if the merge drops facet guides that the SHE path lacks: the replay FN definition (procedures==0 AND actions==0) is blind to a partial recall drop where SOME procedures survive. The item adds replay_dualpath_agreement.py but reuses the SAME flawed FN definition. Safeguard: add a set-containment invariant (facet guide_code set ⊆ merged set) as a hard property test that fails on ANY dropped facet guide, not just total wipeout — the item mentions this property test but does not make it a veto; promote it to exit-1.
- WS-GATE-2 cosine floor and WS-GATE-3 shadow hard-reject both DROP candidates and can RAISE FN. Both correctly default to off/floor=0 (byte-identical) and gate on false_negative_rate delta<=+0.02. But false_negative_rate is guide-recall-blind (procedures==0 AND actions==0). The real guard is guide_recall@K (WS-EVAL-1). Neither GATE-2 nor GATE-3 depends on WS-EVAL-1, so their stated FN guard is the wrong metric. Safeguard: add WS-EVAL-1 dep and assert guide_recall_at3 non-decrease, not just false_negative_rate.
- WS-OBS-5 / WS-OBS-6 (penalty PG-load-fail policy, decision option B = hard-fail the penalty panel): switching a low-accuracy TTL fallback to a hard-fail is FN-safe for legal correctness but is a SERVING availability regression on the penalty panel. Safeguard: the verification must assert other panels keep serving when penalty hard-fails (degraded != 503), and add a health-probe test that degraded:true still returns HTTP 200 — the item says '200 유지' but no test asserts the penalty panel specifically returns a graceful 'no-answer' rather than throwing and breaking the whole response.
- WS-PROV-2 numeric discount (suspected→needs_clarification) is the ONE provenance item that changes routing, not just display. It can over-flag (raise needs_clarification noise) or, if mis-floored, fail to flag. Safeguard: WS-PROV-4 harness already asserts confidence-0.9 status is unchanged and confidence-0.4 is demoted — this is adequate IF the harness is a hard merge gate for PROV-2. Make WS-PROV-4 a required pre-merge check listed in PROV-2.dependsOn (currently PROV-4 depends on PROV-2, the reverse), so PROV-2 cannot merge without the invariance proof.
- WS-DRIFT-3 penalty prune (DELETE TTL-absent PG rows) can RAISE penalty FN if a still-valid rule is pruned due to a drift-check false-positive (e.g., IRI/code normalization mismatch between TTL and PG). Safeguard: decision option B (soft-deprecate + serving filter) preserves a rollback; the verification must run the prune against a KNOWN-synchronized state first (prune target == 0) to prove no valid rule is removed, then test the drift state — the item states this ordering but does not gate it; make 'prune-target==0 on synced state' a hard precondition assertion.

**계획에 반영할 보정(fixes):**

- Break the WS-SAFETY-2 ↔ WS-SAFETY-5 cycle. Recommended cut: remove WS-SAFETY-2.dependsOn=[WS-SAFETY-5]. SAFETY-2 is runtime wiring (normalizer→match_she ppe/env); SAFETY-5 is response surfacing of unmapped terms + needs_clarification promotion. SAFETY-5 genuinely needs SAFETY-2's normalized ppe/env output, but SAFETY-2 does not need SAFETY-5. Final order: SAFETY-1 → SAFETY-2 → SAFETY-5.
- Fix WS-DEEP-3.dependsOn: replace the dangling 'WS-PROV/A3-02' with 'WS-PROV-1' (the item that introduces RiskFeature.origin and ReasoningTrace.applied_rules/reasoner_rejects that DEEP-3 forwards into the edge graph).
- Add the plan's core safety invariant to the dependency graph, not just prose: add 'WS-OBS-1' to dependsOn of WS-SAFETY-2, WS-SAFETY-5, WS-GATE-3, WS-DEEP-1; and add 'WS-EVAL-1' to dependsOn of WS-GATE-2, WS-GATE-3, WS-DEEP-1, WS-GATE-9, WS-SAFETY-3 (all guide-recall-affecting). This makes 'no recall change before its FN/recall veto' enforceable by the scheduler, not the narrative.
- Resolve the WS-EVAL-1 → WS-EVAL-2 cross-phase reversal: drop WS-EVAL-2 from WS-EVAL-1.dependsOn. EVAL-1 needs only WS-EVAL-4 (hazards-injection + v3 baseline) and WS-OBS-1 to stand up the guide_recall@K veto on synthetic replay; the human gold set (EVAL-2) is for real-photo end-to-end eval, a separate measurement that EVAL-1's synthetic veto does not require. Keep WS-EVAL-3→EVAL-2 (judge κ truly needs human gold) and instead move WS-EVAL-3 to phase 2 alongside EVAL-2.
- Move WS-EVAL-5 (docs) from phase 0 to phase 2. It documents three numbers (synthetic Layer1-3 recall, real-photo e2e recall, ON-flip gate pass) that only exist after EVAL-1 (p1) and EVAL-2 (p2). A phase-0 docs item cannot cite phase-1/2 outputs.
- Fix WS-DRIFT-6 phase: it depends on WS-DRIFT-4 (p1) for _INDEX_HEALTH, so DRIFT-6 cannot be phase 0. Either move DRIFT-6 to phase 1, or split it: ship the static empty-bind-mount count probe in phase 0 (no DRIFT-4 dep) and the stale-baseline comparison in phase 1 (after DRIFT-4 stamps the index). The pg_baseline comparison branch is the part that needs DRIFT-4.
- Add a guide-recall-aware FN metric and stop relying on false_negative_rate (procedures==0 AND actions==0) as the recall guard. The current definition (replay_synthetic_observations.py L186-191) only catches TOTAL procedure wipeout on positives; any partial recall drop is invisible. WS-OBS-1 (positive SHE recall miss) + WS-EVAL-1 (guide_recall@3, top1_relevance) together fix this — make BOTH hard veto keys in regression_gate.compare (currently only 4 METRIC_KEYS + 2 MAX_RATE_KEYS), and document that false_negative_rate alone is insufficient for any guide-recall-raising item.
- Make WS-PROV-4 a pre-merge gate for the items it validates by reversing the dependency expression in the merge checklist: although PROV-4.dependsOn=[PROV-1,2,3] is correct for build order, each of PROV-1/2/3's verification must list 'WS-PROV-4 harness exit 0' as a required check (PROV-2 especially, since it changes routing). Add this to PROV-1/2/3 verification text.
- Add executable doc-claim gates: create a make verify-docs-claims target wrapping the grep assertions from WS-GATE-1, WS-OBS-2, WS-EVAL-5 (overclaim strings 0건, '100% 정확도' 0건) and reference it in the phase-0 exitGate so the checks cannot silently rot.
- Lock the open decisions that gate FP/FN safety before their items merge: SAFETY-2 routing = option (a) candidate-only + no early-return extension; GATE-2 floor = (b) 0.20 FN-conservative; GATE-3 = (a) opt-in off at ship; OBS-5 = (b) penalty hard-fail with graceful per-panel degrade; PROV-2 = (a) floor 0.5 discount-on. These are all FN-conservative and consistent with the safety domain; leaving them open blocks the dependent items' verification from being concrete.

**종합 판정:** Coverage is complete — all 22 risks (A1-A12, B1-B10) are closed by at least one item, verified against the codebase (every referenced file/line target checked and accurate; the OWA→CWA green-collapse root cause at analysis_pipeline.py _overall_risk_level L1102-1111 fallthrough-to-'low' and the dual-path overwrite at L376-377 both confirmed real). The plan's phasing philosophy (visibility → veto-then-recall → eval) is sound and the FN-asymmetric framing is correct. HOWEVER the plan is NOT ready to execute as written: there is a hard scheduling deadlock (WS-SAFETY-2↔WS-SAFETY-5 cycle), a dangling dependency (WS-DEEP-3→'WS-PROV/A3-02'), and five phase-order reversals where an item depends on a later-phase prerequisite (DRIFT-6→DRIFT-4, EVAL-1/3→EVAL-2, EVAL-5→EVAL-1/2). Most importantly, the plan's central safety invariant — 'no recall-raising change merges before its FN veto exists' — is asserted only in phasing prose and is NOT encoded in any item's dependsOn, so the dependency graph as given would permit exactly the regression the plan is built to prevent. Compounding this, the regression suite's false_negative_rate is guide-recall-blind (fires only on total procedure wipeout, L186-191), so several FN guards (GATE-2/3, DEEP-1, GATE-9) are watching the wrong metric and must depend on WS-EVAL-1's guide_recall@K. Verdict: structurally fixable, not shippable as-is. Apply the 11 fixes (break the cycle, fix the dangling/reversed deps, hard-wire OBS-1/EVAL-1 into the recall items' dependsOn, add the guide-recall veto keys, gate the open FP/FN decisions to their FN-conservative options) and the plan becomes safe to execute.

### 5.1 비평 반영 — 정정 적용 (권위본)

비평이 지적한 11개 결함을 위 표(§3 단계계획·§4 항목인덱스)에 **모두 반영 완료**. 정정 요약:

1. **순환 의존 해소** — `WS-SAFETY-2 ↔ WS-SAFETY-5` 데드락 제거: SAFETY-2 dep에서 SAFETY-5 삭제 → 단방향 **SAFETY-1 → SAFETY-2 → SAFETY-5**(critical path도 정정).
2. **Dangling dep 수정** — `WS-DEEP-3` dep `WS-PROV/A3-02`(존재하지 않는 id) → **`WS-PROV-1`**.
3. **핵심 안전 불변식을 그래프에 인코딩** — "veto가 존재한 뒤에만 recall 상향 항목 머지"를 prose가 아닌 dependsOn으로 강제: recall에 영향 주는 모든 항목(SAFETY-2/5, GATE-2/3, GATE-9, DEEP-1, SAFETY-3)의 dependsOn에 **WS-OBS-1 / WS-EVAL-1** 추가.
4. **Phase 역순 4건 수정** — `WS-EVAL-1` dep에서 EVAL-2 제거(synthetic veto는 human gold 불요, OBS-1만 필요) · `WS-EVAL-3`·`WS-EVAL-5` → **Phase 2** · `WS-DRIFT-6` → **Phase 1**(소비하는 DRIFT-4가 Phase1).
5. **guide-recall veto 키 보강** — `regression_gate`의 `false_negative_rate`(절차 *전멸*만 감지, 부분 recall 하락에 blind)에 더해 **positive SHE recall(OBS-1) + guide_recall@K·top1(EVAL-1)** 을 hard-veto 키로 추가. GATE-2/3·DEEP-1·GATE-9의 FN 가드는 이 키로 평가(false_negative_rate 단독 불충분).
6. **실행 게이트화** — docs 주장 검사를 `make verify-docs-claims`(overclaim/'100% 정확도' grep, exit 1)로 Phase0 exitGate에 배선 · `WS-PROV-4`(byte-identity harness)를 PROV-1/2/3의 **pre-merge 필수 체크**로(특히 라우팅 변경하는 PROV-2).
7. **안전 결정 FN-보수 기본값 잠금**(착수 전 §2에서 확정, 권장안) — **D2**=(a) ppe/env unsafe_state는 candidate-only·early-return 미확장 · **D4**=(b) cosine floor 0.20 · **D5**=(a) shadow hard-reject opt-in off · **D10**=(b) penalty 패널만 graceful hard-fail(타 패널 200 유지) · **D11**=(a) evidence floor 0.5 + discount on.

> 이 정정으로 데드락·dangling·phase 역순이 해소되고, "recall 변경은 그 FN veto 뒤에만"이라는 안전 순서가 스케줄러로 강제됩니다. 나머지 14개 결정(§2)은 사용자 확정 대기.

---

## 6. 워크스트림 상세

## WS-SAFETY — 안전 정보 손실 차단 (가장 치명적)

> Closes: **A1**(UNKNOWN/green-collapse, 1순위 critical), **A2**(ppe/env silent-drop + unmapped safety terms)
> Root: `serving-team/08-app/` (backend `app/`, frontend `src/`)

### 문제 한 줄 요약
이 파이프라인은 OWA(GPT/온톨로지)의 **"모름"**을 CWA(PG/UI)의 **"안전"**으로 붕괴시킨다. 구체적으로 ① `_overall_risk_level`이 `finding_status ∉ {confirmed, suspected}`면 무조건 `"low"`(녹색 '낮음')를 반환하고 enum에 "평가했고 안전" vs "평가 못 함"을 구분하는 상태가 없으며(A1-F1), ② 상단 배지는 `hazards[]`를 보지 않아 GPT가 high 위험 카드를 띄워도 상단은 녹색이 되는 자기모순이 있고(A1-F4), ③ normalizer의 `axis_to_field`/`axis_map`이 3축만 산출해 GPT가 emit한 `ppe_state`/`environmental`을 구조적으로 버려 `she_matcher`의 `unsafe_state` 승격 경로가 런타임에서 사문화되며(A1-F2), ④ alias 미등재 어휘는 `unknown_codes`/`unknown_hazards`로만 남고 응답 어디에도 노출되지 않아 화학/전기 같은 고위험 미해석 항목이 흔적 없이 drop된다(AX4-F1). **안전·법률 제품에서 missed hazard(FN)가 최악인데 전 구간이 FN에 "눈 감는" 방향으로 정렬돼 있다.** 본 워크스트림은 명시적 **UNKNOWN/not_assessed 채널을 risk axis와 분리**해 소스에서 녹색-붕괴를 차단하고, ppe/env를 런타임에 배선하며, 미해석 안전어휘를 1급 신호로 응답에 surfacing한다.

핵심 코드 사실(재확인 완료):
- `app/data/risk_feature_catalog.json`에 `ppe_state`(50 codes), `environmental`(18 codes) 축이 **이미 존재**하고, `she_matcher.UNSAFE_PPE_STATES`(8) / `UNSAFE_ENVIRONMENTAL_STATES`(8) 코드가 **카탈로그에 전부 포함**(어휘 정합 OK). 즉 배선만 하면 promote가 fire 가능.
- `openai_client.ONTOLOGY_OBSERVATION_SCHEMA`의 `risk_feature_candidates.axis` enum에 `ppe_state`/`environmental`이 이미 포함(L163) → GPT는 5축을 emit하나 `normalize_risk_feature_candidates.axis_to_field`(L364-368, 3축)에서 소실.
- `she_matcher.match_she`는 `ppe_states`/`environmental` 인자를 **이미 받음**(L776-777). matcher 측 무변경.
- DB `product_analysis.overall_risk_level`은 `String(20)`(models.py:282) → "unknown" 저장에 마이그레이션 불필요.
- `replay_synthetic_observations.build_fake_result`는 3축만 inject(L102-118)하나 synthetic eval set은 `expected_features.ppe_states`(929건)·`environmental`(889건)을 **이미 보유** → 회귀 게이트가 ppe/env 경로를 행사하려면 harness inject 확장이 선행되어야 함(WS-SAFETY-2의 회귀 불변식 핵심).

---

### WS-SAFETY-1 — 백엔드 UNKNOWN/not_assessed 위험 상태 도입 (소스에서 녹색-붕괴 차단)
**Closes:** A1 (A1-F1) · **Severity:** critical · **Phase:** 0 · **Effort:** M

`finding_status`가 `not_determined`/`needs_clarification`(= SHE/SR 폐쇄세계가 아무것도 못 잡은, 가장 위험한 케이스)일 때 `_overall_risk_level`이 `"low"`를 반환하지 못하게 소스에서 차단하고, persisted/history가 동일 verdict를 운반하게 한다.

**Target**
- `app/models/hazard.py` — `RiskLevel(str, Enum)`에 `UNKNOWN = "unknown"` 추가(이미 `CRITICAL` 존재).
- `app/services/analysis_pipeline.py::AnalysisPipeline._overall_risk_level` (L1102-1111) — 분기 추가: `finding_status in {"not_determined","needs_clarification"}` → `"unknown"` 반환(현재 fallthrough `return "low"`는 "관찰 없음·findings 없음"의 진짜 무위험 케이스로만 좁힌다).
- 동 파일 `run` (L154-157, L189-195) — `_overall_risk_level` 결과를 그대로 `RiskLevel(...)` 래핑 후 `_persist_response`에 전달(이미 그렇게 흐름; enum 확장만으로 history/PG 운반됨).
- `app/services/analysis_pipeline.py::_summary` (L1124) — 빈 결과 문구를 "위험 유무를 확정할 수 없습니다(추가 현장 확인 필요)" 류로 교체. 단, 진짜 무위험(관찰 0·hazards 0)과 미판정을 구분해 두 문구 사용.

**Steps**
1. `RiskLevel`에 `UNKNOWN="unknown"` 추가.
2. `_overall_risk_level` 시그니처는 유지하되 분기 추가(아래 WS-SAFETY-3가 hazards 인자를 추가하므로 본 항목은 finding_status 기준 분기만; 충돌 회피 위해 WS-SAFETY-3와 같은 PR로 묶거나 dependsOn 순서 준수).
3. `_summary`에서 미판정(she_matches 또는 risk_features는 있으나 actionable 0) vs 진짜 무신호를 분기해 문구 분리.
4. `finding_status` enum 자체는 변경하지 않음(이미 `needs_clarification`/`not_determined` 보유). 단 "평가했고 안전"을 표현할 명시 상태가 필요하면 decisionNeeded 참조.

**Verification**
- 신규 단위테스트 `tests/unit/test_overall_risk_level.py`: `finding_status="not_determined"`/`"needs_clarification"` → `_overall_risk_level(...) == "unknown"` (절대 `"low"` 아님); `confirmed`+HIGH→`high`, `suspected`→`medium` 회귀 불변.
- `python scripts/replay_synthetic_observations.py --save current.json` 후 `python scripts/regression_gate.py current.json --tolerance 0.02` — `she_accuracy/sr_accuracy/penalty_accuracy/overall_accuracy` 비-vetoed, `false_negative_rate` 상승(>+0.02) 없음. **FN 방향 핵심**: green-collapse 차단은 positive 케이스의 actionability를 바꾸지 않으므로(표시 라벨만 변경) replay 지표는 불변이어야 함 — 만약 `false_negative_rate`가 움직이면 분기 로직 오류.
- `negative` 케이스가 `unknown`으로 over-flag되지 않는지 확인: replay에서 `case_type=negative & overall_risk_level=="unknown"` 비율을 새 로그 필드로 측정, baseline 대비 신규 false-alarm.

**Rollback:** `_overall_risk_level` 분기 1줄 revert + `RiskLevel.UNKNOWN` 제거(프론트가 unknown을 못 받으면 중립 라벨로 graceful fallback하도록 WS-SAFETY-4에서 default 처리하므로 enum 제거만으로 안전 복귀).

**dependsOn:** 없음 (WS-SAFETY-3와 같은 함수를 건드리므로 동일 PR 권장)
**decisionNeeded:** 향후 "평가했고 안전(assessed_safe)" 상태를 finding_status에 추가할지. 옵션 (a) 지금은 not_determined/needs_clarification→unknown만 처리하고 assessed_safe는 후속, (b) 동시에 `assessed_safe` 상태 신설(녹색 low 허용). **권장 (a)** — FN-보수적, 작은 변경.

---

### WS-SAFETY-2 — ppe_state/environmental 런타임 배선 (사문화된 unsafe_state 승격 경로 활성화)
**Closes:** A2 (A1-F2, AX4-F2 일부) · **Severity:** high · **Phase:** 1 · **Effort:** M

GPT가 emit하는 `ppe_state`/`environmental` 신호를 normalizer→situation_assessment→`match_she`까지 배선해, 카탈로그에 이미 존재하는 `unsafe_state` 기반 candidate/confirmed 승격을 활성화한다. matcher는 무변경.

**Target**
- `app/services/hazard_normalizer.py::normalize_risk_feature_candidates` — `axis_to_field`(L364-368)에 `"ppe_state":"ppe_states"`, `"environmental":"environmental"` 추가. faceted dict에 두 키 초기화.
- 동 파일 `normalize_faceted_hazards` (L394-485) — `result` dict에 `"ppe_states":[]`,`"environmental":[]` 초기화 + `axis_map`(L403-407)에 두 축 추가. `_resolve_alias_code`는 축-제네릭(catalog `_get_valid_codes(axis)` 사용)이라 무변경. 중복제거 루프(L463)에 두 필드 포함.
- `app/services/situation_assessment_service.py::match_situational_patterns` (L33-53) — `match_she(...)` 호출에 `ppe_states=...`, `environmental=...` 전달. **데이터 출처는 decisionNeeded** (canonical은 ppe/env를 운반 안 함; `normalized`에서 가져와야 함).
- `app/services/analysis_pipeline.py::run`/`_build_knowledge_context` — `match_situational_patterns`에 `normalized`(또는 ppe/env만)를 추가 전달(현재 시그니처는 `canonical`만 받음 → 인자 1개 추가). `has_observable_violation_signal`은 이미 `normalized.get("ppe_states"/"environmental")`을 읽으므로(situation_assessment_service.py:26-27) normalizer만 채우면 자동 활성.
- (배선 행사 전제) `scripts/replay_synthetic_observations.py::build_fake_result` (L102-118) — `axis_map`에 `("ppe_state","ppe_states")`,`("environmental","environmental")` 추가해 synthetic의 `expected_features.ppe_states/environmental`(929/889건)을 inject. 이게 없으면 회귀 게이트가 새 경로를 한 번도 행사하지 못함.

**Steps**
1. normalizer 2축 배선(axis_to_field + axis_map + result 초기화 + dedup).
2. `match_situational_patterns` 시그니처에 ppe/env 인자 추가 + 호출부 배선(decisionNeeded 결정 후 confirmed vs candidate routing 적용).
3. `risk_rule_service.apply_risk_rules`/`hazard_rule_engine.apply_rules`는 ppe/env를 result에 보존하지 않으므로(L245-251 확인), canonical 경로 대신 **normalized**의 ppe/env를 matcher에 전달(권장). 또는 apply_rules result에 두 키를 passthrough로 추가.
4. `build_fake_result` ppe/env inject 추가.
5. FP 재활성 가드: unsafe_state→confirmed 승격(she_matcher L689-693)이 GPT-단정 ppe/env에서 fire하므로 penalty-exposure FP를 별도 추적.

**Verification**
- 신규 단위테스트 `tests/unit/test_normalize_faceted_hazards_ppe_env.py`: `risk_feature_candidates`에 `{axis:"ppe_state",text:"HELMET_MISSING"}`,`{axis:"environmental",text:"WET_SURFACE"}` → `normalize_*` 결과 `ppe_states==["HELMET_MISSING"]`, `environmental==["WET_SURFACE"]` (round-trip). 
- 신규 통합테스트 `tests/integration/test_match_she_unsafe_state.py`: `match_she(db, ppe_states=["HELMET_MISSING"])` (3축 빈 입력)에서 status가 `candidate` 도출되는지 — **단, 현 `match_she` L815 early-return은 accident/agent/context만 체크하므로 ppe/env-only 입력은 여전히 `[]`**. 따라서 본 테스트는 (a) accident/agent/context 중 1축 + unsafe ppe 조합으로 candidate→confirmed 승격, 또는 (b) WS-SAFETY-2 범위에 early-return을 `or ppe_states or environmental` 확장 포함 여부를 명시(decisionNeeded와 연동).
- 회귀: `replay → regression_gate --tolerance 0.02`. ppe/env inject 후 `she_accuracy`/`overall_accuracy` 비-퇴행, `false_positive_rate` 상승 ≤ tolerance. **FN 방향**: ppe/env 배선은 recall을 올리는 방향이므로 `false_negative_rate` 하락 또는 불변이어야 정상; 상승 시 배선 오류.
- `evaluate_stage2_5_pipeline_quality.py` 재실행해 SHE recall(현 54.9%)이 하락하지 않고 ppe/env 보유 positive 케이스(929/889)에서 `has_actionable_she` 개선되는지 측정.

**Rollback:** normalizer axis_to_field/axis_map의 2축 항목 제거 → 즉시 사문화 상태로 복귀(matcher/하류 무변경이라 안전). `build_fake_result` inject도 동시 revert.

**dependsOn:** WS-SAFETY-5 (early-return/routing 결정), 사실상 WS-SAFETY-2 내부 decisionNeeded
**decisionNeeded:** **confirmed-vs-candidate routing (FP risk).** GPT-단정 ppe/env가 `unsafe_state`→`confirmed`로 직행하면 `is_direct_penalty_match`(status=='confirmed')가 true가 되어 photo_based penalty가 fire → 오탐 시 벌칙 오신호. 옵션 (a) **ppe/env-only 유래 unsafe_state는 `candidate`(confirmation_required)로만 라우팅**해 penalty-path defensibility 보호(권장, FN은 막되 FP 억제), (b) 시각 score 충족 시 confirmed 허용(현 matcher 기본 동작). 또한 `match_she` early-return(L815)을 ppe/env 포함으로 확장할지(확장 시 ppe/env-only 사진도 SHE 후보 검색 → recall↑ but FP risk) 결정 필요.

---

### WS-SAFETY-3 — 상단 배지 hazards[] OR-in (CWA 상단 vs OWA hazards 모순 제거)
**Closes:** A1 (A1-F4) · **Severity:** high · **Phase:** 0 · **Effort:** S

상단 `overall_risk_level`이 `hazards[]`(GPT 직접 위험) 신호를 무시해 high 카드가 떠도 상단이 녹색이 되는 모순을 차단. hazards가 비어있지 않거나 high면 절대 녹색 'low' 금지. provenance 보존(silent promote 금지).

**Target**
- `app/services/analysis_pipeline.py::_overall_risk_level` (L1102-1111) — 시그니처에 `hazards: list[HazardItem] | None = None` 추가하고 `run`(L154)에서 `self._build_hazard_items(...)` 결과(또는 `hazards_payload`)를 전달. `HAZARD_DIRECT_MODE=="off"`(L57)면 OR-in skip(control arm 보존).
- 로직: finding-derived level과 `max(hazard.risk_level)`를 비교해, hazard가 더 높으면 silent promote 대신 **별도 플래그**(예: `AnalysisResponse.unverified_high_hazard: bool` 또는 기존 unknown 상태 활용) 세팅 + 상단이 녹색 low가 되지 않게 차단. hazards high & finding이 not_determined/needs_clarification → `overall_risk_level="unknown"`(중립) + 플래그.
- `app/models/analysis.py::AnalysisResponse` — `unverified_high_hazard: bool = False`(또는 동등) 필드 추가(display-only, scoring 미반영 — provenance 규칙 준수).

**Steps**
1. `_overall_risk_level`에 hazards 인자 + OR-in 로직(off 모드 존중).
2. high hazard & 약한 finding → `unknown` + 플래그(promote는 medium/high로 올리지 않음 → CWA/OWA 출처 구분 유지).
3. 응답 모델에 플래그 필드 추가.

**Verification**
- 단위테스트: `hazards=[{risk_level:"high"}]` + `finding_status ∈ {not_determined, needs_clarification, suspected}` → `_overall_risk_level`이 절대 `"low"` 반환 안 함 + `unverified_high_hazard==True`. `HAZARD_DIRECT_MODE="off"` → OR-in skip(녹색 가능) 회귀 확인.
- 회귀: replay(`HAZARD_DIRECT_MODE` 미주입 = hazards[] ∅이므로 무발동) → `regression_gate` 지표 불변(설계상 replay는 hazards 미주입).

**Rollback:** `_overall_risk_level` hazards 인자/OR-in 분기 revert(인자 default None이라 호출부 영향 없음) + 응답 플래그 필드 제거.

**dependsOn:** WS-SAFETY-1 (같은 함수 + `unknown` 상태 사용)
**decisionNeeded:** null

---

### WS-SAFETY-4 — 프론트엔드 UNKNOWN 중립 렌더 + "미탐지 ≠ 안전" disclaimer
**Closes:** A1 (A1-F1, A1-F4 disclosure) · **Severity:** critical · **Phase:** 0 · **Effort:** M

신규 `unknown` 상태를 **중립색(회색/slate, 녹색 절대 아님)** + "판정 불가 — 안전 보장 아님" 라벨로 렌더하고, 빈 패널의 "…없습니다"를 "미탐지 ≠ 안전" disclaimer로 교체. 상단 배지가 OWA high hazard와 모순 시 consistency 경고.

**Target**
- `src/types/hazard.ts` — `RiskLevel`에 `'unknown'` 추가; `riskLevelLabels.unknown = '판정 불가 — 안전 보장 아님'`; `riskLevelColors.unknown = 'risk-unknown'` (TS가 `Record<RiskLevel,string>` 누락 시 컴파일 에러로 강제).
- `src/styles/globals.css` — `.risk-unknown { @apply bg-slate-100 text-slate-700 border-slate-300; }` (중립, 녹색 `risk-low`와 명확히 구분).
- `src/components/common/RiskLevelBadge.tsx` — 신규 상태 자동 처리(맵 기반이라 코드 변경 불필요; 미지정 level graceful fallback 위해 `riskLevelColors[level] ?? riskLevelColors.unknown` 방어 추가 권장).
- `src/components/results/ResultSummary.tsx` (L29) / `src/pages/ResultPage.tsx` (L76-77 근처) — `overall_risk_level==='unknown'` 또는 `unverified_high_hazard` 시 상단에 배너: "이 사진으로는 위험 유무를 확정할 수 없습니다. 미탐지는 안전을 의미하지 않습니다 — 추가 현장 확인 필요. (GPT 추정 · SHE/SR 미확인)".
- `src/components/results/RiskOverviewPanel.tsx` (L98/120/154), `ImmediateActionsPanel.tsx` (L56), `PenaltyPathPanel.tsx` (L49-50) — `unknown`일 때 빈 상태 문구를 "미탐지 ≠ 안전 (분석이 위험을 확정하지 못함)" 톤으로 교체(완전 무위험과 구분).
- `src/components/results/resultLabels.ts` — finding_status 라벨 정합 유지(`not_determined`='판단 불가' 기존 OK).
- `src/pages/HistoryPage.tsx` (L84) — 동일 배지 맵 사용이라 자동 반영(persisted unknown이 회색으로 표시됨).

**Steps**
1. 타입/색/라벨 3종 동시 추가(TS 컴파일이 누락 강제).
2. 배너 컴포넌트 + ResultPage 배선.
3. 패널별 빈 상태 문구 조건부 교체.

**Verification**
- 프론트 단위테스트(Vitest/RTL) `RiskLevelBadge`: `level="unknown"` → 라벨 '판정 불가 …', 클래스 `risk-unknown`(녹색 클래스 아님).
- 회귀 불변 테스트 `tests/results/no-green-on-unknown.test.tsx`: `overall_risk_level ∈ {unknown}` 또는 `hazards`에 high 존재 시, 렌더 트리에 `risk-low`(녹색) 클래스가 **절대 등장하지 않음**을 assert. (A1 핵심 lock — FN 방향 시각 회귀 차단)
- `npm run build` (tsc) — 누락된 RiskLevel 키 컴파일 에러 0.
- 수동: `verify` 스킬로 앱 기동 후 not_determined 케이스 스크린샷 — 상단 회색 + disclaimer 확인.

**Rollback:** 타입/색/라벨/배너 커밋 revert. 백엔드가 `unknown`을 보내도 프론트 방어 fallback(`?? risk-unknown` 또는 중립)이 있으면 안전, 없으면 백엔드 WS-SAFETY-1과 함께 revert.

**dependsOn:** WS-SAFETY-1 (백엔드가 `unknown`을 emit해야 의미), WS-SAFETY-3 (`unverified_high_hazard` 플래그)
**decisionNeeded:** null

---

### WS-SAFETY-5 — 미분류 위험 / unmapped_safety_terms 응답 surfacing + 고위험 미해석 needs_clarification 승격
**Closes:** A2 (AX4-F1, AX4-F2, AX4-F5 일부) · **Severity:** high · **Phase:** 1 · **Effort:** M

alias 미등재로 drop되던 `normalizer_unknown_codes`(faceted enum drop)와 `hazard_canonical["unknown_hazards"]`(hazard-direct drop)를 응답에 **미분류 위험**으로 노출해 "위험 없음" vs "해석 못 한 항목"을 구분(defensibility 핵심). 화학/전기/high-severity 미해석은 `finding_status=needs_clarification`로 승격해 사용자 후속을 강제.

**Target**
- `app/models/analysis.py::AnalysisResponse` — `unmapped_safety_terms: List[UnmappedTerm] = []` 추가(신규 모델 `UnmappedTerm{ raw_text:str, axis:str|None, source:"faceted_enum"|"hazard_direct", risk_level:str|None, is_high_concern:bool }`). display-only, scoring 미반영.
- `app/services/analysis_pipeline.py::run`/`_build_knowledge_context` — `knowledge.normalizer_unknown_codes`(L406)와 `hazard_canonical["unknown_hazards"]`(normalize_hazards_array 출력, hazard_normalizer.py:638)를 합쳐 `unmapped_safety_terms` 구성. 응답 조립부(L159-187)에 필드 추가.
- `app/services/analysis_pipeline.py::_finding_status` (L706-734) — 미해석 항목이 chemical/electrical/high-severity(예: raw가 THF/CO/화학·전기 패밀리 또는 hazard risk_level=="high")면, 기존 `not_determined`로 떨어지는 분기에서 `needs_clarification`로 승격(unresolved-high 우선). 단 sr_ids 보유 케이스 의미 변경 금지.
- `src/types/analysis.ts` + 신규 패널/섹션(또는 RiskOverviewPanel 확장) — `unmapped_safety_terms`를 "미분류 위험 (해석 보류 — 추가 확인 필요)"로 렌더, hazard-direct unmapped는 "법령/벌칙 근거 보류" 라벨.

**Steps**
1. `UnmappedTerm` 모델 + 응답 필드.
2. 파이프라인에서 두 출처 병합 + high-concern 판정(간단 키워드/축 기반: hazardous_agent 축 미해석 또는 hazard risk_level=="high").
3. `_finding_status`에 unresolved-high 승격 분기(needs_clarification → WS-SAFETY-1 덕분에 상단 `unknown`+중립으로 표시됨).
4. 프론트 렌더.

**Verification**
- 단위테스트 `tests/unit/test_unmapped_safety_terms.py`: `risk_feature_candidates=[{axis:"hazardous_agent",text:"THF"}]`(catalog 밖) → 응답 `unmapped_safety_terms` 비어있지 않음 + `is_high_concern==True` + `finding_status=="needs_clarification"`. 일반(비고위험) 미해석은 needs_clarification 강제 안 함(과대 승격 방지).
- 회귀: `replay → regression_gate --tolerance 0.02`. **FN 방향**: unmapped surfacing은 정보 추가일 뿐 actionability 미변경 → `she_accuracy`/`false_negative_rate` 불변. `_finding_status` 승격이 `false_positive_rate`를 tolerance 초과로 올리지 않는지 확인(negative 케이스에 미해석 고위험이 거의 없어야 함).
- `evaluate_stage2_5` 재실행 — needs_clarification 승격이 SR/penalty 정밀도 지표를 퇴행시키지 않음.

**Rollback:** 응답 필드/모델/`_finding_status` 승격 분기 revert(필드 default `[]`라 하류 무영향). 프론트 섹션 revert.

**dependsOn:** WS-SAFETY-1 (needs_clarification가 상단 `unknown`으로 중립 표시되어야 의미), WS-SAFETY-2 (ppe/env 배선과 같은 normalizer 영역)
**decisionNeeded:** **high-concern 판정 기준.** 옵션 (a) 축 기반(`hazardous_agent` 축의 미해석 + hazard risk_level=="high")만 승격(권장, 단순·보수), (b) 키워드 사전(THF/CO/전기 패밀리) 추가(정밀하나 유지보수 부담·또 다른 미등재 위험). 또한 미해석 surfacing을 동기 human-queue로 보낼지 — 감사 결론은 **동기 큐 불필요(~0.1% 볼륨), 응답 가시화 + needs_clarification 승격으로 충분**.

---

### 통합 회귀 불변식 (WS-SAFETY 전체 게이트)
1. **녹색-붕괴 lock**: `overall_risk_level ∈ {unknown}` 또는 `hazards`에 high 존재 또는 `finding_status ∈ {not_determined, needs_clarification}`인 어떤 분석도 **녹색 'low'(risk-low / "낮음")로 렌더되지 않는다** — 백엔드 단위테스트(`_overall_risk_level`) + 프론트 RTL 테스트 양쪽에서 assert.
2. **ppe/env round-trip**: HELMET_MISSING / WET_SURFACE가 normalize→match_she까지 살아 candidate(또는 routing 결정에 따른 status)로 도출.
3. **회귀 게이트**: `python scripts/replay_synthetic_observations.py --save current.json && python scripts/regression_gate.py current.json --tolerance 0.02` — 4개 accuracy 비-vetoed, `false_negative_rate`/`false_positive_rate` ≤ +0.02. **단 ppe/env inject(WS-SAFETY-2)가 build_fake_result에 반영된 뒤 baseline 재캡처 필요** (`--save-baseline`).

---

## WS-GATE — 검증 게이트: soft match를 fact로 굳히기 전에 막기

### 워크스트림 개요

이 워크스트림은 **OWA(GPT vision 확률적 hazard) → 임베딩 soft match → CWA(서빙된 표준개선절차=사실)** 전이 지점에서 "검증"이 사실상 PG 존재확인뿐이라는 구조적 갭을 닫는다. 두 감사가 확인한 핵심: (1) 벡터 attach 경로에 closed-world disjoint/domain hard reject도, 절대 cosine floor도 없어 부적합 guide가 무조건 부착된다(B1, 기본 config에서 **현재 라이브** — `OHS_ENABLE_HYBRID_SEARCH=True`/`OHS_ENABLE_SEMANTIC_RERANK=True`). (2) ontology→PG 재물질화 전이점에 일관성/SHACL 자동 게이트가 0개이고, 있는 도구(`local_consistency_check.py`)는 SHACL non-conform에도 항상 `return 0`이다(A6). (3) shacl-construct R-14/R-15가 폐지된 `haz:Hazard`를 참조해 0건 fire하고 R-24가 cascade-dead인데, "룰 0회 발화" detector가 없어 아무도 모른다(A10). (4) 파생 캐시 `learned.json`이 `support≥2`만으로 reasoner/domain 게이트 없이 promoted된다(B5, `OHS_ENABLE_ATTACH_CACHE=False`라 **현재 dormant** — flag-on 전 hardening).

도메인 원칙(불변): **false-negative(놓친 위험·드롭된 관련 guide)가 최악**. 따라서 hard reject류는 전부 confidence-thresholded opt-in으로 시작하고, FN 방향 회귀(`regression_gate.py`의 `false_negative_rate`)를 게이트로 박는다. 온톨로지=SoT/PG=스냅샷/OWL 추론은 요청 경로 밖 원칙을 준수해, 게이트는 전부 오프라인/배치 CI 단계에 건다. 생성 산출물은 손대지 않고 생성기/스크립트를 고친다.

우선순위: Phase 0(B1 docstring·floor 등 며칠 내 가시화·저위험) → Phase 1(A6 consistency-gate·A10 dead-rule·detector 구조적 안전망) → Phase 2(B5 pre-enablement gate, 캐시 flag-on 전제).

---

### WS-GATE-1 — hybrid_search docstring overclaim 제거 (truth-in-docstring)
**closes:** B1 · **severity:** medium · **phase:** 0 · **effort:** S

`hybrid_search.py` 모듈 docstring L4-5 "부착의 검증·추론·전파는 온톨로지(Phase 3)가 보증"은 hollow overclaim이다. 실제 attach 경로(`_semantic_guide_candidates`)의 유일한 검증은 PG 존재확인(`if g is None: continue`) + industry soft 주석 + (기본 on) soft LLM rerank이며, closed-world disjoint/domain reject은 `hazard_to_guide_service.py:157` 주석대로 미구현이다. docstring을 "후보 생성(recall)만 담당. 부착은 SSOT 존재검증 + soft 산업정합 주석 + (기본 on) soft LLM rerank를 거치며, **closed-world disjoint/domain 검증은 아님**"으로 정정한다. `hazard_to_guide_service._semantic_guide_candidates` / `_semantic_sr_candidates`의 docstring도 동일 톤으로 정정한다. 코드 변경 없음 → 회귀 불가.

### WS-GATE-2 — semantic attach 절대 cosine floor + no-match sentinel
**closes:** B1 · **severity:** high · **phase:** 1 · **effort:** M

`HybridIndex.search`는 vscore(cosine)를 계산하지만 RRF 융합은 순위만 쓰고 절대 유사도를 버린다. `_semantic_guide_candidates`/`_guide_section_recall`은 ordinal score(`0.92−0.04·rank`)만 부여해, 코퍼스에 진짜 적합 guide가 없어도 top-K best가 무조건 부착된다(judge_semantic_attach: rescue 세그먼트 40%가 on_score=0 오부착). top vscore를 attach 레이어로 surface하고, calibrated floor(text-embedding-3-small에서 ~0.20-0.25 시작, judge set으로 보정) 미만 후보를 드롭하며, rerank가 전부 0점/floor가 전부 거부 시 `_rerank_guides_llm`·fallback의 "recall 순서 유지(coverage 보존)"를 **no-match sentinel(빈 결과)**로 바꿔 `guide_rows`에 spurious 표준개선절차 근거가 들어가지 않게 한다. floor는 env 게이트(`OHS_SEMANTIC_COSINE_FLOOR`)로 노출해 0이면 현행 동작(무회귀)으로 둔다.

### WS-GATE-3 — shadow_reasoner를 log-only → opt-in hard reject로 승격 (domain-incompat 게이트)
**closes:** B1 · **severity:** high · **phase:** 1 · **effort:** M

이미 물질화된 `guide_domain_incompatibilities` PG 테이블과 `shadow_reasoner.shadow_validate`가 존재하나 (a) `analysis_log.jsonl` write-only이고 (b) 기본 off인 `_apply_llm_rerank`(LLM_RERANK_MODE shadow/active) 경로에서만 호출돼 **기본 served 경로에 전혀 안 걸린다**. 기본 경로인 `analysis_pipeline.py:358-377`(`_semantic_attach_enabled() and hazard_guide_relations` → `guide_rows` 대체) 직전에 `shadow_validate(industry_ko, candidate_guide_codes)`를 호출하고, `level=="vetted"` AND `confidence ≥ OHS_DOMAIN_REJECT_CONF`(기본 매우 높게, 예 0.9)인 reject만 hard drop한다. confidence-thresholded opt-in이라 FN을 방지한다. **DECISION: 운영 기본값을 opt-in(off)으로 두되, eval 통과 후 default-on 전환할지는 사용자 결정.**

### WS-GATE-4 — `make consistency-gate` (check_disjoint + Fuseki Openllet owl:Nothing live ASK)
**closes:** A6 · **severity:** high · **phase:** 1 · **effort:** M

OWA→CWA 전이점(PG 재물질화)에 논리 일관성을 강제하는 자동 게이트가 0개다. `check_disjoint_consistency.py`는 이미 collisions 시 exit 1이므로 신규 작성 없이 그대로 1차 게이트로 승격한다. 2차로 `verify_fuseki_inference.sh`에 `ASK { ?x a owl:Nothing }`를 추가(REASONER_MODE=openllet 라이브 endpoint — Pellet on-demand 추론을 실제 trigger; "Server Started"≠일관 함정 회피)하거나, CI에서 일회성 Openllet load smoke로 `isConsistent()`를 호출한다. `make consistency-gate` 타깃을 신설해 둘을 묶는다. 게이트 부재가 향후 라이브가 될 G.3(penalty_rule_index)/G.4(she_patterns) 먼저 보호.

### WS-GATE-5 — `local_consistency_check.py --gate` 버그 수정 (SHACL non-conform → exit 1)
**closes:** A6 · **severity:** medium · **phase:** 1 · **effort:** S

정본처럼 인용되는 `local_consistency_check.py`가 SHACL `conforms=false`(현 산출물 19,879 violations)·CQ coverage=0%여도 항상 `return 0`(L230)이라 어떤 자동 게이트로도 쓸 수 없다. `--gate` 플래그를 추가해 SHACL `conforms=false` & violation count>0이면 exit 1을 반환한다(TBox-only 실행은 conforms=True라 `--skip-instances --skip-sparql --gate` 조합이 실제 enforce 가능). full-ABox 모드의 CQ coverage는 in-memory rdflib 추론 부재 artifact이므로 pass/fail 판정에서 제외하고, 출력에 "advisory(체인 추론 없음)" 배너를 단다. `scripts/audit_code_consistency.py --gate`의 exit-code 패턴을 미러.

### WS-GATE-6 — consistency-gate를 phase-g3/g4 import의 Makefile prerequisite로 hard-wire
**closes:** A6 · **severity:** high · **phase:** 1 · **effort:** S · **depends:** WS-GATE-4, WS-GATE-5

게이트가 있어도 "엔지니어가 sprint 중 기억"에 의존하면 무의미하다. Makefile의 사용자대면 materialization 타깃(`phase-g3-import`/`phase-g4-import`, 신설 시 포함)에 `consistency-gate`(WS-GATE-4) + `local_consistency_check.py --skip-instances --skip-sparql --gate`(WS-GATE-5)를 prerequisite로 박아, 비일관/비적합 KB가 PG로 흐르기 전에 차단한다. 최소 pre-push hook 또는 경량 CI로 "수동 sprint 기억" 의존을 제거한다.

### WS-GATE-7 — R-14/R-15 dead clause 수정 (haz:Hazard → haz:AccidentType), R-24 cascade revive
**closes:** A10 · **severity:** medium · **phase:** 1 · **effort:** S

`kosha-rules-r14-r30-shacl-construct.ttl` R-14(L66)·R-15(L84)가 `?hazd a haz:Hazard`를 매칭하는데 `haz:Hazard`는 B5/F4-c에서 클래스째 폐지됐다(`kosha-facet-axis-disjoint.ttl:7`) → 모든 그래프에서 0건 fire. R-24(L243-254)는 R-15가 만드는 `bridge:appliesTo`에 의존 → cascade-dead. 두 절을 `?hazd a haz:AccidentType`로 repoint한다(현행 `sr:addressesAccidentType`/`risk:correspondsToHazard→AccidentType` 모델과 일치; demo-chain L43 `demo:Haz1 a haz:AccidentType`가 이미 충족). **R-16/R-26은 건드리지 않는다** — 본문이 untyped `?hazd`라 이 원인으로 죽지 않았다(감사 권고의 R-16/R-26 repoint는 misdirected). 생성기/룰 파일을 직접 고치되, 생성 산출물(materialized triples)은 재실행으로만 갱신.

### WS-GATE-8 — per-rule fire-coverage detector + TBox-liveness 게이트
**closes:** A10 · **severity:** medium · **phase:** 1 · **effort:** M · **depends:** WS-GATE-7

(1) `run_shacl_rules.py`는 docstring이 "rule별 inferred triple count"를 약속하나 실제론 aggregate `after-before`만 출력한다. 룰별로 SHACL을 개별 적용해 inferred triple 수를 emit하고, 본문을 만족하는 fixture(demo-chain)에서 0건 fire하는 룰을 WARN/FAIL한다(F5 `check_data_coverage` 패턴 미러). (2) `verify_rule_parity.py`가 빈 fixture에서 0≡0으로 죽은 룰을 정당화하던 문제는, demo-chain에 canonical AccidentType-typed individual이 이미 있으므로 "각 룰 SHACL 측 >0 inference" non-vacuous assertion을 추가해 차단. (3) CONSTRUCT 본문이 참조하는 모든 class/property가 현행 TBox에 live한지 검사하는 TBox-liveness 가드를 `validate_manifest.py`(make verify-manifest) 계열에 추가 → R-14류 dead rule을 정적으로 자동 적발.

### WS-GATE-9 — learned.json promote 게이트 (B5 pre-enablement: domain-guard + reasoner + single-axis 배제)
**closes:** B5 · **severity:** medium · **phase:** 2 · **effort:** M · **depends:** WS-GATE-3

`hybrid_attach_store.promote()`는 `support≥2`만으로 status='promoted'를 부여하고 "온톨로지 검증은 record측 책임"을 주석으로만 위임한다. 실제 record측(`accumulate_hybrid_attach.py:68-69`)은 raw pipeline 출력을 confidence=1.0 하드코딩해 기록 → 임베딩 co-occurrence가 무게이트로 서빙 사실이 된다(learned.json에 `work_context.GENERAL_WORKPLACE` 류 generic 단일축 promoted 실재). **`OHS_ENABLE_ATTACH_CACHE`를 켜기 전 전제**로: (a) `promote()`/`record_link()`에서 generic 단일축 code_sig(work_context.* 단독, no-risk alias) 배제 또는 임계 상향(domain-guard "broad feature alone cannot create top procedure" 원칙 적용), (b) recorder의 semantic path를 WS-GATE-3의 domain-disjoint 배제로 라우팅, (c) promoted 전 최소 reasoner consistency(owl:Nothing) 통과 요구, (d) 테스트 코퍼스가 promoted 단일축 work_context link 0건임을 회귀 assert. **DECISION: 캐시 read-path를 enable할지/언제 할지 사용자 결정(현재 의도적 dormant).**

---

> 회귀 안전 공통: 코드/스코어링 변경은 `replay_synthetic_observations.py`(2,360 cases) + `regression_gate.py`(tolerance 0.02, **`false_negative_rate` veto 방향이 FN 게이트**) 통과. 온톨로지 변경은 Fuseki Openllet `ASK {?x a owl:Nothing}` 라이브(Openllet lazy prepare≠일관) + `make verify-manifest`/`verify-prefixes` + `check_disjoint_consistency.py`(exit 0). 정밀도 게이트(B1)는 `judge_semantic_attach.py`의 on_score=0 비율 하락 + on_score≥2 rescue 유지로 검증.

---

## WS-OBS — 관측성: 조용한 고장에 신호 붙이기

> 이 워크스트림은 "결과가 틀렸다"가 아니라 **"결과가 조용히 나빠졌는데 아무도 모른다"** 를 막는다. 안전/법률 도메인에서 최악은 false-negative(놓친 위험·검증 전에 버려진 guide)이며, 현재 시스템은 (1) FN을 게이트·baseline·프로덕션 어디서도 측정하지 않고(A3), (2) PG가 죽으면 절반 정확도 fallback으로 조용히 degrade하며(A5), (3) 벡터 인덱스가 비거나 embedding이 실패하면 facet-only로 신호 없이 후퇴하고(B3), (4) embedding pre-filter의 drop-ratio를 보는 주체가 전무하다(B10). 공통 원칙: **degrade를 막는 게 아니라 degrade를 가시화한다.** graceful fallback은 유지하되, 모든 fallback·drop·empty-recall에 신호(WARNING + metric + 응답/health 표식)를 붙인다.

> HARD CONSTRAINT 준수: provenance/source/degraded는 **표시·운영 신호 전용**이며 runtime scoring에 절대 미반영(`provenance는 scoring에 미반영`). 온톨로지=SoT/PG=스냅샷, OWL reasoning은 요청 경로 밖. 회귀 안전: 모든 변경은 `replay_synthetic_observations.py`(2,360) + `regression_gate.py`(tol 0.02)를 통과해야 하며, FN 방향을 올릴 수 있는 변경은 비대칭 게이트로 차단한다.

> 현재 노출도(2026-06 기준): `LLM_RERANK_MODE` 기본값 `off`라 embedding filter는 사실상 dormant(analysis_log 9,721행 중 7,141행 `off_skipped`, drop>0는 16행). 따라서 B3/B10 항목 다수는 **긴급 패치가 아니라 `active` 승격 전 반드시 선행해야 할 예방 계측**으로 스코프한다. 반대로 A3/A5는 지금 켜져 있는 경로(회귀 게이트·penalty fallback)의 공백이므로 우선순위가 높다.

---

### WS-OBS-1 — 회귀 게이트에 positive-only SHE recall을 FN-비대칭 1급 veto 키로 추가 (A3)

`regression_gate.py`가 감시하는 `false_negative_rate`(positive AND should_match_she AND procedures==0 AND actions==0)는 절차가 1건이라도 나오면 FN에서 빠지는 **좁은 정의(baseline 46건)** 라, 실제 SHE 패턴 미매칭(909건, recall ~55%)과 ~20배 다른 별개 지표다. 유일하게 recall에 반응하는 `she_accuracy`는 (a) 2,360건 전체에 희석되고 (b) boolean equality라 negative specificity 개선이 positive recall 회귀를 상쇄하면 위험 방향 회귀가 silently 통과한다.

- **target**:
  - `serving-team/08-app/backend/scripts/replay_synthetic_observations.py` — `evaluate_case`(L147-220)에 `she_recall_miss`(positive AND should_match_she AND NOT she_matched, **절차·조치 유무 무관**) bool 추가; `build_summary`(L249-308)에 `she_recall_miss_rate`(=miss/positive-should-match) + `per_case_type.positive.she_recall`(=TP/(TP+FN)) 키 산출.
  - `serving-team/08-app/backend/scripts/regression_gate.py` — `MAX_RATE_KEYS`에 `she_recall_miss_rate` 추가하고, `compare`(L57-87)에 per-key tolerance를 도입(FN 키는 `recall_tolerance` 기본 0.005, 기존 FP·accuracy 키는 0.02 유지); `positive_she_recall`을 `METRIC_KEYS`(expect_higher)에 추가하되 비대칭 하락 tolerance(≤0.005) 적용.
  - `data-team/05-enrichment/llm-scripts/f3_drift_check.py` — `METRICS` dict의 `false_negative_rate` 라벨을 `"positive인데 무출력(좁은 정의)"`로 정정하고 `she_recall_miss_rate`를 critical-fn 임계 대상에 추가.
- **steps**:
  1. `evaluate_case`에 `she_recall_miss` 계산 추가(이미 `she_matched`/`she_expected` 존재 → `she_expected and not she_matched`). `she_correct`는 손대지 않는다(기존 게이트 무변경).
  2. `build_summary`에 `she_recall_miss_count`/`she_recall_miss_rate`(분모=positive-should-match 모집단)와 `per_case_type["positive"]["she_recall"]` 추가. positive 모집단이 909 정의와 일치하도록 `should_match_she==True`만 분모로.
  3. `regression_gate.compare`를 per-key tolerance 맵으로 리팩터(기존 단일 `tolerance` 인자는 default로 유지, FN 키만 override). `--recall-tolerance` CLI 인자(default 0.005) 추가.
  4. baseline JSON(`replay_baseline.json`/`replay_baseline_v3.json`)에 새 키가 없을 때 `compare`가 KeyError 안 나도록 `baseline.get(key, ...)` 경로 확인(이미 `.get` 사용). 단, 새 키 baseline 값은 한 번 `--save-baseline` 재생성으로 채운다.
  5. `f3_drift_check`의 FN 라벨 정정 + 신규 키 verdict 분기 추가.
- **verification**:
  - `make f1-regression`(= replay 2,360 + `regression_gate.py /tmp/replay_f1.json`) → 새 키 포함 PASS 확인.
  - **FN-direction 증명**: `she_recall`을 의도적으로 떨어뜨리는 mutation(예: `she_matcher`에서 한 패턴 임시 비활성)으로 replay 재실행 → `regression_gate`가 `positive_she_recall`/`she_recall_miss_rate` 단독으로 `exit 1` veto하는지 확인(0.005 초과 시). 동시에 negative specificity를 올려 `she_accuracy`를 보존시키는 mutation에서도 veto가 떨어지는지(상쇄 악용 차단) 확인.
  - 무회귀: mutation 없이 동일 코드 replay 시 `delta≈0`, PASS.
- **rollback**: `regression_gate.py`/`replay_synthetic_observations.py`/`f3_drift_check.py` 세 파일 revert. baseline JSON은 generator 재실행으로 복원(수동 편집 금지 — 자동 산출물). 신규 키는 게이트가 `.get(key,0)`로 안전 무시.
- **closesRisks**: A3
- **severity**: high · **phase**: 1 · **effort**: S
- **dependsOn**: 없음
- **decisionNeeded**: `recall_tolerance` 값(0 vs 0.005). 권장 0.005(replay 비결정성·LLM 호출 없는 합성 경로라 사실상 결정적이지만 ε 여유). 0으로 두면 어떤 미세 회귀도 hard-veto — 안전 최대화하나 false-alarm 위험. **사용자 결정 필요.**

---

### WS-OBS-2 — baseline.md에 "Layer1-3 metric, Vision FN excluded" 캐비엇 명시 (A3)

정본 `54.9% SHE recall`은 `build_fake_result`(replay L91-144)가 case의 `expected_features`를 confidence 0.9로 주입하므로 **Vision이 완벽하다고 가정한 Layer1-3 지표**다. 가장 위험한 FN(Vision 누락·오인)은 구조적으로 측정 불가(v1~v10 SHE FN=0이 그 증거). headline 지표가 end-to-end 안전 recall로 오해되면 defensibility를 해친다.

- **target**: `docs/status/evaluation-baseline.md` — `54.9%` 라인(L959) 인접, per-version SHE-recall 표(L999-1014) 인접. (이 문서는 baseline 정본이며 **수동 산출이 아닌 prose 문서**라 직접 편집 허용 — generator 산출물 아님.)
- **steps**:
  1. L958-959 블록 위/아래에 캐비엇 박스 추가: "이 SHE recall/FN/FP는 **Layer 1-3 한정** 지표로, replay가 `expected_features`를 ground truth로 주입(`replay_synthetic_observations.py:91-144 build_fake_result`)하기 때문에 **Vision(Layer 0) false-negative는 구조적으로 제외**된다. 따라서 end-to-end 안전 recall이 아니다."
  2. L999-1014 표 캡션에 "SHE FN=0 across all versions는 Vision-perfect 가정의 산물"이라는 각주 추가, replay docstring로 cross-link.
  3. WS-OBS-3(prod FN proxy)·WS-EVAL gold-set 항목으로 forward-link(end-to-end recall은 거기서 측정).
- **verification**: 문서 리뷰 + `make verify-manifest`(문서 링크 무결성 게이트가 있으면)·markdown 링크 깨짐 없음. 코드 무변경이라 replay/게이트 회귀 N/A.
- **rollback**: 문서 diff revert(저위험·additive).
- **closesRisks**: A3
- **severity**: medium · **phase**: 0 · **effort**: S
- **dependsOn**: 없음
- **decisionNeeded**: 없음

---

### WS-OBS-3 — analysis_log.jsonl 경량 프로덕션 집계기 + 추세-델타 알람 (A3)

프로덕션에서 `_append_analysis_log`는 capture만 하고 "위험을 놓쳤다"는 신호로 전환되는 메커니즘이 없다. drift 알람은 합성 replay에서만 돈다. `eval_real_photos_day6.py`/`auto_register_aliases.py`는 log를 읽지만 alias 비교·mining 용도일 뿐 **she_match_count==0 추세·drop-ratio·miss-suspect를 집계하는 모니터는 전무**다.

- **target**:
  - 신규 스크립트 `data-team/05-enrichment/llm-scripts/analysis_log_monitor.py`(f3_drift_check.py의 JSON/exit-code/slack-hook 패턴 재사용).
  - 입력: `data-team/05-enrichment/runtime-artifacts/analysis_log.jsonl`. 출력: `analysis_log_monitor_log.jsonl`(시계열) + stdout 표 + exit code(0/1/2).
  - Makefile `obs-prod-monitor` 타깃 추가(`f3-drift-check` 인접).
- **steps**:
  1. 로그를 읽어 윈도우(예: 직전 N행 vs 그 이전 N행)별로 산출: ① `she_match_count==0` 비율, ② `normalizer_unknown_codes` 평균/스파이크, ③ **miss-suspect 비율 = `candidate_count>0 AND she_match_count==0`**(후보는 있었으나 SHE 매칭 실패 → 진짜 miss 우선순위), ④ mode별 분리(`off_skipped_*`는 정상 경로이므로 raw 카운트가 아닌 분포 delta만 알람).
  2. 알람은 **추세-델타** 기준(절대 임계 아님 — she_match_count==0의 ~35%는 정상 '위험 없음'이라 raw 알람은 fatigue): 직전 baseline 윈도우 대비 miss-suspect rate가 tolerance 초과 상승 또는 normalizer_unknown spike 시 exit 1/2.
  3. f3_drift_check의 `_maybe_rel`/`DRIFT_LOG` append/`--json` 출력 패턴 그대로 차용. cron weekly 가정.
- **verification**:
  - 합성 검증: 알려진 분포의 jsonl fixture로 `analysis_log_monitor.py --json` 실행 → miss-suspect rate/exit code가 기대값과 일치(단위 테스트).
  - 실로그 smoke: 현재 `analysis_log.jsonl`에 대해 실행 → off_skipped 73%를 정상 분류하고 false-alarm 없이 baseline 산출.
  - **FN-direction**: miss-suspect rate를 인위적으로 올린 fixture(candidate_count>0 & she=0 행 다수 append)에서 exit≥1 발생 확인.
  - 코드 경로 무변경(읽기 전용 스크립트)이라 replay 게이트 회귀 영향 없음.
- **rollback**: 신규 스크립트·Makefile 타깃 삭제(서빙 경로 무영향, 순수 additive).
- **closesRisks**: A3
- **severity**: high · **phase**: 1 · **effort**: M
- **dependsOn**: WS-OBS-4 (per-stage drop attribution 필드가 있으면 miss-suspect를 normalizer-0축 vs SHE-threshold vs gate-reject로 더 정밀 분해 가능 — soft dep, 없어도 candidate_count 기반 1차 동작)
- **decisionNeeded**: 알람 채널(slack webhook vs exit-code-only cron 로그). 권장 exit-code + JSON 산출(기존 f3 패턴), slack은 후속.

---

### WS-OBS-4 — `_append_analysis_log`에 per-stage drop attribution 필드 추가 (A3)

909 FN의 책임 소재(normalizer 0축 / SHE threshold 0후보 / observable·actionable 게이트 reject)를 런타임에서 구분·로깅하지 않아 사후 진단이 불가능하다. 이건 909 FN을 분해해 어느 단계를 고칠지 결정하기 위한 **전제**이자 safety-audit defensibility 항목이다(additive log 필드, behavior 무변경).

- **target**:
  - `serving-team/08-app/backend/app/services/analysis_pipeline.py` — `_append_analysis_log`(L1019-1093) entry dict(L1066-1088)에 attribution 필드 추가; 호출부 `_apply_llm_rerank`(L922-934)·`_log_skipped_analysis`(L1000-1012)에 인자 전달.
  - 데이터 출처: `knowledge.canonical`(accident/agent/context 축), `knowledge.she_matches`(상태 분포), `observable_violation_signal`/`actionable_matches`(게이트 결과 — 단, 이 둘은 현재 log 호출 시점 scope 밖이므로 `knowledge` dataclass에 carry 필요).
- **steps**:
  1. `AnalysisKnowledgeContext`(L70-)에 `observable_violation_signal: bool`, `actionable_match_count: int`, `she_status_breakdown: dict`(confirmed/candidate/context_only/review_candidate 카운트) 필드 추가, `run`(L232-250)에서 채움.
  2. `_append_analysis_log` entry에 `normalizer_axis_counts`(accident/agent/context 각 len), `she_returned_empty`(she_matches==[] bool), `she_status_breakdown`, `observable_violation_signal`, `actionable_match_count` 추가.
  3. attribution 라벨 파생: `drop_stage` ∈ {`normalizer_zero_axis`, `she_empty`, `she_nonactionable_only`, `gate_rejected`, `served`} 단일 필드로 요약(monitor가 바로 소비). **scoring·응답에 영향 없음**(log 전용).
  4. `_log_skipped_analysis`는 early-return 경로라 일부 필드 N/A → 0/false 기본.
- **verification**:
  - replay 2,360 실행 후 `analysis_log.jsonl` 신규 행에 attribution 필드 존재 + `drop_stage` 분포가 baseline stage-failure 표(stage3=1,288 등)와 정성적으로 정합 확인.
  - **무회귀(필수)**: `make f1-regression` → she/sr/penalty/overall accuracy + FN 키 모두 `delta≈0`(순수 additive log, scoring 무변경 증명).
  - log 필드 추가가 응답 직렬화에 누출 안 됨 확인(`AnalysisResponse`에 미추가).
- **rollback**: entry dict 신규 키 제거 + dataclass 필드 제거. 서빙 응답 무관(log only)이라 안전.
- **closesRisks**: A3
- **severity**: medium · **phase**: 1 · **effort**: M
- **dependsOn**: 없음
- **decisionNeeded**: 없음

---

### WS-OBS-5 — penalty/profile/incompat 로더에 responding-source 스탬프 + fallback WARNING/metric (A5)

`_load_penalty_index`(TTL fallback, 정확도 0.4551→0.1835로 절반↓), `_load_manual_profiles`(JSON fallback), `shadow_reasoner._load_axioms`(JSON fallback) 셋 다 PG 실패를 조용히 삼키고 `logger.info(...fallback)` 한 줄만 남긴다. 어느 경로가 응답했는지 응답에 표식이 없어, PG가 잠깐 죽으면 **법적으로 load-bearing한 penalty 3경로가 <50% 정확도 답으로 silently degrade**한다. `enrich_sr_with_sparql`의 `source:"pg_only"/"pg+sparql"` 패턴(hazard_rule_engine.py:847-858)을 재사용한다.

- **target**:
  - `serving-team/08-app/backend/app/services/hazard_rule_engine.py` — `_load_penalty_index`(L1035-)·`_load_penalty_index_from_pg`(L995-). 모듈 전역에 `_PENALTY_INDEX_SOURCE` 스탬프(`"pg"|"ttl_fallback"|"empty"`) 기록, fallback 진입 시 `logger.warning`(현 L1067 info→warning 승격).
  - `serving-team/08-app/backend/app/services/guide_domain_profile.py` — `_load_manual_profiles`(L469-483)에 `_PROFILE_SOURCE` 스탬프 + JSON fallback WARNING.
  - `serving-team/08-app/backend/app/services/shadow_reasoner.py` — `_load_axioms`(L115-121) JSON fallback은 이미 WARNING(L65,69) 있음 → source 스탬프만 모듈 전역에 노출.
  - `serving-team/08-app/backend/app/models/hazard.py`(`ReasoningTrace`) 또는 `AnalysisResponse`에 **display-only** `data_sources: dict`(예: `{"penalty":"ttl_fallback"}`) 필드 추가.
- **steps**:
  1. 각 로더가 사용한 source를 모듈 전역/싱글톤 속성으로 기록하는 getter(`get_penalty_source()` 등) 추가.
  2. fallback 진입 로그를 `logger.warning`으로 승격(penalty 우선). penalty의 TTL fallback은 `logger.error` 레벨 검토(정확도 절반↓·법적 출력).
  3. `analysis_pipeline.run`에서 응답 조립 시 세 getter를 모아 `AnalysisResponse.data_sources`(display-only)로 surface. **scoring·routing에 절대 미사용**(HARD CONSTRAINT: provenance는 scoring 미반영).
  4. (옵션, decisionNeeded) penalty PG-load 실패를 hard-error로 — "penalty unavailable + provenance" 반환 vs 저정확도 TTL 서빙. WS-OBS-6 health 게이트와 연계.
- **verification**:
  - 단위: PG 세션을 mock으로 실패시켜 `_load_penalty_index`가 `_PENALTY_INDEX_SOURCE=="ttl_fallback"` + `logger.warning` 발생 확인.
  - 통합: replay 한 케이스에서 `response.data_sources["penalty"]`가 정상 시 `"pg"` 표식 확인.
  - **무회귀(필수)**: `make f1-regression` → `penalty_accuracy`(0.4551) 등 전 키 `delta≈0`. data_sources는 display-only라 scoring 무영향 증명. `make phase-g-verify`(sample_query_equality)로 PG/fallback 동등성 샘플 유지.
- **rollback**: source 스탬프/warning/`data_sources` 필드 revert. fallback 동작 자체는 무변경이라 안전.
- **closesRisks**: A5
- **severity**: high · **phase**: 1 · **effort**: M
- **dependsOn**: 없음
- **decisionNeeded**: penalty PG-load 실패 처리 정책 — **옵션 A**: 저정확도 TTL fallback 계속 서빙 + degraded 표식(현 동작 + 가시화), **옵션 B**: penalty 패널만 "산출 불가 + provenance" hard-fail(FN-보수적: 틀린 법적 답보다 무답이 방어 가능). 권장 B(법적 출력), 단 다른 패널(SHE/guide)은 계속 서빙. **사용자 결정 필요.**

---

### WS-OBS-6 — startup/health active probe: penalty_index/profile/axiom이 PG에서 로드됐는지 능동 확인 (A5)

현재 `/api/v1/health`(health.py L6-8)는 `{"status":"healthy"}` 고정 stub이라 벡터·PG 로더 상태와 무관하다. `main.py` lifespan은 Fuseki만 probe하고 penalty/profile/axiom의 PG 로드 성공을 능동 확인하지 않는다 → 첫 user request에서 lazy degrade.

- **target**:
  - `serving-team/08-app/backend/app/main.py` — `lifespan`(L16-64)에 PG 로더 active probe 추가(Fuseki probe L53-62 인접).
  - `serving-team/08-app/backend/app/api/v1/health.py` — static stub을 로더 source/count 블록 반환으로 확장.
- **steps**:
  1. lifespan에서 `_load_penalty_index()`/`_load_manual_profiles()`/`shadow_reasoner._ensure_loaded()`를 호출해 source를 확인하고, fallback이면 `logger.warning`(boot-time, per-request 아님)으로 명시. PG 미로드 시 degraded mode 플래그를 app.state에 기록.
  2. `/api/v1/health`(또는 신규 `/api/v1/diag`)가 `{penalty:{source,count}, profile:{source,count}, axiom:{source,count}, degraded: bool}` 반환 — uptime monitor/airgap 운영자가 "PG 죽음 vs 정상"을 구분.
  3. degraded면 health status를 `"degraded"`로(단 200 유지 — graceful, hard-fail 안 함; HARD CONSTRAINT: serving 차단 금지).
- **verification**:
  - PG 정상 부팅 시 `/api/v1/health` → 세 source 모두 `"pg"`, degraded:false.
  - PG mock 실패 부팅 → lifespan WARNING 로그 + health degraded:true + 해당 source `ttl_fallback`/`json_fallback`.
  - **무회귀**: 서빙 요청 경로 무변경(probe는 boot/health 전용) → `make f1-regression` delta≈0.
- **rollback**: lifespan probe 블록 + health 확장 revert → 기존 static stub 복원.
- **closesRisks**: A5
- **severity**: high · **phase**: 1 · **effort**: S
- **dependsOn**: WS-OBS-5 (source 스탬프 getter가 선행돼야 health가 source를 읽음)
- **decisionNeeded**: 없음

---

### WS-OBS-7 — 벡터 recall 경로 degrade 가시화: health 카운트 + startup probe + facet(hybrid_unavailable) 표식 (B3)

`OHS_ENABLE_HYBRID_SEARCH` on 상태에서 ChromaDB `ohs_*` 컬렉션이 비거나(airgap bind-mount 실패) embedding이 실패하면 semantic recall이 facet-only로 **에러·health 신호 없이** 후퇴한다(`hybrid_search._vector_rank` count==0 시 `[]`, `_semantic_*_candidates` 예외 시 `return []`). 운영자는 "추천이 약함"과 "인덱스가 죽음"을 구분 못 한다. (precision-half인 npz-passthrough는 `LLM_RERANK_MODE=off`에서 inert이므로 이 항목은 **live recall 경로만** 스코프.)

- **target**:
  - `serving-team/08-app/backend/app/main.py` — `lifespan`에 `OHS_ENABLE_HYBRID_SEARCH` true 시 `get_index("ohs_guide_section").count()` + `get_index("ohs_ci_raw").count()` 확인, 0이면 명시 ERROR/WARN(기존 legacy-index 로그와 구분).
  - `serving-team/08-app/backend/app/api/v1/health.py` — `vector_index` 블록(per-collection count + `degraded:true` when 필수 ohs_* empty).
  - `serving-team/08-app/backend/app/services/hazard_to_guide_service.py` — semantic recall이 `[]`인데 facet fallback이 진행되는 경로(`_semantic_guide_candidates` L292-293 / 호출부 L635-642)에서 `attach_method`를 `"facet(hybrid_unavailable)"`로 구분 set(현 `"facet"`는 semantic ∅과 인덱스-죽음을 동일 취급); empty-rows 분기에 1줄 WARN 추가.
  - `serving-team/08-app/backend/app/services/hybrid_search.py` — `_vector_rank`(L88-95) count==0/embed-fail `[]` 분기에 WARN(현재 embed-fail만 WARN, count==0은 무로그).
  - `serving-team/08-app/deploy/airgap/load_and_up.sh` — bind-mount 후 count-probe verify 스텝 추가, 0이면 fail-loud.
- **steps**:
  1. lifespan startup probe(상기). `is_available()`/count() distinct로 "인덱스 없음 at boot"를 per-request 전에 노출.
  2. health에 `vector_index` 블록 + degraded 플래그.
  3. `attach_method`에 `facet(hybrid_unavailable)` 분기: semantic_on인데 recall `[]`이고 인덱스 count==0일 때만(정상 semantic ∅과 구분). WS-OBS-3 monitor가 이 표식을 집계.
  4. `_semantic_*_candidates` empty branch + `hybrid_search._vector_rank` count==0 branch에 WARN 1줄.
  5. `load_and_up.sh`에 `docker compose exec backend python -c "...count probe..."` 또는 별도 verify 스크립트 호출, 0 컬렉션 시 `exit 1` + 안내. `deploy/server/README.md` "추천 결과 빈약" 트러블슈팅에 vector-index count 포인터 추가.
- **verification**:
  - 빈 ChromaDB로 부팅 → lifespan ERROR + `/api/v1/health` vector_index degraded:true.
  - 정상 인덱스 → counts>0, degraded:false.
  - **FN-direction**: 인덱스를 비우고 한 analysis 요청 → relation `attach_method=="facet(hybrid_unavailable)"` + WARN 로그 + (WS-OBS-3 monitor가 이 표식 비율 추세 알람). graceful fallback(서빙 안 죽음) 유지 확인.
  - **무회귀**: 정상 인덱스에서 `make f1-regression` delta≈0(표식·WARN은 scoring 무영향).
  - airgap: `load_and_up.sh`를 빈 tar로 실행 → count-probe가 fail-loud.
- **rollback**: 각 파일 degrade-가시화 코드 revert. fallback 동작은 무변경이라 서빙 안전.
- **closesRisks**: B3
- **severity**: medium · **phase**: 1 · **effort**: M
- **dependsOn**: WS-OBS-6 (health 확장 인프라 공유)
- **decisionNeeded**: 없음

---

### WS-OBS-8 — embedding pre-filter drop-ratio 모니터(over-drop / degenerate 이중 알람) — `LLM_RERANK_MODE=active` 승격 전제조건 (B10)

`FilterResult.reduction_ratio`(guide_embedding_filter.py:64-69)는 정의돼 있으나 **호출처가 전무**하고, drop bucket(cosine<0.25)은 LLM 게이트를 건너뛰므로 over-aggressive threshold나 stale/dim-mismatch npz가 관련 guide를 **검증 없이 silently drop**(FN)해도 알람이 없다. 현재는 `mode=off`라 dormant이지만, `active` 광범위 활성화 순간 recall이 신호 없이 붕괴할 수 있다.

- **target**:
  - WS-OBS-3의 `analysis_log_monitor.py`를 확장(또는 동일 스크립트 내 drop-ratio 섹션) — `data-team/05-enrichment/runtime-artifacts/analysis_log.jsonl`의 `filter_keep/gray/drop`(이미 기록됨, analysis_pipeline.py:1073-1075) 소비.
  - `serving-team/08-app/backend/app/services/guide_embedding_filter.py` — `_try_load`(L106-156) 직후 npz `metadata`(dim/model/build_ts/guide count) 일관성 assert(dim==런타임 scene-embedding 모델 dim) 추가.
- **steps**:
  1. monitor에서 shadow/active 행만 필터(off_skipped 제외)해 mode별 `mean(filter_drop/candidate_count)` + 추세 산출.
  2. **두 가지 실패 형태 분리 알람**: (a) over-drop — mode-mean > 0.3 또는 단일 scene 대량 drop; (b) degenerate/dormant — active 행이 누적되는데 drop_ratio가 ~0으로 붕괴(stale/passthrough 인덱스 또는 mistuned threshold 신호).
  3. drop bucket이 LLM 미검증이므로, 0.25 경계 근방(±0.02) drop된 `(guide_code, similarity)` 샘플을 spot-audit용으로 surface.
  4. `guide_embedding_filter._try_load`에 dim/model/build_ts 메타 검증 — 불일치 시 dot-product 루프 진입 전 fail-loud(logged/alerted degrade, mid-request numpy 에러 방지).
  5. **게이팅**: 이 monitor 존재를 `LLM_RERANK_MODE=active` 활성화의 전제조건으로 문서화(`docs/`·runbook). active 승격 PR이 이 항목 dependsOn.
- **verification**:
  - 합성 fixture(active 행 + drop_ratio 0.5)로 monitor 실행 → over-drop 알람 exit≥1; drop_ratio 0 fixture → degenerate 알람.
  - npz dim mismatch fixture로 `_try_load` → fail-loud(passthrough로 조용히 안 빠짐).
  - **FN-direction**: 경계 근방 drop 샘플이 audit 출력에 나타나는지 확인(unreviewed FN 가시화).
  - 현재 prod 무영향(off 기본) — 읽기 전용 monitor + load-time assert라 서빙 경로 무변경, `make f1-regression` delta≈0.
- **rollback**: monitor의 drop-ratio 섹션 + `_try_load` assert revert. assert는 fail-loud→기존 passthrough로 복원 가능(단 stale 인덱스 silent risk 재현).
- **closesRisks**: B10, B3(partial — dim-mismatch fail-loud 공유)
- **severity**: medium · **phase**: 2 · **effort**: M
- **dependsOn**: WS-OBS-3 (동일 monitor 인프라 확장)
- **decisionNeeded**: over-drop mode-mean 임계(0.3은 placeholder) — gold-set 기반 PR 곡선(WS-EVAL)으로 데이터 확정 권장. 임시값으로 착수하되 곡선 확보 후 재튜닝. (gold-set 의존이라 phase 2)

---

### 의존성 요약

- WS-OBS-1·2·4는 독립 착수 가능(phase 0~1, 빠른 가시화).
- WS-OBS-5 → WS-OBS-6 (source 스탬프 → health probe).
- WS-OBS-6 → WS-OBS-7 (health 인프라 공유).
- WS-OBS-3 → WS-OBS-8 (monitor 인프라 → drop-ratio 확장).
- WS-OBS-4 → WS-OBS-3 (soft: attribution 필드로 miss-suspect 정밀화).
- WS-OBS-8은 `LLM_RERANK_MODE=active` 프로덕션 승격(다른 워크스트림 결정)의 **선행 전제조건**으로 게이팅.

---

## WS-PROV — 출처/근거 태깅: 약한 근거를 약하다고 표시

### 배경 / 문제 한 줄 요약

이 워크스트림은 **서빙 응답의 per-answer 근거(provenance)와 신뢰도(confidence)를 "표시(display)"하는** 3개 갭을 닫는다. 모두 false-negative(놓친 위험)가 아니라 **방어성(defensibility) / 감사성(auditability)** 결손이며, 산업안전·법령 도메인에서 "약한 근거가 강한 근거처럼 보이는" 문제다.

- **A3-05(display 부분)** — 온톨로지 룰이 *추론*한 위험요소(예: `SCAFFOLD → +FALL`)와 GPT가 *직접 관찰*한 위험요소가 응답·트레이스에서 구분되지 않는다. `apply_rules`가 만든 `applied_rules`와 shadow_reasoner의 `reasoner_rejects`가 `analysis_log.jsonl`에만 남고 사용자/감사자 트레이스에 도달하지 않는다.
- **A1-F3(A12)** — GPT per-observation/per-candidate confidence가 normalizer·rule engine을 지나며 "코드 개수 기반 스칼라"로 평탄화된다. PenaltyPath/Finding에 `evidence_confidence`가 없어, *수치상 저신뢰*하지만 *문장은 단정적*인 관찰이 conditional penalty 안내를 구동해도 그 약함이 표면화되지 않는다(lexical UNCERTAINTY_TERMS gate만 존재).
- **B7(V2-3)** — ChromaDB 임베딩 fuzzy 매치로 부착된 guide가 `standard_procedures` 패널에서 결정적 SHE/규칙 매치와 동일한 'PG Guide(검증됨)' badge로 렌더된다. `_build_standard_procedures`가 `mapping_type`을 버려(L373에서 dict엔 담기지만 모델로 전파 안 됨) `hybrid_semantic`/`hybrid_cache` 부착을 "검증된 것"으로 위장한다.

### 불변 제약 (전 항목 공통)

> **provenance/confidence는 DISPLAY 전용. scoring·relevance·정렬에 절대 반영 금지** (`docs/architecture/source-provenance.md:155` — "The OHS recommendation score must not use provenance directly"). 모든 WS-PROV 변경은 **응답 점수/순서가 byte-identical**임을 증명해야 채택된다. FN(놓친 위험) 방향으로의 회귀 가능성이 없는 순수 가산(additive) 변경이며, A1-F3의 numeric discount만 *suspected→needs_clarification* 한 방향(보수적·FN을 늘리지 않는 격하)으로 동작한다.

> **Replay 특이성**: `replay_synthetic_observations.py`는 candidate를 confidence 0.9로 주입하고 `hazards[]`를 주입하지 않는다 → 임베딩 semantic-attach 경로(B7)는 replay에서 휴면이고, 모든 candidate가 0.5 floor 위(A1-F3)다. 따라서 replay/regression_gate 통과는 "무회귀"를 보이지만 "표시 정확성"은 증명하지 못한다 → **별도 hazards 주입 smoke 테스트**로 표시 정확성과 점수 byte-identity를 함께 증명한다.

---

### WS-PROV-1 — RiskFeature origin('gpt_observed' vs 'rule_derived') + ReasoningTrace 추론/정규화 분리 (A3-05 display)

**closesRisks**: A7, A3-05 · **severity**: medium · **phase**: 0 · **effort**: M

가장 값이 크고 위험이 낮은 fix를 먼저. (1) `RiskFeature`(app/models/hazard.py)에 `origin: str = "gpt_observed"` 필드 추가. (2) `_build_risk_features`(analysis_pipeline.py:459)에서 `canonical['applied_rules']`의 `R-cross:/R-exclude:` 문자열을 파싱(또는 `apply_rules`를 `derived_codes:set` 구조 반환으로 보강 — 권장)해 룰이 *추가한* 코드를 `origin='rule_derived'`로 마킹. (3) `_build_reasoning_trace`(analysis_pipeline.py:656)에 `applied_rules`와 shadow_reasoner `rejects`를 인자로 전달(현재 미전달) → `ReasoningTrace`에 `applied_rules: List[str]`, `reasoner_rejects: List[dict]` 가산. (4) 프론트 `ReasoningTracePanel.tsx`에서 risk_feature 라벨을 origin에 따라 `[추론]` vs `[정규화]`로 분기, applied_rules/rejects를 별도 줄로 표시.

**target**:
- `app/models/hazard.py` — `RiskFeature`(L28-33)에 `origin` 필드; `ReasoningTrace`(L101-109)에 `applied_rules`, `reasoner_rejects` 필드
- `app/services/analysis_pipeline.py` — `_build_risk_features`(L459-477), `_build_reasoning_trace`(L656-680) 시그니처에 `applied_rules`/`rejects` 추가, 호출부(L138-147)에서 `knowledge.canonical.get('applied_rules')` 전달
- `app/services/hazard_rule_engine.py` — `apply_rules`(L164-256): `result`에 구조적 `derived_codes`(rule이 추가한 코드 집합) 추가(문자열 파싱 회피용, 권장)
- `app/services/shadow_reasoner.py` — `shadow_validate`(L186) 반환 `rejects`를 knowledge에 보존
- frontend `src/components/results/ReasoningTracePanel.tsx`(L16-23 첫 TraceBox), `src/types/analysis.ts`(`RiskFeature` L23-29, `ReasoningTrace` L96-105)

**decisionNeeded**: 없음 (origin은 추가 표시 필드이며 라우팅 변경 아님). 단, `rule_derived` 항목을 confirmed-status/penalty 라우팅에서 별도 취급할지는 **WS 범위 밖**(여기선 표시만).

**verification**:
- 단위: `tests/unit/test_risk_feature_origin.py`(신규) — `apply_rules`에 `work_contexts=['SCAFFOLD']` 입력 → 결과 RiskFeature 중 `FALL`이 `origin=='rule_derived'`, 입력 그대로인 코드는 `'gpt_observed'`임을 assert.
- 무회귀(점수): `python scripts/replay_synthetic_observations.py` → `python scripts/regression_gate.py current.json --tolerance 0.02` exit 0. origin은 가산 필드라 `she/sr/penalty_accuracy`·`false_negative_rate` 불변.
- 표시 byte-identity: WS-PROV-4의 smoke가 origin 추가 전/후 응답의 **scoring 필드(relevance_score, penalty 순서, finding_status)** 가 동일함을 assert.

**dependsOn**: 없음

**rollback**: `origin` 기본값 `'gpt_observed'`, `ReasoningTrace` 신규 필드 기본 `[]` → 필드 추가 자체가 하위호환. 프론트 분기 revert 시 모두 `[정규화]`로 복귀. 단일 커밋 revert로 안전.

---

### WS-PROV-2 — evidence_confidence on PenaltyPath/Finding + 저신뢰 근거 badge + numeric→needs_clarification discount (A1-F3 / A12)

**closesRisks**: A12, A7 · **severity**: medium · **phase**: 1 · **effort**: L

코드-개수 confidence를 *덮어쓰지 않고*(추출 완전성 지표로 보존), per-observation/per-candidate numeric confidence의 **min/mean 집계**를 canonical에 별도 보존. (1) normalizer(hazard_normalizer.py:369-374)가 candidate `confidence`를 버리지 않고 코드별로 보존(현재 `axis`+`text`만 읽음). (2) `_build_risk_features`가 집계 confidence를 RiskFeature로 운반. (3) `PenaltyPath`(hazard.py:89-98)·`Finding`(hazard.py:47-54)에 `evidence_confidence: Optional[float]` + `low_confidence_basis: bool` 가산, 기여 관찰의 min 집계로 채움. (4) `_finding_status`/`_match_needs_confirmation`(analysis_pipeline.py:706-742)에서 **기여 관찰이 전부 <0.5면** UNCERTAINTY_TERMS 텍스트 없이도 `suspected→needs_clarification`으로 격하(numeric discount, lexical blind-spot 보완). (5) 프론트: `evidence_confidence < floor`인 conditional/suspected 안내에 '저신뢰 근거' badge. **photo_based(visual_score>=0.2 / confirmed) gate는 손대지 않음** — 고노출 경로의 올바른 보호.

**target**:
- `app/services/hazard_normalizer.py` — `normalize_risk_feature_candidates`(L353-375): candidate `confidence` 코드별 보존 맵; `normalize_faceted_hazards`(L378) 통과
- `app/services/hazard_rule_engine.py` — `apply_rules`(L164-256): 코드-개수 `confidence`(L233-243)는 유지하고 `evidence_confidence_agg`(min/mean) 별도 추가
- `app/services/analysis_pipeline.py` — `_build_risk_features`(L459-477) 집계 운반; `_finding_status`(L706-734)·`_match_needs_confirmation`(L736-742) numeric discount; `_build_findings`(L635-654)에 evidence_confidence 채움
- `app/models/hazard.py` — `PenaltyPath`(L89-98), `Finding`(L47-54)에 `evidence_confidence`/`low_confidence_basis`
- `app/services/hazard_rule_engine.py` — `build_penalty_paths`(L1185-1230): conditional tier(L1206)에 evidence_confidence 부착(scoring 미반영, 표시용)
- frontend `src/components/results/`(PenaltyPath/Finding 렌더 컴포넌트) + `SourceBadge.tsx`에 '저신뢰 근거' 표시, `src/types/analysis.ts` `PenaltyPath`(L84-94)/`Finding`(L42-50)

**decisionNeeded**: **저신뢰 floor 값 확정 필요.** 옵션 (a) 0.5(audit 권장, 보수적) — needs_clarification 격하가 더 자주 발생 → FN 안전하나 conditional 안내가 줄어 사용자 노이즈↓; (b) 0.4 — 격하 드뭄, 표시 badge 위주; (c) badge-only(격하 없음, 순수 표시) — 가장 안전하나 lexical blind-spot 미보완. 권장 (a) + step(4) discount 포함. **사용자 product 결정**: numeric discount를 켤지(라우팅에 영향) 순수 표시만 할지.

**verification**:
- 단위/회귀(FN 방향): `tests/unit/test_low_confidence_discount.py`(신규) — 합성 케이스: 기여 관찰 confidence 전부 0.4 + 문장 단정적(UNCERTAINTY_TERMS 미트리거) → 결과 `finding_status=='needs_clarification'`(또는 flagged suspected), unflagged penalty notice 아님을 assert. **역방향(놓침) 증명**: confidence 0.9 케이스는 기존과 동일 status 유지(격하 없음) assert → discount가 강근거를 약화시키지 않음.
- 무회귀(점수): `replay_synthetic_observations.py`(candidate confidence 0.9 → 전부 floor 위 → 격하 0건) + `regression_gate.py --tolerance 0.02` exit 0. `false_negative_rate(0.0436)` 불변 또는 ↓(격하는 over-promote만 억제).
- scoring 불변: WS-PROV-4 smoke가 evidence_confidence 추가 전/후 penalty 정렬·max_severity_score byte-identical assert (evidence_confidence는 scoring 미투입 증명).

**dependsOn**: WS-PROV-1 (RiskFeature 모델 변경과 같은 파일·집계 운반 경로 공유; 순서대로 머지)

**rollback**: `evidence_confidence`/`low_confidence_basis` 기본 `None`/`False`, discount는 floor=0.0(비활성)로 설정 시 no-op. step(4) discount만 별도 flag(`PROV_NUMERIC_DISCOUNT`)로 가드 → 라우팅 영향 즉시 off 가능.

---

### WS-PROV-3 — StandardProcedure mapping_type/provenance 전파 + '임베딩 후보(미검증)' vs '규칙 검증' badge (B7 / V2-3)

**closesRisks**: B7, A7 · **severity**: medium · **phase**: 0 · **effort**: S

**Cheap-first 변형(모델·API 무변경)**: semantic-attach 조립부(analysis_pipeline.py:371-374)에서 evidence_summary에 명시 마커(`[hybrid_semantic]`/`[hybrid_cache]`) prepend → `SourceBadge.tsx`의 `inferProcedureSource`(L73-79)에 임베딩 prefix 인식 분기 + 신규 SourceType `embedding_candidate`(label '임베딩 후보(미검증)') 추가. **Robust 변형(권장·durable)**: `StandardProcedure`(hazard.py:76-86)에 `mapping_type`/`provenance` 필드 추가 → `_build_standard_procedures`(L599-633)에서 `row.get('mapping_type')` 전파(현재 완전 누락) → 프론트가 `hybrid_*`/`cache`는 '임베딩 후보(미검증)', `she_*`/`facet_fusion`/`sr_ci_link`/`asserted`는 '규칙 검증' badge. `GuideProcedurePanel.tsx:14`의 하드코딩 `pg_guide` 헤더 badge도 패널 내 혼합 출처를 반영하도록 제거/동적화. **scoring 미반영**(source-provenance.md:155 준수, 표시 전용).

**target**:
- `app/services/analysis_pipeline.py` — semantic guide_rows 조립(L356-377, 특히 L371-374 evidence_summary 마커 또는 mapping_type 키 보존); `_build_standard_procedures`(L599-633)에서 `mapping_type`/`provenance` 전파(현재 미독취)
- `app/models/hazard.py` — `StandardProcedure`(L76-86)에 `mapping_type: Optional[str]`, `provenance: Optional[str]`(robust 변형)
- frontend `src/components/results/SourceBadge.tsx` — `SourceType`(L17-28)에 `embedding_candidate` 추가, `SOURCE_META`(L30-42)에 '임베딩 후보(미검증)' 항목, `inferProcedureSource`(L73-79)에 `hybrid_*`/`cache` 분기
- frontend `src/components/results/GuideProcedurePanel.tsx`(L14 헤더 badge, L19 `inferProcedureSource` 호출), `src/types/analysis.ts` `StandardProcedure`(L71-82)
- 참조 매핑값(producers): `hazard_to_guide_service.py`(L323/L353 `hybrid_semantic`/`hybrid_cache`), `guide_recommendation_service.py:1772`(`she_sr_wp_guide`), `match_fusion_service.py:171`(`facet_fusion`)

**decisionNeeded**: 없음 (표시 라벨 추가; 라우팅·점수 무변경). 단 cheap vs robust 변형 선택은 구현 판단(권장: robust — `GuideRef`는 이미 mapping_type 보유(types L128), StandardProcedure만 불일치이므로 일관성 위해 모델 필드 추가).

**verification**:
- smoke(핵심 assert): `tests/integration/test_procedure_provenance.py`(신규) — `mapping_type='hybrid_semantic'` guide_row를 주입한 응답에서 해당 StandardProcedure가 프론트 `inferProcedureSource` 기준 **절대 `pg_guide`('검증됨')로 렌더되지 않음**을, 그리고 `she_sr_wp_guide`/`facet_fusion`은 '규칙 검증'으로 렌더됨을 assert (audit V2-3 권장 회귀 가드).
- 무회귀(점수): WS-PROV-4 smoke — mapping_type 전파 전/후 `standard_procedures`의 `confidence`(relevance_score)·정렬 순서가 **byte-identical**(provenance가 점수 미투입 증명).
- replay: `replay_synthetic_observations.py`는 hazards 미주입 → semantic-attach 휴면 → 기존 결과 불변. `regression_gate.py` exit 0.

**dependsOn**: 없음 (WS-PROV-1/2와 독립; 다른 파일 영역)

**rollback**: `inferProcedureSource`에서 임베딩 분기 제거 시 기존 `pg_guide` 폴백으로 복귀. 모델 신규 필드 기본 `None` → 하위호환. evidence_summary 마커는 prefix라 텍스트 표시에 무해.

---

### WS-PROV-4 — Display-only 불변성 증명 harness (scoring byte-identity + 위장-금지 smoke)

**closesRisks**: A7, A12, B7 · **severity**: medium · **phase**: 1 · **effort**: M

WS-PROV-1~3는 모두 "표시만, 점수 무영향"이 채택 조건인데 기존 `replay`는 (a) hazards 미주입으로 semantic-attach·임베딩 경로를 안 타고 (b) origin/provenance 같은 표시 필드를 비교하지 않는다. 이 항목은 **hazards[]를 주입해 임베딩/추론 경로를 실제로 켠 상태에서**, WS-PROV 변경 전/후 응답의 *scoring 부분집합*(relevance_score, penalty 정렬, max_severity_score, finding_status, overall_risk_level)이 **byte-identical**임과, 동시에 *표시 부분집합*(RiskFeature.origin, StandardProcedure.mapping_type/badge, evidence_confidence)이 기대대로 채워짐을 동시에 검증하는 골든 비교 harness를 만든다.

**target**:
- `serving-team/08-app/backend/scripts/prov_display_invariance.py`(신규) — hazards 주입 고정 픽스처(예: SCAFFOLD+FALL, hybrid_semantic guide 포함) N개를 파이프라인에 통과시켜 응답 JSON 생성; baseline JSON과 (1) scoring 키만 추출해 deep-equal assert, (2) 표시 키 존재/값 assert. baseline은 변경 전 커밋에서 1회 생성.
- 참조: `app/services/analysis_pipeline.py` `analyze`(응답 조립 L159-187), `AnalysisResponse.model_dump_json()`(L697 패턴 재사용)
- 게이트 연동: `scripts/regression_gate.py`(L37-46 METRIC_KEYS) 옆에 표시-불변 별도 exit code

**decisionNeeded**: 없음

**verification**:
- self: `python scripts/prov_display_invariance.py --check` → scoring deep-equal 실패 시 exit 1(채택 veto), 표시 필드 미충족 시 exit 2.
- 통합: WS-PROV-1/2/3 각 PR이 이 harness exit 0 + `regression_gate.py --tolerance 0.02` exit 0 둘 다 통과해야 머지(문서 "Regression safety" 규칙 충족).
- FN 방향: harness 픽스처에 confidence 0.4 단정-문장 케이스 포함 → WS-PROV-2 discount가 needs_clarification을 만들되 강근거(0.9) 케이스의 status는 불변임을 동시 assert.

**dependsOn**: WS-PROV-1, WS-PROV-2, WS-PROV-3 (이들의 표시 필드를 검증 대상으로 삼으므로 픽스처/assert는 각 항목과 함께 증분 작성; harness 골격은 선행 가능)

**rollback**: 순수 테스트 스크립트 — 삭제만으로 revert, 런타임 무영향.

---

### 요약 의존 순서

1. **Phase 0 (며칠 가시화·저위험)**: WS-PROV-1(origin), WS-PROV-3(임베딩 badge) — 둘 다 가산 표시 필드, 독립 머지 가능.
2. **Phase 1 (구조적 안전망)**: WS-PROV-2(evidence_confidence + numeric discount, **floor·discount on/off 사용자 결정 필요**), WS-PROV-4(불변성 harness, 전 항목의 채택 게이트).

전 항목 공통 채택 조건: `regression_gate.py --tolerance 0.02` exit 0 **그리고** `prov_display_invariance.py` scoring byte-identity exit 0 (provenance/confidence가 점수에 새지 않았음을 기계적으로 증명).

---

## WS-DRIFT — 드리프트 / 버전 결속 (원본 ↔ DB·색인 어긋남 자동 감지)

### 배경 / 문제 정의

이 시스템의 정본(SoT)은 온톨로지 TTL(`kosha-instances.ttl` 등)이고, 서빙은 그 **특정 시점 스냅샷**인 PG SELECT + ChromaDB 벡터 인덱스로 한다. 그런데 SoT → PG → 벡터인덱스로 내려오는 세 평면이 서로 어긋나도(drift) 이를 **자동 감지하는 게이트가 한 곳도 없다**. 구체적으로:

- **A4 (ontology→PG content drift)**: 모든 import가 `on_conflict_do_update` UPSERT-only라 SoT에서 철회된 사실이 PG에 영구 잔존(스냅샷이 SoT 부분집합이 아니라 누적 합집합). `kosha-instances.ttl`이 현 PG보다 **+23K triple** 드리프트한 것이 무관한 F20 sprint 중 사람 눈에 우연히 발견됐다(`docs/status/current-session.md:48`). 기존 두 "drift" 도구(`f3_drift_check.py`=정확도 회귀 replay, `sample_query_equality.py`=PG↔JSON fallback 동등성)는 둘 다 "PG가 현 온톨로지를 반영하는가"를 보지 않는다.
- **A7-version (provenance/version binding)**: `penalty_rule_index` 등 legal-critical PG 행에 `ontology_commit/ttl_sha/snapshot_id`가 없다(`created_at`은 '언제 적재'일 뿐 '어느 SoT에서'가 아님). 분쟁/감사 시 served answer를 정확한 SoT 리비전으로 재현·증명 불가.
- **B2 (index↔PG revision binding + stale tarball)**: 6개 ChromaDB 컬렉션 metadata가 전부 `{}`, npz에도 PG baseline/git SHA 없음. SSOT 존재검증은 '인덱스엔 있는데 PG엔 없는' over-coverage stale만 거부하고, '인덱스엔 없는 새 PG 항목'은 후보조차 안 돼 침묵 under-coverage(=missed hazard). air-gap 타르볼이 소스 인덱스보다 stale이고 PG dump↔chromadb tar 동기성 매니페스트가 없다.
- **B9 (model pinning + cache key)**: `EMBED_MODEL='text-embedding-3-small'`이 4~5곳에 분산 하드코딩, scene 캐시 키가 `sha256(scene_text)`뿐이라 모델 버전 미포함. 모델 교체/silent 갱신 시 쿼리공간↔인덱스공간이 다른 좌표계에 놓여 cosine이 조용히 망가진다(차원 1536 동일 → 예외 없음).
- **B4-binding (rebuild trigger)**: 인덱스는 오프라인 빌드인데 `hybrid_search()` 공개 wrapper가 `pool` 인자를 `.search`로 forward하지 않아 회수 깊이가 영구 30 고정 — 빌드↔서빙 결속과 rebuild 규율이 함께 비어 있다(깊이 튜닝은 WS-RECALL 소관이나, "어느 PG revision으로 빌드됐나"의 결속은 본 워크스트림).

**SAFETY/LEGAL 도메인 원칙**: 누락된 SoT 사실/색인 미반영 항목 = 조용한 false-negative이고 약한 provenance = 방어성 손상. 따라서 본 워크스트림은 (a) drift를 **strict exit-1 게이트**로 가시화하고, (b) FN을 늘릴 수 있는 prune·floor 변경은 회귀 게이트로 잠그며, (c) 모든 TTL-side 변경은 **생성기 수정**으로만 한다(round-trip 정규화가 무관 트리플을 변형시키는 known hazard — current-session.md:46).

**하드 제약 준수**: 정본=온톨로지·서빙=PG SELECT(ms) 유지(OWL 추론은 요청경로 밖). run_id/snapshot_id/model 스탬프는 전부 **display-only**(scoring 미반영). 자동생성 산출물(export TTL, npz, chromadb)은 수동 편집 금지 — 생성 스크립트를 고친다.

---

### WS-DRIFT-1 — materialization_runs 출처 테이블 + run_id 스탬프(legal-critical 우선) (A7-version)

**closes**: A7-version (A3-02 일부) · **severity**: high · **phase**: 1 · **effort**: M

> 🟡 **부분완료 (2026-06-14, commit `87d9e63`, Track A ② reasoning slice).** `materialization_runs` 테이블이 생성되어 reasoning slice의 PROV run-tracking에 사용됨 — `run_id`, `ontology_commit`(git rev), `source_ttl_sha256`(content-hash), `triple_count`, `status` 캡처 (runs #1-4). **단, 이 stamp는 `sr_inferred_relations` 물질화에 적용됐고, 원래 본 항목의 spec 타깃인 `penalty_rule_index`에는 아직 `run_id` FK가 스탬프되지 않았다** — 그 부분은 TODO. (스키마 컬럼명은 본문 spec의 `ttl_sha256`/`baseline_id`/`started_at` 대신 reasoning slice가 `source_ttl_sha256`/`rule_set`/`status`를 사용 — penalty 확장 시 정합 필요.)

서빙 답변을 정확한 SoT 리비전으로 역추적할 수 있게, 단일 `materialization_runs` 테이블(`run_id`, `ontology_commit`=git rev, `ttl_sha256`, `baseline_id`, `started_at`)을 도입하고 legal-critical 테이블(`penalty_rule_index` 먼저)에 `run_id` FK를 스탬프한다. 서빙 시 사용 행의 `run_id`/snapshot id를 `AnalysisResponse`에 **display-only**로 surface한다(scoring 미반영 — runtime 규칙 준수).

- target:
  - 신규 DDL `serving-team/07-materialization/pg-sync-scripts/schema_materialization_runs.sql` (`materialization_runs` + `penalty_rule_index.run_id` FK 컬럼 ADD)
  - `serving-team/07-materialization/pg-sync-scripts/import_penalty_to_pg.py` — `extract_penalty_rules`(git rev/ttl sha 계산), `upsert_rows`(run insert + row에 run_id 부여; 현재 L113-143)
  - `serving-team/08-app/backend/app/db/models.py` — `PgPenaltyRuleIndex`(+`run_id`), 신규 `PgMaterializationRun`
  - `serving-team/08-app/backend/app/models/analysis.py` — `AnalysisResponse`에 `ontology_snapshot_id: Optional[str] = None`(L89-108, display-only)
  - `serving-team/08-app/backend/app/services/hazard_rule_engine.py` — `_load_penalty_index_from_pg`(L995-1032)가 max(run_id) 라벨을 함께 반환
- steps:
  1. `materialization_runs` DDL 작성(run_id SERIAL PK, ontology_commit/ttl_sha256/baseline_id/started_at). `penalty_rule_index`에 `run_id INTEGER REFERENCES materialization_runs(run_id)` 추가(nullable, 무중단 ALTER).
  2. `import_penalty_to_pg.py`: TTL 경로에서 `git rev-parse HEAD`(또는 TTL 파일의 `git log -1 --format=%H`) + `sha256(TTL bytes)`를 import run마다 1회 계산 → `materialization_runs` insert → 그 run_id를 모든 upsert row의 `run_id`로 세팅(동일 트랜잭션, WS-DRIFT-3의 prune-in-txn과 합류).
  3. SQLAlchemy 모델에 컬럼/테이블 추가, `AnalysisResponse`에 display-only 필드 추가, 서빙이 사용한 penalty 행들의 run_id를 응답에 forward(스칼라/표시용, scoring 로직 미참조 — grep으로 점수 계산에서 미사용 확인).
  4. 동일 패턴을 `articles`/`norm_statements`/`safety_requirements`로 확장은 후속(이 항목은 penalty 우선).
- verification:
  - DB: `import_penalty_to_pg.py --apply` 후 `SELECT count(*) FROM penalty_rule_index WHERE run_id IS NULL` = 0; `materialization_runs`에 ontology_commit이 실제 `git rev-parse HEAD`와 일치(assert 스크립트).
  - 회귀(FN 방향): `make f1-regression`(replay 2,360 + `regression_gate.py` tolerance 0.02) PASS — run_id는 display-only이므로 SHE/SR/penalty accuracy 무변동이어야 함(메트릭 delta=0 확인). scoring 코드에서 run_id 미참조를 `Grep`로 증명.
- rollback: `ALTER TABLE penalty_rule_index DROP COLUMN run_id; DROP TABLE materialization_runs;` + import 스크립트/모델/응답 필드 revert. 컬럼 nullable이라 drop 무손실.
- dependsOn: (없음 — WS-DRIFT-3의 prune과 같은 트랜잭션으로 합치는 것이 이상적이나 독립 착수 가능)
- decisionNeeded: 없음(기본 단일 `materialization_runs` FK 방식 채택; 행별 `commit/sha` 컬럼 분산안은 churn 큼).

---

### WS-DRIFT-2 — ontology_pg_drift_check.py + strict 게이트 + 주간 CI (A4 탐지)

**closes**: A4 (A3-01) · **severity**: high · **phase**: 1 · **effort**: M

술어→jsonb 컬럼 매핑별로 `(guide_code, code)` 페어 집합을 온톨로지측·PG측에서 각각 산출해 **symmetric diff = 0**을 검증하는 신규 `ontology_pg_drift_check.py`를 만든다. 단순 row-count 동등 assert는 매핑 구조(predicate→jsonb)상 불충분. `import_*.py --apply` 직후 비-제로 diff면 exit 1(현 WARN→strict), `make verify-ontology-pg-drift` + 주간 CI에 강제.

- target:
  - 신규 `serving-team/07-materialization/validation-scripts/ontology_pg_drift_check.py`
  - 1차 방어 대상: `serving-team/07-materialization/pg-sync-scripts/import_guide_facets_to_pg.py`의 `PRED_COL`(L34-38: `addressesHazard→addresses_hazard_canonical` 등 3술어→3컬럼) + `build_iri_to_code`(L41-53, SSOT 역변환)
  - `import_domain_incompatibilities_to_pg.py` WARN(L309-311) → exit 1 승격
  - `Makefile` — 신규 `verify-ontology-pg-drift` 타깃, `f3-weekly-cycle`(L345-357) 옆에 등록
- steps:
  1. `ontology_pg_drift_check.py`: derived TTL을 `import_guide_facets_to_pg.py`와 **동일 파서/매퍼**(`build_iri_to_code` 재사용)로 읽어 술어별 `(guide_code, code)` 집합 산출 → PG `kosha_guides`의 해당 jsonb 컬럼을 풀어 동일 집합 산출 → `ontology_set ^ pg_set`(symmetric diff) 계산. diff≠0이면 (어느 쪽에만 있는지) 출력 + exit 1.
  2. penalty 평면도 추가: `import_penalty_to_pg.py`의 추출 로직과 동일 키(`(sr_id, penalty_rule_id)`)로 TTL set vs `penalty_rule_index` set diff.
  3. `import_guide_facets_to_pg.py`에 최소 1차 assert(ontology facet set == PG facet set) 인라인, `import_domain_incompatibilities_to_pg.py:309-311`의 row-count mismatch를 WARN→`sys.exit(1)`로 승격(strict 모드 플래그 `--strict` 기본 on).
  4. `Makefile`에 `verify-ontology-pg-drift` 등록하고 `f3-weekly-cycle`에 1 step 추가(LLM 비용 0).
- verification:
  - `make verify-ontology-pg-drift` exit 0(현 동기 상태). 의도적으로 PG 1행 삭제/추가 후 재실행 → exit 1 + 정확한 diff 출력(양방향 탐지 증명: PG-only 잔존행 **그리고** TTL-only 미적재행 둘 다 잡는지).
  - 회귀: 게이트 자체는 read-only 검증이라 serving 무영향. import 스크립트의 strict 승격은 `--strict`를 끈 dry-run으로 기존 동작 보존 확인 후 켠다.
- rollback: 신규 스크립트/Makefile 타깃 제거, `import_domain_incompatibilities_to_pg.py`의 exit(1)을 WARN으로 환원. import 데이터 변경 없음(검증 전용).
- dependsOn: 없음(WS-DRIFT-3가 prune을 추가하면 이 게이트가 그 효과를 검증).
- decisionNeeded: 없음.

---

### WS-DRIFT-3 — penalty import reconcile/prune (TTL-absent PG 행 in-txn 제거) (A4 잔존행)

**closes**: A4 (A3-03) · **severity**: high · **phase**: 1 · **effort**: M

UPSERT-only가 만드는 "철회된 사실 영구 잔존"을 사용자대면 penalty 경로부터 닫는다. `import_penalty_to_pg.py`에 snapshot-swap reconcile을 추가: TTL key set을 빌드 → **동일 트랜잭션 내**에서 그 set에 없는 PG `(sr_id, penalty_rule_id)` 행을 prune(서빙이 부분 상태를 절대 읽지 않게 load-new-then-prune). 동일 repo 템플릿(`import_ci_sr_link_candidates.py:246` delete-by-method)을 재사용.

- target:
  - `serving-team/07-materialization/pg-sync-scripts/import_penalty_to_pg.py` — `upsert_rows`(L113-143)를 reconcile 트랜잭션으로 확장; prune 템플릿 = `serving-team/08-app/backend/scripts/import_ci_sr_link_candidates.py:241-270`(`_replace_method_rows`)
- steps:
  1. `upsert_rows`를 `engine.begin()` 단일 트랜잭션으로: (a) 새 rows upsert, (b) source key set = `{(r.sr_id, r.penalty_rule_id)}` 계산, (c) `DELETE FROM penalty_rule_index WHERE (sr_id, penalty_rule_id) NOT IN (source set)` — 동일 txn 안에서 swap. (WS-DRIFT-1의 run_id 스탬프와 한 트랜잭션으로 합류.)
  2. dry-run에서 prune 대상 행 수/샘플을 출력(`--apply` 없이는 미실행), `--apply` 시에만 commit.
  3. README의 "옛 행 정리" 선언과 코드 갭 정합화(주석/문서 한 줄 수정 — 자동생성 산출물 아님).
- verification:
  - DB: prune 후 `ontology_pg_drift_check.py`(WS-DRIFT-2) penalty 평면 symmetric diff = 0. 의도적으로 TTL에서 1 rule 제거→재export(생성기 경로)→import 시 해당 PG 행이 사라지는지 확인.
  - 회귀(FN 방향 핵심): `make f1-regression` penalty_accuracy/penalty_fn_rate가 baseline 대비 tolerance 0.02 내 — prune이 **유효 rule을 잘못 지우지 않음**을 증명(FN 증가 0). prune 대상이 0인 동기 상태에서 먼저 적용해 무회귀 확인 후, drift 상태에서 효과 검증.
- rollback: reconcile 블록을 제거하면 즉시 UPSERT-only로 환원. prune은 트랜잭션이라 실패 시 자동 롤백; 운영 안전을 위해 첫 배포는 `--prune` 플래그를 별도로 두고 기본 off로 점진 활성 가능.
- dependsOn: WS-DRIFT-2(diff 게이트가 prune의 정확성 검증자) — 동시 착수 가능하나 검증은 2 선행.
- decisionNeeded: **prune 즉시-삭제 vs soft-deprecate**. 옵션 (A) `DELETE`(완전 스냅샷 동등, 단순) / 옵션 (B) `deprecated_at` 마킹 후 서빙 필터(감사 추적 보존, 컬럼 1개 추가). legal 도메인 감사성 고려 시 (B) 권장하나 서빙 쿼리 1곳 수정 필요 — 사용자 결정 요망.

---

### WS-DRIFT-4 — 빌드→서빙 PG baseline 결속(Chroma/npz 스탬프 + 첫 로드 비교 + 번들 manifest) (B2)

**closes**: B2 (V3-1, V3-6), B4-binding 일부 · **severity**: medium · **phase**: 1 · **effort**: M

벡터 인덱스를 빌드 출처 PG revision에 결속한다. `build_kb_embeddings.py`가 kind별 PG baseline 식별자(row-count + `max(updated_at)` 또는 `(id,updated_at)` 해시)를 **Chroma 컬렉션 metadata와 npz 양쪽**에 스탬프; `HybridIndex`/`GuideEmbeddingFilter` 첫 로드 시 저장값 vs 라이브 PG 비교 → mismatch면 WARN + health flag. 번들 빌드/로드 스크립트가 `manifest.json`(PG baseline id + chromadb tar sha256 + UTC ts)을 방출·검증. Guide-path 침묵 SSOT 거부에 SR-path와 동일 aggregate WARN 추가.

- target:
  - `serving-team/08-app/backend/scripts/build_kb_embeddings.py` — `build_kind`(L119-159), `get_or_create_collection(metadata=...)`(L138), KINDS별 baseline SQL
  - `serving-team/08-app/backend/app/services/hybrid_search.py` — `HybridIndex.collection`(L57-63) 첫 로드 비교; 프로세스-레벨 health flag 모듈변수
  - `serving-team/08-app/backend/app/services/guide_embedding_filter.py` — `_try_load`(L106-156) npz baseline 비교
  - `serving-team/08-app/backend/app/services/hazard_to_guide_service.py` — Guide-path SSOT 거부 L306-307·L343-344에 SR-path(L205-206) 패턴의 aggregate WARN 추가
  - `serving-team/08-app/deploy/server/build_bundle.sh`(L21-23) / `serving-team/08-app/deploy/airgap/build_and_save.sh`(L18-22) — manifest.json 방출
  - `serving-team/08-app/deploy/server/load_and_up.sh`(L26-46) / `serving-team/08-app/deploy/airgap/load_and_up.sh`(L17-21) — restore 후 manifest 비교
- steps:
  1. `build_kb_embeddings.py`: kind별 source 테이블에서 `SELECT count(*), max(updated_at)`(없으면 `md5(string_agg(id||coalesce(updated_at,''),''))`)로 baseline_id 산출 → `get_or_create_collection(metadata={"hnsw:space":"cosine","pg_baseline":..., "built_at":...})`에 기록. npz writer(`build_guide_domain_embeddings.py` L156-170)에도 `pg_baseline`/git sha 추가.
  2. `HybridIndex.collection` 최초 materialize 시 컬렉션 metadata의 `pg_baseline`을 라이브 PG와 비교, 불일치면 `logger.warning` + `hybrid_search._INDEX_HEALTH[col]=stale`. `GuideEmbeddingFilter._try_load`도 동일.
  3. Guide-path: `_semantic_guide_candidates`(L304-307)와 `_cached_guides`(L341-344)의 `if g is None: continue`를 카운트해 루프 후 `rejected_missing>0`이면 SR-path와 동일한 `logger.info/warning` aggregate 로그(침묵 거부 제거).
  4. 번들 스크립트: `build_bundle.sh`/`build_and_save.sh`가 tar 직후 `manifest.json`(pg_baseline, `sha256sum ohs-chromadb.tar.gz`, UTC ts) 작성. `load_and_up.sh`(server)는 restore 후 라이브 PG baseline과 manifest 비교 → mismatch면 loud WARN(airgap은 서버 기존 PG와 manifest의 EXPECTED baseline 비교). 최소 가드: chromadb 소스가 PG dump보다 newer면 빌드 에러/force-rebuild.
  5. rebuild runbook: facet-derivation(`import_guide_facets_to_pg.py`) + `build_kb_embeddings.py`를 한 PG revision으로 묶는 절차를 `docs/status/current-session.md`의 Fuseki rebuild 규율 옆에 기술(문서, 생성물 아님).
- verification:
  - 빌드 후 `chromadb` 컬렉션 metadata에 `pg_baseline` 존재(sqlite 조회). PG에 1행 추가 후 backend 부팅 → 로그에 stale WARN + `/api/v1/health`(WS-DRIFT-6과 합류 시) degraded flag.
  - 번들: `build_bundle.sh` 산출 `manifest.json`의 tar sha256이 실제 tar과 일치; `load_and_up.sh`에서 의도적 baseline 불일치 시 WARN 출력.
  - 회귀: 빌드 metadata 추가는 recall 결과 불변 — `make f1-regression` 무변동(임베딩 벡터/순서 동일). Guide-path WARN은 로그-only, 서빙 결과 무영향.
- rollback: metadata 키/manifest 방출/비교 코드 제거 → 기존 `{}` metadata로 환원(하위호환: 비교는 키 부재 시 skip). 번들 스크립트 revert.
- dependsOn: 없음(WS-DRIFT-5의 model 스탬프와 같은 metadata write 지점을 공유하므로 함께 구현 권장).
- decisionNeeded: 없음(baseline_id 산출식은 `count + max(updated_at)` 기본; 테이블에 updated_at 없으면 content hash로 자동 폴백).

---

### WS-DRIFT-5 — embedding model/dim 중앙화 + 스탬프 + startup 비교 + 캐시 키에 모델 포함 (B9)

**closes**: B9 (V3-4) · **severity**: medium · **phase**: 0 · **effort**: S

`EMBEDDING_MODEL`/`EMBEDDING_DIM`을 `app/config.py` 단일 상수로 중앙화하고 5개 site가 import(분산 리터럴 제거). 빌드 시 model+dim을 Chroma metadata + npz 양쪽에 스탬프, startup에서 저장값 vs 런타임 비교(mismatch=loud WARN + degrade flag, hard-fail 금지). scene 캐시 키 = `sha256(MODEL + '\x00' + scene)`.

- target:
  - `serving-team/08-app/backend/app/config.py` — `Settings`에 `EMBEDDING_MODEL: str = "text-embedding-3-small"`, `EMBEDDING_DIM: int = 1536`
  - import 지점: `app/services/hybrid_search.py`(L32 `EMBED_MODEL`), `scripts/build_kb_embeddings.py`(L40), `app/services/guide_embedding_filter.py`(L35 `DEFAULT_EMBEDDING_MODEL`, L179 캐시키, L192 embed 호출), `data-team/05-enrichment/llm-scripts/build_guide_domain_embeddings.py`(L45), `serving-team/08-app/backend/scripts/reindex_articles.py`(L52-55 collection metadata) + `article_service.py`(L220/371, audit 지목)
  - startup: `serving-team/08-app/backend/app/main.py` `lifespan`(L16-64, Fuseki probe L53-62 옆)
- steps:
  1. `config.py`에 `EMBEDDING_MODEL`/`EMBEDDING_DIM` 추가. 5개 site의 하드코딩 리터럴/env default를 `from app.config import settings; settings.EMBEDDING_MODEL`로 교체(스크립트는 import 경로 보장).
  2. `build_kb_embeddings.py:138` 및 `reindex_articles.py:52` `get_or_create_collection(metadata=...)`에 `{"embedding_model": settings.EMBEDDING_MODEL, "embedding_dim": settings.EMBEDDING_DIM}` 추가(WS-DRIFT-4의 pg_baseline과 동일 dict). npz metadata(이미 `model` 보유)에 `dim` 일관 기록.
  3. `main.py` lifespan에 로드된 각 컬렉션/npz의 저장 model+dim vs `settings.EMBEDDING_MODEL/DIM` 비교 — 불일치 시 `logger.warning("evidence index/model mismatch ...")` + 프로세스 degrade flag(graceful-degrade 유지, hard-fail 금지).
  4. `guide_embedding_filter.py:179` 캐시 키를 `hashlib.sha256((settings.EMBEDDING_MODEL + "\x00" + scene_text).encode()).hexdigest()`로 변경 — 모델 교체 후 옛 임베딩 재사용 차단.
- verification:
  - `Grep`로 `text-embedding-3-small` 리터럴이 config.py 1곳으로 수렴 확인(5 site → 0). 빌드 후 컬렉션 metadata에 `embedding_model`/`embedding_dim` 존재.
  - mismatch 테스트: `OPENAI_EMBEDDING_MODEL`을 다른 모델로 띄워 startup이 loud WARN + degrade flag 세팅(서비스는 계속 기동) 확인.
  - 회귀: model 미변경 정상 경로에서 `make f1-regression` 무변동(캐시 키 변경은 첫 호출 cache-miss 1회만, 결과 동일). 캐시 키에 모델 추가가 동일 모델에서 동일 벡터를 반환함을 단위 확인.
- rollback: config 상수/스탬프/비교/캐시키 변경 revert. metadata 키는 하위호환(부재 시 비교 skip)이라 인덱스 재빌드 불요.
- dependsOn: 없음(WS-DRIFT-4와 동일 metadata write/startup 지점 공유 → 묶어 구현 권장; 단독으로도 가장 작은 phase-0 착수점).
- decisionNeeded: 없음.

---

### WS-DRIFT-6 — startup 벡터 인덱스 health probe + /health degrade 신호 (B2/B9 가시화 wiring)

**closes**: B2 (V3-2 일부, stale flag surfacing) · **severity**: medium · **phase**: 0 · **effort**: S

WS-DRIFT-4/5가 세팅한 stale/mismatch health flag를 운영자가 볼 수 있게 한다. `main.py` lifespan에 서빙 경로가 실제 쓰는 컬렉션(`ohs_guide`/`ohs_guide_section`/`ohs_ci_raw`) count probe + baseline/model flag 집계, 정적 stub인 `/api/v1/health`를 `vector_index` 블록(per-collection count + `degraded:true`)으로 확장.

- target:
  - `serving-team/08-app/backend/app/main.py` `lifespan`(L16-64)
  - `serving-team/08-app/backend/app/api/v1/health.py`(현재 L6-8 정적 `{"status":"healthy"}`)
  - flag 출처: `app/services/hybrid_search.py`(`_INDEX_HEALTH`, WS-DRIFT-4), `guide_embedding_filter` model flag(WS-DRIFT-5)
- steps:
  1. lifespan에 `OHS_ENABLE_HYBRID_SEARCH` true일 때 `get_index('ohs_guide_section').count()` / `get_index('ohs_ci_raw').count()` 호출 — 0이면 명시적 ERROR 로그(legacy 인덱스 로그와 구분).
  2. `health.py`를 `vector_index: {collection: count, baseline_ok: bool, model_ok: bool}` + 상위 `degraded: bool`(어느 required 컬렉션이 empty이거나 baseline/model mismatch면 true) 반환으로 확장.
  3. air-gap 운영자 runbook에 "/api/v1/health degraded 확인" 한 줄 추가(문서).
- verification:
  - 빈 bind-mount로 부팅 → lifespan ERROR 로그 + `/api/v1/health`가 `degraded:true`·count 0 반환. 정상 인덱스에서 `degraded:false`.
  - 회귀: probe는 read-only(count + flag 읽기)라 서빙/정확도 무영향 — `make f1-regression` 무변동. probe 예외는 graceful(WARN)이라 부팅 차단 없음.
- rollback: health.py를 정적 stub로 환원, lifespan probe 블록 제거.
- dependsOn: WS-DRIFT-4(baseline flag), WS-DRIFT-5(model flag) — 두 flag 소비자이므로 그 뒤 착수.
- decisionNeeded: 없음.

---

### 의존/순서 요약

- **Phase 0 (며칠 가시화, 저위험)**: WS-DRIFT-5(모델 중앙화·캐시키) → WS-DRIFT-6(health probe).
- **Phase 1 (구조적 안전망)**: WS-DRIFT-2(diff 게이트) → WS-DRIFT-3(prune, 2가 검증) → WS-DRIFT-1(provenance run_id). WS-DRIFT-4(인덱스 결속)는 5와 metadata 지점을 공유하므로 5와 묶어 진행.
- 모든 TTL-side 효과(예: prune 검증용 재export)는 **생성기 경로**로만(`export_owl.py` 등) — round-trip 정규화로 무관 트리플을 변형시키는 known hazard(current-session.md:46) 회피.

---

## WS-EVAL — 평가 신뢰성: 측정 없이 못 고친다

### 왜 이 워크스트림이 먼저인가

다른 모든 워크스트림(UNKNOWN 채널, silent-drop, FN 측정, vector floor 등)의 "고쳤다"를 증명하려면 **신뢰할 수 있는 측정 도구가 먼저** 있어야 한다. 그런데 현재 arch-bot의 평가 인프라는 세 가지 구조적 거짓말 위에 서 있다.

1. **게이트가 정작 서빙 경로를 실행하지 않는다.** `replay_synthetic_observations.py::build_fake_result`(L91-144)는 `hazards` 키를 절대 방출하지 않는다. 그런데 v5 semantic attach(hybrid recall → `_stack_semantic_first` → `_rerank_guides_llm`) 전체가 `analysis_pipeline.py:319`의 `if HAZARD_DIRECT_MODE != "off" and hazards_payload:` 뒤에 게이트되어 있다. 코드 L380 주석이 스스로 인정한다: "replay는 hazards[] 미주입 → hazard_sr_ids ∅ → 미발동(무회귀)". 즉 `OHS_ENABLE_HYBRID_SEARCH=True`(config.py:36, **기본 ON**)인 서빙 경로를 2,360-case 회귀 게이트가 **단 한 번도 밟지 않는다**. semantic_attach 기본 ON 플립의 FN-무회귀 증거는 비어 있다 (V4-6).

2. **FN 정의가 너무 좁아 개별 guide over-drop을 통과시킨다.** `evaluate_case`(L185-191)의 false_negative는 `case_type=='positive' AND should_match_she AND procedures_count==0 AND actions_count==0` — 즉 **절차가 0개일 때만** FN. 관련 guide 1개가 vector drop/rerank 0-점으로 빠져도 generic 절차가 하나라도 남으면 FN=0. 안전/법령 도메인에서 missed hazard가 최악인데, 게이트가 보는 false_negative_rate(0.0436)는 실제 SHE recall miss(45.1%/909건)와 ~20배 다른 별개 지표다 (A5-F2, V4-5).

3. **정확도라고 부르는 숫자가 정확도가 아니다.** 8-photo eval(`eval_hazard_direct_8photo.py`)은 `mapping_rate`/`avg_mapping_rate`(L140,197)만 산출하고 gold/ground_truth/expected_guide 키가 0이다. 그런데 evaluation-baseline.md:24는 이를 "8-photo Guide mapping 80%→**100% (27/27)**"로, 다른 문서들은 "검증된 100% 정확도"로 보고한다 — 실제로는 추락 사진에 '급식실 시설' guide가 confidence 0.99로 붙는 오매칭이 standard_procedures lane에 실재한다 (A5-F4). 한편 정본 baseline 54.9% SHE recall은 `build_fake_result`가 expected_features를 confidence 0.9로 주입해 **Layer 0(Vision)를 완벽하다고 가정**한 Layer 1-3 지표일 뿐, Vision FN(가장 위험한 FN 원천)을 구조적으로 배제한다 (A5-F1).

게다가 이미 사람-라벨 gold 인프라가 **있는데 죽어 있다**: `label_ground_truth.py`(L48-50)와 `evaluate_catalog.py`(L50)의 `GOLD_FILE`/`OHS_DIR`이 더 이상 존재하지 않는 `ROOT/"OHS"`를 가리키고, `gold-truth-v1.jsonl`은 0 bytes, .bak-20260429-140028에 사람 라벨 4건만 남아 있다 (B8, V4-2). vector 경로 검증도 순환적이다: production rerank(gpt-4.1-mini)를 같은 gpt-4.1-mini judge가, 게다가 production이 절대 못 보는 `expected_corrective_direction`(정답 단서)을 `rich_text()`에 넣은 채 채점한다 (B8, V4-1). recall 회수 깊이(pool)는 `hybrid_search()` 래퍼(hybrid_search.py:172-177)가 pool 인자를 forward하지 않아 ohs_ci_raw(54,631 docs)에서도 영구 30(=0.055% 깊이)으로 고정돼 있고, recall@k를 측정할 oracle-rank 로그조차 없다 (B4 recall 부분, V1-3).

**설계 원칙**: (1) 사람-라벨 industrial gold set(30→100)을 **Vision 포함 full pipeline**에 통과시켜 end-to-end recall을 측정하고 precision@k/recall@k를 PRIMARY, facet-교집합 ontopic@k를 SECONDARY로 강등. (2) 고아 gold 인프라를 되살린다(경로 수정 + .bak 복원 + stratify). (3) judge에서 정답 누설을 제거하고 cross-vendor(Claude) judge를 추가해 same-model loop를 끊는다. (4) hazards를 주입하는 replay variant로 게이트가 ON 경로를 실제 실행하게 하고 guide_recall@K / top1-relevance veto를 추가하며 pool forward 버그와 DEFAULT_BASELINE v1→v3를 고친다. (5) ON-flip 통과와 caveat를 evaluation-baseline.md에 문서화.

**HARD CONSTRAINT 준수**: 모든 변경은 offline 배치 평가 경로에만 닿는다(서빙 PG SELECT 경로 불변). gold set은 추적 파일(eval-data/)이지 생성 산출물 수동편집이 아니다. scoring은 provenance/version에 의존하지 않는다(gold는 display-아닌 정답 라벨로만 사용). 모든 게이트 신규 키는 FN 방향에 **비대칭 tolerance**(recall 하락 ≤0.005, 0 권장)를 적용해 회귀가 false-negative를 올리지 못하게 한다.

---

### WS-EVAL-1 — replay에 hazards 주입 + guide_recall@K / top1-relevance FN veto (게이트가 ON 경로를 실제로 밟게)

**closesRisks**: B6(V4-5, V4-6), A3(A5-F2 부분), B4 recall 부분
**severity**: high · **phase**: 1 · **effort**: M

현재 게이트 맹점의 **근본 원인**은 FN 정의의 좁음이 아니라 *서빙 경로 미실행*이다. `build_fake_result`가 `hazards`를 안 만들어 `analysis_pipeline.py:319/358`의 semantic 경로가 replay에서 영구 dormant다. 따라서 단순히 METRIC_KEYS에 guide_recall을 더하면 legacy facet-fusion(`match_fusion_service.build_recommendation_rows`)만 재는 함정에 빠진다 (V4-5 검증자 경고). 먼저 하니스가 hazards를 흘려보내게 고친 뒤 guide-level veto를 단다.

**target**:
- `serving-team/08-app/backend/scripts/replay_synthetic_observations.py` — `build_fake_result()`(L91-144): 반환 dict에 `hazards` 키 추가. 각 case `expected_features`(accident/agent/context) → 1개 hazard entry로 매핑(`{"name": expected_primary_risk, "risk_level": "high", "preventive_measures":[expected_corrective_direction], "description": photo_description+visual_cues}`), `match_hazards_to_guides`/`match_hazards_to_ci`가 발동하도록. `evaluate_case()`(L147-220): per-case `expected_guide_codes`(WS-EVAL-2 gold) 대비 `guide_recall@3`, `top1_relevant`(top-1 guide가 expected에 속하는지) 계산해 row에 추가. `build_summary()`(L249-308): `guide_recall_at3`, `top1_relevance_rate`, 그리고 절차유무 무관 `she_recall_miss`(positive AND should_match_she AND NOT she_matched) 집계 키 추가.
- `serving-team/08-app/backend/scripts/regression_gate.py` — `METRIC_KEYS`(L37-42)에 `guide_recall_at3`, `top1_relevance_rate` 추가(expect_higher). `MAX_RATE_KEYS`(L43-46)에 `she_recall_miss_rate` 추가(expect_lower). `compare()`(L57-87): FN-방향 키에 비대칭 tolerance 지원(신규 `--fn-tolerance` 기본 0.005).
- `Makefile` — `f1-regression`(L248-252): hazards-injected replay로 실행되도록 env 확인(이미 config ON이므로 추가 플래그 불필요), gate 호출에 신규 키 반영.

**steps**:
1. `build_fake_result`에 `_expected_to_hazards(case)` 헬퍼 추가 — expected_features 3축을 단일 hazard payload로 합성. `hazards` 키로 반환에 포함. (legacy facet 경로는 그대로 두어 무회귀.)
2. limited 실행(`--limit 50`)으로 `analysis_pipeline.py:325 match_hazards_to_guides` / L348 `match_hazards_to_ci`가 실제 호출되는지 로그로 확인(hazard_guide_relations non-empty 검증).
3. `evaluate_case`에 guide_recall@3 / top1_relevant / she_recall_miss 산출 추가. WS-EVAL-2 gold가 아직 없으면 8-photo + curated synthetic subset의 expected_guide로 seed.
4. `build_summary`에 신규 집계 키 추가. `regression_gate.compare`에 FN-비대칭 tolerance 도입.
5. 새 baseline(`replay_baseline_v4.json`, hazards-injected) 1회 생성 — 단, **현 시점 ON 경로 출력을 baseline으로 박제하기 전에** 사람 검수(top1_relevance_rate가 합리적인지) 후 채택.
6. Makefile `f1-regression`가 신규 veto 키를 출력·강제하도록 수정.

**verification**:
- `make f1-regression` 가 PASS/FAIL을 출력하고, 의도적으로 `_rerank_guides_llm`에 0-점 강제 drop을 1줄 주입한 mutant에서 `guide_recall_at3`/`top1_relevance_rate`가 vetoed(exit 1) 되는지 **regression-of-the-gate** 테스트로 증명(FN-방향 민감도 확인). 정상 코드에서는 신규 키가 PASS.
- `she_recall_miss_rate`가 evaluation-baseline.md의 909건/54.9%와 정합(±1%p)함을 대조 — 좁은 false_negative_rate(0.0436)와 분리됐음을 수치로 확인.
- 기존 4개 METRIC_KEYS(she/sr/penalty/overall)는 tolerance 0.02 내 무변동(legacy 무회귀).

**rollback**: `build_fake_result`의 `hazards` 키와 신규 집계 키는 additive — `regression_gate`의 METRIC_KEYS/MAX_RATE_KEYS에서 신규 키만 제거하면 즉시 구 동작. baseline은 v3로 되돌림.

**dependsOn**: WS-EVAL-4 (DEFAULT_BASELINE v3 정합이 먼저), WS-EVAL-2 (per-case expected_guide gold; 없으면 8-photo seed로 임시 진행 가능)

**decisionNeeded**: 신규 guide-level veto를 **hard veto(exit 1)** 로 즉시 승격할지, 1-2주 **observe-only(WARN)** 로 baseline 안정화 후 hard화할지. 옵션 A(즉시 hard): ON-flip을 곧장 보호하나 noisy baseline으로 false-veto 위험. 옵션 B(WARN→hard): 안전하나 그 사이 ON 경로 회귀 무방비. 권장은 B(2주).

---

### WS-EVAL-2 — 고아 human-gold 인프라 부활 + industrial gold set 30→100 (NEGATIVE 포함)

**closesRisks**: A9(A5-F3, A5-F4), B8(V4-2)
**severity**: high · **phase**: 2 · **effort**: L

새 gold set을 처음부터 만들 필요 없다 — **이미 있는 인프라가 경로가 깨진 채 비어 있다**. `label_ground_truth.py`(L48-50)와 `evaluate_catalog.py`(L50)의 `ROOT/"OHS"`는 모노레포 재구성으로 사라졌고(실 위치 `serving-team/08-app`), `gold-truth-v1.jsonl`은 0 bytes, 사람 라벨은 .bak-20260429-140028에 4건만 생존. 이를 살려 industrial gold set(30→100)을 만들고 **Vision 포함 full pipeline**으로 통과시켜 end-to-end recall/precision을 측정한다.

**target**:
- `serving-team/08-app/scripts/eval/label_ground_truth.py` — `GOLD_FILE`/`SCENARIOS_FILE`/`SR_REGISTRY`/`REVIEWED_FILE_*`(L48-56): `ROOT/"OHS"/...` → `ROOT/"serving-team"/"08-app"/...` 또는 `BACKEND_DIR`-기반 repath. `SR_REGISTRY`는 `koshaontology/pipe-C` → 현 `data-team/03-validation/pipe-C` 위치 확인 후 수정.
- `serving-team/08-app/scripts/eval/evaluate_catalog.py` — `OHS_DIR`(L50) 및 `sys.path.insert`(L56) 동일 repath.
- `serving-team/08-app/data/eval/gold-truth-v1.jsonl` — .bak-20260429-140028(4건)에서 복원 후 라벨링 재개. industry × accident_type stratify. **expected NEGATIVE case** 명시(위험 없는 정상 작업 사진 → guide/SR 0 기대)로 over-promotion과 missed-hazard 양방향 측정 가능하게.
- `serving-team/08-app/data/eval/scenarios-v1.jsonl` — ground_truth가 42/100 self-referential(source guide ∈ own gold, V4-2 검증). 사람 라벨은 이 self-reference를 **상속하지 않도록** 독립 라벨링.
- 신규: gold set을 Vision 포함 full pipeline에 통과시키는 end-to-end 하니스(`eval_real_photo_e2e.py` 신설 또는 `eval_hazard_direct_8photo.py` 확장) — `analyze_image` 입력 + expected_guide/she/sr/work_context 대비 precision@k/recall@k.

**steps**:
1. `label_ground_truth.py`/`evaluate_catalog.py`의 죽은 경로 전부 repath(상수만 수정, 로직 불변). 한 번 streamlit/CLI 기동으로 import·DB 연결 확인.
2. `.bak-20260429-140028` → `gold-truth-v1.jsonl` 복원, 4건 검수.
3. industrial 실사진 30건 1차 라벨링(건설·제조·금속가공 등 stratified) + NEGATIVE 5-10건. 100건까지 확장은 phase 2 후속.
4. end-to-end 하니스 신설: 각 gold 이미지 → Vision(gpt-4.1) → full pipeline → expected_guide_codes/expected_she/expected_sr/expected_work_context 대비 **precision@k, recall@k(PRIMARY)**, facet-intersection ontopic@k(SECONDARY).
5. `eval_hazard_direct_8photo.py`의 `mapping_rate`(specificity proxy)와 분리해 lane별(hazard_guide_relations vs legacy standard_procedures) 측정 — 한 '100%' 숫자로 합치지 않음.
6. gold-truth-v1.jsonl을 추적 파일로 commit(eval-data 정책 준수).

**verification**:
- `python serving-team/08-app/scripts/eval/label_ground_truth.py`(또는 streamlit) 가 import·경로 에러 없이 기동하고 progress가 4/100 이상으로 표시.
- end-to-end 하니스가 NEGATIVE case에서 guide=0(precision 보호)을, positive case에서 recall@3 산출. Vision-FN(positive인데 hazard 0개 탐지)이 **별도 카운트**로 잡히는지 확인 — 합성 replay가 구조적으로 못 보는 클래스가 여기서 보여야 함(A5-F1 갭 메움).
- 회귀 안전: 본 항목은 측정 도구 신설이라 서빙·기존 게이트 무영향. `make f1-regression` 결과 불변.

**rollback**: 신설 하니스/gold 파일은 평가 전용 — 삭제만 하면 원복. repath는 상수 변경이라 git revert로 즉시 복귀.

**dependsOn**: 없음 (WS-EVAL-1, WS-EVAL-3가 이 gold를 소비하므로 가능한 먼저 착수)

**decisionNeeded**: gold 라벨링 **주체와 SoT**. 옵션 A: 사용자(온톨로지 엔지니어) 본인이 도메인 전문가로 직접 라벨(label_ground_truth.py 원래 의도). 옵션 B: KOSHA guide 원문 근거를 단 별도 검수자. 또한 confirmed-vs-candidate 라우팅처럼 **expected_guide를 "정확히 1개 정답"인지 "관련 guide 집합(recall@k)"** 인지 결정 필요 — 권장은 집합(recall@k) + 그중 top-1 적합(precision@1).

---

### WS-EVAL-3 — judge 정답누설 제거 + cross-vendor(Claude) judge로 순환 평가 차단

**closesRisks**: B8(V4-1, V4-2)
**severity**: medium · **phase**: 1 · **effort**: M

rerank-lift의 유일한 실증 근거 delta +0.8(rescue +1.05)은 **같은 모델이 자기 출력에 후한 점수**일 수 있다. production rerank `_rerank_guides_llm(model="gpt-4.1-mini")`를, `judge_rerank_lift.py`가 `judge_semantic_attach.judge`(역시 gpt-4.1-mini)로 채점한다. 게다가 `judge_semantic_attach.rich_text()`(L42-47)는 production이 **절대 못 보는** `expected_corrective_direction`(정답 시정방향)을 judge 입력에 넣는다 — 누설.

**target**:
- `serving-team/08-app/backend/scripts/judge_semantic_attach.py` — `rich_text()`(L42-47): `expected_corrective_direction` 항을 **제거**(photo_description + visual_cues만, production 입력과 일치). `judge()`(L50-66): vendor 추상화(OpenAI/Anthropic 분기) 추가, `--judge-vendor {openai,anthropic}` 인자.
- `serving-team/08-app/backend/scripts/judge_rerank_lift.py` — L29 `from judge_semantic_attach import judge, rich_text` 의 누설-제거 버전 사용. L71 `judge(oai, "gpt-4.1-mini", ...)`를 vendor 파라미터화. 동일 입력으로 OpenAI judge와 Claude judge 두 번 실행해 delta 비교.
- 신규: human-gold(WS-EVAL-2) 라벨된 subset에서 LLM-judge ↔ human 일치도(Cohen's κ/상관) 산출 스크립트.

**steps**:
1. `rich_text()`에서 `expected_corrective_direction` 제거. `judge_rerank_lift.py`/`judge_semantic_attach.py` **재실행**해 delta +0.8/+0.6이 누설 제거 후에도 생존하는지 보고(누설 가설 직접 검증).
2. `judge()`에 Anthropic 분기 추가(claude-* 모델 — claude-api skill로 현행 모델 id 확인). rerank-lift를 **cross-vendor**로 재실행: gpt-4.1-mini rerank 출력을 Claude judge가 채점. win-rate가 붕괴하면 +0.8은 self-agreement였음.
3. WS-EVAL-2 human-gold subset에서 LLM-judge vs human κ 산출. κ가 낮으면 어떤 LLM-judge delta도 승급 근거로 인용 금지.
4. 산출물(judge_rerank_lift.json, judge_semantic_attach.json) regenerate. validation docstring/notes에 "judge가 reranker와 model+rubric 공유했고 정답단서를 봤으므로 기존 lift는 upper bound"임을 명기.

**verification**:
- 누설-제거 + cross-vendor 재실행 후 delta를 **누설판/cross-vendor판 나란히** 보고. 둘 다 양수이고 rescue에서 on_loss/rerank_loss가 낮으면 lift 견고; 붕괴하면 rerank 승급 근거 철회.
- human-gold subset에서 κ ≥ 0.4(moderate) 이상이어야 LLM-judge를 continuous proxy로 신뢰.
- 회귀 안전: 평가 스크립트만 변경 — 서빙·게이트 무영향. ontopic@k(facet-독립) 신호는 유지되므로 attach 결정의 비-LLM 백업 존재.

**rollback**: `rich_text` 1줄 복귀로 원복. vendor 분기는 `--judge-vendor openai` 기본값으로 기존 동작 보존.

**dependsOn**: WS-EVAL-2 (human-gold subset이 κ 산출에 필요; 누설제거+cross-vendor는 gold 없이도 선행 가능)

**decisionNeeded**: cross-vendor judge로 **어떤 Claude 모델**을 SoT judge로 둘지(비용 vs 품질). 또한 누설 제거 후 delta가 유의하게 줄면 **rerank 기본 ON 유지 여부**를 재결정해야 함(WS-EVAL-1 ON-flip 검증과 연동) — 옵션: (A) rerank 유지하되 게이트로만 정당화, (B) flag-gated로 강등.

---

### WS-EVAL-4 — DEFAULT_BASELINE v1→v3 + pool forward 버그 수정 + oracle-rank recall@k 계측

**closesRisks**: B4(V1-3 recall 부분), B6(V4-6의 stale baseline), B2 일부(stale baseline)
**severity**: medium · **phase**: 0 · **effort**: S

세 개의 좁고 확실한 버그. (1) `regression_gate.py:32-34` `DEFAULT_BASELINE = replay_baseline.json`(**v1**)인데 `phase3-baseline-shift.md`/Makefile `f1-regression`(L252)은 `replay_baseline_v3.json`을 강제. `regression_gate.py`를 `--baseline` 없이 직접 호출하면 stale v1로 비교돼 잘못된 PASS/FAIL. (2) `hybrid_search.py::hybrid_search()` 래퍼(L172-177)가 `pool` 인자를 받지도 forward하지도 않아 per-channel pool이 영구 30 — `ohs_ci_raw`(54,631 docs, hazard_to_ci_service.py:48)에서 0.055% 깊이, pool 밖 정답은 영구 불가시(회수 FN). `_guide_section_recall`(hazard_to_guide_service.py:210-228)의 `pool=40`은 `n_results=40`(post-fusion slice)으로만 쓰여 착시. (3) recall@30 vs @100을 잴 oracle-rank 로그가 없어 "pool이 충분히 깊은가"가 숫자가 아닌 가정.

**target**:
- `serving-team/08-app/backend/scripts/regression_gate.py` — `DEFAULT_BASELINE`(L32-34): `replay_baseline.json` → `replay_baseline_v3.json`(WS-EVAL-1 후엔 v4).
- `serving-team/08-app/backend/app/services/hybrid_search.py` — `hybrid_search(kind, query, n_results=10, pool=30)`(L172-177): `pool` 파라미터 추가 + `.search(query, n_results=n_results, pool=pool)`로 forward.
- `serving-team/08-app/backend/app/services/hazard_to_ci_service.py:48` — `hybrid_search("ci_raw", query, n_results=..., pool=<deeper>)`로 대형 컬렉션에 깊은 pool 전달.
- `serving-team/08-app/backend/app/services/hazard_to_guide_service.py:228` — `_guide_section_recall`이 진짜 per-channel pool을 전달하도록 수정.
- 신규: WS-EVAL-2 gold(hazard→정답 guide/CI) 기반 oracle-rank 로깅 — vector-only/BM25-only 각각 정답의 rank를 기록해 recall@30 vs @100/200 산출하는 eval 모드.

**steps**:
1. `DEFAULT_BASELINE`를 v3로 수정(1줄). `regression_gate.py current.json`(baseline 무지정) 실행이 v3와 비교함을 확인.
2. `hybrid_search()` 래퍼에 `pool` 추가·forward. 두 hazard 서비스 caller가 대형 컬렉션(ci_raw 54.6K, guide_section 12.7K)에 깊은 pool 전달하도록 수정. ohs_guide(1,038)는 pool=30이 ~3% 깊이라 변경 불필요.
3. oracle-rank 계측: gold item별 vector-only/BM25-only rank 기록 → recall@30, recall@100 산출. `ablation_pool.json` 산출물로 박제(ablation_embedding.json 패턴).
4. recall@30 ≪ recall@100이면 pool 상향(상수 결정은 데이터 기반). RRF_K {30,60,100} grid는 후속.

**verification**:
- `regression_gate.py /tmp/x.json` (baseline 무지정) stdout의 `baseline:` 라인이 `replay_baseline_v3.json` 경로를 출력.
- pool forward: `hazard_to_ci_service`를 deeper pool로 호출 시 `_vector_rank`/`_bm25_rank`의 n이 실제로 증가하는지(로그/단위테스트) 확인.
- oracle-rank: `ablation_pool.json`에 recall@30, recall@100 수치가 기록되고, ci_raw에서 recall@30 < recall@100 이면 회수 FN 정량 확인.
- 회귀 안전: pool 상향은 **recall만 늘리고 줄이지 않음**(상위 후보 집합 확대 → 후속 RRF/rerank가 좁힘). `make f1-regression`(WS-EVAL-1 적용 후)에서 guide_recall_at3 비감소 확인 — FN 방향 안전.

**rollback**: 각 변경이 독립 1-3줄. `DEFAULT_BASELINE` 되돌림, `pool` 인자 기본값 30 유지로 caller 무영향, oracle-rank 스크립트는 평가 전용 삭제.

**dependsOn**: 없음 (WS-EVAL-1의 v4 baseline 생성 시 DEFAULT_BASELINE을 v4로 다시 갱신)

**decisionNeeded**: pool 상향 값. 옵션: oracle-rank 측정 후 recall@k 곡선이 평탄해지는 지점(예 100/200)으로 결정 — 측정 전 임의 상향 금지. 비용(임베딩 query는 1회/scene, pool 확대는 ChromaDB·BM25 slice만 키움 → 저비용)이라 FN-보수적으로 넉넉히 잡아도 안전.

---

### WS-EVAL-5 — evaluation-baseline.md에 ON-flip 통과 + 측정 caveat 문서화

**closesRisks**: A9(A5-F1, A5-F4 문서 과장), B6(V4-6 silent baseline), B8 일부
**severity**: medium · **phase**: 0 · **effort**: S

방어 가능성(legal defensibility) 직결. 현재 문서는 측정 산출물을 과대 진술한다: evaluation-baseline.md:24 "8-photo Guide mapping **100% (27/27)**", L28 "Guide 추천은 synthetic corpus 채점 대상 외", 54.9% SHE recall이 Layer-0-perfect 가정 위 지표임을 명시하지 않음. semantic_attach 기본 ON임에도 baseline 문서가 ON-flip 검증을 침묵.

**target**:
- `docs/status/evaluation-baseline.md` — L24 인근: "mapping 100%"를 "**하자드→코드 매핑 커버리지 100% (정확도 아님, n=8 비통계, scene-correctness 미측정)**"로 정정. 54.9% SHE recall 라인 인근: "Layer 1-3 지표(Vision FN은 replay의 expected_features 주입으로 구조적 배제) — end-to-end safety recall 아님" caveat 블록 추가, `build_fake_result` docstring 크로스링크. semantic_attach ON-flip 통과 결과(WS-EVAL-1의 guide_recall@3/top1_relevance baseline) 신규 섹션 기록.
- 본 항목은 **수동편집 금지 산출물이 아님**(evaluation-baseline.md는 정본 문서, 생성물 아님 — CLAUDE.md 정책상 baseline 메트릭 정본 위치).

**steps**:
1. 8-photo "100%" 문구를 mapping-coverage(정확도 아님)로 정정. 동일 표현이 퍼진 current-session.md / guide-recommendation-accuracy.md / llm-dependency-evolution.md에도 동일 정정(WS-EVAL-2 lane 분리 결과 반영).
2. 54.9%/84.0% 라인에 Layer-0-perfect 가정 caveat + replay docstring 링크.
3. WS-EVAL-1 hazards-injected 게이트의 ON 경로 통과(guide_recall@3, top1_relevance_rate, she_recall_miss_rate) 결과를 표로 기록 — "ON-flip이 FN-무회귀 게이트를 통과함"의 증거.
4. WS-EVAL-2 end-to-end real-photo recall을 synthetic recall과 **명확히 분리**된 라인으로 기록(절대 안전-품질 주장은 real-photo gold 인용).

**verification**:
- 문서 lint/링크 체크(docs/README.md 색인 정합). "100% 정확도" 류 표현이 grep으로 0건(전부 'mapping coverage'로 정정).
- evaluation-baseline.md가 (a) synthetic Layer-1-3 recall, (b) real-photo end-to-end recall, (c) ON-flip 게이트 통과 세 숫자를 **서로 다른 라벨**로 명시.

**rollback**: 문서 변경이라 git revert로 즉시 원복.

**dependsOn**: WS-EVAL-1 (ON-flip 통과 수치), WS-EVAL-2 (real-photo recall 라인)

**decisionNeeded**: 없음.

---

## WS-DEEP — 깊은 구조: 근본 모델·추론 정합

### 워크스트림 개요

이 워크스트림은 파이프라인의 "표면 버그"가 아니라 **모델·추론 정합성의 구조적 결함** 3건을 다룬다. 모두 false-negative를 직접 주입하지는 않지만(그래서 severity는 high가 아닌 medium), SAFETY/LEGAL 도메인에서 가장 중요한 **방어성(defensibility)·근거 추적·검증 soundness**를 약화시킨다. 공통 설계 원칙은 (1) **FN-conservative** — 어떤 변경도 SHE/facet이 이미 잡은 근거를 침묵 제거하지 못하게 하고, (2) **격리** — 추론 정합 강화 작업이 서빙(SRV)/물질화(MAT) 경로 회귀를 만들지 않도록 별도 profile/채널로 분리하며, (3) **모델 결정 분리** — 진짜 재모델링(BFO 축 재배치)은 사용자 결정(B6)으로 남기고, 그 전까지 결함을 "리즈너에 가시화"하는 안전한 계측·detector만 추가한다.

세 항목의 의존 흐름: **WS-DEEP-1(이중경로 merge)** 와 **WS-DEEP-3(ReasoningTrace edge)** 는 서빙 백엔드(analysis_pipeline) 작업으로 독립 착수 가능. **WS-DEEP-2(BFO 축 detector)** 는 온톨로지 팀 작업으로 완전 독립이며, 그 결과(어느 ctx 클래스가 unsatisfiable인가)가 B6 재모델링 결정의 회귀 게이트가 된다. WS-DEEP-1의 ground-truth agreement 메트릭은 WS-EVAL의 gold set에 의존한다.

---

### WS-DEEP-1 — 이중경로 guide overwrite를 corroboration-보존 MERGE로 + disagreement 가시화 + per-path agreement 메트릭

**closesRisks**: A8 (AX4-F3) · 부분적으로 A3-05(guide source 태깅 측면)
**severity**: high · **phase**: 1 · **effort**: L

**문제(재확인)**: `analysis_pipeline.py`의 `_build_knowledge_context`에서 SHE 경로와 hazard-direct 경로가 독립 실행된 뒤 결과를 단순 합치기만 한다. SR-id는 L383 `sr_ids = self._unique([*hazard_sr_ids, *sr_ids])` 로 **비파괴적 union**(이건 FN을 주입하지 않음 — 두 view 모두 응답에 독립 반환됨). 그러나 guide는 L358–377에서 semantic on일 때 `guide_rows = _sem_guides` 로 **통째 덮어쓰기**된다. 이 `_sem_guides`(hazard-direct)는 `guide_code/title/relevance_score/mapping_type/evidence_summary` 만 갖고, match_fusion이 만든 SHE/facet `guide_rows`가 보유한 **`ci_hit_count`(CI corroboration), `work_process_steps`, `corroborating_ci_count`**(match_fusion_service.py L164–177)를 모두 잃는다. 결과적으로 `_build_standard_procedures`(L599–633)가 `work_process_steps` 빈 절차를 만들고, CI로 보강된(더 잘 grounded된) 표준개선절차 guide가 침묵 제거된다 — 표준개선절차 패널의 precision/grounding 회귀. 추가로 두 경로의 합의/불일치를 정량화하는 산출물이 어디에도 없다(parallel이 "검증용 기본값"이라면서도).

**target**:
- `serving-team/08-app/backend/app/services/analysis_pipeline.py` → `AnalysisPipeline._build_knowledge_context` (guide overwrite 블록 현재 L356–377; SR union L379–389), `AnalysisPipeline._append_analysis_log` (L1019)
- `serving-team/08-app/backend/app/services/match_fusion_service.py` → `build_recommendation_rows` (guide_rows 스키마, `ci_hit_count`/corroboration source)
- `serving-team/08-app/backend/app/services/hazard_to_guide_service.py` → `match_hazards_to_guides` (hazard-direct guide 산출, 검증용 `semantic_sr_ids`/`facet_sr_ids` union L597)

**steps**:
1. **MERGE 함수 신설** — `analysis_pipeline.py`에 `_merge_guide_rows(facet_rows, sem_rows)` private 메서드를 추가. guide_code 기준으로 dict union하되: (a) 두 경로 모두 등장 → source_path=`both`, facet의 `ci_hit_count`/`work_process_steps`/`corroborating_ci_count`를 **반드시 보존**하고 sem의 `relevance_score`가 높으면 점수만 갱신; (b) facet에만 → source_path=`she_facet` 보존; (c) sem에만 → source_path=`hazard_direct`. **회귀 불변식: 결과 guide_code 집합 ⊇ facet guide_code 집합**(CI-corroborated guide는 절대 drop 금지). L376–377의 `guide_rows = _sem_guides`를 `guide_rows = self._merge_guide_rows(guide_rows, _sem_guides)`로 교체.
2. **source_path 필드 배선** — 각 guide_row에 `source_path` 키 추가. `StandardProcedure` 모델(`app/models/hazard.py`)에 `source_path: Optional[str] = None` 추가하고 `_build_standard_procedures`에서 `row.get("source_path")` 전달(display-only, scoring 미반영 — 하드 제약 준수).
3. **disagreement 분류 emit** — `_append_analysis_log` 호출부에 신규 인자 `path_agreement` 추가: SR-id와 guide별 `{she_only, hazard_direct_only, both}` 분류를 계산해 analysis_log.jsonl 엔트리에 `path_agreement` 필드로 기록(F.3.5 채널 재사용, non-empty일 때만). 새 dict는 reasoner_rejects와 동일하게 옵셔널.
4. **'검토필요' 플래그(down-weight 금지)** — 한 경로에서만 잡힌 **high-severity** hazard(hazards_payload severity=HIGH 이면서 한 경로 SR/guide에만 출현)는 점수를 깎지 말고 `StandardProcedure`/`HazardGuideRelation`에 `review_required: bool` 플래그를 세워 노출. 두 경로 finding 모두 visible 유지.
5. **per-path agreement 메트릭** — `replay_synthetic_observations.py`는 `build_fake_result`에 `hazards` 키가 없어(L134–144) hazard-direct 경로가 **replay에서 dormant**다. 따라서 hazards[]를 주입하는 별도 하니스 `scripts/replay_dualpath_agreement.py`를 신설 — synthetic corpus + ground-truth(WS-EVAL gold set)에서 per-hazard `agreement_rate`, 경로별 `independent_recall`(she_recall vs hazard_direct_recall)을 **같은 자(yardstick)**로 산출. 8-photo set은 overlap_count=0(GT 부재)이라 사용 금지.

**verification**:
- **무회귀(필수)**: `python scripts/replay_synthetic_observations.py --output cur.json && python scripts/regression_gate.py cur.json` 이 exit 0. replay는 hazards[] 미주입이라 merge 경로가 dormant → MERGE는 SHE-only 경로에 무영향이어야 함(diff 0 기대). 단, **MERGE는 hazards[] 주입 시 procedures_count를 절대 0으로 떨어뜨리지 않아야** 하므로, 신규 `replay_dualpath_agreement.py`로 hazards[] 주입 케이스에서 `false_negative`(replay 정의: positive ∧ should_match_she ∧ procedures_count==0 ∧ actions_count==0, replay L186–191)가 **SHE-only baseline 대비 증가 0**임을 assert(FN-direction 게이트).
- **불변식 단위 테스트**: `_merge_guide_rows` 에 대해 "facet guide_code 집합 ⊆ merged guide_code 집합" property test 추가. `ci_hit_count>0` 인 facet guide가 merged에 살아있고 `work_process_steps`가 비지 않음을 assert.
- **메트릭 산출 확인**: `replay_dualpath_agreement.py` 가 `agreement_rate`/`independent_recall`/`she_only_count`/`hazard_direct_only_count` 를 JSON으로 emit하고, analysis_log.jsonl에 `path_agreement` 엔트리가 1건 이상 기록됨을 grep으로 확인.

**rollback**: env `HAZARD_DIRECT_MODE=off`로 hazard-direct 경로 전체 비활성(merge 미발동). 또는 `_merge_guide_rows` 한 줄을 다시 `guide_rows = _sem_guides`로 되돌리면 즉시 원복(단일 지점). 모델 필드 추가는 Optional default None이라 응답 계약 하위호환.

**dependsOn**: WS-EVAL gold set 아이템(per-path agreement 메트릭의 ground-truth) — gold set이 늦으면 step 1–4는 선행 착수하고 step 5만 대기 가능.

**decisionNeeded**: 없음. (단 step 4의 '검토필요' 임계 — high-severity 단독경로만 vs 모든 단독경로 — 는 보수적으로 high-severity로 고정; 확장 시 WS-EVAL 데이터로 사후 튜닝.)

---

### WS-DEEP-2 — BFO 축 모순 grounding을 리즈너/static detector에 가시화 (격리된 CON-strict profile + detector 확장)

**closesRisks**: A11 (A2-04, 백로그 F1)
**severity**: medium · **phase**: 1 · **effort**: M

**문제(재확인)**: `kosha-ontology-v2.owl`이 BFO IRI를 subClassOf 타깃으로 실사용한다 — `risk:RiskFeature ⊑ BFO_0000019(Quality)`(L1416). 그런데 그 자식 중 `ctx:WorkContext`(L1016–1021)는 **동시에** `risk:RiskFeature` 이면서 `BFO_0000015(Process)`, `ctx:WorkActivity`(L1333–1334) 도 Process, `ctx:TemporalStage`(L1883–1884) 는 `BFO_0000003(Occurrent)`. 실제 BFO에서 Quality⊥Process, Continuant(Quality 상위)⊥Occurrent 이므로 이 3개 클래스는 unsatisfiable이어야 한다. 그러나 BFO 본문이 리포에 0개이고(`owl:imports bfo.owl` L145는 라벨일 뿐 미해소), BFO 상위클래스 disjoint 로컬 공리도 0건 → 리즈너에게 BFO_0000019와 BFO_0000015는 무관한 불투명 IRI라 모순이 영원히 무탐지. 즉 validation이 광고하는 "grounding 검증"이 정작 grounding 모순을 못 본다. 정적 detector `check_disjoint_consistency.py`도 facet-axis disjoint(개체 레벨)만 보고 BFO 차원/클래스 레벨은 다루지 않는다.

**target**:
- (신규) `ontology-team/06-reasoning/ontology/kosha-bfo-axis-disjoint.ttl` — hand-authored 최소 disjoint stub (기존 `kosha-facet-axis-disjoint.ttl` 패턴 미러)
- `ontology-team/06-reasoning/ontology/assembly/manifest_source.py` → `PROFILES`, `_CODE` (신규 `consistency-strict`/`CST` profile 코드 추가), `_E` 리스트(신규 entry, profiles={CST}만 — SRV/CON/MAT/FAC 미포함으로 격리)
- `ontology-team/06-reasoning/ontology/scripts/check_disjoint_consistency.py` → `main()` 에 'BFO-axis clash' 클래스-레벨 detector 추가(기존 `ancestors`/`disj` 인프라 재사용)

**steps**:
1. **최소 BFO disjoint stub 작성** — `kosha-bfo-axis-disjoint.ttl`에 BFO 전체가 아니라 단편만: `obo:BFO_0000019(Quality) owl:disjointWith obo:BFO_0000015(Process)`; `obo:BFO_0000002(Continuant) owl:disjointWith obo:BFO_0000003(Occurrent)`; `obo:BFO_0000019(Quality) rdfs:subClassOf obo:BFO_0000020(SpecificallyDependentContinuant)`, `obo:BFO_0000020 rdfs:subClassOf obo:BFO_0000002(Continuant)`(Quality→Continuant 폐포로 Quality⊥Occurrent 도출). 주석에 "BFO 본문 import 아님, 모순 가시화용 최소 stub" 명시.
2. **CON-strict profile 격리 등록** — `manifest_source.py`의 `PROFILES`에 `"consistency-strict"`, `_CODE`에 `"CST": "consistency-strict"` 추가. `_E`에 신규 entry: `("bfo-axis-disjoint", "kosha-bfo-axis-disjoint.ttl", "axioms-disjoint", "L3-reasoning", {"CST"}, "turtle", "최소 BFO 축 disjoint stub — F1 모순 가시화 전용, SRV/MAT 격리")`. 또한 base/vocab/she ABox 등 모순을 보려면 같은 entry들에 `CST`를 추가하되, **`SRV`/`MAT`/`FAC` 집합은 변경 금지**(이들이 비일관 stub을 절대 안 받게). gen_manifest.py 재실행해 assembly-manifest.json 재생성(생성물 — 수동편집 금지, 생성기만 수정).
3. **static class-level detector 확장** — `check_disjoint_consistency.py main()`에 신규 섹션: 개체뿐 아니라 **owl:Class 노드**에 대해서도 ancestor 폐포를 계산해, 폐포 안에 서로소 두 클래스(stub의 Quality⊥Process 등)가 동시 존재하는 클래스를 'BFO-axis clash'로 리포트. `--profile consistency-strict` 일 때만 BFO stub이 로드되므로 이 모드에서 WorkContext/WorkActivity/TemporalStage 3건이 적발돼야 함. rdflib만 사용(리즈너 불요) → 즉시·결정론적.
4. **Openllet 라이브 owl:Nothing 확인 절차 문서화** — CST profile을 Pellet/Openllet에 로드 후 `ASK { ctx:WorkContext rdfs:subClassOf owl:Nothing }`(또는 SELECT unsat classes) 실쿼리로 unsatisfiable 떨어짐을 확인. prepare()는 lazy이므로 "Server Started"≠일관 — 실추론 쿼리 필수(ref_fuseki_endpoints 교훈). 이 쿼리를 B6 재설계의 회귀 게이트로 고정(재모델 후 0건이어야 통과).

**verification**:
- **detector 적발**: `python scripts/check_disjoint_consistency.py --profile consistency-strict` 이 exit 1 + 정확히 `ctx:WorkContext`, `ctx:WorkActivity`, `ctx:TemporalStage` 3건을 'BFO-axis clash'로 출력(회귀 baseline). 깨끗한 자식(AccidentType/AgentState/PPEState/EnvironmentalFactor=Quality)은 미출력 — false-positive 0 확인.
- **격리 증명(무회귀 핵심)**: `python scripts/check_disjoint_consistency.py --profile serving` 과 `--profile shacl-materialize` 가 **변경 전과 동일 출력**(BFO stub 미로드 → 신규 충돌 0). 즉 SRV/MAT 일관성 unchanged. `verify-manifest`/`verify-prefixes` (gen_manifest 재생성 후 graph-diff 0 except 신규 stub) 통과.
- **라이브 확인**: CST profile Openllet `owl:Nothing` 라이브 쿼리에서 위 3 클래스 unsatisfiable 반환(prepare lazy 우회 위해 실쿼리). SRV Fuseki 엔드포인트는 stub 미로드라 owl:Nothing 신규 0건.

**rollback**: `kosha-bfo-axis-disjoint.ttl` 삭제 + `manifest_source.py`의 CST entry/코드 revert + gen_manifest 재실행. detector 신규 섹션은 `--profile consistency-strict` gating이라 다른 profile에 무영향이므로 단독 revert 가능. SRV/MAT는 stub을 애초에 안 받으므로 rollback 위험 0.

**dependsOn**: 없음(완전 독립). B6 재모델링(WS-DEEP-2의 decisionNeeded)의 **선행 진단**이므로 B6보다 먼저 착수.

**decisionNeeded**: **진짜 수정(B6, 백로그 status '대기')은 모델 결정이다 — `ctx:WorkContext`/`WorkActivity`/`TemporalStage`를 어느 BFO 축에 둘 것인가.** 옵션 A: 이들을 `risk:RiskFeature`(Quality) 하위에서 떼어내고 Process/Occurrent 그대로 둠(RiskFeature는 순수 Quality 축 유지 — facet=Quality 일관). 옵션 B: BFO grounding을 Process/Occurrent → Quality로 변경해 RiskFeature 하위 유지(작업맥락을 '품질'로 모델링). 옵션 C: `risk:RiskFeature`의 BFO 상위를 Quality에서 더 추상적인 `BFO_0000001(entity)`로 올려 자식의 축 자유 허용(가장 약한 grounding). 이 결정은 490 facet의 grounding 상속 + she:hasWorkContext 등 range 의미에 영향. **WS-DEEP-2의 detector/CON-strict는 이 결정 없이 안전하게 선행 가능하며, 결정 후 회귀 게이트로 재사용된다.** (B6-ontology 백로그로 라우팅.)

---

### WS-DEEP-3 — ReasoningTrace를 node-list에서 edge graph로 + rule/reasoner 근거 forward + 추론파생 항목 배지

**closesRisks**: A3-05(A7-deep) · A3-02와 합쳐질 때 version-pinning 효과(WS 외부)
**severity**: medium · **phase**: 1(step 1–2) / 2(step 3 edge graph) · **effort**: L

**문제(재확인)**: `ReasoningTrace`(`app/models/hazard.py` L101–109)는 8개 평면 `List[str]`로 edge가 없다. `_build_reasoning_trace`(analysis_pipeline.py L656–680)는 각 단계 ID만 모으고 **`canonical`(=`apply_risk_rules` 결과)을 전달받지 않는다** — 그래서 `apply_rules`가 만든 `applied_rules`(예: `"R-cross: SCAFFOLD → +FALL"`, hazard_rule_engine.py L206–216)와, **규칙이 추가한 코드**(accident_types/agents에 append, L206/213)가 trace에 보존되지 않는다. 더 심각히, `_build_risk_features`(L459–477)는 GPT가 직접 본 feature와 **규칙이 추론한 feature를 source 플래그 없이 동일하게** RiskFeature로 평탄화 → 프론트 `ReasoningTracePanel.tsx`에서 **모든 feature가 `[정규화]`로만 표시**(L21), `[추론]` 구분 0, 컬럼 간 edge 0. shadow_reasoner의 reject(`{guide_code, guide_domain, axiom_pair, confidence, level}`)는 analysis_log에만 가고 응답 trace엔 안 온다. SAFETY/LEGAL에서 "이 벌칙이 왜 이 사진에서 나왔나"를 단계 재구성 불가.

**target**:
- `serving-team/08-app/backend/app/models/hazard.py` → `RiskFeature`(신규 `origin` 필드), `ReasoningTrace`(신규 edge 필드)
- `serving-team/08-app/backend/app/services/analysis_pipeline.py` → `_build_risk_features`(origin 태깅), `_build_reasoning_trace`(canonical/applied_rules/reasoner_rejects 인자 추가), 호출부 L138–147
- `serving-team/08-app/backend/app/services/hazard_rule_engine.py` → `apply_rules`(derived 코드를 별도 `derived_codes` 리스트로도 반환)
- `serving-team/08-app/backend/app/services/shadow_reasoner.py` → `shadow_validate`(반환 reject를 응답으로 forward — 신규 호출만, 기존 로깅 유지)
- `serving-team/08-app/frontend/src/components/results/ReasoningTracePanel.tsx` → `[추론]` 배지 + edge 렌더

**steps**:
1. **(S, 최고가치) RiskFeature origin 태깅** — `apply_rules`가 derived 코드를 식별할 수 있으므로(append 시점), 반환 dict에 `derived_codes: list[str]` 추가. `_build_risk_features`에서 `code in derived_codes` 면 `origin="rule_derived"`, 아니면 `origin="gpt_observed"`. `RiskFeature` 모델에 `origin: str = "gpt_observed"`(display-only, **scoring 미반영** — 하드 제약). 프론트 `ReasoningTracePanel.tsx`에서 origin=`rule_derived`는 `[추론]` 배지, 나머지는 `[정규화]`/`[GPT]`로 구분 렌더(SCAFFOLD→FALL이 직접관찰과 시각적으로 분리).
2. **(M) applied_rules + reasoner_rejects forward** — `_build_reasoning_trace`에 `applied_rules: list[str]`, `reasoner_rejects: list[dict]` 인자 추가하고 호출부(L138)에서 `knowledge.canonical.get("applied_rules")` 와 shadow reject를 전달. `ReasoningTrace`에 `applied_rules: List[str] = []`, `reasoner_rejects: List[dict] = []` 필드 추가. analysis_log에만 있던 온톨로지 근거가 응답 trace에 도달.
3. **(L) edge graph 승격** — `ReasoningTrace`에 edge 필드 신설: `feature_to_sr: List[dict]`(feature_code→sr_id), `sr_to_article: List[dict]`, `sr_to_penalty: List[dict]`, `rule_to_derived: List[dict]`(applied_rule→derived_code), 각 edge에 `justified_by`(axiom/SWRL rule id 또는 PG mapping source, reasoner_rejects의 `axiom_pair` 재사용). edge는 **이미 응답에 존재하는** SR-level 관계(SituationMatch.applies_sr_ids, PenaltyPath.source_sr_ids, ProcedureStep.source_sr_ids)를 재사용해 조립 — 신규 조회 없음. 프론트는 5 컬럼 사이에 edge 라인/참조 렌더. **A3-02(version stamping, WS-PROV)와 페어링**해 각 edge의 justification이 ontology 버전에도 pin.

**verification**:
- **무회귀(필수)**: `python scripts/replay_synthetic_observations.py --output cur.json && python scripts/regression_gate.py cur.json` exit 0. 신규 필드는 전부 default-empty Optional이라 응답 계약·점수 불변(she/sr/penalty/overall accuracy delta 0, FN-rate 변동 0). origin/edge가 **scoring에 영향 0**임을 단위 테스트로 assert(provenance→scoring 미반영 하드 제약).
- **기능 확인**: SCAFFOLD만 GPT가 보고 FALL이 R-cross로 파생되는 합성 케이스에서 응답 `risk_features`에 `origin="rule_derived"`인 FALL feature가 존재하고, `reasoning_trace.applied_rules`에 `"R-cross: SCAFFOLD → +FALL"`이 포함됨을 assert. shadow reject가 있는 케이스에서 `reasoning_trace.reasoner_rejects` non-empty.
- **edge 무결성(step 3)**: 모든 `feature_to_sr`/`sr_to_penalty` edge의 양끝 노드가 각 node-list에 존재함(dangling edge 0)을 property test로 검증.
- **프론트**: ReasoningTracePanel 스냅샷 테스트로 `[추론]` 배지가 rule_derived feature에만 붙고 edge가 렌더됨 확인.

**rollback**: 신규 필드 default-empty라 step 1–2는 프론트 렌더만 끄면 사실상 무영향(백엔드 필드는 무해 잔존). step 3 edge 조립은 `_build_reasoning_trace` 내 별도 헬퍼라 한 함수 revert로 원복. `apply_rules`의 `derived_codes` 반환은 기존 키 미변경(additive)이라 호환.

**dependsOn**: A3-02 version stamping(WS-PROV) — step 3의 edge `justified_by`에 버전 pin을 붙이려면 선행이면 이상적이나, edge 자체는 버전 없이도 착수 가능(version pin은 후속 보강). step 1–2는 의존 없음.

**decisionNeeded**: 없음. (edge `justified_by`에 어떤 id를 넣을지 — SWRL rule id vs SHACL shape id vs PG mapping source — 는 reasoner_rejects의 `axiom_pair`/applied_rules 문자열을 우선 사용하고, 정식 axiom id 부여는 B6 이후로 미룸. 모델 결정 불요.)

---
