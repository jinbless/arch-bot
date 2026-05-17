# Phase F.1 — Normalizer Alias Auto-Registration (Operator Runbook)

> Layer 4 Module 4.1. Automated alias registration to Normalizer (Layer 1) with 4-Gate trust validation.
> **Status**: Day 1-7 완료 (2026-05-18). 6 aliases mined, 5 promoted to vetted, 1 candidate.

## TL;DR — Quick Start

```bash
# 1. Mining (synthetic + log)
make f1-mine                              # dry-run, see what would be processed
make f1-mine-gate2                        # with LLM verify (~$0.05)
make f1-mine ARGS='--apply --gate2'       # apply candidates to file

# 2. Promotion (candidate → vetted main)
make f1-status                            # list current candidates
make f1-promote                           # dry-run (auto: uses >= 5)
make f1-promote ARGS='--apply --by-confidence --min-conf 0.85'

# 3. Verification (always before/after changes)
make f1-regression                        # 2,360 replay + Gate 3 (~5 min)
make f1-eval                              # 8 photo eval ON/OFF (~$0.40 + 8 min)
```

## Architecture — 4-Gate Pipeline

```
INPUT
├── f1_light_proposals.json (synthetic LLM 제안, 1,235개)
│   └── recover_catalog_mismatch.py로 catalog 매핑 보강 (Stage 1-3)
└── analysis_log.jsonl[normalizer_unknown_codes] (A hook, production miss)

         │
         ▼
   ┌─────────────────────────────────┐
   │ Gate 1: Embedding similarity    │
   │   text-embedding-3-small        │
   │   cosine ≥ 0.7 vs               │
   │     existing aliases + code str │ ← Day 6.5 cross-lingual
   └─────────────────────────────────┘
         │
         ▼
   ┌─────────────────────────────────┐
   │ Gate 2: LLM verify              │
   │   gpt-5.4-nano (Korean prompt)  │
   │   is_alias + correct_axis       │
   │   confidence ≥ 0.8 (default)    │
   │   axis-flip → pending_*.jsonl   │
   └─────────────────────────────────┘
         │
         ▼
   ┌─────────────────────────────────┐
   │ Gate 4: Atomic write (candidate)│
   │   risk_feature_aliases_         │
   │     candidates.json (tier1)     │
   │   meta + audit jsonl sidecars   │
   └─────────────────────────────────┘
         │
         ▼  (Normalizer cascade step 4.5 active)
   ┌─────────────────────────────────┐
   │ Gate 3: Regression hard-stop    │
   │   replay_synthetic + replay_    │
   │     baseline_v3.json            │
   │   delta ≤ 0.02 (tolerance)      │
   │   Openllet OWL DL + SHACL       │
   │     + 2,192 disjoint axioms     │
   └─────────────────────────────────┘
         │
         ▼
   PROMOTE (manual / auto-by-confidence)
         │
         ▼
   risk_feature_aliases.json (main, vetted)
```

## File Layout

| Path | Purpose |
|---|---|
| `data-team/05-enrichment/llm-scripts/auto_register_aliases.py` | Main mining script (Day 1-5) |
| `data-team/05-enrichment/llm-scripts/promote_aliases.py` | candidate→vetted promotion (Day 7) |
| `data-team/05-enrichment/llm-scripts/recover_catalog_mismatch.py` | 3-stage hybrid (Rule + Embed + Sonnet) |
| `serving-team/08-app/backend/app/data/risk_feature_aliases.json` | Main (vetted) aliases |
| `serving-team/08-app/backend/app/data/risk_feature_aliases_candidates.json` | Candidate aliases (level=candidate) |
| `serving-team/08-app/backend/app/services/hazard_normalizer.py` | Layer 1 Normalizer (cascade step 4.5 통합) |
| `runtime-artifacts/alias_candidate_meta.jsonl` | Per-alias: uses, last_used_at, gate2_conf |
| `runtime-artifacts/alias_audit.jsonl` | All gate decisions (accept/reject 전체 trail) |
| `runtime-artifacts/alias_embedding_cache.json` | Gate 1 cache (text-embedding-3-small) |
| `runtime-artifacts/pending_axis_corrections.jsonl` | R3 axis-flip requeue |
| `runtime-artifacts/f1_light_proposals.json` | F.1-light 산출 (1,235 LLM 제안) |
| `runtime-artifacts/f1_light_proposals_recovered.json` | recovery 후 (auto_register drop-in) |
| `runtime-artifacts/new_subcode_candidates.jsonl` | F.2 forward (catalog 신규 등재 후보) |

## Operator Cadence

### Daily / On-Demand
- `make f1-status` — 현재 candidate 현황
- `make f1-regression` — 환경 변경 후 회귀 확인

### Weekly
- `make f1-mine-log ARGS='--apply'` — production traffic mining (analysis_log 누적분)
- `make f1-promote ARGS='--apply --auto'` — uses 기반 자동 승격

### On New Mining Batch
1. `make f1-mine` — dry-run, expected candidate 수 확인
2. `make f1-mine-gate2` — LLM verify 후 expected PASS 확인
3. `make f1-mine ARGS='--apply --gate2'` — candidate file write
4. `make f1-regression` — Gate 3 (필수, 새 alias 추가 후)
5. PASS 시: 운영 traffic으로 uses 누적 후 promote
6. FAIL 시: `rm risk_feature_aliases_candidates.json` (rollback)

### On Catalog Recovery (1회성, F.2 영역 진입 전)
1. `make f1-recover ARGS='--skip-sonnet'` — Rule + Embedding (~$0.02)
2. `make f1-recover` — full 3-stage (Sonnet 4.6, ~$5)
3. 검토: `runtime-artifacts/new_subcode_candidates.jsonl` (F.2 forward)
4. catalog patch는 별도 plan (Phase 2)

