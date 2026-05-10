# 다음 세션 시작 지침

최신 갱신일: 2026-05-10

이 문서는 다른 Codex/LLM 세션이 현재 상태를 빠르게 이어받기 위한 시작점이다.

## 1. 현재 작업 디렉토리

```text
C:\project\arch-bot
```

현재 기준은 root `arch-bot` monorepo 전환 브랜치다.

```text
branch: codex/monorepo-snapshot-import
```

`OHS/`와 `koshaontology/`는 기존 child GitHub repo의 pushed baseline을 root로 snapshot import한 디렉토리다. `legalize-kr/`는 외부 의존 repo로 유지하며 root git에서 추적하지 않는다.

## 2. 먼저 읽을 문서 순서

1. `README.md`
2. `MONOREPO_TRANSITION_PLAN.md`
3. `DATA_GOVERNANCE.md`
4. `repositories.md`
5. `docs/status/evaluation-baseline.md`
6. `docs/architecture/source-provenance.md`
7. `WORKPLAN_LLM_DOMAIN_GUARD.md`
8. `온톨로지_통합구조_및_흐름도.md`
9. `OHS/README.md`
10. `needToChangeCode.md`
11. `koshaontology/pipe-A/status_pipea.md`
12. `koshaontology/pipe-B/status_pipeb.md`
13. `koshaontology/pipe-C/status_pipec.md`

레이어별 세부 구조:

```text
온톨로지_법령레이어_상세도.md
온톨로지_SR레이어_상세도.md
온톨로지_위험상황레이어_상세도.md
온톨로지_가이드레이어_상세도.md
온톨로지_벌칙레이어_상세도.md
```

## 3. Repository / Data Baseline

Snapshot import baseline:

```text
koshaontology imported baseline: 60d025ee873e071faf9c90cc0b1a89b05c4812bd
OHS imported baseline: 7eed7280e1ece9fa7bb32beb182017f5cfa96f5a
root pre-import baseline: 1565a9d14e76b7e3ceb6753354621f5d043c92de
legalize-kr observed upstream: 732764e9e8e116bbc40eb5278207e3a08b31297e
```

Tracked data policy:

```text
kosha-guides/parsed/**: tracked, 1,038 parsed Guide JSON files
kosha-guides/manifest/**: tracked provenance manifest
pictures-json/synthetic_observations_v*.jsonl: tracked
pictures-json/reports-manifest.json: tracked report index
pictures-json/reports/**: ignored local/external report bodies
kosha-guides raw PDFs: ignored external/LFS candidates
```

## 4. Product / Ontology Baseline

서비스 목적:

```text
사업주가 사진을 업로드하면
→ 사진 속 관찰 사실과 시각 단서를 추출하고
→ 위험 특징으로 정규화하고
→ 재사용 가능한 SHE 위험상황 패턴에 매칭하고
→ SR/법령/Guide/CI/PenaltyPath를 조회해
→ 즉시 조치, 표준 개선 절차, 벌칙 3경로, 근거를 보여준다.
```

핵심 온톨로지 기준:

```text
risk:RiskFeature = 위험 지식 공통 추상 계층
haz/agent/ctx = risk:RiskFeature 하위 분류 어휘
she:SituationalHazardPattern = 사진별 사건이 아니라 재사용 가능한 위험상황 패턴
VisualTrigger = 사진에서 보여야 하는 시각 단서
Guide/WorkProcess = 표준 개선 절차 중심
ChecklistItem = 즉시 조치/보조 단서/검색 색인
PenaltyPath = 사업주용 일반 위반 또는 일반 산재 / 사망 / 중대재해 3경로 안내
```

Source/provenance metadata는 별도 layer로 설계한다. `kosha-guides/manifest`를 운영 원천으로 보고, W3C PROV-O/DCAT/DCTERMS/SHACL 조합으로 `source-provenance.ttl`, `source-catalog.ttl`, `source-shapes.ttl`을 생성하는 방향이다. 이 provenance layer는 추천 점수에 직접 쓰지 않고 감사/debug/rebuild에 사용한다.

## 5. OHS 실행

백엔드:

```bash
cd C:/project/arch-bot/OHS/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

프론트:

```bash
cd C:/project/arch-bot/OHS/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

브라우저:

```text
http://127.0.0.1:5173/ohs/
```

주의:

- `OPENAI_API_KEY`가 없으면 실제 이미지/텍스트 분석은 503이 날 수 있다.
- PostgreSQL은 `postgresql://kosha:1229@localhost/kosha` 기준이다.

## 6. 현재 검증 기준선

Accepted baseline: `usage_profile11`

```text
synthetic Guide v1~v10 total: 2,360
legacy obvious top Guide mismatch: 1,145
current obvious top Guide mismatch: 165
reduction: 85.59%
NO_TOP: 395
v10 SHE recall: 100.0%
v10 SHE false negative: 0
v10 SHE false positive: 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
```

Tracked baseline summary:

```text
docs/status/evaluation-baseline.md
pictures-json/reports-manifest.json
```

Local/external report bodies:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile11_20260510_011317.*
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile11_20260510_011333.*
pictures-json/reports/synthetic_observations_v10_usage_profile11_report.*
pictures-json/reports/actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038.*
```

## 7. 검증 명령

Python 문법 검증:

```bash
cd C:/project/arch-bot/OHS/backend
python -c "import pathlib; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in pathlib.Path('.').rglob('*.py') if '__pycache__' not in p.parts]; print('compile ok')"
```

프론트 빌드:

```bash
cd C:/project/arch-bot/OHS/frontend
npm run build
```

Monorepo import 검증:

```bash
cd C:/project/arch-bot
git ls-files OHS | wc -l
git ls-files koshaontology | wc -l
git ls-files kosha-guides/parsed | wc -l
git ls-files | rg '\\.env|node_modules|\\.venv|\\.dev-logs|pictures-json/reports/|kosha-guides/.+\\.pdf'
```

기대 count:

```text
OHS: 161
koshaontology: 2268
kosha-guides/parsed: 1038
```

## 8. 바로 이어서 할 일

1. `codex/monorepo-snapshot-import` 브랜치가 push/PR까지 완료됐는지 확인한다.
2. 이후 새 작업은 root `arch-bot`에서 수행한다.
3. Guide 품질 작업은 `usage_profile11` 기준으로 이어간다.
4. 다음 구조적 보강 대상은 `NO_TOP 395`, `missing_usage_profile`, `industry_boundary_gap`, `workprocess_mismatch` 큐다.
5. 단순 keyword 추가가 아니라 Guide usage profile의 `observable_required_cues`, `negative_boundaries`, `procedure_role`, `primary_work_process_ids` 보강으로 처리한다.
