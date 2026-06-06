# OWA→CWA 보완 — Phase 1 진행 handoff (worktree)

> 이 워크트리에서 진행 중인 OWA→CWA 보완 작업의 **resume point**. 정본 plan: [owa-cwa-remediation-plan.md](owa-cwa-remediation-plan.md).

## 위치 / 브랜치
- worktree: `C:\project\arch-bot\.claude\worktrees\owa-cwa-remediation` (= `/mnt/c/project/arch-bot/.claude/worktrees/owa-cwa-remediation` under WSL)
- branch: `worktree-owa-cwa-remediation` (base origin/main `86cdcdc`), **미push**(로컬 워크트리)

## 커밋 (`fd61575` → `d775f4b`)
`fd61575` plan · `f1650d5` P0 가시화 · `5267db6` P0 safety-be · `8f5f281` P0 fe · `4ee687d` P1 OBS-1 · `13ea7b2` P1 SAFETY-5 · `a1e1e0e` baseline 재캡처 · `3813ded` handoff · `d775f4b` **P1 C묶음(GATE-4~8)**

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

## ⛔ SAFETY-2 backed out — 재시도 주의
naive ppe/env 배선 → **penalty −0.042 / overall −0.072 VETOED**(vs 정직한 baseline). 근본: ppe/env가 `min_matched_dims=2`를 충족 → 약한 primary+ppe만으로 spurious SHE 매치 → 잉여 penalty. **재설계 방향**: ppe/env는 **corroborate/boost만**(min_matched_dims 미충족), 또는 SAFETY-5 display-only로 충분(현재 채택). 편집은 `git checkout`으로 revert됨 — 코드에 없음.

## 다음: Phase 1 잔여 (A·C 완료, 모두 서빙측·측정 항목)
- **DRIFT**: DRIFT-1(materialization_runs run_id 스탬프, legal-critical) · DRIFT-2(ontology_pg_drift_check 양방향 symmetric-diff 게이트) · DRIFT-3(penalty prune, DRIFT-2 후) · DRIFT-4(빌드→서빙 PG baseline 결속) · DRIFT-6(startup 벡터 health probe, DRIFT-4/5 후).
- **OBS**: OBS-3(analysis_log 경량 집계기, OBS-4 후) · OBS-4(per-stage drop attribution) · OBS-5/6(penalty 로더 source 스탬프 + startup active probe) · OBS-7(벡터 recall degrade 가시화).
- **PROV**: PROV-2(evidence_confidence discount — 라우팅 영향·L·PROV-4 선행) · PROV-4(byte-identity harness) · PROV-1(RiskFeature origin, apply_rules 계측 → DEEP-3와).
- **DEEP**: DEEP-2(BFO 축 detector+CON-strict, 모델결정 무관 선행 가능) · DEEP-1(dual-path MERGE, **EVAL-1 의존**) · DEEP-3(ReasoningTrace edge graph, PROV-1 후).
- **gold 의존(Phase 2 경계)**: EVAL-1(replay hazards 주입 → guide_recall@K/top1 FN veto) → EVAL-2(gold set 30→100) → GATE-2/3, GATE-9, OBS-8, EVAL-3/5. recall 상향(GATE-2/3, DEEP-1)은 **EVAL-1 머지 후에만** 진입(plan 안전 불변식).

### ⚠️ C묶음 중 발견(별건·무관)
- `verify_fuseki_inference.sh`가 repo에 **CRLF로 저장**(pre-existing, HEAD blob에 CR). 순수 WSL `bash -n` 시 CRLF 구문오류. 내 V0 추가분 자체는 valid bash(CR strip 후 확인). 전체 파일 LF 정규화는 별도 정리(autocrlf 정책 확인 후).

## 환경 runbook (재발견 방지)
- **backend venv (WSL 전용)**: `/mnt/c/project/arch-bot/serving-team/08-app/backend/.venv/bin/python` (py3.14). git-bash엔 venv 없음.
- **PG/Fuseki**: `kosha-pg`(localhost:5432)·`kosha-fuseki` 컨테이너 가동 중.
- **replay**: `cd <worktree>/serving-team/08-app/backend && <venv> scripts/replay_synthetic_observations.py --output <PERSISTENT>`. ⚠️ **/tmp는 WSL 재시작 시 wipe** → `/mnt/c` 경로로 출력. ~수십분 → background. (gate는 summary만 읽음 — task output의 summary JSON으로 baseline 재구성 가능.)
- **gate**: `<venv> scripts/regression_gate.py <current.json> --tolerance 0.02` (DEFAULT_BASELINE=`replay_baseline_v3.json`). **정직한 baseline 비교 필수**(stale가 회귀 마스킹). WSL 따옴표 안 `$?`/`$VAR`/`PIPESTATUS`는 외부 shell 값 잡힘 → 종료코드는 `cmd >/dev/null && echo OK || echo FAIL`로.
- **frontend tsc**: WSL node 없음·esbuild linux 전용 → Vite 실행 불가. **tsc만** = Windows node + node_modules **junction**: `New-Item -ItemType Junction <worktree>/frontend/node_modules -Target <main>/frontend/node_modules` 후 `node .\node_modules\typescript\bin\tsc --noEmit`.
- **backend 로직 smoke**: 스크립트를 backend 디렉토리에 두고(`import app` 위해) `<venv> _smoke.py` 실행, 후 삭제.
- **replay 후**: `analysis_log.jsonl` 수정됨 → `git checkout -- data-team/05-enrichment/runtime-artifacts/analysis_log.jsonl` (런타임 산출물, 커밋 제외).
- **FN-보수 결정 잠금**(plan §2): D1=a, D2=a, D4=floor 0.20, D5=off, D8=tol 0.005, D10=penalty graceful hard-fail, D11=floor 0.5.
