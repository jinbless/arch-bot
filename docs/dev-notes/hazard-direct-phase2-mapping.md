# Hazard-Direct Pivot — Phase 2 Day 1 (Seed Generator)

> **Sprint**: [hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md) Phase 2 / 5
> **Predecessor**: [hazard-direct-phase1-schema.md](hazard-direct-phase1-schema.md)
> **Status**: Day 1 스크립트 작성 + dry-run 검증 완료. Sonnet 4.6 실호출은 사용자 환경에서 별도 진행.

---

## Day 1 작업 요약

### 신규 스크립트

`data-team/05-enrichment/llm-scripts/generate_hazard_name_seed.py`

- 입력: `.compare_moellab/*.json` 8 photo (moellab 응답)
- 입력: `risk_feature_catalog.json` (529 codes / 5 axes)
- 처리: Sonnet 4.6에 unique hazard.name 매핑 요청 (tool schema enum 강제)
- 출력: `data-team/05-enrichment/runtime-artifacts/hazard_name_seed.json`

### dry-run 결과 (8 photo 분포)

```
[catalog v3.3] 5 axes / 532 codes
[moellab] 8 photos / 21 unique hazard names / 37 occurrences

Top names by frequency:
  7  전도/미끄럼
  4  낙하물
  3  끼임/협착
  3  감전
  2  추락
  2  절단
  2  유해물질
  1  중량물 취급
  1  인간공학적 위험(부적절 자세)
  1  근골격계 부담작업
  1  화재/폭발
  1  화상
  1  충돌(지게차 등)
  ...
```

`(지게차 등)`, `(부적절 자세)` 같은 변형 표기 + 일부 중복 ('충돌' vs '충돌(지게차 등)', '중량물' vs '중량물 취급') 포함. Sonnet 매핑이 같은 catalog code로 수렴할 가능성 높음.

---

## Sonnet 4.6 tool schema

```python
{
  "name": "map_hazard_name",
  "input_schema": {
    "type": "object",
    "properties": {
      "axis": {"enum": ["accident_type", "hazardous_agent", "work_context",
                        "ppe_state", "environmental", "UNMAPPABLE"]},
      "code": {"type": "string"},  # post-validation으로 vocab 확인
      "confidence": {"type": "number", "minimum": 0, "maximum": 1},
      "reasoning": {"type": "string", "maxLength": 300}
    },
    "required": ["axis", "code", "confidence", "reasoning"]
  }
}
```

후처리 validation:
- `axis == 'UNMAPPABLE'` 또는 `code == 'UNMAPPABLE'` → unmappable로 분류
- `code` ∉ `axis_codes[axis]` → reject (audit에 기록)
- `confidence < --min-conf` (default 0.80) → reject

---

## 실행 방법

### 분포 확인 (Sonnet 호출 안 함)

```bash
PYTHONIOENCODING=utf-8 python data-team/05-enrichment/llm-scripts/generate_hazard_name_seed.py --dry-run
```

### Sonnet 호출 + seed 생성 (~$0.02-0.05, 1-2분)

```bash
export ANTHROPIC_API_KEY=...
PYTHONIOENCODING=utf-8 python data-team/05-enrichment/llm-scripts/generate_hazard_name_seed.py --apply
# 또는 stricter
PYTHONIOENCODING=utf-8 python data-team/05-enrichment/llm-scripts/generate_hazard_name_seed.py --apply --min-conf 0.85
```

### Plan 예측 cost와의 차이

Plan은 `~$0.20`을 가정 (30-50 unique names + reasoning). 실측 unique names = 21이므로 실제 cost는 ~$0.02-0.05. 사용자가 추가로 더 다양한 photo로 확장하면 cost 증가 (선형).

---

## 출력 schema (`hazard_name_seed.json`)

```json
{
  "generated_at": "2026-05-19T...",
  "model": "claude-sonnet-4-6",
  "min_confidence": 0.80,
  "source_photos": 8,
  "unique_names": 21,
  "total_occurrences": 37,
  "accepted": 16,
  "rejected": 5,
  "mappings": [
    {
      "name": "끼임/협착",
      "frequency": 3,
      "axis": "accident_type",
      "code": "ENTANGLE",
      "confidence": 0.95,
      "reasoning": "...",
      "validation": "ok",
      "vetted": false
    }
  ],
  "unmappable": [...],
  "per_photo_names": {...}
}
```

`vetted: false`는 사용자 검토 대기 (REVIEWED.json 패턴).

---

## 다음 단계 (Phase 2 Day 2-7)

### Day 2 — 사용자 vetted 검토 (1시간)

1. `--apply` 실행해서 `hazard_name_seed.json` 생성
2. JSON 수동 검토:
   - 정확한 매핑 → `vetted: true`
   - 부정확/누락 → axis/code 수정 + `vetted: true`
   - 매핑 불가 → `vetted: false` 유지 (auto_register Gate 1-2가 거부)
3. unmappable 목록 검토 → catalog v3.4 후보 신규 코드 식별 (별도 sprint)

### Day 3-4 — runtime 매핑 함수 (`hazard_normalizer.py`)

`normalize_hazards_array()` 신규 함수 (Plan에 명시):
```python
def normalize_hazards_array(hazards: list[dict]) -> dict:
    """GPT hazards[] → canonical (3축) + unknown_names"""
    canonical = {"accident_types": [], "hazardous_agents": [], "work_contexts": [],
                 "ppe_states": [], "environmental_factors": []}
    unknown_names = []
    for h in hazards:
        name = h.get("name", "")
        # Tier 1 (vetted alias) → Tier 2 (candidate) 순서로 시도
        for axis in ("accident_type", "hazardous_agent", "work_context",
                     "ppe_state", "environmental"):
            code = _resolve_alias_code(name, axis)
            if code:
                canonical[_axis_key(axis)].append(code)
                _log_alias_usage(name, axis, code)
                break
        else:
            unknown_names.append(h)
    return {"canonical": canonical, "unknown_names": unknown_names}
```

기존 `_resolve_alias_code()`, `_log_alias_usage()` 재사용 (T1.C 패턴).

### Day 5 — closed-loop 자동 등재 (auto_register_aliases.py 확장)

unknown_names 누적 시:
- Gate 1: embedding similarity ≥ 0.75 → candidate
- Gate 2: Sonnet LLM verify → vetted
- 50회 사용 또는 confidence ≥0.85 → promote_aliases.py로 vetted 승격

### Day 6-7 — 8 photo + 2360 synthetic 회귀 검증

- 8 photo `make f1-eval` → 매핑 정확도 AC-2 ≥85%
- 2360 synthetic replay → Gate 3 PASS

---

## Related

- [hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md) — Sprint plan 정본
- [hazard-direct-phase1-schema.md](hazard-direct-phase1-schema.md) — Phase 1 Day 1
- [F.1-auto-register-aliases.md](F.1-auto-register-aliases.md) — Gate 1-2 closed loop (재사용 대상)
- [moellab-vs-devserver-comparison.md](moellab-vs-devserver-comparison.md) — 37 hazards 원본 분포
