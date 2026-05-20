# arch-bot 문서 색인

최신 갱신일: 2026-05-20 (Hazard-Direct Architecture Pivot 완주 + Phase G PG materialization + Tier 4 SWRL Pellet, main `164de5a`)

이 디렉토리는 `arch-bot` 모노레포의 모든 문서의 단일 진입점이다.
루트에는 `README.md`(짧은 진입)와 `CLAUDE.md`(Claude Code 자동 로드 메타)만 두고, 모든 콘텐츠는 여기 산하에 둔다.

## 하위 디렉토리

| 디렉토리 | 용도 |
|---|---|
| [governance/](governance/) | 모노레포 운영 정책, 데이터 거버넌스, repo 매핑, 정리 이력 |
| [ontology/](ontology/) | 온톨로지 5개 레이어(법령/SR/위험상황/가이드/벌칙) 구조 이해용 한글 설계 문서 |
| [architecture/](architecture/) | 시스템 아키텍처 (4-Layer + Layer 4 Ontology Learning 등) |
| [workplans/](workplans/) | 활성 워크플랜 (현재 진행 중인 단일 큰 작업의 상세 운영 문서) |
| [dev-notes/](dev-notes/) | Phase/Tier 실행 runbook + 결정 기록 (append-only) |
| [backlog/](backlog/) | 리팩토링 후보 백로그 (다주제 아이디어 큐) |
| [status/](status/) | 현재 baseline, 다음 작업 큐, 검증 메트릭, 문서 인벤토리 |
| [deliverables/](deliverables/) | 최종 산출물 요약 |

## 현재 기준 문서 (작업 진입 시 권장 읽기 순서)

루트:

1. [README.md](../README.md) — 프로젝트 개요
2. [CLAUDE.md](../CLAUDE.md) — 5개 디렉토리 역할 + 메타 규칙

docs:

3. [status/current-session.md](status/current-session.md) — 다음 세션 시작 지침
4. [status/evaluation-baseline.md](status/evaluation-baseline.md) — 현재 baseline 정본
5. [status/document-inventory.md](status/document-inventory.md) — 문서 현황·최신성 점검
6. [workplans/llm-accelerated-ontology-engineering.md](workplans/llm-accelerated-ontology-engineering.md) ⭐ — **메인 plan** (Phase 0~Hazard-Direct Pivot 진행 통합)
7. [workplans/hazard-direct-architecture-pivot.md](workplans/hazard-direct-architecture-pivot.md) — 최신 완료 sprint (Hazard-Direct Architecture Pivot)
8. [governance/monorepo-transition.md](governance/monorepo-transition.md) — 모노레포 전환 이력
9. [governance/data-governance.md](governance/data-governance.md) — 데이터 추적/제외 정책
10. [governance/repositories.md](governance/repositories.md) — 레포 매핑 + 외부 의존
11. [architecture/source-provenance.md](architecture/source-provenance.md) — 출처/근거 레이어 설계
12. [architecture/4-layer-architecture.md](architecture/4-layer-architecture.md) — Layer 0-4 전체 구조
13. [architecture/ontology-learning-layer.md](architecture/ontology-learning-layer.md) — Layer 4 7-module 정밀 설계
14. [workplans/llm-domain-guard.md](workplans/llm-domain-guard.md) — 활성 워크플랜
15. [ontology/README.md](ontology/README.md) → [00-integrated-structure.md](ontology/00-integrated-structure.md) → 01~05 레이어
16. [backlog/refactor-candidates.md](backlog/refactor-candidates.md) — 리팩토링 후보 큐

하위 프로젝트:

- [serving-team/08-app/README.md](../serving-team/08-app/README.md) — OHS 서비스 운영
- [data-team/02-extraction/pipe-A/CLAUDE.md](../data-team/02-extraction/pipe-A/CLAUDE.md), [status_pipea.md](../data-team/02-extraction/pipe-A/status_pipea.md), [plan_pipea.md](../data-team/02-extraction/pipe-A/plan_pipea.md)
- [data-team/02-extraction/pipe-B/CLAUDE.md](../data-team/02-extraction/pipe-B/CLAUDE.md), [status_pipeb.md](../data-team/02-extraction/pipe-B/status_pipeb.md), [plan_pipeb.md](../data-team/02-extraction/pipe-B/plan_pipeb.md)
- [data-team/03-validation/pipe-C/CLAUDE.md](../data-team/03-validation/pipe-C/CLAUDE.md), [status_pipec.md](../data-team/03-validation/pipe-C/status_pipec.md), [plan_pipec.md](../data-team/03-validation/pipe-C/plan_pipec.md)

## 문서 정책

- baseline 메트릭의 **정본은 [status/evaluation-baseline.md](status/evaluation-baseline.md) 한 곳**. 다른 곳에는 링크만 둔다.
- 활성 워크플랜은 `workplans/`, 다주제 후보 큐는 `backlog/`로 분리한다. 백로그 항목이 안정화되면 별도 워크플랜으로 승격.
- 정리 이력은 [governance/cleanup-log.md](governance/cleanup-log.md)에 append-only로 기록한다.
- 자동 생성 산출물 (`ontology-team/06-reasoning/ontology/serving-validation-report-*.md`, `data-team/02-extraction/pipe-B/data/manual-enrichment-*.md`)은 손대지 말고 생성 스크립트를 수정한다.
