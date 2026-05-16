# arch-bot

`arch-bot` is the top-level monorepo for the ontology-based KOSHA workplace-risk assistant.

> When a business owner uploads a workplace photo, the system identifies visible risk factors, recommends corrective actions, and explains possible penalty paths if the risk is not corrected.

## Documentation

| Entry point | Purpose |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Claude Code 자동 로드 — 9단계 × 3팀 매핑, 메타 규칙, 절대 금지 |
| [docs/README.md](docs/README.md) | 모든 문서의 단일 색인 |
| [docs/status/current-session.md](docs/status/current-session.md) | 다음 세션 시작 지침 (먼저 읽을 문서·다음 작업 큐) |
| [docs/status/evaluation-baseline.md](docs/status/evaluation-baseline.md) | **평가 baseline 정본** |
| [docs/architecture/](docs/architecture/) | 팀 구조 / 단계 매핑 / repo 분리 계획 / 오픈소스 준비 |

## 9단계 작업 모델 × 3팀

```text
arch-bot/
├── data-team/                  데이터팀 (1~5단계, 향후 private kosha-data-pipeline repo)
│   ├── 01-parsing/             법령(legalize-kr) + KOSHA Guide PDF 파싱
│   ├── 02-extraction/          LLM으로 NS/SR/CI 추출 (pipe-A, pipe-B)
│   ├── 03-validation/          PG 적재로 적합성/FK 규칙 검증 (pipe-C)
│   ├── 04-ontology-export/     PG → 온톨로지 export
│   └── 05-enrichment/          (현재 집중) LLM enrichment — 6번 완성 시 폐지
│
├── ontology-team/              온톨로지팀 (6단계, 향후 public kosha-ontology-reasoning repo, 오픈소스)
│   └── 06-reasoning/           공리/OWL/SHACL/리즈너 — Framework + KOSHA TBox + ABox 전부 공개 대상
│
├── serving-team/               서빙팀 (7~8단계, 향후 private kosha-ohs repo)
│   ├── 07-materialization/     보정 내용 PG 재물질화
│   └── 08-app/                 OHS backend(FastAPI) + frontend(React+Vite)
│
├── shared/                     팀 간 공유 (reference data, 인터페이스 contract)
├── legalize-kr/                외부 법령 git repo clone (root git ignored)
└── docs/                       거버넌스 / 아키텍처 / 온톨로지 설계 문서
```

원칙:
- 1~4번은 1회성(새 데이터 추가 시만). 5번은 임시(6번 완성 시 폐지). 6번이 핵심 오픈소스. 7~8번이 서빙.
- 온톨로지는 데이터 관리/확장 표준 DB 역할. 서빙에 직접 관여하지 않음.

## Repository / Data Baseline

| 영역 | 원본 repo | Imported baseline | 정책 |
|---|---|---|---|
| `data-team/` + `ontology-team/` (구 `koshaontology/`) | <https://github.com/jinbless/koshaontology> | `60d025ee873e071faf9c90cc0b1a89b05c4812bd` | tracked |
| `serving-team/08-app/` (구 `OHS/`) | <https://github.com/jinbless/OHS> | `7eed7280e1ece9fa7bb32beb182017f5cfa96f5a` | tracked |
| `legalize-kr/` | <https://github.com/legalize-kr/legalize-kr> | `732764e9e8e116bbc40eb5278207e3a08b31297e` | ignored |

자세한 정책: [docs/governance/](docs/governance/) (monorepo-transition / data-governance / repositories / cleanup-log)

## Current Design Baseline

- `risk:` = 위험 지식 공통 추상 계층. `haz:`/`agent:`/`ctx:`는 `risk:RiskFeature` 하위 어휘
- `she:SituationalHazardPattern` = 재사용 가능한 위험상황 패턴 (사진별 사건 아님)
- `Guide/WorkProcess` = 표준 개선 절차 중심. `ChecklistItem` = 즉시 조치/시각 단서/검색 색인
- `PenaltyPath` = 일반 위반·산재 / 사망 / 중대재해 3경로
- LLM은 관찰사실/시각단서만 추출. 법령/벌칙 선택 안 함
- PostgreSQL materialized table이 서빙 경로. OWL/RDFS는 배치 보강·일관성 검증용

자세한 온톨로지 구조: [docs/ontology/](docs/ontology/) (5개 레이어 상세 설계)

## Current Product Implementation

```text
photo/text input
→ observations and visual cues
→ risk:RiskFeature normalization
→ she:SituationalHazardPattern matching
→ SR / Article / Guide / CI / PenaltyPath lookup
→ business-owner result screen
```

백엔드 서비스 구조와 운영 절차: [serving-team/08-app/README.md](serving-team/08-app/README.md)

## Quick Start

```bash
make dev-up         # backend(8001) + frontend(5173) 백그라운드 기동
make dev-check      # PG + backend + frontend 헬스체크
make dev-down       # 정지
```

상세 검증 명령: [docs/status/current-session.md](docs/status/current-session.md)

## Current Status

- **Accepted runtime baseline**: `ci_cross_guide_broad_only_guard1` (2026-05-16)
- **Previous accepted baseline**: `ci_unrelated_action_filter1`
- **메트릭/historical baseline/PG candidate refresh 전체**: [docs/status/evaluation-baseline.md](docs/status/evaluation-baseline.md) 정본 참조

핵심 요약:

```text
synthetic Stage 2~5 v1~v10: 2,360 cases
Guide mismatch: 5   NO_TOP: 88   CI no_action: 495
serving ontology validation: PASS (hard 0, warning 0)
actual response 240 status changed: 0
```

## Next Session

[docs/status/current-session.md](docs/status/current-session.md)부터 읽는다.
