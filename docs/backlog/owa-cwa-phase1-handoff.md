# OWA→CWA 보완 — Phase 1 진행 handoff (worktree)

> 이 워크트리에서 진행 중인 OWA→CWA 보완 작업의 **resume point**. 정본 plan: [owa-cwa-remediation-plan.md](owa-cwa-remediation-plan.md).

## 위치 / 브랜치
- worktree: `C:\project\arch-bot\.claude\worktrees\owa-cwa-remediation` (= `/mnt/c/project/arch-bot/.claude/worktrees/owa-cwa-remediation` under WSL)
- branch: `worktree-owa-cwa-remediation` (base origin/main `86cdcdc`), **미push**(로컬 워크트리)

## 커밋 (`fd61575` → `2496082`)
`fd61575` plan · `d775f4b` **P1 C묶음(GATE-4~8)** · `b44aad9` **P1 EVAL-1** · `ba23bac` handoff · `c72e89a` **P1 GATE-2** · `4f491a2` handoff · `cd0ec9f` **P1 GATE-3** · `2496082` **P1 DEEP-1** · (+baseline v4-alive 정정). (중간: f1650d5/5267db6/8f5f281 P0 · 4ee687d OBS-1 · 13ea7b2 SAFETY-5 · a1e1e0e/3813ded/dea6987 baseline·handoff)

## 완료
- **Phase 0 (8)**: OBS-2, GATE-1, DRIFT-5(core), EVAL-4(core), SAFETY-1, SAFETY-3, SAFETY-4, PROV-3 — 전체 검증(replay 2360/0err + gate PASS + tsc exit0 + UNKNOWN 시각 확인).
- **Phase 1 A**: OBS-1(FN-방향 veto, mutation 검증) · baseline 재캡처(현 PG 기준 v3, self-test PASS) · SAFETY-5(display-only 미분류 위험 surfacing).
- **Phase 1 C (GATE-4~8, `d775f4b`)**: 온톨로지 일관성·dead-rule 하드게이트(서빙 무영향).
  - GATE-7 repoint `haz:Hazard`(폐지)→`haz:AccidentType` (R-14/R-15). **단일 dead clause가 R-14/15 직접 + R-24→R-25→R-28→R-30 penalty 체인까지 6룰 cascade-collapse**시켰음을 mutation으로 입증. repoint 후 demo-chain 16/16 fire.
  - GATE-8 `run_shacl_rules.py --per-rule`(closure 기준 룰별 fire, 0-fire→exit1; $this 미참조 룰은 targetClass 주입) + **신규 `check_rule_tbox_liveness.py`**(CONSTRUCT body type-test 클래스 정적 liveness, fixture 없이 dead class 적발) + `verify_rule_parity.py` stale-경로 crash 수정+비-vacuous 가드. `make verify-rules`/`verify-manifest` 배선.
  - GATE-5 `local_consistency_check.py --gate`(기존 항상 return 0 버그 → conforms=false&violations>0 시 exit1, fail-closed; CQ는 advisory).
  - GATE-4 `make consistency-gate` = check_disjoint(offline) + local_consistency --gate(offline) + Fuseki Openllet owl:Nothing live ASK(가동 시). `verify_fuseki_inference.sh` V0 추가.
  - GATE-6 `consistency-gate`를 `phase-g1-import` prerequisite로 hard-wire(g2/3/4 신설 시 동일 패턴).
  - **검증**: `make consistency-gate` PASS(**live Openllet 포함** — Fuseki 가동중 owl:Nothing 0 확인) · `make verify-rules` 16/16 · GATE-5 TBox-only exit0 / 주입 disjoint 음성테스트 exit1 · GATE-8 mutation 6-rule dead exit1. **서빙(backend/app) 무변경 → replay N/A**(검증은 각 게이트 직접 실행).
