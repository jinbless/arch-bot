# 다음 세션 시작 지침

최신 갱신일: 2026-05-15

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

Accepted runtime baseline: `ci_cross_guide_broad_only_guard1`.

Previous accepted baseline: `ci_unrelated_action_filter1`.

This pass keeps the risk/SHE/SR/status/penalty boundary stable and keeps the top standard-procedure Guide boundary stable. It changes only Stage 5 immediate-action filtering: a non-primary standard-procedure Guide cannot supply an immediate-action CI when its only SR evidence is broad secondary SR. It still does not write asserted legal mappings or `ci_sr_mapping`.

Report bodies stay local/external under `pictures-json/reports/**`; root git tracks the manifest and summary instead:

- `pictures-json/reports-manifest.json`
- `docs/status/evaluation-baseline.md`

Referenced current local report bodies:

- `pictures-json/reports/pipeline_quality_v1_v10_ci_cross_guide_broad_only_guard1_pg.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_ci_broad_sr_guard4.md`
- `pictures-json/reports/stage2_5_no_top_actionability_ci_broad_sr_guard4.md`
- `pictures-json/reports/synthetic_observations_v10_ci_cross_guide_broad_only_guard1_report_report.md`
- `pictures-json/reports/actual_response_samples_ci_cross_guide_broad_only_guard1.md`
- `pictures-json/reports/ci_boundary_mismatch_triage_ci_cross_guide_broad_only_guard1.md`
- `pictures-json/reports/stage2_5_no_top_root_cause_ci_cross_guide_broad_only_guard1.md`
- `pictures-json/reports/stage2_5_no_top_actionability_ci_cross_guide_broad_only_guard1.md`
- `pictures-json/reports/pg_guide_usage_profiles_sync_ci_broad_sr_guard4.md`
- `pictures-json/reports/ci_sr_candidate_promotion_ci_broad_sr_guard4.md`
- `pictures-json/reports/ci_no_action_triage_ci_cross_guide_broad_only_guard1.md`
- `pictures-json/reports/ci_mapping_review_semantic_ci_cross_guide_broad_only_guard1.md`
- `pictures-json/reports/ci_sr_mapping_candidate_review_ci_cross_guide_broad_only_guard1.md`
- `pictures-json/reports/pg_ci_sr_link_candidates_ci_cross_guide_broad_only_guard1_apply.md`
- `pictures-json/reports/ci_sr_candidate_promotion_ci_cross_guide_broad_only_guard1.md`
- `koshaontology/ontology/serving-validation-report-ci_cross_guide_broad_only_guard1.*`
- `koshaontology/ontology/serving-workprocess-alignment-ci_cross_guide_broad_only_guard1.*`

Summary:

```text
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 5
Stage 2~5 NO_TOP: 88
NO_TOP actionability: accepted empty top 31 / source-taxonomy review 57 / runtime repair candidates 0
industry_boundary_gap: 0
workprocess_mismatch: 5
broad_sr_overreach: 0
photo_unmatchable_top_count: 0
followup_only_retained_count: 16
CI no_action: 495
CI context_mismatch: 0
CI broad_sr_only: 0
CI needs_review_used: 0
CI guide_boundary_mismatch: 1
v10 SHE recall: 100.0%, FN 0, FP 0
v1~v10 SHE smoke: recall 100.0%, FN 0, FP 67
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
serving ontology validation: PASS, hard violations 0, warnings 0
accepted photo-actionable role overrides: 10
```

Serving validation snapshot:

```text
snapshot: koshaontology/ontology/serving-snapshot-ci_cross_guide_broad_only_guard1.ttl
validation report: koshaontology/ontology/serving-validation-report-ci_cross_guide_broad_only_guard1.*
WorkProcess alignment report: koshaontology/ontology/serving-workprocess-alignment-ci_cross_guide_broad_only_guard1.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 0
primary WorkProcess alignment: 4,715 / 4,715 same Guide
PG guide_usage_profiles sync: PASS, 1,038 rows
PG primary WorkProcess check: missing 0 / cross-guide 0
```

Implementation note: `ci_cross_guide_broad_only_guard1` keeps the `ci_unrelated_action_filter1` status/penalty/SHE/SR, Guide/WorkProcess, top standard-procedure, and photo policy behavior. It adds one narrow final immediate-action rule: if a non-primary standard-procedure Guide supplies a CI using only broad secondary SR evidence, suppress that CI. CI guide-boundary mismatch improves `2 -> 1`; CI no_action changes `494 -> 495`; CI broad_sr_only and needs_review leaks remain `0`.

NO_TOP interpretation: `NO_TOP` is not automatically a defect. Current audit splits 88 cases into 31 accepted empty-top cases and 57 source/taxonomy review cases. Runtime repair candidates are 0; do not reduce the remaining 88 with broad aliases or generic Guide fallback. The remaining CI guide-boundary mismatch tail is now 1 case and should be handled as source/profile/taxonomy review, not broad action fallback.

PG candidate review refresh on 2026-05-16: `ci_candidate_review_v1` still has 50 review rows in `guide_sr_link_candidates`; 17 are serving `candidate`, 33 remain `needs_review`, all are `asserted=false`, and `ci_sr_mapping` inserts remain 0. Verification report `pipeline_quality_v1_v10_ci_cross_guide_broad_only_guard1_pg` confirms Guide mismatch 5, NO_TOP 88, CI no_action 495, CI guide-boundary mismatch 1, CI needs_review_used 0.

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
3. Guide 품질 작업은 `ci_cross_guide_broad_only_guard1` 기준으로 이어간다.
4. `she-stage3-new-pattern-candidates-reference-guard1` 230건은 runtime SHE 확정으로 import하지 않는다. `true_new_she`도 첫 사이클에서는 review-only다.
5. NO_TOP 88건은 `accepted empty top 31`, `source/taxonomy review 57`, `runtime repair candidate 0`으로 분리됐다. 억지로 broad alias/support를 추가하지 않는다.
6. 다음 구조적 보강 대상은 `CI no_action 495`, `CI guide_boundary_mismatch 1`의 남은 꼬리다. `CI broad_sr_only`는 13건에서 0건으로 해소했다. 현장에 맞는 Guide가 없으면 억지 top Guide를 만들지 않는다. `B_wrong_guide_boundary`와 `D_safe_scene_overpromoted`는 0건이다.
7. parent context는 검색 확장에만 쓰고, parent-only match는 confirmed/status/penalty/direct SR/표준절차 top 후보를 만들 수 없다.
8. photo_matchability는 표준절차 top lane에만 적용한다. 즉시조치, SHE status, SR evidence, penalty path에는 적용하지 않는다.
9. 온톨로지 검증 경고는 `structure_issue`, `data_issue`, `algorithm_issue`, `corpus_gap`, `review_only`로 나눠 원천 artifact 쪽에서 정리한다.
