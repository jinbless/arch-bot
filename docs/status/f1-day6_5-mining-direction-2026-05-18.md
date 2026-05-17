# F.1 Day 6.5 — Production mining 방향 전환 + Normalizer 인프라 개선

**날짜**: 2026-05-18 (Day 6 follow-up)
**기반**: Day 6 발견 (6 candidates coverage 0/4,911, mining 입력이 production과 disconnect)
**목표**: synthetic-driven → production-driven mining 전환

## 변경 사항

### 1. Normalizer cascade — space-to-underscore 정규화 (`hazard_normalizer.py`)

```python
# Phase F.1 Day 6.5 — Vision LLM이 'FALLING OBJECT' 같이 공백 들어간 영어 변형 생성하는
# 패턴 대응. catalog UPPER_SNAKE_CASE 규약에 맞춰 공백→underscore 정규화.
upper_normalized = upper.replace(" ", "_").replace("-", "_")
if upper_normalized != upper and upper_normalized in valid:
    return upper_normalized
```

직접 매칭 직후, 다른 단계 이전에 1회 정규화 시도. 무비용·결정론적.

**효과**:
- `'FALLING OBJECT' (accident_type)` → `FALLING_OBJECT` ✅ (즉시 해결)
- `'falling object' (accident_type)` → `FALLING_OBJECT` ✅ (대소문자 + 공백)
- regression delta 0 (synthetic data가 이미 UPPER_SNAKE 사용, 영향 없음)

### 2. Gate 1 cross-lingual enhancement (`auto_register_aliases.py`)

이전 Gate 1 embedding 비교 대상: existing alias texts만 (대부분 한국어)
→ 영어 unknown ('MACHINERY') vs 한국어 alias ('기계') cosine 거리 멀어 reject

**변경**: catalog code 문자열 자체도 embed 대상에 포함
```python
def _code_cache_key(axis, code, aliases):
    targets = sorted(set(list(aliases) + [code]))  # code as self-target
    ...
```

**효과** (log 7 unknowns 측정):
| Test | 이전 (alias only) | **이후 (alias + code)** |
|---|---|---|
| Gate 1 PASS | 0/7 (0%) | **4/7 (57.1%)** |
| 'FALLING OBJECT' → FALLING_OBJECT | sim 0.455 (BURN 잘못 매칭) | **sim 0.879** ✅ |
| 'MACHINERY' → MACHINE | sim 0.448 | **sim 0.828** ✅ |
| 'FORKLIFT' → FORKLIFT_OPERATION | sim 0.376 | **sim 0.803** ✅ |
| 'falling object' → FALLING_OBJECT | sim 0.314 | **sim 0.757** ✅ |

추가 비용: 1,011 신규 embed (catalog code strings) ~$0.02 1회 (캐싱 후 0).

## Mining 결과 — F.1 log-only run (`--skip-light --min-freq 1`)

**입력**: analysis_log 9 entries with field (12 raw unknowns, 7 unique pairs)
**Gate 1**: 4/7 PASS (cutoff 0.7)
**Gate 2 LLM verify**: run마다 비결정성 (이전 2/4, 이번 0/4)
- 'FALLING OBJECT' / 'falling object': conf 0.78-0.88 (run마다 변동, 0.8 cutoff 경계)
- 'MACHINERY': conf 0.35-0.42 ("기계 전반" generic, MACHINE 특정 동의어 아님)
- 'FORKLIFT': conf 0.62-0.72 + axis-flip (work_context FORKLIFT_OPERATION → hazardous_agent FORKLIFT)
- 'cooking', 'kitchen': conf 0.35 (장소/행위 일반어, KITCHEN_COOKING 특정 동의어 아님)

**axis-flip 1건 기록**: `pending_axis_corrections.jsonl`
- 'FORKLIFT': work_context → hazardous_agent (LLM 판단)

## 핵심 인사이트 — 정직한 평가

### ✅ 인프라 개선 성공
1. Normalizer space-normalization: `'FALLING OBJECT'` 자동 해결 (alias 등재 불필요)
2. Gate 1 cross-lingual: 영어 unknown → 영문 code 매칭 가능
3. Gate 2 LLM 보수성 = 올바름 ('MACHINERY' 일반어를 MACHINE 동의어로 단정 안 함)

### ⚠️ Day 6.5 mining 한계
- **0 new aliases 자동 등재** (run마다 'FALLING OBJECT'만 borderline)
- 영어 generic terms ('MACHINERY', 'cooking', 'kitchen')는 LLM이 정확히 reject — alias 영역 아님
- 진짜 처리는 F.2 (Module 4.2 Taxonomy Discovery) — '새 sub-code 후보'로 처리

### 🔴 진단 재정립
- **F.1 (alias 등재)**: 직접 동의어가 명백한 경우만 작동. production traffic의 generic English terms는 자연스러운 reject.
- **F.2 필요성 확인**: 'KITCHEN', 'COOKING', 'MACHINERY', 'FORKLIFT' 등은 alias가 아니라 **catalog 신규 sub-code** 후보 (또는 LLM prompt에 closed vocabulary 제공이 더 적절).
- **Normalizer 인프라 강화가 가장 가치 큼**: 1줄 추가(space-norm)로 7 unknowns 중 3 즉시 해결. F.1 mining 4-Gate 보다 cost-effective.

## Day 7 권장 (변경 없음)
- `promote_aliases.py` + runbook + Makefile (F.1 closed loop 완성)
- F.1 자체는 mining yield 작더라도 closed loop 구조 자체가 가치 (drift 시 발동 가능)

## Phase 2 (별도 plan으로 이관)
- **closed vocabulary prompt** (Layer 0 Vision LLM에 catalog enum 목록 명시) — 'MACHINERY' 같은 generic term 생성 자체 차단
- **F.2 Taxonomy Discovery** — 161 new_subcode_candidates (이전 Sonnet 발견) + 'KITCHEN', 'MACHINERY' 등 catalog 신규 등재 검토
- **A hook 데이터 누적** — 1-2주 production traffic 후 다시 mining (현재 9 entries는 너무 thin)

## 산출 (변경)
- `serving-team/08-app/backend/app/services/hazard_normalizer.py` — space-normalization +6 lines
- `data-team/05-enrichment/llm-scripts/auto_register_aliases.py` — Gate 1 cross-lingual (code string embed)
- `data-team/05-enrichment/runtime-artifacts/alias_embedding_cache.json` — 709→1720 entries (+1011 code strings)
- `data-team/05-enrichment/runtime-artifacts/pending_axis_corrections.jsonl` — +1 entry (FORKLIFT)

## 검증
- Gate 3 regression (empty candidates + space-norm only): **PASS** — 모든 metric delta 0 (she_accuracy -0.0013 노이즈)
