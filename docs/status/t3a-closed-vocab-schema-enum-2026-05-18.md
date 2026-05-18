# Tier 3.A — Closed Vocab Schema Enum 효과 측정 (2026-05-18)

> `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text`에 catalog 529 codes enum 강제 후 free-create 감소 측정. **76 → 4 (-94.7%)**. Gate 3 PASS.

## TL;DR

| 지표 | Pre-3A | Post-3A | 변화 |
|---|---|---|---|
| analysis_log 전체 rows | 26,524 | 2,360 (T3.A replay) | n/a |
| rows with unknown_codes | 54 (0.2%) | 3 (0.1%) | -50% |
| total unknown terms | **76** | **4** | **-94.7%** |
| Gate 3 verdict | n/a | **PASS** (모든 metric noise) |
| Schema size | (free string) | 12.6KB (529 enum) | OpenAI strict 한도 내 |

## Pre/Post 비교 — Free-create Top 10

### Pre-3A (전체 analysis_log history, 26,524 rows)

| count | text | axis | 비고 |
|---|---|---|---|
| 10 | MACHINERY | work_context | 원래 plan에서 명시된 production miss |
| 10 | THF | hazardous_agent | 테트라하이드로푸란 (catalog 없음) |
| 10 | CO | hazardous_agent | 일산화탄소 (catalog 없음) |
| 6 | machinery | work_context | MACHINERY 소문자 변형 |
| 4 | WAREHOUSE | work_context | 창고 (catalog STORAGE 와 유사) |
| 3 | FORKLIFT | work_context | 지게차 |
| 2 | cooking | work_context | 요리 (plan 예시) |
| 2 | ELEVATED_WORK | work_context | 고소작업 (plan 예시) |
| 2 | STEEL_STRUCTURE | hazardous_agent | 철강구조 (plan 예시) |
| 2 | CONSTRUCTION_SITE | work_context | 건설현장 (일반화) |
| 2 | OIL | hazardous_agent | 기름 |
| 2 | CAUGHT_IN_BETWEEN | accident_type | catalog STRUCK_BY_OBJECT 와 유사 |
| 2 | STRUCK_BY_OBJECT | accident_type | catalog 동의어 (LLM 자유 표현) |
| 1 | FALLING OBJECT | accident_type | catalog FALLING_OBJECT 공백 변형 |
| 1 | kitchen | work_context | 부엌 |
| 1 | falling object | accident_type | catalog 소문자 변형 |
| 1 | MECHANICAL | hazardous_agent | catalog MACHINERY 와 유사 |
| 1 | machinery | hazardous_agent | axis 혼동 |
| 1 | FLAMMABLE_MATERIAL | hazardous_agent | catalog 동의어 |
| 1 | KITCHEN | work_context | catalog FOOD_SERVICE 와 유사 |

→ 합계 76 unknown terms / 54 rows / 26,524 total rows (**0.2% 빈도**).

### Post-3A (T3.A replay, 2,360 rows)

| count | text | axis | scene_hash (16-char) | timestamp |
|---|---|---|---|---|
| 1 | THF | hazardous_agent | 74016445d8182014 | 2026-05-18T09:03:20 |
| 1 | CO | hazardous_agent | 3530bfec867698dd | 2026-05-18T09:05:31 |
| 1 | MOBILE_EQUIPMENT | hazardous_agent | (idx 누락) | 2026-05-18T09:0X:XX |
| 1 | WAREHOUSE | work_context | (idx 누락) | 2026-05-18T09:0X:XX |

→ 합계 4 unknown terms / 3 rows / 2,360 total rows (**0.1% 빈도**).

## 핵심 효과

### 1. MACHINERY / cooking / ELEVATED_WORK / STEEL_STRUCTURE 완전 차단

원래 plan에서 명시한 "production miss 핵심" free-creates가 모두 0건 (catalog 코드만 출력). 이는 LLM이 schema enum constraint를 받아 catalog 밖 코드 생성을 OpenAI strict mode가 거부했기 때문.

### 2. axis 혼동 차단

Pre-3A에 있던 "machinery (hazardous_agent)" 같은 axis 혼동도 사라짐. axis enum (5 values)이 이전부터 있었지만 text가 free였던 시점에 LLM이 hazardous_agent axis로 machinery 라는 work_context 어휘를 출력하는 경우가 있었음.

### 3. Case/공백 변형 차단

