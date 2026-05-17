# arch-bot 작업 가이드 (Claude Code 자동 로드)

> 이 파일은 Claude Code가 루트에서 작업 시작할 때 자동으로 로드한다.
> 변동성 낮은 메타 규칙·팀 구조·단계 매핑만 담는다.
> 현재 baseline·다음 작업 큐 등 변동 부분은 [docs/status/current-session.md](docs/status/current-session.md) 참조.

## 응답 원칙

- 사용자와 한국어로 소통. 기술 용어/식별자/코드 키워드는 영어 그대로 OK.
- 코드/구조보다 추론 결과의 의미와 추론된 트리플 수가 더 중요한 검증 지표.

## 작업 모델 — 9단계 × 3팀

```text
arch-bot/
├── data-team/                  데이터팀 (1~5단계)
│   ├── 01-parsing/             1. 법령(legalize-kr) + KOSHA Guide PDF 파싱
│   ├── 02-extraction/          2. LLM으로 NS/SR/CI 추출 (pipe-A, pipe-B)
│   ├── 03-validation/          3. PG 적재로 적합성/FK 규칙 검증 (pipe-C)
│   ├── 04-ontology-export/     4. PG → 온톨로지 export
│   └── 05-enrichment/          5. (현재 집중) LLM으로 서빙 부족 온톨로지 레이어 enrichment — 6번 완성 시 폐지
│
├── ontology-team/              온톨로지팀 (6단계, 향후 오픈소스 공개)
│   └── 06-reasoning/           6. 공리/OWL/SHACL → 리즈너로 문제 발견·수정 (Framework + KOSHA TBox + ABox)
│
├── serving-team/               서빙팀 (7~8단계)
│   ├── 07-materialization/     7. 보정된 내용을 PG로 재물질화
│   └── 08-app/                 8. OHS backend(FastAPI) + frontend(React+Vite) PG 기반 서비스
│
├── shared/                     팀 간 공유 (reference data, 인터페이스)
├── legalize-kr/                외부 법령 git repo clone (root git ignored)
└── docs/                       거버넌스/아키텍처/온톨로지 설계 문서
```

**9단계 원칙**: 1~4번은 1회성(새 데이터 추가 시만 실행). 5번은 현재 집중, 6번 완성 시 자연 폐지. 6번은 LLM 활용 최소화하고 온톨로지 구조화로 대체. 7~8번은 서빙. **온톨로지는 데이터 관리/확장 표준 DB 역할이며 서빙에 직접 관여하지 않는다.**

**팀 분담의 의미**:
- 데이터팀: 데이터 보정 (LLM enrichment 5번 포함). 향후 private `kosha-data-pipeline` repo로 분리 예정.
- 온톨로지팀: TBox/ABox/공리/리즈너. **오픈소스 공개 대상**. 향후 public `kosha-ontology-reasoning` repo로 분리 예정.
- 서빙팀: PG 물질화 + OHS 서빙. 향후 private `kosha-ohs` repo로 분리 예정.

## 현재 작업 디렉토리

```text
Windows path: C:\project\arch-bot
WSL path:     /mnt/c/project/arch-bot
branch:       main
```

## Repository / Data Baseline

Snapshot import baseline (Phase 1 시점):

```text
koshaontology imported baseline: 60d025ee873e071faf9c90cc0b1a89b05c4812bd  (현재 data-team + ontology-team으로 분산)
OHS imported baseline:           7eed7280e1ece9fa7bb32beb182017f5cfa96f5a  (현재 serving-team으로 이동)
root pre-import baseline:        1565a9d14e76b7e3ceb6753354621f5d043c92de
legalize-kr observed upstream:   732764e9e8e116bbc40eb5278207e3a08b31297e
```

Tracked data policy:

```text
data-team/01-parsing/kosha-guides/parsed/**:        tracked, 1,038 parsed Guide JSON files
data-team/01-parsing/kosha-guides/manifest/**:      tracked provenance manifest
data-team/05-enrichment/eval-data/synthetic_*.jsonl: tracked
data-team/05-enrichment/eval-data/reports-manifest.json: tracked report index
data-team/05-enrichment/eval-data/reports/**:       ignored local/external report bodies
kosha-guides raw PDFs:                              ignored external/LFS candidates
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
risk:RiskFeature             위험 지식 공통 추상 계층
haz/agent/ctx                risk:RiskFeature 하위 분류 어휘
she:SituationalHazardPattern 재사용 가능한 위험상황 패턴 (사진별 사건 아님)
VisualTrigger                사진에서 보여야 하는 시각 단서
Guide/WorkProcess            표준 개선 절차 중심
ChecklistItem                즉시 조치/보조 단서/검색 색인
PenaltyPath                  사업주용 일반 위반/일반 산재 / 사망 / 중대재해 3경로 안내
```

LLM은 법령/벌칙을 판단하지 않는다. 관찰사실/시각단서만 추출. 법령/SR/가이드/벌칙 연결은 물질화된 온톨로지 데이터와 Python/PostgreSQL 조회 로직이 담당.

