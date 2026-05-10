# 다음 세션 시작 지침

최신 갱신일: 2026-05-10

이 문서는 다른 Codex/LLM 세션이 현재 상태를 빠르게 이어받기 위한 시작점이다.

## 1. 현재 작업 디렉토리

```text
C:\project\arch-bot
```

하위 프로젝트는 별도 git repository다.

```text
C:\project\arch-bot\OHS
C:\project\arch-bot\koshaontology
C:\project\arch-bot\legalize-kr
```

루트 `git status`만 보면 `OHS` 변경사항이 보이지 않을 수 있다. 반드시 필요한 경우 각 하위 디렉토리에서 따로 확인한다.

## 2. 먼저 읽을 문서 순서

1. `README.md`
2. `MONOREPO_TRANSITION_PLAN.md`
3. `DATA_GOVERNANCE.md`
4. `repositories.md`
5. `docs/architecture/source-provenance.md`
6. `WORKPLAN_LLM_DOMAIN_GUARD.md`
7. `온톨로지_통합구조_및_흐름도.md`
8. `OHS/README.md`
9. `needToChangeCode.md`
10. `koshaontology/pipe-A/status_pipea.md`
11. `koshaontology/pipe-B/status_pipeb.md`
12. `koshaontology/pipe-C/status_pipec.md`

레이어별 세부 구조를 봐야 하면 다음 문서를 읽는다.

```text
온톨로지_법령레이어_상세도.md
온톨로지_SR레이어_상세도.md
온톨로지_위험상황레이어_상세도.md
온톨로지_가이드레이어_상세도.md
온톨로지_벌칙레이어_상세도.md
```

## 3. 현재 구조 요약

### 3.1 Repository / monorepo baseline

현재는 실제 monorepo 편입 전 단계다. 루트 `arch-bot`은 main article과 운영 기준 문서를 관리하고, `OHS`, `koshaontology`, `legalize-kr`는 여전히 별도 `.git`을 가진 child repository다.

2026-05-10 기준:

```text
koshaontology pushed baseline: 60d025ee873e071faf9c90cc0b1a89b05c4812bd
OHS pushed baseline: 7eed7280e1ece9fa7bb32beb182017f5cfa96f5a
legalize-kr: external dependency, push target excluded
```

다음 세션에서 git 작업을 할 때는 여전히 각 디렉토리에서 따로 상태를 확인한다.

```bash
git -C /mnt/c/project/arch-bot status --short
git -C /mnt/c/project/arch-bot/koshaontology status --short
git -C /mnt/c/project/arch-bot/OHS status --short
git -C /mnt/c/project/arch-bot/legalize-kr status --short
```

### 3.2 Product / ontology baseline

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

## 4. OHS 실행

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

- 프론트 개발 기본 API fallback은 `http://localhost:8001/api/v1`이다.
- CORS 허용 origin은 `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`이다.
- `OPENAI_API_KEY`가 없으면 실제 이미지/텍스트 분석은 503이 날 수 있다.
- PostgreSQL은 `postgresql://kosha:1229@localhost/kosha` 기준이다.

## 5. 검증 명령

Python 문법 검증은 `__pycache__` 권한 문제를 피하기 위해 compile 기반으로 수행한다.

```bash
cd C:/project/arch-bot/OHS/backend
python -c "import pathlib; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in pathlib.Path('.').rglob('*.py') if '__pycache__' not in p.parts]; print('compile ok')"
```

프론트 빌드:

```bash
cd C:/project/arch-bot/OHS/frontend
npm run build
```

합성 테스트 smoke:

```bash
cd C:/project/arch-bot/OHS/backend
python scripts/evaluate_synthetic_observations.py --input ../../pictures-json/synthetic_observations_v10.jsonl --report-prefix synthetic_observations_v10_domain_guard2
```

최신 참고 리포트:

```text
pictures-json/reports/synthetic_observations_v10_domain_guard2_report.md
pictures-json/reports/actual_response_samples_v1_v10_domain_guard2_vs_pipeb1038.md
pictures-json/reports/synthetic_observations_v1_v10_v10fix6_confusion_matrix.md
```

## 6. 현재 검증 기준선

```text
Python compile: OK
OHS backend compileall: OK
frontend npm run build: OK
synthetic Guide v1~v10 usage_profile5:
  total samples 2,360
  legacy obvious top Guide mismatch 1,151
  current obvious top Guide mismatch 220
  reduction 80.89%
v10 usage_profile5:
  SHE recall 100.0%
  SHE false negative 0
  SHE false positive 0
  normal suppression 100.0%
actual response 240 usage_profile5_vs_pipeb1038:
  status changed 0
  negative_false_positive 10
  positive_missed 2
  ambiguous_over_promoted 5
```

