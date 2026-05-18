# Phase F.2 — Taxonomy Discovery (Module 4.2 Operator Runbook)

> Layer 4 Module 4.2. Catalog axis 신설 + new code 등재 + SHE pattern 5-dim 채우기 + v3.1 기술 부채 해소.
> **Status**: F.2 Day 1-7 완료 (2026-05-18). catalog v3.1 → v3.3 (5 axes × 481 codes), 790 SHE enriched, 79 pending review.

## TL;DR — Quick Start

```bash
# Catalog patches (1회성)
make f2-patch-v32                                          # +25 codes + 2 axes (ppe_state, environmental)
make f2-patch-v33                                          # +52 codes (matcher hardcoded + synthetic frequent)

# SHE enrichment (Sonnet 4.6)
make f2-enrich-sonnet ARGS='--dry-run'                     # cost preview (~$6, 1,205 SHE)
make f2-enrich-sonnet ARGS='--apply'                       # 790 SHE OTHER → specific

# v3.1 code SHE linking (status='pending_review')
make f2-link-v31 ARGS='--dry-run'                          # 94 v3.1 codes preview
make f2-link-v31 ARGS='--apply'                            # 77 SHE pending_review

# Verification (필수)
make f1-regression                                          # 2,360 replay + Gate 3
make f1-eval                                                # 8-photo (~$0.40, 8min)
```

## Architecture

```
catalog v3.0 (404 codes, 3 axes)
   │
   ▼
 [Day 1] patch_catalog_v3_2.py
   - axes 신설: ppe_state (보호구 상태), environmental (환경 조건)
   - 161 후보 재검토 (conf ≥ 0.7)
   - +25 codes (v3.1 deferred + 신규)
   │
   ▼
 catalog v3.2 (429 codes, 5 axes)
   │
   ▼
 [Day 2] patch_catalog_v3_3.py
   - Source 1: she_matcher.py hardcoded 24 codes
   - Source 2: synthetic frequent (UPPER_SNAKE, freq >= 3)
   - +52 codes (HELMET_MISSING, WET_SURFACE, HIGH_ELEVATION, …)
   │
   ▼
 catalog v3.3 (481 codes, 5 axes)
   │
   ├─ [Day 3-4] enrich_she_with_sonnet.py
   │    - 1,207 SHE rows with OTHER (ppe_state OR environmental)
   │    - Sonnet 4.6 enum-constrained tool_use
   │    - 790 applied (65.6%), confidence ≥ 0.85 + catalog vocab
   │    - PG she_catalog UPDATE (jsonb_set)
   │
   └─ [Day 5] link_v31_codes_to_she.py
        - 94 v3.1 origin codes (_source='f1_recovery_sonnet_4_6')
        - Sonnet 4.6 generates 8-axis SHE pattern
        - 79 accepted, status='pending_review' (matcher 제외)
        - Manual promotion 필요 (Day 7 promote_she_review.py 후속)

 [Day 6] 8-photo eval — Vision LLM stochasticity 한계, 회귀 없음 확인
 [Day 7] runbook + Makefile + 정리
```

## File Layout

| Path | Purpose |
|---|---|
| `data-team/05-enrichment/llm-scripts/patch_catalog_v3_2.py` | Day 1: ppe_state/environmental axis 신설 |
| `data-team/05-enrichment/llm-scripts/patch_catalog_v3_3.py` | Day 2: matcher hardcoded + synthetic frequent codes |
| `data-team/05-enrichment/llm-scripts/enrich_she_with_sonnet.py` | Day 3-4: 790 SHE OTHER 교체 (Sonnet 4.6) |
| `data-team/05-enrichment/llm-scripts/link_v31_codes_to_she.py` | Day 5: 79 new SHE for v3.1 codes (pending_review) |
| `data-team/05-enrichment/llm-scripts/_rollback_day5_she.py` | Day 5 emergency rollback (audit jsonl 기반) |
| `serving-team/08-app/backend/app/data/risk_feature_catalog.json` | catalog v3.3 (481 codes, 5 axes) |
| `serving-team/08-app/backend/app/data/risk_feature_catalog.v3.1.backup.json` | Day 1 rollback target |
| `serving-team/08-app/backend/app/data/risk_feature_catalog.v3.2.backup.json` | Day 2 rollback target |
| `runtime-artifacts/she_enrichment_audit.jsonl` | Day 3-4 audit (1,215 rows) |
| `runtime-artifacts/v31_codes_she_link_audit.jsonl` | Day 5 audit (79 accepted + rejections) |
| `docs/status/f2-sprint-day6-eval-2026-05-18.md` | Day 6 8-photo 결과 |

## Operator Cadence

### One-time (catalog patches)
- v3.2, v3.3는 1회성. 재실행 안 함 (이미 적용됨).
- 향후 catalog 확장: 새 v3_N.py 작성 (기존 패턴 재사용)

### Periodic (SHE enrichment)
- 새 SHE 추가 시 (Phase 3C 등): `make f2-enrich-sonnet ARGS='--apply'` 재실행
- 신규 OTHER SHE만 추가 처리 (자동 filter)

