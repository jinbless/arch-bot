# 프로젝트 정리 로그

가장 최근 entry가 위에 오는 append-only 이력 문서.

---

## 2026-05-16 (Phase 2): 팀별 디렉토리 재배치

### 변경 요약

9단계 작업 모델 + 3팀 분담에 맞춰 모노레포 디렉토리를 팀 중심으로 재배치.

```text
arch-bot/
├── data-team/                  데이터팀 (1~5단계, 향후 private kosha-data-pipeline repo)
│   ├── 01-parsing/             (구) kosha-guides
│   ├── 02-extraction/          (구) koshaontology/pipe-A, pipe-B
│   ├── 03-validation/          (구) koshaontology/pipe-C
│   ├── 04-ontology-export/     (Phase B에서 ontology/scripts/export_* 이동 예정)
│   └── 05-enrichment/          (구) pictures-json + koshaontology/{data,db,scripts}/she
│
├── ontology-team/              온톨로지팀 (6단계, 향후 public kosha-ontology-reasoning repo, 오픈소스)
│   └── 06-reasoning/           (구) koshaontology/ontology + dashboard 시각화
│
├── serving-team/               서빙팀 (7~8단계, 향후 private kosha-ohs repo)
│   ├── 07-materialization/     (Phase B에서 import_*_to_pg.py 이동 예정)
│   └── 08-app/                 (구) OHS 통째
│
└── shared/                     팀 공유 reference (구 koshaontology/config/hazard-taxonomy-unified.json)
```

### 주요 이동 (commit `cb0a63b`, 3,639 files changed)

- `kosha-guides` → `data-team/01-parsing/kosha-guides`
- `koshaontology/pipe-A,B,C` → `data-team/02-extraction/pipe-A,B` + `03-validation/pipe-C`
- `koshaontology/ontology` → `ontology-team/06-reasoning/ontology`
- `koshaontology/{scripts,data,db}/she` → `data-team/05-enrichment/she-*`
- `koshaontology/scripts/dashboard-*` + `kosha-ontology-dashboard.html` → `ontology-team/06-reasoning/visualization`
- `koshaontology/config/hazard-taxonomy-unified.json` → `shared/reference`
- `pictures-json` → `data-team/05-enrichment/eval-data`
- `OHS/{backend,frontend,docker-compose,package*,playwright,scripts,data,etc}` → `serving-team/08-app/`

### 외부 의존 경로 수정

- `Makefile`: `BACKEND_DIR`/`FRONTEND_DIR` 새 경로
- `pipe-A scripts/config`: `../../legalize-kr/` → `../../../legalize-kr/`
- `pipe-B docs`: `../../kosha-guides/` → `../../01-parsing/kosha-guides/`
- `.gitignore`: 모든 경로 새 구조로 통합 (`OHS/.gitignore`, `koshaontology/.gitignore` 흡수)

### 잔여 정리

- `OHS/202167904_1280.jpg` 삭제 (미사용 sample)
- 빈 디렉토리(`koshaontology/`, `OHS/`) 제거
- `OHS/.env.example` → `serving-team/08-app/.env.example`

### commit 2 (이번 PR)

- 신규: `data-team/README.md`, `ontology-team/README.md`, `serving-team/README.md`, `shared/README.md`
- 신규: `docs/architecture/README.md`, `team-structure.md`, `stage-mapping.md`, `inter-stage-interfaces.md`, `repo-split-plan.md`, `open-source-readiness.md`
- 갱신: 루트 `README.md`, `CLAUDE.md` (3팀 + 9단계 매핑)
- 갱신: `docs/`, `serving-team/08-app/README.md` 등의 옛 경로 일괄 치환 (29 files)

### 5번 영역 남은 작업 (별도 PR)

5번 작업이 활발히 진행 중이므로 이번에는 큰 묶음만 이동. 다음을 다음 PR로 분리:
- `serving-team/08-app/backend/scripts/{build_*,evaluate_*,analyze_*,triage_*,review_*,...}` → `data-team/05-enrichment/{llm-scripts,evaluation-scripts}/`
- `serving-team/08-app/backend/app/data/*.json` → `data-team/05-enrichment/runtime-artifacts/` (backend가 import path 수정 동반)
- `serving-team/08-app/backend/scripts/import_*_to_pg.py` → `serving-team/07-materialization/pg-sync-scripts/`
- `ontology-team/06-reasoning/ontology/scripts/export_*` → `data-team/04-ontology-export/`

