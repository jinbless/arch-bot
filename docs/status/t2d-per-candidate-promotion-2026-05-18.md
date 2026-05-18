# T2.D — F.3.2 8 Candidates 1-by-1 Vetted Promotion (2026-05-18)

> Tier 2 sprint T2.D. F.3.2 first batch에서 mining된 8 candidate axiom을 1-by-1로 vetted 승격하면서 Gate 3 regression으로 검증. **8/8 PASS** (예상 5-6 PASS 대비 100% 통과).

## Input

- KB 초기 상태: vetted_count = 0, candidate_count = 8 (source = `f32_axiom_miner`)
- 평가 corpus: 2,360 synthetic observations (v1~v10 EN transform 후)
- Baseline: `data-team/05-enrichment/runtime-artifacts/replay_baseline_v3.json`
- Tolerance: 0.02 (regression_gate.py default)

## Methodology

`promote_f32_per_candidate.py --apply`:

각 candidate 단독 promote → full replay → regression_gate → keep or rollback.

```
for each candidate (1..8):
  1. promote_one_in_memory (level: candidate → vetted) + save_kb
  2. run_replay (full 2,360 synthetic)
  3. run_regression vs baseline_v3 (tolerance 0.02)
  4. if pass: keep vetted, audit "per_candidate_promote_pass"
     else:    rollback level → candidate, audit "per_candidate_rollback_fail"
```

Asymmetric trust 반영 (vetted penalty -0.18, candidate -0.05 = 3.6x 강화). 예상은 5-6 PASS (높은 confidence 위주 통과, 낮은 confidence 회귀).

## Per-Candidate Results

| idx | domain_a | domain_b | conf | replay valid/total | Gate 3 | verdict |
|---|---|---|---|---|---|---|
| 1 | BUTCHER_MEAT_RETAIL | CONSTRUCTION | 0.86 | 2,360 / 2,360 | PASS | **vetted** |
| 2 | CONSTRUCTION | METAL_MACHINING | 0.86 | 2,360 / 2,360 | PASS | **vetted** |
| 3 | MANUFACTURING | ELECTRICAL_CONSTRUCTION | 0.72 | 2,360 / 2,360 | PASS | **vetted** |
| 4 | BUTCHER_MEAT_RETAIL | LANDSCAPING_GREENSPACE | 0.82 | 2,360 / 2,360 | PASS | **vetted** |
| 5 | GAS_PIPING_INSTALLATION | CHEMICAL_INDUSTRY | 0.84 | 2,360 / 2,360 | PASS | **vetted** |
| 6 | 편의점 | METAL_MACHINING | 0.78 | 2,360 / 2,360 | PASS | **vetted** |
| 7 | GAS_PIPING_INSTALLATION | CONSTRUCTION | 0.74 | 2,360 / 2,360 | PASS | **vetted** |
| 8 | FIRE_PROTECTION_INSTALLATION | CHEMICAL_INDUSTRY | 0.74 | 2,360 / 2,360 | PASS | **vetted** |

**최종 KB 상태**: vetted_count = 8, candidate_count = 0 (source = `f32_axiom_miner`). Total incompatibilities: 2,232 vetted + 8 = 2,240.

## Gate 3 Metric Snapshot (each iteration)

각 iteration 마지막 Gate 3 결과는 모두 동일 (모든 8 vetted 누적, baseline_v3 대비 delta noise 수준):

| metric | baseline_v3 | T2.D final (8 vetted) | delta | verdict |
|---|---|---|---|---|
| she_accuracy | 0.5771 | 0.5758 | -0.0013 | ok (noise) |
| sr_accuracy | 0.7581 | 0.7581 | 0.0000 | ok |
| penalty_accuracy | 0.1835 | 0.1835 | 0.0000 | ok |
| overall_accuracy | 0.1377 | 0.1377 | 0.0000 | ok |
| false_positive_rate | 0.8696 | 0.8696 | 0.0000 | ok |
| false_negative_rate | 0.0625 | 0.0639 | +0.0014 | ok (within tolerance) |

## Expected vs Actual

| 항목 | 예상 | 실제 |
|---|---|---|
| PASS 수 | 5-6 | **8** |
| FAIL 수 | 2-3 | 0 |
| ERRORS 수 | 0 | 0 |
| Total time | ~60-90분 | ~48분 (full replay 8회 × ~5-6분) |

**100% PASS = F.3.2 mining quality 매우 우수**. 가장 낮은 conf (0.72 = idx 3 MANUFACTURING × ELECTRICAL_CONSTRUCTION)도 통과. asymmetric trust penalty 3.6x 강화가 회귀를 일으키지 않는 axiom만 mining에서 통과한 것을 확인.

## Lessons Learned

### 1차 실행 cp949 unicode bug (Day 2)

`promote_f32_per_candidate.py`의 print statement가 Windows cp949 codec encoding 불가:

```python
# 문제: ✓ ✗ → — (U+2713 / U+2717 / U+2192 / U+2014)
print(f"  ✓ Gate 3 PASS — keep as vetted")
# UnicodeEncodeError: 'cp949' codec can't encode character '✗'
```

**증상**:
- 1차 실행 시 idx 0 (BUTCHER × CONSTRUCTION) replay 후 print 단계에서 exception
- defensive rollback handler가 다시 같은 unicode print를 시도 → 무한 fail loop
- idx 1 (CONSTRUCTION × METAL) 가 vetted state로 stuck (rollback 미수행)

**수정**:
1. 모든 unicode chars → ASCII: `✓` → `[PASS]`, `✗` → `[FAIL]`, `→` → `->`, `—` → `--`
2. 환경: `PYTHONIOENCODING=utf-8 python -u` (unbuffered stdout)
3. Stuck axiom 수동 rollback (CONSTRUCTION × METAL → candidate 복귀)
4. 클린 재실행 → 8/8 PASS

**Future 가이드**: 모든 Windows-cross-platform 스크립트는 ASCII-only print + PYTHONIOENCODING=utf-8 권장. 또는 cp949-safe 문자 (한글은 cp949 호환).

### Vetted penalty 3.6x 강화가 통과를 막지 않은 이유

asymmetric trust 본래 설계 (vetted -0.18, candidate -0.05)는 vetted state에서 회귀를 빠르게 catch하기 위함. 그러나 F.3.2 mining 자체가 4-Gate (embedding + LLM verify + regression + asymmetric trust)를 통과한 axiom만 candidate로 등록 → vetted 승격 후에도 회귀 거의 없음.

= **mining quality > penalty tightening**. 후속 batch에서도 동일 패턴 예상.

## Audit Trail

```bash
# audit log
cat data-team/05-enrichment/runtime-artifacts/incompatibility_audit.jsonl \
  | grep "per_candidate" | head -20

# summary
cat data-team/05-enrichment/runtime-artifacts/f32_per_candidate_promotion_results.json \
  | python -m json.tool | head -40
```

## Related Documents

- [docs/dev-notes/F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md) — T2.D 통합 runbook
- [docs/status/f33-gate3-regression-2026-05-17.md](f33-gate3-regression-2026-05-17.md) — 이전 F.3.3 Gate 3 (candidate state)
- [docs/status/evaluation-baseline.md](evaluation-baseline.md) — Gate 3 history
- [docs/workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md) — Tier 2 T2.D entry