OWL 추론은 요청 경로 밖에서 배치 보강/일관성 검증/근본원인 분석에만 사용. PostgreSQL materialized table이 서빙 경로.

폐기 용어 (본문 설명에 새 구조처럼 등장 금지):

```text
PenaltyRoute / penaltyForArticle / SeverityLevel / hasSeverityLevel
she:ContextFeature / she:SituationalHazardEvent
```

## 절대 금지

- `legalize-kr/`를 push하거나 root git에 import하지 않는다 (외부 의존 repo)
- raw KOSHA PDF를 git에 추적하지 않는다 (external/LFS 후보)
- `data-team/05-enrichment/eval-data/reports/**` 본문을 git에 추적하지 않는다 (~11GB, manifest만 추적)
- `serving-team/08-app/frontend/node_modules/**`을 편집하지 않는다
- 자동 생성 산출물(`ontology-team/06-reasoning/ontology/serving-validation-report-*.md/csv/json`, `data-team/02-extraction/pipe-B/data/manual-enrichment-*.md`)을 수동 편집하지 않는다. 생성 스크립트를 고친다.
- baseline 메트릭의 정본은 [docs/status/evaluation-baseline.md](docs/status/evaluation-baseline.md) 한 곳이다. 다른 곳에는 링크만 둔다.

## 문서 진입점

| 목적 | 경로 |
|---|---|
| **🚀 현재 메인 plan (2026-05-17~)** | **[docs/workplans/llm-accelerated-ontology-engineering.md](docs/workplans/llm-accelerated-ontology-engineering.md)** ⭐ |
| 현재 세션 상태 + 다음 세션 진입 | [docs/status/current-session.md](docs/status/current-session.md) |
| 4-Layer Architecture | [docs/architecture/4-layer-architecture.md](docs/architecture/4-layer-architecture.md) |
| Layer 4 (Ontology Learning) 상세 | [docs/architecture/ontology-learning-layer.md](docs/architecture/ontology-learning-layer.md) |
| LLM 의존 단계적 폐지 path | [docs/architecture/llm-dependency-evolution.md](docs/architecture/llm-dependency-evolution.md) |
| 학계 9 paper references | [docs/governance/ontology-learning-references.md](docs/governance/ontology-learning-references.md) |
| 모든 문서 색인 | [docs/README.md](docs/README.md) |
| 평가 baseline 정본 | [docs/status/evaluation-baseline.md](docs/status/evaluation-baseline.md) |
| 운영/거버넌스 정책 | [docs/governance/](docs/governance/) |
| 시스템 아키텍처 | [docs/architecture/](docs/architecture/) |
| 온톨로지 구조 한글 설계 | [docs/ontology/](docs/ontology/) |
| 활성 워크플랜 | [docs/workplans/](docs/workplans/) |
| 리팩토링 백로그 | [docs/backlog/](docs/backlog/) |
| 최종 산출물 | [docs/deliverables/](docs/deliverables/) |
| 데이터팀 / 온톨로지팀 / 서빙팀 README | [data-team/README.md](data-team/README.md) / [ontology-team/README.md](ontology-team/README.md) / [serving-team/README.md](serving-team/README.md) |
| 파이프라인별 작업 가이드 | [pipe-A](data-team/02-extraction/pipe-A/CLAUDE.md) / [pipe-B](data-team/02-extraction/pipe-B/CLAUDE.md) / [pipe-C](data-team/03-validation/pipe-C/CLAUDE.md) |

## 핵심 아키텍처 — 4-Layer + Cross-cutting Layer 4

> 자세히: [docs/architecture/4-layer-architecture.md](docs/architecture/4-layer-architecture.md)

```
Layer 0: Vision LLM       (gpt-4.1, 영구 잔존)
Layer 1: Normalizer       (alias + catalog)
Layer 2: Semantic Reasoning (SHE + OWL DL + SWRL/SHACL)
Layer 3: PG Materialization (cache, ms 응답)
────────────────────────────────────────────────
★ Layer 4: Ontology Learning (cross-cutting) ★
   학습기 — Layer 1-3 데이터를 학습 대상으로
   7 module: Term Extraction / Taxonomy / Relation / Axiom / CQ / GraphRAG / Continual
```

**LLM 의존 단계적 폐지** (자세히: [docs/architecture/llm-dependency-evolution.md](docs/architecture/llm-dependency-evolution.md)):
- Vision LLM (gpt-4.1) → **영구 유지**
- Phase B LLM rerank → 점진 폐지 (OWL DisjointClasses + SHACL 대체)
- 5번 LLM enrichment json → 폐지 (OWL TBox + SWRL 정형화)
- Phase C self-refine → 유지 (Layer 4.7 영구 학습 루프)

## 새 작업 시작 전 체크

```bash
git status --short --branch    # clean 상태 확인
```

**다음 세션 진입 순서**: [docs/status/current-session.md](docs/status/current-session.md) → [docs/workplans/llm-accelerated-ontology-engineering.md](docs/workplans/llm-accelerated-ontology-engineering.md) → 필요 시 architecture/ 문서.
