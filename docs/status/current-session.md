# 현재 세션 / 다음 세션 시작 지침

최신 갱신일: 2026-05-16

이 문서는 다른 Codex/LLM 세션이 현재 상태를 빠르게 이어받기 위한 시작점이다. 변동성 높은 작업 상태(현재 baseline, 다음 작업 큐 등)를 담는다.

불변 메타 규칙(5개 디렉토리 역할, 폐기 용어, 절대 금지)은 루트 [../../CLAUDE.md](../../CLAUDE.md) 참고.

## 1. 먼저 읽을 문서 순서

1. [../../README.md](../../README.md)
2. [../../CLAUDE.md](../../CLAUDE.md)
3. [../README.md](../README.md) — 문서 색인
4. [evaluation-baseline.md](evaluation-baseline.md) — 현재 baseline 정본
5. [../governance/monorepo-transition.md](../governance/monorepo-transition.md)
6. [../governance/data-governance.md](../governance/data-governance.md)
7. [../governance/repositories.md](../governance/repositories.md)
8. [../architecture/source-provenance.md](../architecture/source-provenance.md)
9. [../workplans/llm-domain-guard.md](../workplans/llm-domain-guard.md)
10. [../ontology/00-integrated-structure.md](../ontology/00-integrated-structure.md)
11. [../../OHS/README.md](../../OHS/README.md)
12. [../backlog/refactor-candidates.md](../backlog/refactor-candidates.md)
13. [../../koshaontology/pipe-A/status_pipea.md](../../koshaontology/pipe-A/status_pipea.md)
14. [../../koshaontology/pipe-B/status_pipeb.md](../../koshaontology/pipe-B/status_pipeb.md)
15. [../../koshaontology/pipe-C/status_pipec.md](../../koshaontology/pipe-C/status_pipec.md)

레이어별 세부 구조 (`../ontology/`):

```text
01-law-layer.md
02-sr-layer.md
03-risk-situation-layer.md
04-guide-layer.md
05-penalty-layer.md
```

## 2. OHS 실행

백엔드:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

프론트:

```bash
cd /mnt/c/project/arch-bot/OHS/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

브라우저:

```text
http://127.0.0.1:5173/ohs/
```

주의:

- `OPENAI_API_KEY`가 없으면 실제 이미지/텍스트 분석은 503이 날 수 있다.
- PostgreSQL은 `postgresql://kosha:1229@localhost/kosha` 기준이다.

## 3. 현재 검증 기준선

Accepted runtime baseline: `ci_cross_guide_broad_only_guard1` (2026-05-16).
Previous accepted baseline: `ci_unrelated_action_filter1`.

**전체 메트릭 / 변경 설명 / historical baseline은 [evaluation-baseline.md](evaluation-baseline.md) 정본을 참조한다. 다른 곳에 복제하지 않는다.**

핵심 요약:

```text
synthetic Stage 2~5 v1~v10 total: 2,360
Guide mismatch: 5    NO_TOP: 88
CI no_action: 495    CI guide_boundary_mismatch: 1
CI broad_sr_only: 0  CI needs_review_used: 0
serving ontology validation: PASS (hard 0, warning 0)
actual response 240 status changed: 0
```

## 4. 검증 명령

Python 문법 검증:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python -c "import pathlib; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in pathlib.Path('.').rglob('*.py') if '__pycache__' not in p.parts]; print('compile ok')"
```

프론트 빌드:

```bash
cd /mnt/c/project/arch-bot/OHS/frontend
npm run build
```

Monorepo import 검증:

```bash
cd /mnt/c/project/arch-bot
git ls-files OHS | wc -l
git ls-files koshaontology | wc -l
git ls-files kosha-guides/parsed | wc -l
git ls-files | rg '\.env|node_modules|\.venv|\.dev-logs|pictures-json/reports/|kosha-guides/.+\.pdf'
```

기대 count:

```text
OHS: 161
koshaontology: 2268
kosha-guides/parsed: 1038
```

## 5. 바로 이어서 할 일

1. 새 작업은 root `arch-bot/main`에서 수행한다.
2. 작업 전 `git status --short --branch`로 clean 상태를 확인한다.
3. Guide 품질 작업은 `ci_cross_guide_broad_only_guard1` 기준으로 이어간다.
4. `she-stage3-new-pattern-candidates-reference-guard1` 230건은 runtime SHE 확정으로 import하지 않는다. `true_new_she`도 첫 사이클에서는 review-only다.
5. NO_TOP 88건은 `accepted empty top 31`, `source/taxonomy review 57`, `runtime repair candidate 0`으로 분리됐다. 억지로 broad alias/support를 추가하지 않는다.
6. 다음 구조적 보강 대상은 `CI no_action 495`, `CI guide_boundary_mismatch 1`의 남은 꼬리다. `CI broad_sr_only`는 13건에서 0건으로 해소했다. 현장에 맞는 Guide가 없으면 억지 top Guide를 만들지 않는다. `B_wrong_guide_boundary`와 `D_safe_scene_overpromoted`는 0건이다.
7. parent context는 검색 확장에만 쓰고, parent-only match는 confirmed/status/penalty/direct SR/표준절차 top 후보를 만들 수 없다.
8. photo_matchability는 표준절차 top lane에만 적용한다. 즉시조치, SHE status, SR evidence, penalty path에는 적용하지 않는다.
9. 온톨로지 검증 경고는 `structure_issue`, `data_issue`, `algorithm_issue`, `corpus_gap`, `review_only`로 나눠 원천 artifact 쪽에서 정리한다.