- **Phase 1 EVAL-1 (`b44aad9`)**: replay에 hazards[] 주입 → hazard-direct ON 경로(guide/ci/penalty)가 replay에서 실제 발동(v3는 dormant). **버그정정**: hazard.name은 문장(plan 처방)이 아니라 **canonical 코드**여야 normalize 매핑됨(문장은 0 guide). 신규 지표 `guide_coverage_rate`(0.6718)·`she_recall_miss_rate`(0.4168) FN-비대칭 hard veto + `guide_recall@3`/`top1` observe-only(gold 대기). **legacy 6키(she/sr/penalty/overall/fp/fn) v3와 byte-identical** → ON 활성이 무회귀 → **v4 baseline 채택**(regression_gate `DEFAULT_BASELINE` + Makefile `F1_BASELINE` v3→v4). mutation: ON guide drop → `guide_coverage_rate` ok(1.0)→VETOED(0.0), she_recall_miss는 불변(SHE 독립). **이로써 recall 상향 블록(GATE-2/3·DEEP-1) 진입 가능**.
- **v4 baseline 정정(semantic-alive)**: 위 EVAL-1 v4는 워크트리 Chroma 빈 stub 탓에 semantic-dead로 캡처됐었음. chromadb junction 후 **semantic-alive + rerank-off로 v4 재캡처**. 결과: **gated 키(she/sr/penalty/overall/fp/fn) + guide_coverage_rate(0.6718) + she_recall_miss_rate(0.4168) 전부 v4-dead와 동일** — FN veto 지표는 semantic 활성/비활성에 robust. 차이는 비-게이트 stat뿐(avg_on_guides 4.12→2.62, avg_proc 4.48→3.27 — semantic이 더 selective). `replay_baseline_v4.json`을 semantic-alive 값으로 교체(`config` 필드에 semantic_recall on/rerank off 명시).
- **Phase 1 GATE-2 (`c72e89a`)**: semantic attach 절대 cosine floor + no-match sentinel. RRF가 버린 top vscore를 surface, `OHS_SEMANTIC_COSINE_FLOOR`(기본 0=off=무회귀) 미만 후보 드롭, 전부 거부 시 sentinel. 검증: floor=0 byte-identical(full replay) · floor 로직 unit test(0.3→below-floor 3개 드롭, 0.9→sentinel) · floor=0.45 LIVE(semantic alive) coverage/count 안정(**facet-direct fallback이 recall 보존 = FN-safe by design**; floor 효과는 precision=provenance, judge eval로 별도 검증). relevant vscore ~0.45라 D4 시작값 0.20은 보수적.
- **Phase 1 GATE-3 (`cd0ec9f`)**: shadow_reasoner log-only→opt-in domain hard-reject. `shadow_validate`(analysis_log write-only로만 쓰이던 도메인 모순 신호)를 기본 served 경로(semantic attach 직전)에서 `level==vetted` & `confidence≥OHS_DOMAIN_REJECT_CONF`(0.9)만 hard-drop. `shadow_reasoner.domain_reject_codes` 신설 + config `OHS_ENABLE_DOMAIN_REJECT`(기본 False) + `OHS_DOMAIN_REJECT_CONF`(0.9). **semantic(hazard-direct) 후보에만 적용** → facet은 무영향(DEEP-1 merge가 재보존), 전부 드롭 시 facet 생존(FN-safe). 검증: 단위 7 assertions(off=무회귀/vetted&conf만 drop/low-conf·candidate FN보수 무시) + **full replay(semantic-alive,rerank-off,default-off) → v4 12지표 전부 delta 0.0000 byte-identical PASS**. D5: 운영 기본 opt-in(off), default-on은 사용자 결정.
- **Phase 1 DEEP-1 (`2496082`)**: 이중경로 guide overwrite(`guide_rows=_sem_guides`)→corroboration MERGE. facet CI-corroboration(`ci_hit_count`)·`work_process_steps` grounded guide가 침묵 제거되던(A8) 문제 해소. `_merge_guide_rows`(both=facet 베이스 구조필드 보존+score max+§근거, **불변식 결과⊇facet**) + `source_path`/`review_required`(StandardProcedure, 표시전용) + `path_agreement`(guides·SR별 she_only/hazard_direct_only/both, SR union 전 계산→정확) emit + `scripts/replay_dualpath_agreement.py` 집계기. 검증: 단위 A~F(불변식·FN-safety·overwrite동등·전파) + **full replay → regression_gate vs v4 12지표 delta 0.0000 PASS**, avg_procedures **3.27→6.65**(positive 3.7→7.55)만 상승=보존된 facet guide(전 corpus she_only **7990개**) grounding 가시화, negative 0.54 불변(FP 무증가). path_agreement 1393 엔트리, guide 합의율 1.67%(overwrite가 facet 8214 guides 버리던 것 실측 확증). **v4가 유효 gate baseline 유지**(신규 gated 키 없음); independent_recall은 EVAL-2 gold 의존 연기. **frontend 배지(`354201f`)**: 표준개선절차 패널에 source_path(양경로 합의/SHE-facet/위험직결) + review_required(⚠검토필요) 배지 렌더(`ProcedurePathBadge`/`ReviewRequiredBadge`, 표시전용), tsc --noEmit exit0.

