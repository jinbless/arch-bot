# 다음 세션 시작 지침

최신 갱신일: 2026-05-14

이 문서는 다른 Codex/LLM 세션이 현재 상태를 빠르게 이어받기 위한 시작점이다.

## 1. 현재 작업 디렉토리

```text
Windows path: C:\project\arch-bot
WSL path: /mnt/c/project/arch-bot
```

현재 기준은 root `arch-bot` monorepo `main` 브랜치다.

```text
branch: main
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

## 6. 현재 검증 기준선

Accepted runtime baseline: `context_safe_gate1`

Previous accepted baseline: `corpus_gap_guard1`

```text
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 15
Stage 2~5 NO_TOP: 85
industry_boundary_gap: 1
workprocess_mismatch: 14
broad_sr_overreach: 0
photo_unmatchable_top_count: 0
followup_only_retained_count: 15
CI no_action: 482
CI context_mismatch: 12
CI broad_sr_only: 14
CI needs_review_used: 0
CI guide_boundary_mismatch: 26
v10 SHE recall: 100.0%
v10 SHE false negative: 0
v10 SHE false positive: 0
v1~v10 SHE smoke recall: 100.0%
v1~v10 SHE smoke false negative: 0
v1~v10 SHE smoke false positive: 67
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
```

`context_safe_gate1` keeps the previous status/penalty/SHE/SR boundary and changes only Stage 5 standard-procedure ranking. It adds context-required gates for `pipe_support_installation_welding` and `airborne_infectious_disease_workplace_prevention`, and adds safe welding suppression phrases (`차광 커튼`, `차광막`, `국소 배기 가동`, `국소 배기 장치가 가동`, `자동 차광 헬멧`, `착용 완비`). Public API shape, SHE approval, asserted mappings, legal SR evidence, status, and penalty behavior are unchanged.

Serving ontology validation snapshot:

```text
export script: koshaontology/ontology/scripts/export_serving_snapshot.py
validation script: koshaontology/ontology/scripts/validate_serving_snapshot.py
policy: koshaontology/ontology/serving-policy.ttl
snapshot: koshaontology/ontology/serving-snapshot-context_safe_gate1.ttl
shapes: koshaontology/ontology/serving-validation-shapes.ttl
report: koshaontology/ontology/serving-validation-report-context_safe_gate1.*
alignment report: koshaontology/ontology/serving-workprocess-alignment-context_safe_gate1.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 1
accepted photo-actionable role overrides: 10
primary WorkProcess links aligned: 4,715 / 4,715
```

해석: PostgreSQL 기준 `kosha-instances.ttl` 동기화 이후 `primary_workprocess_not_in_base_ttl` 문제는 0건으로 유지된다. `context_safe_gate1`은 이전 broad SR attention과 `B-M-20-2026`/`H-186-2016` 반복 mismatch 경고를 해소했다. 남은 warning은 `G-76-2011`이 7개 synthetic case에서 `workprocess_mismatch`로 반복되는 알고리즘 큐다. TTL을 직접 고치지 말고 원천 Guide profile, OHS scoring, Pipe-B/PG export 경로를 고친 뒤 재생성한다.

SituationFrame support-only artifact:

```text
classified Stage 3 candidates: 230
runtime SHE approved update: 0
asserted mapping update: 0
child contexts: 178
Guide support candidates v20: 227
NO_TOP support covered cases: Stage3 support 136, curated Stage2 support 20
```

## 7. 검증 명령

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
git ls-files | rg '\\.env|node_modules|\\.venv|\\.dev-logs|pictures-json/reports/|kosha-guides/.+\\.pdf'
```

기대 count:

```text
OHS: 161
koshaontology: 2268
kosha-guides/parsed: 1038
```

## 8. 바로 이어서 할 일

1. 새 작업은 root `arch-bot/main`에서 수행한다.
2. 작업 전 `git status --short --branch`로 clean 상태를 확인한다.
3. Guide 품질 작업은 `context_safe_gate1` 기준으로 이어간다.
4. `she-stage3-new-pattern-candidates-reference-guard1` 230건은 runtime SHE 확정으로 import하지 않는다. `true_new_she`도 첫 사이클에서는 review-only다.
5. NO_TOP 85건은 runtime repair보다 corpus/taxonomy/review boundary 성격이 크다. 억지로 broad alias/support를 추가하지 말고, exact source Guide가 생기거나 별도 public/customer/animal-safety taxonomy를 만들 때만 재검토한다.
6. 다음 구조적 보강 대상은 잔여 `G-76-2011 workprocess_mismatch 7`, `CI no_action 482`, `CI guide_boundary_mismatch 26`, `workprocess_mismatch 14`, `NO_TOP 85`이다. `B_wrong_guide_boundary`와 `D_safe_scene_overpromoted`는 0건이다.
7. parent context는 검색 확장에만 쓰고, parent-only match는 confirmed/status/penalty/direct SR/표준절차 top 후보를 만들 수 없다.
8. photo_matchability는 표준절차 top lane에만 적용한다. 즉시조치, SHE status, SR evidence, penalty path에는 적용하지 않는다.
9. 온톨로지 검증 경고는 `structure_issue`, `data_issue`, `algorithm_issue`, `corpus_gap`, `review_only`로 나눠 원천 artifact 쪽에서 정리한다.
