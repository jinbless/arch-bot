# Hazard-Direct Architecture Pivot (Sprint Plan, ~3주)

> **Status**: 계획 등록 완료 (2026-05-19, 사용자 승인 후 정본화). Phase 1부터 다음 세션 시작.
> **Trigger**: 본 세션 [moellab-vs-devserver-comparison.md](../dev-notes/moellab-vs-devserver-comparison.md) + [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md) 결과로 식별된 architecture pivot 후보.
> **Predecessor**: T4 #1 후속 sprint (manual review + matcher refactor plan) — main `1bfd6b8` ~ `4783edc`
> **Predicted duration**: ~3주 (5 Phase × 평균 5일)
> **Predicted cost**: ~$0.50 ($0.20 Phase 2 seed Sonnet + ~$0.30 Phase 2 Day 5-7 closed loop)

---

## Context

### 문제 진단

본 세션 결과로 다음 두 가지가 입증됨:

1. **현재 SHE matcher 회귀 문제**:
   - [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md) Step 2 결과: approve 57 SHE 중 5만 promote해도 **she_accuracy -10.17%p VETOED**. audit 5회 history 모두 동일 패턴(-7~-10%p) → matcher 자체 로직 문제.
   - sub-cause: PPE state를 hard signal로 사용 + broadness_score를 ranking에 미반영 (테마 A 8건 manual review 결과로 입증).

2. **GPT의 hazard 직접 식별이 매우 정확**:
   - [moellab-vs-devserver-comparison.md](../dev-notes/moellab-vs-devserver-comparison.md): moellab(우리 초안)에서 GPT-4.x 1회 호출로 자연어 hazards 추출 → **8 사진 / 37 hazards 모두 합리적 (false positive 0)**.
   - moellab의 한계는 hazard 식별이 아니라 `related_guides`의 `mapping_type: "title_match"` (단순 제목 키워드) — 우리 ontology reasoning이 이 부분 우위.

### Pivot 가설

> **Vision LLM이 위험요소(hazards)를 자연어로 직접 출력 → 자연어 hazard.name → catalog code alias 매핑 → 우리 ontology reasoning으로 Guide/Penalty 추천**
>
> ⇒ SHE matcher 회귀 부담 본질적 감소 + GPT 자연어 정확성 + 우리 ontology 차별점 (3-경로 penalty + SWRL 추론) 모두 유지.

### 의도된 결과

- 사용자 화면: moellab 스타일 자연어 `hazards[]` (직관적) + 우리 정형 Guide procedure + 3-경로 penalty 병기
- A/B Gate 3 PASS: 새 hazard-direct path가 기존 SHE-based path보다 she_accuracy regression 없거나 개선
- SHE matcher는 fallback (broadness refactor sprint와 통합 또는 후행)

---

## Architecture (Before/After)

### Before (현재)

```
Vision LLM (ONTOLOGY_OBSERVATION_SCHEMA, 532 codes enum)
  └─ risk_feature_candidates[] (axis, code enum, evidence, confidence)
  ↓
hazard_normalizer.normalize_risk_feature_candidates() (T1.C alias step 4.5)
  ↓
risk_rule_service.apply_risk_rules() → canonical (3축)
  ↓
situation_assessment_service.match_situational_patterns() → SHE matches  ← ❌ 회귀 risk
  ↓
sr_lookup_service.query_safety_requirements() → SR ids
  ↓
guide_recommendation_service.get_standard_guides() → guide rows
  ↓
penalty_path_service.build_penalty_paths() → 3-경로
```

### After (Pivot)

```
Vision LLM (HAZARD_DIRECT_SCHEMA, hazards[] + risk_feature_candidates[] 둘 다)
  ├─ hazards[] (name 자연어, risk_level, location, description, preventive_measures)  ← ⭐ 신규
  └─ risk_feature_candidates[] (기존 그대로, 호환성/fallback)
  ↓
hazard_normalizer.normalize_hazards_array()  ← ⭐ 신규
  └─ hazard.name → catalog code (T1.C alias + 신규 Gate 1-2 자동 등재)
  ↓
hazard_to_guide_service.match_hazards_to_guides()  ← ⭐ 신규
  ├─ canonical 3축 → hazard_rule_engine.query_sr_for_facets() (재사용)
  └─ get_guides_from_srs() (재사용)
  ↓
guide_recommendation + Phase G.2 domain profile (재사용)
  ↓
penalty_path_service.build_penalty_paths() (재사용, 3-경로 차별점)
  ↓
AnalysisResponse 확장:
  ├─ hazards: List[HazardItem]  ← ⭐ 신규 (자연어 + preventive_measures)
  ├─ hazard_guide_relations: List[HazardGuideRelation]  ← ⭐ 신규
  ├─ standard_procedures (기존, Guide procedure)
  └─ penalty_paths (기존, 3-경로)

SHE matcher path: fallback layer (broadness-aware refactor 후 통합)
```