최신 신규 리포트:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile5_20260510_000306.md
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile5_20260510_000435.md
pictures-json/reports/synthetic_observations_v10_usage_profile5_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile5_vs_pipeb1038.md
pictures-json/reports/synthetic_observations_v10_domain_guard_broad_sr_policy_report.md
pictures-json/reports/actual_response_samples_v1_v10_domain_guard1_vs_pipeb1038_broad_sr_policy.md
pictures-json/reports/actual_response_samples_v1_v10_domain_guard1_vs_pipeb1038_broad_sr_policy_watch_summary.md
```

## 7. 바로 이어서 할 일

우선순위는 다음 순서다.

1. `synthetic_guide_no_top_queue_usage_profile5_20260510_000435.*`의 404 NO_TOP 큐를 먼저 처리한다. `synthetic_fixture_gap` 72는 평가 fixture 수정/제외 후보이고, 나머지는 taxonomy/profile/WorkProcess coverage 후보로 본다.
2. 남은 `industry_boundary_gap` 211을 보되, 단순 keyword 추가가 아니라 Guide usage profile의 `observable_required_cues`, `negative_boundaries`, `procedure_role`, `primary_work_process_ids` 보강으로 처리한다.
3. `B-M-11`, `A-G-9`, `A-G-14`, `A-G-18`, `D-C-7` 등 아직 top count가 큰 Guide는 실제 positive까지 잘라내지 않는지 샘플을 보고 조정한다.
4. DB import를 한다면 먼저 `guide_sr_link_candidates` duplicate unique key 2쌍을 evidence merge/pre-aggregate하고, `method=codex_manual_pilot` replace-per-method 전략으로 candidate table에만 적재한다. asserted mapping update는 계속 0으로 둔다.
5. 브라우저 자동화로 분석 화면까지 timeout 없이 smoke test한다.

### 2026-05-09 usage_profile2 인계

위 2번의 1차 보강은 완료됐다. 다음 세션은 usage_profile2 리포트를 기준으로 이어간다.

```text
리포트:
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile2_20260509_233015.md
pictures-json/reports/synthetic_observations_v10_usage_profile2_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile2_vs_pipeb1038.md

결과:
synthetic Guide mismatch 1,150 -> 361 (68.61% 감소)
v10 SHE recall 100.0%, FN 0, FP 0
actual response 240 status changed 0
negative_false_positive 10
positive_missed 2
ambiguous_over_promoted 5
```

다음 우선순위:

```text
1. NO_TOP/missing_usage_profile 367건을 taxonomy/profile gap과 정상 no-procedure로 분리한다.
2. 남은 top overexposed Guide: A-G-12, A-G-9, C-70, H-100, A-R-2, H-187, A-G-14, E-M-4.
3. WorkProcess mismatch: D-C-7, E-G-22, H-116, M-62.
4. negative safe case no-procedure gate를 설계한다.
```

### 2026-05-10 usage_profile5 인계

위 우선순위 중 overexposed Guide 2차 보강과 NO_TOP 큐 분리는 완료됐다. 다음 세션은 usage_profile5 리포트를 기준으로 이어간다.

```text
리포트:
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile5_20260510_000306.md
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile5_20260510_000435.md
pictures-json/reports/synthetic_observations_v10_usage_profile5_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile5_vs_pipeb1038.md

결과:
synthetic Guide mismatch 1,151 -> 220 (80.89% 감소)
NO_TOP 404: synthetic_fixture_gap 72, taxonomy/profile/workprocess gap 332
v10 SHE recall 100.0%, FN 0, FP 0
actual response 240 status changed 0
negative_false_positive 10
positive_missed 2
ambiguous_over_promoted 5
```

### 2026-05-10 usage_profile11 인계

usage_profile5 이후 negative/safe-case Guide 과추천을 더 보수적으로 줄였다. 현재 세션의 최신 기준선은 usage_profile11이다.

핵심 변경:

```text
표준절차/즉시조치 추천은 actionable SHE match만 직접 근거로 사용한다.
context-only/non-actionable SHE는 finding reasoning에는 남지만 Guide 절차를 단독 생성하지 않는다.
hazard_normalizer/hazard_rule_engine을 넓히는 방식은 actual 240 status 경계를 흔들어서 폐기했다.
```

리포트:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile11_20260510_011317.md
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile11_20260510_011333.md
pictures-json/reports/synthetic_observations_v10_usage_profile11_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038.md
```

결과:

```text
synthetic Guide mismatch 1,145 -> 165 (85.59% 감소)
NO_TOP 395
v10 SHE recall 100.0%, FN 0, FP 0
actual response 240 status changed 0
negative_false_positive 10
positive_missed 2
ambiguous_over_promoted 5
backend compileall OK
frontend build OK
```

다음 우선순위:

```text
1. usage_profile11을 현재 accepted baseline으로 둔다.
2. NO_TOP 395는 risk alias 추가가 아니라 Guide usage_profile/WorkProcess coverage 보강으로 처리한다.
3. 우선 큐는 chemical_profile_gap 64, construction_fall_profile_gap 57, service_sector_taxonomy_gap 49, machine_profile_gap 43, burn_heat_profile_gap 25다.
4. `C-C-80-2026`, `G-93-2012`처럼 일반/문서 성격 Guide가 CI-SR fallback으로 현장 표준절차에 뜨는 잔여 케이스를 먼저 감사한다.
5. candidate DB import 전 duplicate SR 후보 evidence merge/pre-aggregate와 replace-per-method 전략을 확정한다. asserted mapping update는 0 유지.
```

## 8. 작업 시 주의

- `OHS/frontend/node_modules/**` 문서는 vendor 문서이므로 수정하지 않는다.
- `pictures-json/reports/**`의 과거 생성 리포트는 최신 문서 링크만 갱신하고 본문을 일괄 수정하지 않는다.
- `koshaontology` phase 문서는 과거 실행 재현 문서다. 현재 구조와 다르다고 본문을 새 기록처럼 바꾸지 말고, 상단 안내나 Pipe 상태 문서에서 차이를 설명한다.
- `PenaltyRoute`, `penaltyForArticle`, `SeverityLevel`, `hasSeverityLevel`, `she:ContextFeature`, `she:SituationalHazardEvent`는 과거 용어다. 새 설계 설명에서는 쓰지 않는다.