### 검증

- ✅ `serving-team/08-app/backend` Python compile OK
- ✅ git mv는 모두 R(rename)로 history 보존
- ✅ leakage 0건 (`.env`, `node_modules`, `reports/`, raw PDF)

---

## 2026-05-16 (Phase 1): 모노레포 문서/디렉토리 구조 1차 정리

### 변경 요약

- 루트의 .md 16개를 `docs/` 산하 7개 하위 디렉토리(`governance`, `ontology`, `architecture`, `workplans`, `backlog`, `status`, `deliverables`)로 재배치
- 루트는 `README.md` + `CLAUDE.md` 2개로 축소
- `NEXT_SESSION_INSTRUCTIONS.md`를 분할: 불변 부분은 루트 `CLAUDE.md`로, 변동 부분은 `docs/status/current-session.md`로
- `PROJECT_CLEANUP_LOG.md`를 분할: 인덱스 부분은 `docs/README.md`로, 이력 부분은 이 파일로
- baseline 메트릭 텍스트 정본화 — `docs/status/evaluation-baseline.md`만 정본, README/current-session/OHS-README는 링크로 단축

### 이동 매트릭스

| from | to |
|---|---|
| `MONOREPO_TRANSITION_PLAN.md` | `docs/governance/monorepo-transition.md` |
| `DATA_GOVERNANCE.md` | `docs/governance/data-governance.md` |
| `repositories.md` | `docs/governance/repositories.md` |
| `WORKPLAN_LLM_DOMAIN_GUARD.md` | `docs/workplans/llm-domain-guard.md` |
| `needToChangeCode.md` | `docs/backlog/refactor-candidates.md` |
| `온톨로지_통합구조_및_흐름도.md` | `docs/ontology/00-integrated-structure.md` |
| `온톨로지_법령레이어_상세도.md` | `docs/ontology/01-law-layer.md` |
| `온톨로지_SR레이어_상세도.md` | `docs/ontology/02-sr-layer.md` |
| `온톨로지_위험상황레이어_상세도.md` | `docs/ontology/03-risk-situation-layer.md` |
| `온톨로지_가이드레이어_상세도.md` | `docs/ontology/04-guide-layer.md` |
| `온톨로지_벌칙레이어_상세도.md` | `docs/ontology/05-penalty-layer.md` |
| `최종보고서_온톨로지_AI시스템_핵심요약.md` | `docs/deliverables/ontology-ai-system-summary.md` |

모두 `git mv`로 history 보존.

### 이번 범위에서 제외 (별도 작업으로 분리)

- 영문 문서의 한글 번역 (구조 정리 완료 후 별도 결정)
- `koshaontology/ontology/serving-validation-report-*.md/csv/json` 16개 격리
- `koshaontology/pipe-B/data/manual-enrichment-*.md` 42개 격리
- `koshaontology/pipe-A/B/C/CLAUDE.md` 등 영/한 혼재 정리
- `OHS/` 내부 docs/ 신설 여부
- 최종보고서 PDF는 사용자가 사전에 삭제함

---

## 이전 정리 기준 (2026-05-10)

문서는 최신 구조를 기준으로 유지한다. 과거 phase 실행 문서는 삭제하지 않고, 역사 문서로 보존하되 현재 product 기준과 다르면 상단 안내나 Pipe 상태 문서에서 차이를 명시한다.

원천 데이터, 실행 코드, 온톨로지 파일, 합성 테스트셋, 프론트 의존성은 보존한다.

현재 git 운영 기준은 root `arch-bot/main` monorepo다. `OHS/`와 `koshaontology/`는 root에서 추적하고, `legalize-kr/`는 외부 의존 repo로 ignore한다.

## 보존 대상