---

## Goal + Acceptance Criteria

| # | 기준 | 검증 |
|---|---|---|
| AC-1 | 새 `hazards[]` 응답 필드 항상 채워짐 | 8 real-test-photo 모두 ≥3 hazards, 자연어 카테고리 |
| AC-2 | hazards → catalog code 매핑 정확도 ≥ 85% | 8 photo + 30-50 seed 검증 |
| AC-3 | 새 path Gate 3 통과 | she_accuracy regression ≤ 0.02, penalty_accuracy 유지 또는 개선 (Phase G.3 +27.16%p 보존) |
| AC-4 | A/B 검증 | 기존 SHE path vs 새 hazard-direct path Guide 추천 ≥80% overlap |
| AC-5 | Frontend 자연어 hazard 섹션 + 관련 Guide 병기 정상 렌더링 | 8 photo 시연 통과 |

---

## Phase 1 — HAZARD_DIRECT_SCHEMA + GPT prompt 갱신 (3일)

### Day 1
- `serving-team/08-app/backend/app/integrations/openai_client.py`의 `ONTOLOGY_OBSERVATION_SCHEMA`에 `hazards[]` 신규 필드 추가:
  ```json
  "hazards": {
    "type": "array",
    "items": {
      "type": "object",
      "required": ["name", "risk_level", "location", "description", "preventive_measures"],
      "properties": {
        "name": {"type": "string"},
        "risk_level": {"enum": ["high","medium","low"]},
        "location": {"type": "string"},
        "description": {"type": "string"},
        "preventive_measures": {"type": "array", "items": {"type":"string"}}
      }
    }
  }
  ```
- `IMAGE_ANALYSIS_PROMPT` 갱신: hazards 추출 지침 + moellab 스타일 자연어 카테고리 예시 ("끼임/협착", "전도/미끄럼", "추락", "낙하물", "충돌", "감전", "유해물질", "화재/폭발", "화상", "인간공학" 등).
- 기존 `risk_feature_candidates`는 그대로 유지 (호환성 + fallback).

### Day 2
- 8 real-test-photo로 새 schema 실호출 검증. moellab 결과와 유사한지 spot-check.
- Cost 검증: token 증가량 측정 (~+15% 예상).

### Day 3
- prompt 미세 조정 (false positive 0, 누락 0 목표). 단위 테스트 추가.
- 산출: `docs/dev-notes/hazard-direct-phase1-schema.md` runbook.

---

## Phase 2 — hazard.name → catalog code 자동 매핑 (1주)

### Day 1-2 — 초기 alias seed (Sonnet 4.6 자동 + 사용자 vetted)
- `data-team/05-enrichment/llm-scripts/generate_hazard_name_seed.py` 신규:
  - 입력: moellab 8 사진 응답의 hazards[].name 분포 + catalog v3.3 529 codes
  - Sonnet 4.6 호출 (~$0.20, 1시간 자동): 자연어 → catalog code 매핑 30-50개 제안 + 신뢰도
  - 출력: `data-team/05-enrichment/runtime-artifacts/hazard_name_seed.json`
- 사용자 vetted (1시간): proposal review + 수정 (REVIEWED.json 패턴 답습)
- vetted seed → `auto_register_aliases.py` Gate 1-2 검증 → `risk_feature_aliases.json`에 vetted 등재

### Day 3-4 — runtime 매핑 함수
- `serving-team/08-app/backend/app/services/hazard_normalizer.py`에 신규 함수:
  ```python
  def normalize_hazards_array(hazards: list[dict]) -> dict:
      """GPT hazards[] → canonical + unknown_names"""
      for h in hazards:
          code = _resolve_alias_code(h['name'], axis)  # 기존 함수 재사용
          if code: append; _log_alias_usage(...)
          else: collect_unknown(h)
      return canonical + unknown
  ```
- 기존 `_resolve_alias_code()`, `_log_alias_usage()` 재사용. T1.C 로깅 흐름 유지.

### Day 5 — closed-loop 자동 등재
- unknown hazard.name 누적 시 `auto_register_aliases.py` Gate 1-2 자동 호출.
- `risk_feature_aliases_candidates.json` 후보 추가 → 50회 사용 또는 confidence ≥0.85 시 vetted 승격.

