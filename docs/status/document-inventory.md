# 프로젝트 문서 인벤토리

> 작성일: **2026-05-20** · 기준: origin/main `164de5a` (Hazard-Direct Pivot 완주)
> 목적: arch-bot 모노레포의 모든 사람-관리 문서 현황을 한눈에 파악. 각 문서의 역할 + 최신성 상태.
> 갱신 정책: 대형 sprint 완료 후 또는 문서 구조 변경 시 갱신.

이 문서는 [docs/README.md](../README.md)(문서 색인)와 별개로, **문서 자체의 최신성·정합성 점검** 결과를 담는다.

---

## 1. 검증 기준

| # | 기준 |
|---|---|
| C1 | 박힌 commit hash / "최신 갱신일"이 현재 상태(`164de5a`, 2026-05-19) 반영 |
| C2 | hazard-direct pivot 반영 필요 문서인가 |
| C3 | baseline metric이 정본([evaluation-baseline.md](evaluation-baseline.md))과 일치 |
| C4 | 문서 색인(README류)이 실제 파일 목록과 일치 |
| C5 | 깨진 markdown 링크 없음 |

**append-only 문서**(`dev-notes/*`, `governance/cleanup-log.md`, `status/*-2026-*.md` 스냅샷, 파이프라인 `phase*_step*`): 과거 기록 보존, 신규 항목만 추가.

---

## 2. 디렉토리 구조 (사람-관리 문서)

```
arch-bot/
├── README.md                      프로젝트 개요 (변동성 낮음)
├── CLAUDE.md                      Claude Code 자동 로드 메타 규칙
│
├── docs/                          63 md — 거버넌스/아키텍처/온톨로지 설계
│   ├── README.md                  문서 색인 (단일 진입점)
│   ├── architecture/  (10)        시스템 4-Layer + 팀/repo 구조
│   ├── status/        (15)        baseline 정본 + 검증 스냅샷 + 본 인벤토리
│   ├── workplans/     (6)         활성 워크플랜
│   ├── dev-notes/     (16)        Phase/Tier 실행 runbook (append-only)
│   ├── ontology/      (7)         온톨로지 5-Layer(namespace) 설계
│   ├── governance/    (5)         모노레포 운영·데이터 거버넌스
│   ├── backlog/       (2)         리팩토링 후보 큐
│   └── deliverables/  (2)         최종 산출물 요약
│
├── data-team/                     데이터팀 (1~5단계)
│   ├── README.md
│   ├── 01-parsing/.../manifest/README.md
│   ├── 02-extraction/pipe-A/      CLAUDE+plan+status + phase*_step* 11 + agents 2
│   ├── 02-extraction/pipe-B/      CLAUDE+plan+status + phase*_step* 4 + agents 2 + agent-prompts
│   ├── 03-validation/pipe-C/      CLAUDE+plan+status
│   ├── 04-ontology-export/README.md
│   └── 05-enrichment/README.md
│
├── ontology-team/                 온톨로지팀 (6단계)
│   └── README.md
│
├── serving-team/                  서빙팀 (7~8단계)
│   ├── README.md
│   ├── 07-materialization/README.md
│   └── 08-app/README.md
│
└── shared/README.md               팀 간 공유
```

**자동 생성 산출물 (검증 제외 — 생성 스크립트가 정본)**:
- `ontology-team/06-reasoning/ontology/serving-validation-report-*` (24)
- `ontology-team/06-reasoning/ontology/serving-workprocess-alignment-*.md` (8)
- `data-team/02-extraction/pipe-B/data/manual-enrichment-*` (82)
- `data-team/05-enrichment/runtime-artifacts/{ontoclean_report,synthetic_audit_summary}.md` (2)
- `ontology-team/06-reasoning/visualization/dashboard.html` + `dashboard-data.js` (assemble 산출)

---

## 3. docs/ 문서별 상태표

범례: ✅ 최신 · ⚠️ stale (조치 필요) · 📌 append-only (보존) · 🔒 불변 참조

### architecture/ (10)

| 문서 | 역할 | 상태 |
|---|---|---|
| README.md | architecture 색인 | ⚠️ "핵심 통찰" hazard-direct 미반영 |
| 4-layer-architecture.md | Layer 0-4 전체 구조 | ⚠️ hazard-direct path 미반영 |
| ontology-learning-layer.md | Layer 4 7-module 정밀 설계 | ⚠️ hazard.name auto-register 미반영 |
| llm-dependency-evolution.md | LLM 의존 폐지 path | ⚠️ hazard-direct 미반영 |
| team-structure.md / stage-mapping.md / inter-stage-interfaces.md | 팀·9단계·인터페이스 | ✅ (구조 불변) |
| repo-split-plan.md / open-source-readiness.md | repo 분리·오픈소스 | ✅ (구조 불변) |
| source-provenance.md | PROV-O 출처 레이어 | ✅ |

