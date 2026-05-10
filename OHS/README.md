# OHS product

`OHS`는 온톨로지 기반 KOSHA 위험요소 분석 product의 백엔드/프론트 구현 프로젝트다.

현재 목표는 사업주가 사진이나 텍스트를 입력하면 위험요약, 즉시 조치, 표준 개선 절차, 벌칙 3경로, 근거 보기를 제공하는 것이다.

## Repository Boundary

현재 기준은 root `arch-bot`의 `main` 단일 monorepo다. `OHS`는 더 이상 별도 Git repo로 운영하지 않고, root에서 추적되는 product 디렉토리로 관리한다.

```text
arch-bot/
  OHS/              root-tracked product code and docs
  koshaontology/    root-tracked ontology pipeline code and docs
  legalize-kr/      external ignored dependency, not part of the root repo
  pictures-json/    tracked synthetic inputs plus local/external report bodies
```

과거 독립 `OHS` repo와 `codex/monorepo-snapshot-import` 브랜치 언급은 historical migration context로만 해석한다. 현재 작업, 검증, push 기준은 root `arch-bot/main`이다.

## Current Flow

```text
photo/text input
→ observations and visual cues
→ risk:RiskFeature normalization
→ she:SituationalHazardPattern matching
→ SR / Article / WorkProcess / Guide / CI / PenaltyPath lookup
→ business-owner result screen
```

LLM은 법령 판단자가 아니라 관찰 사실과 시각 단서를 추출하는 역할이다. 법령/SR/가이드/벌칙 연결은 물질화된 온톨로지 데이터와 Python/PostgreSQL 조회 로직이 담당한다.

Guide 추천은 단순 Guide title 랭킹이 아니라 `SHE/SR → WorkProcess/Guide → ChecklistItem` 순서로 구성한다. 중신뢰 후보는 추천 점수에는 쓰지만 법적 확정 근거처럼 표시하지 않는다.

## Backend Structure

핵심 서비스 파일:

```text
backend/app/services/analysis_service.py
  OpenAI 호출 진입점과 기존 API 호환 래퍼

backend/app/services/analysis_pipeline.py
  전체 분석 오케스트레이션

backend/app/services/hazard_normalizer.py
  LLM 단서와 텍스트를 risk feature 후보로 정규화

backend/app/services/risk_rule_service.py
  정규화 feature 보정과 규칙 기반 feature 확장

backend/app/services/she_matcher.py
backend/app/services/she_match_models.py
  SHE pattern 매칭, 상태 판정, DTO

backend/app/services/sr_lookup_service.py
  SR 후보 조회

backend/app/services/guide_recommendation_service.py
  ChecklistItem 즉시 조치와 Guide/WorkProcess 표준 절차 추천
  risk feature, SHE match, visual cue, industry context를 함께 사용

backend/app/services/guide_domain_profile.py
  Guide 고유 업종/작업장 문맥과 사진 문맥의 불일치 평가
  exclusive mismatch는 제외, domain_specific mismatch는 감점

backend/app/services/penalty_path_service.py
  PenaltyRule 후보를 PenaltyPath 3경로로 그룹화
```

중요 데이터 파일:

```text
backend/app/data/risk_feature_aliases.json
backend/app/data/risk_feature_catalog.json
backend/app/data/guide_domain_profiles.json
backend/app/data/broad_sr_policy.json
```

PostgreSQL의 Guide 보강 후보 테이블:

```text
guide_entity_feature_candidates
guide_sr_link_candidates
guide_visual_trigger_candidates
```

`guide_domain_profiles.json`은 Pipe-B의 1,038개 manual Guide usage profile export를 OHS serving용으로 복사한 파일이다. `broad_sr_policy.json`은 broad SR이 단독으로 표준절차를 만들지 못하도록 제한하는 serving policy다.

legacy resource/video/category 기반 파일은 product 런타임에서 제거했다.

## Frontend Structure

결과 화면은 다음 패널 중심이다.

```text
frontend/src/components/results/RiskOverviewPanel.tsx
frontend/src/components/results/ImmediateActionsPanel.tsx
frontend/src/components/results/GuideProcedurePanel.tsx
frontend/src/components/results/PenaltyPathPanel.tsx
frontend/src/components/results/ReasoningTracePanel.tsx
```

분석 실행 중복은 `frontend/src/hooks/useRunAnalysis.ts`로 묶었다.

`standard_procedures`는 기존 카드 호환 필드(`title`, `description`, `guide_code`, `confidence`)를 유지하면서, `steps`가 있으면 WorkProcess 절차형 목록으로 표시한다.

## Run Locally

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

## Environment

백엔드 기본값:

```text
DATABASE_URL=postgresql://kosha:1229@localhost/kosha
FUSEKI_ENDPOINT=http://localhost:3030/kosha/sparql
FUSEKI_ENABLED=true
```

프론트 개발 fallback:

```text
http://localhost:8001/api/v1
```

실제 OpenAI 이미지/텍스트 분석에는 `OPENAI_API_KEY`가 필요하다. 없으면 분석 API가 503을 반환할 수 있다.

## Validation

Python compile:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python -c "import pathlib; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in pathlib.Path('.').rglob('*.py') if '__pycache__' not in p.parts]; print('compile ok')"
```

Frontend build:

```bash
cd /mnt/c/project/arch-bot/OHS/frontend
npm run build
```

Synthetic smoke:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python scripts/evaluate_synthetic_observations.py --input ../../pictures-json/synthetic_observations_v10.jsonl --report-prefix synthetic_observations_v10_usage_profile11
```

Actual response 240 replay:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python scripts/evaluate_actual_response_samples.py --report-prefix actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038
```

Guide recommendation evaluation:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python scripts/evaluate_synthetic_guide_recommendations.py --report-prefix synthetic_guide_recommendations_v1_v10_usage_profile11
```

Current accepted baseline, updated 2026-05-10:

```text
baseline: usage_profile11
Python compile: OK
frontend npm run build: OK
synthetic Guide v1~v10:
  total samples 2,360
  legacy obvious top Guide mismatch 1,145
  current obvious top Guide mismatch 165
  reduction 85.59%
  NO_TOP 395
v10 smoke:
  SHE recall 100.0%
  SHE false negative 0
  SHE false positive 0
  normal suppression 100.0%
actual response 240:
  status changed 0
  negative_false_positive 10
  positive_missed 2
  ambiguous_over_promoted 5
```

## Current Open Work

1. `usage_profile11`의 `NO_TOP 395` 큐를 Guide usage profile, visual trigger, WorkProcess relevance 보강으로 줄인다.
2. `guide_sr_link_candidates` unique key 충돌 후보를 evidence merge/pre-aggregate한 뒤 candidate table import를 dry-run한다.
3. asserted mapping update는 0으로 유지하고, 중신뢰 후보는 법적 확정 근거처럼 표시하지 않는다.
4. 브라우저 자동화로 분석 화면까지 timeout 없이 smoke test한다.
5. WorkProcess step 품질 점수와 industry alignment 점수를 더 세분화한다.

## Notes

- `OHS`는 root `arch-bot/main` monorepo에서 추적되는 일반 디렉토리다.
- `frontend/node_modules/**`는 vendor 영역이므로 문서 최신화 대상에서 제외한다.
- 현재 product는 PostgreSQL 물질화 조회를 serving path로 사용한다. OWL reasoner는 런타임 필수 의존성이 아니라 배치 검증/운영 분석 도구로 본다.

## Runtime Guide Guard Summary

Runtime reads local OHS serving artifacts instead of koshaontology working files:

```text
OHS/backend/app/data/guide_domain_profiles.json
OHS/backend/app/data/broad_sr_policy.json
```

Serving candidate gates:

```text
confidence >= 0.65
review_status in ('candidate', 'asserted')
broad SRs are secondary-only and cannot create standard procedures or legacy fallback results by themselves
needs_review/rejected candidates are excluded from serving
```

Guide recommendations consume the 1,038 manual Guide usage profiles exported from Pipe-B. Standard procedure scoring is guarded so broad SRs, broad/generic features, and industry alignment cannot create top Guide procedures alone.

The current accepted OHS runtime baseline is `usage_profile11`. Guide recommendations require actionable SHE evidence before SHE can directly create standard procedures/checklist items. Context-only SHE still informs reasoning and status, but it no longer creates top Guide procedures by itself.

Latest validation:

```text
baseline: usage_profile11
synthetic Guide v1~v10: 2,360 samples
legacy obvious top Guide mismatch: 1,145
current obvious top Guide mismatch: 165
reduction: 85.59%
NO_TOP: 395
v10 synthetic SHE recall 100.0%, FN 0, FP 0
actual response 240 status changed 0
negative_false_positive 10
positive_missed 2
ambiguous_over_promoted 5
backend compileall OK
frontend npm run build OK
```

Latest reports:

```text
docs/status/evaluation-baseline.md
pictures-json/reports-manifest.json
```

Local/external report bodies referenced by the manifest include the `usage_profile11` synthetic Guide, NO_TOP, v10 smoke, and actual 240 replay reports.

Rejected approach: widening hazard/risk text alias inference at status level. It reduced some NO_TOP cases but changed actual 240 status behavior, so remaining Guide coverage should be handled through usage profiles, visual triggers, and WorkProcess relevance.