### Day 6-7 — 8 photo + 2360 synthetic 회귀 검증
- 8 photo 매핑 정확도 측정 (AC-2 ≥85%).
- 2360 synthetic replay → Gate 3 통과 검증.
- 산출: `docs/dev-notes/hazard-direct-phase2-mapping.md` + 신규 vetted alias 30-50건.

---

## Phase 3 — Hazard-based Guide 추천 layer (1주)

### Day 1-2 — `hazard_to_guide_service.py` 신규
- `serving-team/08-app/backend/app/services/hazard_to_guide_service.py` 신규:
  ```python
  def match_hazards_to_guides(canonical: dict, hazards_raw: list[dict]) -> list[HazardGuideRelation]:
      """canonical 3축 → SR → Guide. 결과를 hazard별로 grouping."""
      sr_ids = hazard_rule_engine.query_sr_for_facets(...)  # 재사용
      guides = hazard_rule_engine.get_guides_from_srs(sr_ids)  # 재사용
      filtered = guide_recommendation_service._prioritize_preferred_guide_ci_results(guides)
      return [HazardGuideRelation(hazard=h, guides=top_n) for h in hazards_raw]
  ```

### Day 3 — analysis_pipeline 통합
- `serving-team/08-app/backend/app/services/analysis_pipeline.py` 갱신:
  - `_build_knowledge_context()`에 hazard-direct path 분기 추가
  - 두 path 병행 (기존 SHE-based + 신규 hazard-direct)
  - 결과 통합: hazards[] / hazard_guide_relations[] / standard_procedures[] (양쪽 union)
- LLM rerank (Phase B)는 양쪽 path 결과에 동일 적용.

### Day 4-5 — A/B 검증
- Feature flag `HAZARD_DIRECT_MODE=parallel|primary|off`:
  - `off`: 기존 path만 (control)
  - `parallel`: 두 path 모두, 결과 union
  - `primary`: hazard-direct 우선, SHE fallback
- 2360 synthetic + 8 photo로 세 mode 비교:
  - she_accuracy / penalty_accuracy / overall_accuracy / false_positive_rate
  - Guide 추천 overlap %

### Day 6-7 — penalty 차별점 검증
- Phase G.3 penalty_accuracy +27.16%p가 새 path에서도 유지되는지 검증.
- `penalty_path_service.build_penalty_paths(sr_ids)` 재사용 (sr_ids는 hazard → canonical → SR 경로로 도달).

---

## Phase 4 — 응답 schema + Frontend 확장 (3일)

### Day 1 — Backend schema
- `serving-team/08-app/backend/app/models/analysis.py`:
  ```python
  class HazardItem(BaseModel):
      name: str
      risk_level: RiskLevel
      location: str
      description: str
      preventive_measures: list[str]
      mapped_codes: list[str] = []  # catalog code 매핑 결과 (audit)

  class HazardGuideRelation(BaseModel):
      hazard_name: str
      guides: list[GuideRef]  # guide_code, title, relevance_score, top_procedure_title

  class AnalysisResponse(BaseModel):
      # 기존 필드 유지
      ...
      hazards: list[HazardItem] = []                            # ⭐ 신규
      hazard_guide_relations: list[HazardGuideRelation] = []    # ⭐ 신규
  ```

### Day 2 — Frontend
- `serving-team/08-app/frontend/src/components/results/`:
  - `RiskOverviewPanel.tsx` 확장: `hazards[]` 자연어 섹션 추가 (moellab 스타일)
  - 신규 `HazardGuideRelationsPanel.tsx`: 각 hazard별 관련 Guide + top procedure title
  - 기존 `GuideProcedurePanel.tsx`는 그대로 (standard_procedures 사용)
- `analysis.ts` type 갱신.

### Day 3 — 통합 시연
- 8 real-test-photo 시연 (dev-up):
  - 화면에 자연어 hazards + 관련 Guide + 3-경로 penalty 동시 표시
  - moellab과 side-by-side 비교 (사용자 검증)

---

## Phase 5 — Verification + 정본 문서 + Architectural debt (3일)

### Day 1 — Gate 3 최종
- 전체 path (Phase 1+2+3+4) 통합 + 2360 synthetic replay + 8 photo eval
- `make f1-eval` + regression_gate
- 모든 AC-1 ~ AC-5 통과 확인