- `OHS/frontend/node_modules`
- `pictures-json/synthetic_observations_v1.jsonl` ~ `synthetic_observations_v10.jsonl`
- `pictures-json/reports-manifest.json`
- `docs/status/evaluation-baseline.md`
- `kosha-guides/parsed/**`
- `kosha-guides/manifest/**`
- `koshaontology/ontology/kosha-ontology.owl`
- `koshaontology/ontology/kosha-ontology.formatted.ttl`
- `koshaontology/ontology/kosha-instances.ttl`
- `koshaontology/ontology/kosha-rules.swrl`
- `legalize-kr` 로컬 외부 의존 repo
- `kosha-guides` raw PDF/source corpus는 외부/LFS 후보로 보존하되 root git 직접 추적 대상은 아님

## 최근 product 정리 상태

`OHS`는 레거시 resource/video/category 중심 구조를 제거하고 현재 온톨로지 흐름에 맞춰 정리했다.

현재 product 흐름:

```text
사진/텍스트 입력
→ 관찰 사실/시각 단서 추출
→ risk:RiskFeature 정규화
→ she:SituationalHazardPattern 매칭
→ SR / WorkProcess / Guide / ChecklistItem / PenaltyPath 조회
→ 사업주용 조치 중심 결과 화면
```

대표 변경:

- `article_chapters.json`, `resources.json`, `safety_videos.json` 기반 런타임 경로 제거
- `risk_feature_aliases.json`, `risk_feature_catalog.json` 도입
- `analysis_pipeline.py` 중심 분석 오케스트레이션 도입
- `GuideProcedurePanel`, `ImmediateActionsPanel`, `PenaltyPathPanel`, `ReasoningTracePanel`, `RiskOverviewPanel` 도입

## 최근 검증 결과

코드 검증:

```text
Python compile: OK
frontend npm run build: OK
```

브라우저/서버 확인:

```text
홈 화면: 최신 product 문구 확인
분석 페이지: HTTP 200 확인
브라우저 자동화: 분석 페이지 상세 확인은 타임아웃 이력 있음
```

`usage_profile11` baseline 시점 검증 메트릭:

```text
baseline: usage_profile11
synthetic Guide v1~v10 total: 2,360
legacy obvious top Guide mismatch: 1,145
current obvious top Guide mismatch: 165
reduction: 85.59%
NO_TOP: 395
v10 SHE recall: 100.0%, FN 0, FP 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
```

최신 baseline 메트릭은 [../status/evaluation-baseline.md](../status/evaluation-baseline.md) 참조.

## 문서 최신성 검증 기준

Root/docs 감사 검색 대상:

- 루트 `*.md`
- `docs/**/*.md`
- `docs/**/*.html`

전체 프로젝트 감사가 필요할 때의 추가 검색 대상:

- `OHS`의 authored `*.md`
- `koshaontology`의 authored `*.md`

제외:

- `OHS/frontend/node_modules/**`
- `pictures-json/reports/**`의 과거 생성 리포트
- 외부 dependency 문서

폐기 용어는 본문 설명에 새 구조처럼 남아 있으면 안 된다. 단, "제거됨", "폐기됨", "과거 명칭" 문맥은 허용한다.

폐기 용어:

```text
폐기 용어: PenaltyRoute
폐기 용어: penaltyForArticle
폐기 용어: SeverityLevel
폐기 용어: hasSeverityLevel
폐기 용어: she:ContextFeature
폐기 용어: she:SituationalHazardEvent
```

최신 핵심 용어:

```text
risk:RiskFeature
risk:RiskPattern
she:SituationalHazardPattern
VisualTrigger
PenaltyPath
violatedArticle
penaltyArticle
Guide/WorkProcess
```

## 남은 후속 과제

1. `확정 위험`과 `확인 필요 후보`의 표시 경계 조정
2. 전체 KOSHA Guide JSON 추출 완료 후 Guide 레이어 리빌딩
3. `VisualTrigger`를 SR + Guide + WorkProcess + ChecklistItem 기반으로 더 구체화
4. 실제 서비스 API에서 `app:` 요약 RDF 저장 구조 구현
5. 브라우저 자동화 타임아웃 없이 분석 화면까지 smoke test 재확인
6. 자동 생성 산출물 격리 (ontology/serving-* 16개, pipe-B/data/manual-enrichment-* 42개) — 생성 스크립트 출력 경로 동시 수정 필요
7. 영문 문서의 한글 번역 검토