## ⛔ SAFETY-2 backed out — 재시도 주의
naive ppe/env 배선 → **penalty −0.042 / overall −0.072 VETOED**(vs 정직한 baseline). 근본: ppe/env가 `min_matched_dims=2`를 충족 → 약한 primary+ppe만으로 spurious SHE 매치 → 잉여 penalty. **재설계 방향**: ppe/env는 **corroborate/boost만**(min_matched_dims 미충족), 또는 SAFETY-5 display-only로 충분(현재 채택). 편집은 `git checkout`으로 revert됨 — 코드에 없음.

## 다음: Phase 1 잔여 (A·C 완료, 모두 서빙측·측정 항목)
- **DRIFT**: DRIFT-1(materialization_runs run_id 스탬프, legal-critical) · DRIFT-2(ontology_pg_drift_check 양방향 symmetric-diff 게이트) · DRIFT-3(penalty prune, DRIFT-2 후) · DRIFT-4(빌드→서빙 PG baseline 결속) · DRIFT-6(startup 벡터 health probe, DRIFT-4/5 후).
- **OBS**: OBS-3(analysis_log 경량 집계기, OBS-4 후) · OBS-4(per-stage drop attribution) · OBS-5/6(penalty 로더 source 스탬프 + startup active probe) · OBS-7(벡터 recall degrade 가시화).
- **PROV**: PROV-2(evidence_confidence discount — 라우팅 영향·L·PROV-4 선행) · PROV-4(byte-identity harness) · PROV-1(RiskFeature origin, apply_rules 계측 → DEEP-3와).
- **DEEP**: DEEP-2(BFO 축 detector+CON-strict, 모델결정 무관 선행 가능) · ~~DEEP-1~~ ✅완료(`2496082`) · DEEP-3(ReasoningTrace edge graph, PROV-1 후).
- **recall 상향 블록 ✅전부 완료**(EVAL-1 `guide_coverage_rate` FN veto 위에서 안전): GATE-2(`c72e89a`) · GATE-3(`cd0ec9f`) · DEEP-1(`2496082`) 모두 full replay regression PASS(v4 baseline, gated 12지표 delta 0.0000). DEEP-1 frontend 배지도 완료(`354201f`). **다음 후보 = (a)** DRIFT/OBS/PROV 서빙측 측정 항목 **(b)** DEEP-2(BFO 축, 온톨로지측 독립 선행) **(c)** DEEP-3(ReasoningTrace edge graph, PROV-1 후) **(d)** Phase 2 gold(EVAL-2, 사용자 D14 라벨링 결정 → GATE-9/OBS-8/EVAL-3/5 + EVAL-1 observe키 hard 승격). 검증은 `make f1-regression`(v4 baseline) + judge eval(precision).
- **gold 의존(Phase 2)**: EVAL-2(gold 30→100, 사용자 D14 라벨링 결정) → GATE-9·OBS-8·EVAL-3/5 + **EVAL-1의 guide_recall@K/top1 observe→hard 승격**(gold 안정화 + 2주, 결정 D13=B).