### Day 2 — 정본 문서 갱신
| 문서 | 변경 |
|---|---|
| `docs/status/current-session.md` | L3 main HEAD + hazard-direct H3 section + 다음 작업 |
| `docs/workplans/llm-accelerated-ontology-engineering.md` | Status 표 — `hazard-direct architecture pivot` ✅ 완료 |
| `docs/architecture/4-layer-architecture.md` | Layer 0 (Vision LLM)에 hazards 직접 출력 추가 |
| `docs/architecture/llm-dependency-evolution.md` | hazard-direct 정식 path 명시 |
| `docs/architecture/ontology-learning-layer.md` | Module 4.1 (Term Extraction) hazard.name auto-register |
| `docs/status/evaluation-baseline.md` | 새 path Gate 3 결과 + A/B 비교 표 |
| `data-team/README.md` + `serving-team/README.md` | 새 service 반영 |
| `scripts/verify_session_docs.py` | SESSION_COMMITS + NEW_DOCS + METRIC_EXPECTATIONS + COMPLETION_MARKERS 확장 |

### Day 3 — commit + main merge + GitHub push + Architectural debt 해소
- 본 sprint 산출 commit + main merge + push
- 잔존 architectural debt 3가지 처리 (Step 6에서 식별):
  - PG → TTL re-export script (`data-team/04-ontology-export/` 채우기)
  - SHACL shape for `she:SituationalHazardPattern` (`serving-validation-shapes-v3-she-patch.ttl`)
  - promote된 SHE의 ontology export 정책 결정
- verify_session_docs.py 실행 PASS 확인.

---

## Critical Files

### 수정 (5 files)
```
serving-team/08-app/backend/app/integrations/openai_client.py
  └─ ONTOLOGY_OBSERVATION_SCHEMA에 hazards[] 추가 + IMAGE_ANALYSIS_PROMPT 갱신
serving-team/08-app/backend/app/services/hazard_normalizer.py
  └─ normalize_hazards_array() 신규 (_resolve_alias_code + _log_alias_usage 재사용)
serving-team/08-app/backend/app/services/analysis_pipeline.py
  └─ _build_knowledge_context에 hazard-direct path 분기 + 결과 union
serving-team/08-app/backend/app/models/analysis.py
  └─ HazardItem, HazardGuideRelation 신규 + AnalysisResponse 확장
serving-team/08-app/frontend/src/components/results/RiskOverviewPanel.tsx
  └─ hazards[] 자연어 섹션 추가
```

### 신규 (4 files + alias data)
```
serving-team/08-app/backend/app/services/hazard_to_guide_service.py
  └─ match_hazards_to_guides() — Phase 3 핵심
serving-team/08-app/frontend/src/components/results/HazardGuideRelationsPanel.tsx
  └─ hazard별 Guide 매핑 표시
data-team/05-enrichment/llm-scripts/generate_hazard_name_seed.py
  └─ Sonnet 4.6 자동 seed 생성 (Phase 2 Day 1-2)
data-team/05-enrichment/runtime-artifacts/hazard_name_seed.json
  └─ 30-50 자연어 → catalog code seed (사용자 vetted 후)
docs/dev-notes/hazard-direct-phase{1,2,3,4,5}-*.md
  └─ 5 phase runbook
```

### 재사용 (변경 없음)
```
hazard_rule_engine.py: query_sr_for_facets() + get_guides_from_srs()
guide_domain_profile.py: evaluate_guide_domain_profile() (Phase G.2 PG primary)
guide_recommendation_service.py: _prioritize_preferred_guide_ci_results()
penalty_path_service.py: build_penalty_paths() (3-경로 차별점)
auto_register_aliases.py: gate1_embedding() + gate2_llm_verify() (closed loop)
promote_aliases.py: candidate → vetted 승격
hazard_normalizer.py: _resolve_alias_code() + _log_alias_usage()
ONTOLOGY_OBSERVATION_SCHEMA의 risk_feature_candidates: 호환성/fallback 유지
```

---

## Verification (End-to-End)

```bash
# 1. unit + schema 검증
PYTHONIOENCODING=utf-8 python -m pytest serving-team/08-app/backend/tests/test_hazard_direct.py

# 2. 8 real-test-photo 매핑 정확도
make f1-eval  # AC-2 ≥85% 검증

# 3. Gate 3 regression
cd serving-team/08-app/backend
.venv/bin/python -u scripts/replay_synthetic_observations.py --output /tmp/replay_pivot.json
.venv/bin/python scripts/regression_gate.py /tmp/replay_pivot.json --baseline runtime-artifacts/replay_baseline_v3.json

# 4. A/B 비교 (HAZARD_DIRECT_MODE=parallel)
HAZARD_DIRECT_MODE=parallel make dev-up
# (frontend에서 8 photo upload → moellab과 화면 side-by-side 비교)

# 5. verify_session_docs.py
PYTHONIOENCODING=utf-8 python scripts/verify_session_docs.py
```

