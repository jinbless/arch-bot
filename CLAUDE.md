# arch-bot 작업 가이드 (Claude Code 자동 로드)

> 이 파일은 Claude Code가 루트에서 작업 시작할 때 자동으로 로드한다.
> 변동성 낮은 메타 규칙과 디렉토리 역할만 담는다.
> 현재 baseline/다음 작업 큐 등 변동 부분은 [docs/status/current-session.md](docs/status/current-session.md) 참조.

## 응답 원칙

- 사용자와 한국어로 소통한다. 기술 용어/식별자/코드 키워드는 영어 그대로 OK.
- 코드/구조보다 추론 결과의 의미와 추론된 트리플 수가 더 중요한 검증 지표.

## 5개 최상위 디렉토리 역할

```text
arch-bot/
├── kosha-guides/    원본 KOSHA Guide PDF + 파싱한 JSON 보관. raw PDF는 git 미추적, parsed/**(1,038개)와 manifest/**만 추적
├── legalize-kr/     외부 법령 관리 git repo를 clone해서 보관. root git에서 ignored. pipe-A가 법령 원천으로 참조
├── koshaontology/   법령/Guide를 온톨로지 구조로 만들기 위한 agent 지시문(prompts)과 결정론적 scripts. pipe-A(법령→NS→SR), pipe-B(Guide→CI/DT/WP/ES/DR), pipe-C(교차검증)
├── OHS/             사용자가 사진 업로드 시 위험 요인을 발견하고 DB와 매핑해서 서빙. backend(FastAPI) + frontend(React+Vite)
└── pictures-json/   GPT가 사진을 분석했다고 가정한 결과를 테스트/분석을 위해 저장. synthetic_observations_v1~v10.jsonl은 합성 입력, reports/**는 평가 보고서 (11GB, git 미추적)
```

**디렉토리 역할 혼동 금지**:
- `kosha-guides`는 원천 데이터 저장소이지 가공된 결과물이 아니다
- `pictures-json`은 테스트 fixture지 production data가 아니다
- `koshaontology`의 scripts는 결정론적, agents는 LLM 지시문
- OHS만 사용자 대면 서빙

## 현재 작업 디렉토리

```text
Windows path: C:\project\arch-bot
WSL path:     /mnt/c/project/arch-bot
branch:       main
```

## Repository / Data Baseline

Snapshot import baseline:

```text
koshaontology imported baseline: 60d025ee873e071faf9c90cc0b1a89b05c4812bd
OHS imported baseline:           7eed7280e1ece9fa7bb32beb182017f5cfa96f5a
root pre-import baseline:        1565a9d14e76b7e3ceb6753354621f5d043c92de
legalize-kr observed upstream:   732764e9e8e116bbc40eb5278207e3a08b31297e
```

Tracked data policy:

```text
kosha-guides/parsed/**:                tracked, 1,038 parsed Guide JSON files
kosha-guides/manifest/**:              tracked provenance manifest
pictures-json/synthetic_observations_v*.jsonl: tracked
pictures-json/reports-manifest.json:   tracked report index
pictures-json/reports/**:              ignored local/external report bodies
kosha-guides raw PDFs:                 ignored external/LFS candidates
```

## 제품 / 온톨로지 핵심 기준 (불변)

서비스 목적:

```text
사업주가 사진을 업로드하면
→ 사진 속 관찰 사실과 시각 단서를 추출하고
→ 위험 특징으로 정규화하고
→ 재사용 가능한 SHE 위험상황 패턴에 매칭하고
→ SR/법령/Guide/CI/PenaltyPath를 조회해
→ 즉시 조치, 표준 개선 절차, 벌칙 3경로, 근거를 보여준다.
```

핵심 온톨로지 용어:

```text
risk:RiskFeature            위험 지식 공통 추상 계층
haz/agent/ctx               risk:RiskFeature 하위 분류 어휘
she:SituationalHazardPattern 사진별 사건이 아니라 재사용 가능한 위험상황 패턴
VisualTrigger               사진에서 보여야 하는 시각 단서
Guide/WorkProcess           표준 개선 절차 중심
ChecklistItem               즉시 조치/보조 단서/검색 색인
PenaltyPath                 사업주용 일반 위반/일반 산재 / 사망 / 중대재해 3경로 안내
```

LLM은 법령/벌칙을 판단하지 않는다. 관찰사실과 시각단서만 추출. 법령/SR/가이드/벌칙 연결은 물질화된 온톨로지 데이터와 Python/PostgreSQL 조회 로직이 담당.

OWL 추론은 요청 경로 밖에서 배치 보강/일관성 검증/근본원인 분석에만 사용. PostgreSQL materialized table이 서빙 경로.

폐기 용어 (본문 설명에 새 구조처럼 등장 금지):

```text
PenaltyRoute / penaltyForArticle / SeverityLevel / hasSeverityLevel
she:ContextFeature / she:SituationalHazardEvent
```

## 절대 금지

- `legalize-kr/`를 push하거나 root git에 import하지 않는다 (외부 의존 repo)
- raw KOSHA PDF를 git에 추적하지 않는다 (external/LFS 후보)
- `pictures-json/reports/**` 본문을 git에 추적하지 않는다 (~11GB, manifest만 추적)
- `OHS/frontend/node_modules/**`을 편집하지 않는다
- 자동 생성 산출물(`koshaontology/ontology/serving-validation-report-*.md/csv/json`, `koshaontology/pipe-B/data/manual-enrichment-*.md`)을 수동 편집하지 않는다. 생성 스크립트를 고친다.
- baseline 메트릭의 정본은 [docs/status/evaluation-baseline.md](docs/status/evaluation-baseline.md) 한 곳이다. 다른 곳에는 링크만 둔다.

## 문서 진입점

| 목적 | 경로 |
|---|---|
| 모든 문서 색인 | [docs/README.md](docs/README.md) |
| 현재 baseline / 다음 작업 큐 | [docs/status/current-session.md](docs/status/current-session.md) |
| 평가 baseline 정본 | [docs/status/evaluation-baseline.md](docs/status/evaluation-baseline.md) |
| 운영/거버넌스 정책 | [docs/governance/](docs/governance/) |
| 온톨로지 구조 한글 설계 | [docs/ontology/](docs/ontology/) |
| 활성 워크플랜 | [docs/workplans/](docs/workplans/) |
| 리팩토링 백로그 | [docs/backlog/](docs/backlog/) |
| 시스템 아키텍처 | [docs/architecture/](docs/architecture/) |
| 최종 산출물 | [docs/deliverables/](docs/deliverables/) |
| OHS 서비스 | [OHS/README.md](OHS/README.md) |
| 파이프라인별 작업 가이드 | [koshaontology/pipe-A/CLAUDE.md](koshaontology/pipe-A/CLAUDE.md), [pipe-B](koshaontology/pipe-B/CLAUDE.md), [pipe-C](koshaontology/pipe-C/CLAUDE.md) |

## 새 작업 시작 전 체크

```bash
git status --short --branch    # clean 상태 확인
```

추가 컨텍스트가 필요하면 [docs/status/current-session.md](docs/status/current-session.md)부터 읽는다.
