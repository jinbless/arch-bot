# Status

현재 검증 메트릭과 다음 세션 시작 지침을 보관한다.

## 파일

| 파일 | 용도 |
|---|---|
| [evaluation-baseline.md](evaluation-baseline.md) | **평가 baseline 정본** — 현재 accepted 메트릭 + historical baseline + PG candidate refresh + Rejected approaches |
| [current-session.md](current-session.md) | 다음 세션 시작 지침 — 먼저 읽을 문서·OHS 실행·검증 명령·다음 작업 큐 |

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