### On v3.1 codes 활용 needed
- 77 pending_review SHE를 신중하게 approved_auto로 승격:
  - 개별 manual 검토 권장 (Day 5 lesson)
  - 5-10건씩 small batch + Gate 3 검증
  - 별도 promote_she_review.py 작성 가능 (후속)

## Rollback

### Catalog v3.3 → v3.2
```bash
cp serving-team/08-app/backend/app/data/risk_feature_catalog.v3.2.backup.json \
   serving-team/08-app/backend/app/data/risk_feature_catalog.json
make f1-regression
```

### Catalog v3.2 → v3.1
```bash
cp serving-team/08-app/backend/app/data/risk_feature_catalog.v3.1.backup.json \
   serving-team/08-app/backend/app/data/risk_feature_catalog.json
make f1-regression
```

### Day 3-4 SHE enrichment rollback
- audit jsonl에 before/after 기록됨
- 별도 rollback script 필요 (jsonb_set 반대 방향 UPDATE)
- 또는 PG snapshot 복원

### Day 5 SHE pending_review rollback
```bash
# audit jsonl 기반 DELETE
.venv/bin/python data-team/05-enrichment/llm-scripts/_rollback_day5_she.py
make f1-regression
```

## Acceptance Criteria (per batch)

### Gate 3 hard-stop
- `make f1-regression` PASS (delta ≤ 0.02 vs replay_baseline_v3.json)
- 각 단계마다 검증 (Day 1/2/3-4/5 각각)

### Manual verification
- Day 1/2 catalog patch: changelog 메타 확인, 추가된 codes 목록 spot-check
- Day 3-4 SHE enrichment: 10건 random update spot-check (semantic OK)
- Day 5 SHE generation: visual_triggers 의미 검증

## Cost & Time Estimates

| Operation | Cost | Time |
|---|---|---|
| `f2-patch-v32` | 0 | <1s |
| `f2-patch-v33` | 0 | <1s |
| `f2-enrich-sonnet --dry-run` | 0 | ~3s |
| `f2-enrich-sonnet --apply` | ~$6 | ~6분 |
| `f2-link-v31 --apply` | ~$2 | ~2분 |
| `f1-regression` | 0 | ~5분 |
| `f1-eval` (8 photo) | ~$0.40 | ~8분 |
| **F.2 sprint total** | **~$8-10** | **~25분 (excluding eval)** |

## Day 1-7 Sprint Summary (2026-05-18)

| Day | 작업 | 결과 |
|---|---|---|
| Day 1 | catalog v3.1 → v3.2 patch | +25 codes, +2 axes (ppe_state, environmental) |
| Day 2 | catalog v3.2 → v3.3 patch | +52 codes (matcher hardcoded + synthetic frequent) |
| Day 3-4 | SHE OTHER → specific (Sonnet) | 790 / 1,205 applied (65.6%), Gate 3 PASS |
| Day 5 | v3.1 codes → SHE generation | 79 / 94 accepted, status=pending_review (lesson: approved_auto → -39.5%p) |
| Day 6 | 8-photo eval | 1/8 improved (stochasticity 한계), Gate 3 PASS 유지 |
| Day 7 | runbook + Makefile | 본 문서 |

### 진척 정리

| 메트릭 | 시작 | **F.2 종료** |
|---|---|---|
| Catalog codes | 404 (3 axes) | **481 (5 axes, +19%)** |
| SHE active patterns | 1,616 | 1,616 (변동 없음) |
| SHE 5-dim coverage (non-OTHER) | ~25% (409/1,616) | **~74% (~1,200/1,616)** |
| Pending review SHE | 0 | **77** (수동 승격 대기) |
| Gate 3 regression | PASS | **PASS 유지** |

## Known Limitations

| 항목 | 영향 | 대응 |
|---|---|---|
| 8-photo eval limited | F.2 인프라 효과는 production scale에서 측정 | 1-2주 traffic 누적 후 재평가 |
| 77 pending_review 미활용 | v3.1 코드 SHE referenced되지만 matcher에 없음 | promote_she_review.py 후속 (incremental) |
| LLM 비결정성 | Day 3-4 Sonnet 재실행 시 다른 결과 | confidence threshold 0.85 + spot-check 보강 |
| Catalog v3.3 일부 codes label 이상 | synthetic-derived label = `"Gloves Worn"` (auto Title-case) | 후속 수동 정리 (영문 label 정책 결정) |

## Related Documents
- [docs/dev-notes/F.1-auto-register-aliases.md](F.1-auto-register-aliases.md) — F.1 runbook (선행)
- [docs/status/f2-sprint-day6-eval-2026-05-18.md](../status/f2-sprint-day6-eval-2026-05-18.md) — Day 6 결과
- [docs/workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md) — 전체 roadmap
- [docs/architecture/ontology-learning-layer.md](../architecture/ontology-learning-layer.md) — Module 4.2

## Future Work (별도 plan)
- **promote_she_review.py** — 77 pending_review SHE를 신중하게 approved_auto로 승격 (5-10건씩, Gate 3 검증)
- **Catalog label cleanup** — synthetic-derived auto Title-case label을 정식 한국어 label로 정정
- **F.3 closing** — F.3.1 reasoner channel, F.3.4 KB compile, F.3.5 cron
- **Closed vocabulary prompt** (Layer 0) — Vision LLM에 catalog enum 목록 명시