---

## Risks + Mitigations

| Risk | Probability | 대응 |
|---|---|---|
| 새 hazards[] 추가로 GPT token cost +15% | 중 | Phase 1 Day 2에 측정. 임계점 초과 시 prompt 축약 |
| hazard.name → catalog code 매핑 정확도 <85% | 중 | Phase 2 Day 1-2 seed 30-50 충분 검증. Gate 1-2 closed loop로 점진 보강 |
| 새 path Gate 3 회귀 (she_accuracy) | 낮 | hazard-direct는 SHE chain 우회 → 회귀 risk 낮음. parallel mode로 안전 검증 |
| Frontend 컴포넌트 추가로 인한 layout regression | 낮 | Phase 4 Day 3 시연 검증 |
| Architectural debt 3가지 누적 | 중 | Phase 5 Day 3에 같이 해소 |
| SHE matcher refactor sprint와 timing 충돌 | 중 | 본 sprint 우선 / SHE matcher는 후행 별도 sprint (결정 완료) |

---

## Limits / Scope

### 명시 포함
- HAZARD_DIRECT_SCHEMA + GPT prompt
- hazard.name → catalog code (T1.C + F.1 Gate 1-2 closed loop 재사용)
- hazard-based Guide 추천 (hazard_rule_engine 재사용)
- Frontend hazards 자연어 섹션 + HazardGuideRelations
- A/B mode (parallel/primary/off)
- 정본 문서 + verify script
- Architectural debt 3가지 (Phase 5 Day 3)

### 명시 제외
- SHE matcher 본격 refactor — [`she-matcher-broadness-refactor.md`](she-matcher-broadness-refactor.md) **별도 후행 sprint** (사용자 결정)
- R-4~R-30 SWRL 변환 (별도 sprint)
- Phase J OBO Foundry (별도 plan, 1-3개월)
- LLM rerank (Phase B) 변경 — 그대로 유지
- BFO+LKIF TBox 변경
- Fuseki Java 변경 (Phase G + T4에서 완료된 상태 유지)

### Critical Path

```
Phase 1 (schema) → Phase 2 (mapping)
                      ↓
                   Phase 3 (Guide layer) → Phase 4 (응답+frontend)
                      ↓                       ↓
                   Phase 5 (verification + 정본 문서 + debt 해소)
```

| Phase | 예상 소요 |
|---|---:|
| 1 (schema) | 3일 |
| 2 (mapping + closed loop) | 7일 |
| 3 (Guide layer + A/B) | 7일 |
| 4 (응답 schema + frontend) | 3일 |
| 5 (verification + 정본 + debt) | 3일 |
| **합계** | **23일 (~3주)** |

---

## 결정 완료 (사용자 선택, 2026-05-19)

1. ✅ **Seed 작성 방식**: Sonnet 4.6 자동 생성 + 사용자 vetted (~$0.20 + 1시간)
2. ✅ **SHE matcher refactor 관계**: hazard-direct 우선, SHE matcher는 후행 별도 sprint

## 결정 진행 중 항목 (Phase 진행하며 결정)

3. **HAZARD_DIRECT_MODE 기본값** (Phase 3 Day 4-5 A/B 검증 결과 후 결정):
   - A) `parallel` (두 path 모두 union, 가장 안전)
   - B) `primary` (hazard-direct 우선, SHE fallback)
   - C) Phase 3 검증 결과 보고 결정
4. **Architectural debt 3가지** (PG→TTL / SHACL / export 정책): Phase 5 Day 3에 같이 해소. 시간 부족 시 별도 debt-cleanup sprint로 이관.

---

## Related

- [moellab-vs-devserver-comparison.md](../dev-notes/moellab-vs-devserver-comparison.md) — pivot 근거 (37 hazards 분석 + 권장 architecture)
- [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md) — SHE matcher 회귀 입증 (-10.17%p VETOED 5회)
- [she-matcher-broadness-refactor.md](she-matcher-broadness-refactor.md) — 후행 별도 sprint plan
- [F.1-auto-register-aliases.md](../dev-notes/F.1-auto-register-aliases.md) — T1.C alias closed loop (재사용)
- [phase-g.3-penalty-rule-index-pg.md](../dev-notes/phase-g.3-penalty-rule-index-pg.md) — penalty 3-경로 차별점 (+27.16%p)