### ⚠️ C묶음 중 발견(별건·무관)
- `verify_fuseki_inference.sh`가 repo에 **CRLF로 저장**(pre-existing, HEAD blob에 CR). 순수 WSL `bash -n` 시 CRLF 구문오류. 내 V0 추가분 자체는 valid bash(CR strip 후 확인). 전체 파일 LF 정규화는 별도 정리(autocrlf 정책 확인 후).

## 환경 runbook (재발견 방지)
- **backend venv (WSL 전용)**: `/mnt/c/project/arch-bot/serving-team/08-app/backend/.venv/bin/python` (py3.14). git-bash엔 venv 없음.
- **PG/Fuseki**: `kosha-pg`(localhost:5432)·`kosha-fuseki` 컨테이너 가동 중.
- **replay**: `cd <worktree>/serving-team/08-app/backend && set -a && . <main>/backend/.env; set +a; <venv> scripts/replay_synthetic_observations.py --output <PERSISTENT>`. ⚠️ **/tmp는 WSL 재시작 시 wipe** → `/mnt/c` 출력. **WS-EVAL-1 후 hazards 주입으로 semantic attach 발동 → `.env`의 `OPENAI_API_KEY` 필요**(임베딩 호출, v3보다 느림 ~20–40분 → background). gate는 summary만 읽음.
- **gate**: `<venv> scripts/regression_gate.py <current.json> [--tolerance 0.02] [--fn-tolerance 0.005]` (DEFAULT_BASELINE=`replay_baseline_v4.json` = hazards-injected). **정직한 baseline 비교 필수**. FN-방향 키(positive_she_recall/she_recall_miss/guide_coverage_rate/she_recall_miss_rate)는 fn-tolerance(0.005)로 엄격. WSL 따옴표 안 `$?`/`$VAR`/`PIPESTATUS` + **PowerShell 안 `$VAR`도 호출 전 확장**(둘 다 변수 깨짐) → 종료코드는 `cmd >/dev/null && echo OK || echo FAIL`, 변수는 full path inline.
- **frontend tsc**: WSL node 없음·esbuild linux 전용 → Vite 실행 불가. **tsc만** = Windows node + node_modules **junction**: `New-Item -ItemType Junction <worktree>/frontend/node_modules -Target <main>/frontend/node_modules` 후 `node .\node_modules\typescript\bin\tsc --noEmit`.
- **⚠️ Chroma 벡터 인덱스(semantic attach)**: 워크트리 `serving-team/08-app/backend/data/chromadb`는 **gitignored → 빈 stub(0.19MB)**이라 `hybrid_search`가 0행 반환 → **semantic attach dead**(facet-direct만 작동). main은 967MB 정본. semantic-alive 검증/baseline엔 **junction 필수**: `Move-Item <wt>/data/chromadb <wt>/data/chromadb.empty-stub-bak; New-Item -ItemType Junction <wt>/data/chromadb -Target <main>/data/chromadb`(읽기전용 query, main 무변경). config 기본 `OHS_ENABLE_HYBRID_SEARCH=True`·`OHS_ENABLE_SEMANTIC_RERANK=True`(LLM/hazard·비결정적)·`OHS_ENABLE_GUIDE_SECTION=False`. **gate baseline은 `SEMANTIC_ATTACH_RERANK=off`(결정적 — rerank LLM은 매 gate run마다 ~2084콜·비결정적이라 회귀게이트 부적합)**. relevant-match vscore ~0.43-0.56 → GATE-2 floor 0.20은 보수적(실튜닝 ~0.45).
- **backend 로직 smoke**: 스크립트를 backend 디렉토리에 두고(`import app` 위해) `<venv> _smoke.py` 실행, 후 삭제.
- **replay 후**: `analysis_log.jsonl` 수정됨 → `git checkout -- data-team/05-enrichment/runtime-artifacts/analysis_log.jsonl` (런타임 산출물, 커밋 제외).
- **FN-보수 결정 잠금**(plan §2): D1=a, D2=a, D4=floor 0.20, D5=off, D8=tol 0.005, D10=penalty graceful hard-fail, D11=floor 0.5.
