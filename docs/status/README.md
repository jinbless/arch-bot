# Status

현재 검증 메트릭과 다음 세션 시작 지침을 보관한다.

## 상시 정본 문서

| 파일 | 용도 |
|---|---|
| [evaluation-baseline.md](evaluation-baseline.md) | **평가 baseline 정본** — 현재 accepted 메트릭 + historical baseline + PG candidate refresh + Rejected approaches |
| [current-session.md](current-session.md) | 다음 세션 시작 지침 — 먼저 읽을 문서·OHS 실행·검증 명령·다음 작업 큐 |
| [document-inventory.md](document-inventory.md) | 프로젝트 문서 인벤토리 — 디렉토리 구조 + 각 문서 역할·최신성 점검 |

## 시점별 검증 스냅샷 (append-only 보존)

| 파일 | 용도 |
|---|---|
| [reasoning-catch-effectiveness-2026-05-17.md](reasoning-catch-effectiveness-2026-05-17.md) | Phase 3 — ontology reasoning이 LLM 환각/과대추정 1,902건 차단 |
| [f30-reject-reason-classification-2026-05-17.md](f30-reject-reason-classification-2026-05-17.md) | F.3.0 — 2,525 reject reason 5 카테고리 분류 (axiom_missing 36.44%) |
| [f33-gate3-regression-2026-05-17.md](f33-gate3-regression-2026-05-17.md) | F.3.3 — 2,360 synthetic Gate 3 regression PASS (8 candidate axiom) |
| [phase3-baseline-shift.md](phase3-baseline-shift.md) | Phase 3D synthetic 변환 후 baseline_v3 shift 분석 |
| [closed-vocabulary-day3-result-2026-05-18.md](closed-vocabulary-day3-result-2026-05-18.md) | Closed vocabulary Day 3 결과 |
| [f1-day6-real-photo-eval-2026-05-18.md](f1-day6-real-photo-eval-2026-05-18.md) | F.1 Day 6 — 8 real-test-photo eval |
| [f1-day6_5-mining-direction-2026-05-18.md](f1-day6_5-mining-direction-2026-05-18.md) | F.1 Day 6.5 — mining 방향 결정 |
| [f2-sprint-day6-eval-2026-05-18.md](f2-sprint-day6-eval-2026-05-18.md) | F.2 sprint Day 6 — taxonomy eval |
| [promote-she-review-impractical-2026-05-18.md](promote-she-review-impractical-2026-05-18.md) | SHE promote 비현실성 분석 |
| [t2d-per-candidate-promotion-2026-05-18.md](t2d-per-candidate-promotion-2026-05-18.md) | T2.D — 8/8 candidate vetted promotion PASS |
| [t3a-closed-vocab-schema-enum-2026-05-18.md](t3a-closed-vocab-schema-enum-2026-05-18.md) | T3.A — closed-vocab schema enum (free-create 76→4) |

## 정책

- **baseline 메트릭은 [evaluation-baseline.md](evaluation-baseline.md) 한 곳만 정본이다.**
- 다른 모든 문서(루트 README, current-session, serving-team/08-app/README 등)는 5~10줄 요약 + 정본 링크만 둔다.
- baseline 갱신 시 이 파일만 수정하면 된다.
- 보고서 본문은 `data-team/05-enrichment/eval-data/reports/**`에 로컬/외부로 보관, root git은 `data-team/05-enrichment/eval-data/reports-manifest.json`과 이 문서만 추적.

## 파이프라인별 상세 status

각 파이프라인의 운영 상세는 해당 디렉토리에 둔다:

- [../../data-team/02-extraction/pipe-A/status_pipea.md](../../data-team/02-extraction/pipe-A/status_pipea.md)
- [../../data-team/02-extraction/pipe-B/status_pipeb.md](../../data-team/02-extraction/pipe-B/status_pipeb.md)
- [../../data-team/03-validation/pipe-C/status_pipec.md](../../data-team/03-validation/pipe-C/status_pipec.md)
- [../../serving-team/08-app/README.md](../../serving-team/08-app/README.md)
