# OWA→CWA 보완 — Phase 1 진행 handoff (worktree)

> 이 워크트리에서 진행 중인 OWA→CWA 보완 작업의 **resume point**. 정본 plan: [owa-cwa-remediation-plan.md](owa-cwa-remediation-plan.md).

## 위치 / 브랜치
- worktree: `C:\project\arch-bot\.claude\worktrees\owa-cwa-remediation` (= `/mnt/c/project/arch-bot/.claude/worktrees/owa-cwa-remediation` under WSL)
- branch: `worktree-owa-cwa-remediation` (base origin/main `86cdcdc`), **미push**(로컬 워크트리)

## 커밋 (`fd61575` → `a1e1e0e`)
`fd61575` plan · `f1650d5` P0 가시화 · `5267db6` P0 safety-be · `8f5f281` P0 fe · `4ee687d` P1 OBS-1 · `13ea7b2` P1 SAFETY-5 · `a1e1e0e` baseline 재캡처

## 완료
- **Phase 0 (8)**: OBS-2, GATE-1, DRIFT-5(core), EVAL-4(core), SAFETY-1, SAFETY-3, SAFETY-4, PROV-3 — 전체 검증(replay 2360/0err + gate PASS + tsc exit0 + UNKNOWN 시각 확인).
- **Phase 1**: OBS-1(FN-방향 veto, mutation 검증) · baseline 재캡처(현 PG 기준 v3, self-test PASS) · SAFETY-5(display-only 미분류 위험 surfacing).

## ⛔ SAFETY-2 backed out — 재시도 주의
naive ppe/env 배선 → **penalty −0.042 / overall −0.072 VETOED**(vs 정직한 baseline). 근본: ppe/env가 `min_matched_dims=2`를 충족 → 약한 primary+ppe만으로 spurious SHE 매치 → 잉여 penalty. **재설계 방향**: ppe/env는 **corroborate/boost만**(min_matched_dims 미충족), 또는 SAFETY-5 display-only로 충분(현재 채택). 편집은 `git checkout`으로 revert됨 — 코드에 없음.

## 다음: Phase 1 **C 묶음** (ontology, 서빙 무영향·precision 위험 0)
- GATE-4 `make consistency-gate` (check_disjoint + Fuseki Openllet owl:Nothing live ASK)
- GATE-5 `local_consistency_check --gate` SHACL conforms=false→exit1 버그
- GATE-6 phase-g3/g4 import Makefile prerequisite hard-wire
- GATE-7 `kosha-rules-r14-r30-shacl-construct.ttl` R-14/R-15 `haz:Hazard`(폐지) → `haz:AccidentType` repoint
- GATE-8 per-rule fire-coverage detector (`run_shacl_rules.py`)
- 파일: `ontology-team/06-reasoning/ontology/{scripts,Makefile,*-shacl-construct.ttl}`, `KoshaFusekiServer.java`

### 그 외 보류
- PROV-1 (apply_rules 계측 필요 → DEEP-3와 함께) · DRIFT-5 stamp/startup·EVAL-4 oracle-rank (→DRIFT-4/6·EVAL-1)
- EVAL-1 guide_recall@K + GATE-2/3·DEEP-1: synthetic에 `expected_guide`/`hazards` 없음 → **gold(EVAL-2/phase2) 의존**

## 환경 runbook (재발견 방지)
- **backend venv (WSL 전용)**: `/mnt/c/project/arch-bot/serving-team/08-app/backend/.venv/bin/python` (py3.14). git-bash엔 venv 없음.
- **PG/Fuseki**: `kosha-pg`(localhost:5432)·`kosha-fuseki` 컨테이너 가동 중.
- **replay**: `cd <worktree>/serving-team/08-app/backend && <venv> scripts/replay_synthetic_observations.py --output <PERSISTENT>`. ⚠️ **/tmp는 WSL 재시작 시 wipe** → `/mnt/c` 경로로 출력. ~수십분 → background. (gate는 summary만 읽음 — task output의 summary JSON으로 baseline 재구성 가능.)
- **gate**: `<venv> scripts/regression_gate.py <current.json> --tolerance 0.02` (DEFAULT_BASELINE=`replay_baseline_v3.json`). **정직한 baseline 비교 필수**(stale가 회귀 마스킹). WSL 따옴표 안 `$?`/`$VAR`/`PIPESTATUS`는 외부 shell 값 잡힘 → 종료코드는 `cmd >/dev/null && echo OK || echo FAIL`로.
- **frontend tsc**: WSL node 없음·esbuild linux 전용 → Vite 실행 불가. **tsc만** = Windows node + node_modules **junction**: `New-Item -ItemType Junction <worktree>/frontend/node_modules -Target <main>/frontend/node_modules` 후 `node .\node_modules\typescript\bin\tsc --noEmit`.
- **backend 로직 smoke**: 스크립트를 backend 디렉토리에 두고(`import app` 위해) `<venv> _smoke.py` 실행, 후 삭제.
- **replay 후**: `analysis_log.jsonl` 수정됨 → `git checkout -- data-team/05-enrichment/runtime-artifacts/analysis_log.jsonl` (런타임 산출물, 커밋 제외).
- **FN-보수 결정 잠금**(plan §2): D1=a, D2=a, D4=floor 0.20, D5=off, D8=tol 0.005, D10=penalty graceful hard-fail, D11=floor 0.5.