## Rollback

### Candidate file 전체 폐기
```bash
mv serving-team/08-app/backend/app/data/risk_feature_aliases_candidates.json \
   serving-team/08-app/backend/app/data/risk_feature_aliases_candidates.json.bak
# Normalizer step 4.5 no-op (R2 invariant)
make f1-regression  # delta 0 확인
```

### Specific code rollback (vetted → candidate)
```bash
make f1-promote ARGS='--apply --rollback FALL_FROM_HEIGHT FINGER_AMPUTATION'
make f1-regression
```

### Normalizer step 4.5 비활성화 (긴급)
`hazard_normalizer.py`의 step 4.5 블록을 주석 처리 (R2: 빈 candidates 시 자동 no-op 이므로 거의 불필요).

## Acceptance Criteria (per batch)

### Gate 3 hard-stop
- `make f1-regression` PASS (delta ≤ 0.02 vs replay_baseline_v3.json)
- empty-candidates case: delta = 0 (R2 invariant)

### Manual verification
- 5건 random spot-check: alias ↔ enum 의미 일치
- `alias_audit.jsonl` 1 row/candidate (4-Gate 결과 모두)
- Backend startup log: candidates file load 정상

### 8 real-test-photo (선택)
- `make f1-eval` — normalizer_miss_rate 측정 (목표: 등재 alias가 실제 production 어휘와 overlap 시 개선)
- Day 6 발견: 6 specific 한국어 candidates는 영어 production 어휘와 거의 overlap 없음 → coverage-aware mining 필요

## Known Limitations

| 항목 | 영향 | 대응 |
|---|---|---|
| A hook early-return | `LLM_RERANK_MODE=off` 또는 `knowledge.guide_rows` 빈 경우 hook 미발동 | 별도 항상-실행 hook (follow-up) |
| LLM 비결정성 | Gate 2 run마다 PASS 수 0~6 변동 (gpt-5.4-nano) | 다중 run 평균 or multi-LLM ensemble (F.3.5) |
| `uses` 추적 미구현 | Normalizer step 4.5 match 시 meta.uses 자동 증가 없음 | --by-confidence 모드 사용 또는 후속 (`scan-usage` 기능) |
| Cross-lingual cutoff | Korean alias ↔ English code embedding similarity 한계 | Day 6.5 cross-lingual 추가 (code 자체 embed), 'kitchen'/'cooking' 등 generic term은 여전히 한계 |
| Synthetic-driven mining | Day 6 coverage 0/4,911 발견 | mining 입력을 production analysis_log로 전환 (`--skip-light --min-freq 1`) |

## Cost & Time Estimates

| Operation | Cost | Time |
|---|---|---|
| `f1-mine` dry-run | 0 | ~3s |
| `f1-mine-gate2` (75 candidates) | ~$0.05 | ~30s |
| `f1-recover --skip-sonnet` | ~$0.02 | ~30s |
| `f1-recover` (full Sonnet 4.6) | ~$3-5 | ~3-5 min |
| `f1-regression` (2,360 replay) | 0 | ~5 min |
| `f1-eval` (16 Vision LLM calls) | ~$0.40 | ~8 min |
| `f1-promote --apply` | 0 | <1s |

## Day 1-7 Sprint Summary (2026-05-17 ~ 18)

| Day | 작업 | 산출 |
|---|---|---|
| Day 1 | Scaffold | `auto_register_aliases.py` 367 lines |
| Day 2 | Dedup + log 집계 + catalog validation | candidate pipeline + 944 mismatch 자동 reject |
| Day 3 | Gate 1 embedding (text-embedding-3-small) | per-code sha256 cache (R1) |
| Day 4 | Gate 2 LLM verify + axis disambiguation | gpt-5.4-nano + `pending_axis_corrections.jsonl` (R3) |
| 후속 | `recover_catalog_mismatch.py` (3-stage hybrid) | 215/378 recovered + 161 new_subcode (F.2 forward) |
| 후속 | catalog v3.1 patch (+94 main codes) | 310 → 404 codes |
| Day 5 | normalizer step 4.5 + Gate 4 atomic write + Gate 3 PASS | 6 candidates 등재 |
| Day 6 | 8-photo eval + coverage 측정 | 1/8 improved + critical insight |
| Day 6.5 | Normalizer space-norm + Gate 1 cross-lingual | infra 강화, 0 new alias |
| Day 7 | `promote_aliases.py` + Makefile + runbook | 5/6 vetted 승격 |

## Related Documents
- [docs/workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md) — F.1 plan
- [docs/architecture/ontology-learning-layer.md](../architecture/ontology-learning-layer.md) — Module 4.1
- [docs/status/f1-day6-real-photo-eval-2026-05-18.md](../status/f1-day6-real-photo-eval-2026-05-18.md) — Day 6 정직한 평가
- [docs/status/f1-day6_5-mining-direction-2026-05-18.md](../status/f1-day6_5-mining-direction-2026-05-18.md) — Day 6.5 진단

## Future Work (별도 plan)
- **F.2 (Module 4.2 Taxonomy Discovery)**: catalog v3.1 + 161 new subcodes + ppe_state/environmental axis
- **Closed vocabulary prompt (Layer 0)**: Vision LLM에 catalog enum 목록 명시 → 'MACHINERY' 같은 generic term 생성 자체 차단
- **F.3.5 Drift detection cron**: F.1 + F.2 + F.3 모두 통합 자동 학습 loop
- **Usage tracking 자동화**: Normalizer step 4.5 match 시 meta.uses 자동 증가
- **alias_embedding_cache.json LFS**: 현재 50.92MB (GitHub 권장 50MB 초과), Git LFS or gzip
