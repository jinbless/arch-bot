# Closed vocabulary prompt — Day 3 honest assessment

**날짜**: 2026-05-18 (Hybrid sprint Day 3)
**작업**: Layer 0 Vision LLM prompt에 catalog enum 명시 + schema axis 5 확장

## 적용한 변경

### 1. Schema fix (`openai_client.py:ONTOLOGY_OBSERVATION_SCHEMA`)
```python
"axis": {"enum": ["accident_type", "hazardous_agent", "work_context",
                  "ppe_state", "environmental"]}  # 3 → 5
```
→ F.2 catalog v3.3 5-axis 활용 가능 (이전 schema에서 ppe_state/environmental 차단됨).

### 2. Prompt enum 동적 첨부 (`prompts/prompt_builder.py`)
- `_load_catalog_enums()`: catalog v3.3 481 codes 동적 load
- `_build_axis_enum_text()`: 5 axis별 codes list를 prompt에 첨부
- token 비용: per-call +3-4K tokens (~$0.001 추가)

## 측정 결과 (8-photo eval ON state, closed vocab 적용)

LLM이 생성한 raw_vision_features 분석:

**부분 효과** ✓:
- `axis` 값을 catalog 5-axis 모두 사용 (ppe_state, environmental 활성화)
- UPPER_SNAKE_CASE 형식 따름 (`HELMET_WORN`, `WET_SURFACE` 등 olds 잘 사용)

**미해결** ✗:
- LLM이 catalog 본 후에도 **자기 판단으로 free creation**:
  - `ELEVATED_WORK (work_context)` — catalog 미존재
  - `STEEL_STRUCTURE (hazardous_agent)` — catalog 미존재
  - `CONSTRUCTION_SITE (work_context)` — catalog 미존재
  - `HARNESS_USED` — `HARNESS_WORN`/`TIED`가 정답
- normalizer_unknown 발생률 **감소 없음 또는 약간 증가** (이전과 유사)

## 진단

**현재 prompt 방식의 한계**:
- catalog 481 codes를 prompt에 명시 → LLM이 인지하나 따르지 않음
- "위 코드 외 생성 금지" 부정 instruction → LLM이 alternative 시도
- Schema text field는 free string (axis enum만 제약)

**진짜 해결 = schema-level text enum constraint**:
- Option A: `text` field에 single big enum (481 codes) — OpenAI strict 호환성 의문, 어떤 axis든 어느 code도 가능 (axis-code mismatch 가능)
- Option B: `oneOf` per-axis (axis별 다른 enum) — OpenAI strict mode 미지원
- Option C: 다른 model (gpt-5 등 stronger instruction following)
- Option D: Few-shot examples — 5-10 input/output pair 추가

## 결정 — Sprint 정리

**이번 sprint에서 얻은 진짜 가치**:
- ✅ Schema axis enum 5로 확장 (F.2 catalog 활용 가능, 진짜 가치)
- ⚠️ Prompt enum 명시 (효과 부분적, 비용 ~$0.001/call)
- ✅ promote_she_review.py 인프라 (Day 5 SHE는 활용 불가지만 코드 보존)
- ✅ Day 1-3 transparency report

**추가 작업 가치 vs cost**:
- Day 4-5 (A/B + Day 6 photo eval): 효과 측정 noise 큼, 비용 ~$1-2
- Day 7 (runbook): closed vocab 효과 미미하면 runbook 가치 낮음
- 결론: Sprint 단축, Day 3 결과 commit 후 마무리

**별도 plan 후보 (closed vocab 본격 진행 시)**:
- Schema text enum 적용 (Option A) — OpenAI strict 호환 확인 후
- Few-shot prompting (Option D)
- gpt-5 model 비교 (Option C)
- broader prompt engineering A/B testing

## 보존 가치

이번 작업의 commit-worthy 항목:
1. `prompt_builder.py` enum 동적 load (rollback 쉬움, 영구 유지 가치)
2. Schema axis 5 확장 (F.2 catalog 활용)
3. `promote_she_review.py` 인프라 (향후 narrower SHE에 활용)
4. 본 보고서 + Day 1-2 promote_she_review 보고서

## 다음 권장
- **option 1**: 본 sprint 종료, F.3 closing 또는 다른 우선순위
- **option 2**: 새 plan 작성 (schema enum or few-shot, 별도 sprint)
- **option 3**: 작은 작업 묶음 (8 candidate axiom promote, A hook always-on, etc.)
