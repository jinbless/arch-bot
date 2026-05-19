# Hazard-Direct Pivot — Phase 1 Day 1 (HAZARD_DIRECT_SCHEMA + Prompt)

> **Sprint**: [hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md) Phase 1 / 5
> **Trigger**: [moellab-vs-devserver-comparison.md](moellab-vs-devserver-comparison.md) — GPT 자연어 hazards 37/37 합리적 입증
> **Status**: Day 1 완료 (schema + prompt + 단위 테스트 8/8 PASS). Day 2-3은 실호출 + 미세 조정.

---

## 변경 요약

| 파일 | 변경 |
|---|---|
| `serving-team/08-app/backend/app/integrations/openai_client.py` | `ONTOLOGY_OBSERVATION_SCHEMA`에 `hazards[]` 신규 필드 + top-level `required`에 `hazards` 추가 |
| `serving-team/08-app/backend/app/integrations/prompts/analysis_prompts.py` | `IMAGE_ANALYSIS_PROMPT` + `TEXT_ANALYSIS_PROMPT`에 hazards 추출 지침 + 14개 표준 라벨 추가 |
| `serving-team/08-app/backend/tests/unit/test_ontology_schema.py` | 신규 — 8개 단위 테스트 (strict mode invariants 자동 검증) |
| `serving-team/08-app/backend/tests/unit/__init__.py` | 신규 — pytest collection |

---

## hazards[] 스키마 (OpenAI strict mode)

```json
"hazards": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "name":                {"type": "string"},
      "risk_level":          {"type": "string", "enum": ["high","medium","low"]},
      "location":            {"type": "string"},
      "description":         {"type": "string"},
      "preventive_measures": {"type": "array", "items": {"type": "string"}}
    },
    "required":            ["name","risk_level","location","description","preventive_measures"],
    "additionalProperties": false
  }
}
```

Strict mode 호환:
- 모든 5개 필드가 `required`에 포함
- `additionalProperties: false`
- top-level `required`에 `hazards` 추가 (배열 자체는 빈 배열 허용, items strict)

기존 `risk_feature_candidates`는 그대로 유지 (호환성/fallback). Pivot 후에도 normalizer 양쪽 path 호출.

---

## 표준 hazard 라벨 (14개)

prompt에서 GPT에 제시하는 가급적 사용 라벨. moellab 출력에 자주 등장 + KOSHA 사고분류 카테고리 정렬:

```text
끼임/협착, 전도/미끄럼, 추락, 낙하물, 충돌, 감전,
유해물질, 화재/폭발, 화상, 인간공학, 기계적위험,
소음/진동, 온도극단, 폐쇄공간/질식
```

사진에 명확한 다른 위험이 보이면 자유 자연어 가능 (Phase 2 매핑 단계에서 alias seed로 학습).

Prompt 규칙:
- 사진에 명확한 단서가 있을 때만 hazard 추가 (가설 금지)
- 같은 사진에서 보통 3-5개 hazard 식별 (moellab 8 photo 평균 4.6)
- `name`은 위험 발생 양상 자체 (사고형). PPE 부족이나 환경 자체는 description/preventive_measures에 기재
  - 예: '안전모 미착용' → name `'낙하물'` 또는 `'추락'`; '안전모 미착용'은 description에
  - 이 분리가 Phase 2 mapping 일관성 + Step 2 T4 #1 후속 manual review 결과 반영

---

## 검증

### 단위 테스트 (8/8 PASS)

```bash
cd serving-team/08-app/backend
PYTHONIOENCODING=utf-8 python tests/unit/test_ontology_schema.py
```

테스트 항목:
1. `test_schema_top_level_has_hazards` — hazards 필드 추가 + required 포함
2. `test_schema_keeps_risk_feature_candidates` — fallback 호환
3. `test_hazards_items_required_full` — 5 필드 모두 required + additionalProperties=False
4. `test_hazards_risk_level_enum` — {high, medium, low}
5. `test_hazards_preventive_measures_is_string_array`
6. `test_schema_strict_mode_invariants` — 모든 object scope 자동 검증
7. `test_risk_feature_candidates_text_enum_still_constrained` — Tier 3.A 보존
8. `test_prompt_mentions_hazards_section` — 표준 라벨 4종 포함

### Schema 구조 cross-check

- top-level properties: `visual_observations`, `visual_cues`, `hazards`, `risk_feature_candidates`, `overall_assessment`, `immediate_actions`
- top-level required: 동일 (6/6)
- catalog codes (text enum): 529개 (Tier 3.A 유지)

---

## Token cost 추정

기존 ONTOLOGY_OBSERVATION_SCHEMA는 ~12.6KB JSON. `hazards[]` 추가로 schema 크기 ~+1.0KB (~+8%). 응답 부분도 보통 3-5 hazards × ~80 tokens ≈ +300-400 tokens / call.

기존 대비 약 +10-15% token 증가 예상 (Plan Phase 1 Day 2에서 8 photo 실호출로 정밀 측정).

임계점 초과 시 prompt 축약 + standard label을 외부 reference로 분리.

---

## 다음 단계 (Phase 1 Day 2-3)

### Day 2 — 8 real-test-photo 실호출 검증
- `make f1-eval` 실행 (8 photo, gpt-4.1 호출, ~$0.40 + 8분)
- moellab `.compare_moellab/*.json` 응답과 hazards[].name spot-check
- token usage 측정 + cost 비교
- 산출: `.compare_moellab/dev_after_pivot_phase1.json`

### Day 3 — Prompt 미세 조정
- false positive 0 / 누락 0 목표
- spot-check 결과 기반 표준 라벨 수정 (예: '기계적위험' → '기계물림' 등)
- 단위 테스트 추가 (false positive 회귀 검증)
- Phase 1 완료 보고서 `phase1-day2-3-validation.md`

### Phase 2 진입 조건
- 8 photo hazards[] ≥3 per photo, false positive 0
- token cost <+20% (~+$0.05/photo)
- 단위 테스트 100% PASS

---

## Related

- [hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md) — Sprint plan 정본
- [moellab-vs-devserver-comparison.md](moellab-vs-devserver-comparison.md) — pivot 근거
- [T3.A-closed-vocab-schema-enum.md](T3.A-closed-vocab-schema-enum.md) — Tier 3.A 보존 정책
- [t4-77-she-manual-review-results.md](t4-77-she-manual-review-results.md) — name vs description 분리 원칙 근거