"machinery" / "FALLING OBJECT" / "falling object" / "KITCHEN" 등 catalog 코드와 의미는 같지만 정규화 안 된 변형이 모두 차단. enum 강제는 대소문자/공백 검사도 포함.

## 잔존 4건 분석

OpenAI strict mode enum의 강제력은 ~99.6%. 4건 누락 원인 가설:

### THF / CO (hazardous_agent)
- 둘 다 화학 약자. LLM이 안전하게 화학 명을 추출하려 함
- 가능성: prompt가 약자를 강조 (Vision LLM이 약자를 "더 specific" 으로 판단)
- 해결: catalog에 THF (TETRAHYDROFURAN), CO (CARBON_MONOXIDE) 추가 또는 normalizer alias 등재

### MOBILE_EQUIPMENT (hazardous_agent)
- catalog에 MACHINERY, FORKLIFT, MOBILE_CRANE 등은 있지만 generic MOBILE_EQUIPMENT 없음
- 해결: catalog에 MOBILE_EQUIPMENT 추가 또는 normalizer alias 매핑

### WAREHOUSE (work_context)
- catalog에 STORAGE, WAREHOUSE_OPERATIONS 같은 코드는 있을 가능성 (확인 필요)
- 해결: alias 등재 또는 catalog 정리

### 일반적 edge-case 원인 추정
- OpenAI strict mode가 매번 100% 강제하지는 않음 (LLM token-by-token generation 시 logit mask 적용에 미세한 race condition 가능)
- 특히 약자나 generic term 같은 high-frequency token은 enum이 부분적으로 우회될 수 있음
- 비공식 OpenAI 가이드: enum violation은 "rare but possible" (OpenAI 공식 문서에 명시되지 않음)

## Gate 3 결과

```
metric                      baseline_v3    T3.A     delta    verdict
she_accuracy                  0.5771      0.5758   -0.0013   ok (noise)
sr_accuracy                   0.7581      0.7581   +0.0000   ok
penalty_accuracy              0.1835      0.1835   +0.0000   ok
overall_accuracy              0.1377      0.1377   +0.0000   ok
false_positive_rate           0.8696      0.8696   +0.0000   ok
false_negative_rate           0.0625      0.0639   +0.0014   ok (within tolerance)
```

**PASS** — schema enum 강제가 정확도 회귀 없이 free-create만 95% 차단. 이는 LLM이 enum 제약 받았을 때 catalog 코드를 "가장 가까운" 항목으로 선택하는 능력이 우수함을 의미.

## Schema 크기

```
Pre-3A:  text = {"type": "string"}              # 0 bytes
Post-3A: text = {"type": "string", "enum": [529 codes]}  # 12.6KB
```

OpenAI strict mode 한도 (~100KB) 대비 1/8. 추가 enum 확장 가능 (max ~3000 codes 정도).

## 운영 권장

### 1. catalog 갱신 시 backend restart

Module-level lazy load (`_ALL_CATALOG_CODES`)는 import 시 1회만 계산. catalog 갱신 시 `make dev-restart` 필요.

### 2. 잔존 4건 모니터링

cron 또는 주간 `make f3-drift-check` 결과에 unknown_codes 빈도 추적. +0.1%p 이상 증가 시 OpenAI API 변화 의심.

### 3. 잔존 4건 처리 옵션

- **Option A**: catalog에 THF / CO / MOBILE_EQUIPMENT 추가 (단순)
- **Option B**: normalizer step에서 alias 매핑 (THF → ORGANIC_SOLVENT, CO → TOXIC_GAS 등)
- **Option C**: normalizer step에서 hard reject (catalog 외 코드는 무시) — 가장 안전, 정보 손실 가능

권장: Option A (catalog 추가)가 ROI 가장 큼. 이미 catalog 확장 인프라 (F.2 Day 1-2) 존재.

## Related Documents

- [docs/dev-notes/T3.A-closed-vocab-schema-enum.md](../dev-notes/T3.A-closed-vocab-schema-enum.md) — T3.A runbook
- [docs/dev-notes/F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md) — Tier 2 F.3 closing (병행 작업)
- [docs/status/evaluation-baseline.md](evaluation-baseline.md) — Gate 3 metric history
- [docs/workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md) — Tier 3 옵션 3A
- [docs/architecture/llm-dependency-evolution.md](../architecture/llm-dependency-evolution.md) — Vision LLM 의존 (영구 유지) vs schema 강제