### status/ (15)

| 문서 | 역할 | 상태 |
|---|---|---|
| current-session.md | 다음 세션 진입 지침 | ✅ 2026-05-19 |
| evaluation-baseline.md | baseline 메트릭 **정본** | ✅ 2026-05-19 |
| document-inventory.md | 본 문서 | ✅ 신규 |
| README.md | status 색인 | ⚠️ 7개 스냅샷 색인 누락 |
| `*-2026-05-*.md` 스냅샷 (11) | 시점별 검증 보고서 | 📌 보존 |

### workplans/ (6)

| 문서 | 역할 | 상태 |
|---|---|---|
| llm-accelerated-ontology-engineering.md | 메인 plan | ✅ 2026-05-19 |
| hazard-direct-architecture-pivot.md | 본 sprint plan (완주) | ✅ 2026-05-19 |
| she-matcher-broadness-refactor.md | 후행 sprint plan | ✅ |
| README.md | workplans 색인 | ⚠️ 메인 plan 상태 + hazard-direct/she-matcher 누락 |
| llm-domain-guard.md / part3-synthetic-en-cleanup.md | 선행·완료 워크플랜 | 📌 보존 |

### dev-notes/ (16) · ontology/ (7) · governance/ (5) · backlog/ (2) · deliverables/ (2)

| 그룹 | 상태 |
|---|---|
| dev-notes/* (phase-g.1-4, t4-*, hazard-direct-phase1-2, F.1-3, moellab 등) | 📌 append-only, 모두 최신 |
| ontology/00-05 (5-Layer namespace 설계) | ✅ TBox 설계 불변 (hazard-direct는 service layer, TBox 무변경) |
| governance/cleanup-log.md | ⚠️ 2026-05-18·19 sprint 항목 누락 (prepend 필요) |
| governance/data-governance / monorepo-transition / repositories / ontology-learning-references | 🔒 불변 정책 |
| backlog/refactor-candidates.md + README | ✅ |
| deliverables/ontology-ai-system-summary.md | 🔒 원본 보고서 요약 (불변 참조) |

### 루트 + 팀 + 파이프라인

| 그룹 | 상태 |
|---|---|
| README.md / CLAUDE.md | ✅ (변동성 낮은 메타 — sprint 결과는 current-session.md 참조) |
| docs/README.md | ⚠️ 갱신일 2026-05-17 + dev-notes/ 색인 누락 |
| serving-team/README.md | ⚠️ hazard-direct 신규 service 미반영 |
| data-team/README.md / ontology-team/README.md | ✅ (hazard-direct는 serving 작업) |
| 파이프라인 pipe-A/B/C `phase*_step*`, `plan_*`, `status_*` | 📌 1회성 작업 기록, 보존 |

---

## 4. stale 수정 대상 요약

| 우선 | 문서 | 조치 |
|---|---|---|
| 1 | docs/README.md | 갱신일·HEAD, dev-notes/ 색인 행 추가, 읽기 순서 현행화 |
| 2 | docs/governance/cleanup-log.md | 2026-05-18·19 sprint 항목 prepend |
| 3 | docs/status/README.md | 7개 status 스냅샷 색인 추가 |
| 4 | docs/workplans/README.md | 메인 plan 상태 + hazard-direct/she-matcher 행 추가 |
| 5 | docs/architecture/4-layer-architecture.md | Layer 0 hazards[] + hazard-direct path |
| 6 | docs/architecture/ontology-learning-layer.md | Module 4.1 hazard.name auto-register |
| 7 | docs/architecture/llm-dependency-evolution.md | hazard-direct 정식 path 명시 |
| 8 | docs/architecture/README.md | "핵심 통찰" hazard-direct 반영 |
| 9 | serving-team/README.md | hazard-direct service 추가 반영 |
| 10 | scripts/verify_session_docs.py | hazard-direct commits/docs/metrics 등록 |

---

## 5. 검증 OK (수정 불필요)

- `status/current-session.md`, `evaluation-baseline.md` — 2026-05-19 최신
- `workplans/hazard-direct-architecture-pivot.md`, `llm-accelerated-ontology-engineering.md` — 최신
- `dev-notes/*` 16개 — append-only runbook, 모두 최신
- `ontology/00-05` — 온톨로지 namespace 5-Layer 설계. hazard-direct는 service layer 추가이며 OWL TBox 무변경 → 설계 문서 불변
- `deliverables/ontology-ai-system-summary.md` — 원본 PDF 보고서 요약 (설계 기준 불변 참조)
- 파이프라인 `phase*_step*` 등 — 1~3단계 1회성 작업 기록
