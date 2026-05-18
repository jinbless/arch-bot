# Phase F.3 — Axiom Discovery (Module 4.4 Operator Runbook)

> Layer 4 Module 4.4. F.3.2 candidate axiom mining → F.3.3 Gate 3 → T2.A pyshacl shadow → T2.B compile to TTL + Fuseki reload → T2.C drift monitor → T2.D vetted promotion (1-by-1).
> **Status**: Tier 2 F.3 closing 완료 (2026-05-18). **Layer 4.4 자율 학습 closed loop 완성**.

## TL;DR — Quick Start

```bash
# T2.A — Reasoner shadow channel (offline batch, 약 30초)
make f3-shadow-validator
make f3-shadow-validator ARGS='--pyshacl --limit 50'   # pyshacl cross-check

# T2.D — F.3.2 candidate vetted 1-by-1 promote (각 ~6분 replay)
make f3-promote-candidates                              # dry-run
make f3-promote-candidates ARGS='--apply'               # 실제 promote + Gate 3

# T2.B — KB compile to SHACL TTL (수초)
make f3-compile-kb                                      # candidate → kb-candidates.ttl
make f3-compile-kb ARGS='--scope vetted'                # vetted scope 검증

# T2.C — Drift detection (수초)
make f3-drift-check                                     # 가장 최근 replay 비교
make f3-drift-check ARGS='--json'                       # CI/slack 통합

# Weekly cron-able (LLM 비용 0)
make f3-weekly-cycle                                    # shadow → compile → replay → drift
```

## Architecture

```
[F.3.0/3.2/3.3] mining → verify (이전 sprint)
   │
   ▼
 KB JSON (guide_domain_incompatibilities.json)
   │
   ├─ [T2.A] pyshacl_shadow_validator.py + shadow_reasoner.py
   │     - offline: analysis_log → shadow_reasoner_log.jsonl
   │     - runtime: analysis_pipeline._append_analysis_log[reasoner_rejects]
   │     - 효과: 어떤 candidate guide가 axiom 위반이었을지 log (실제 reject 안 함)
   │
   ├─ [T2.D] promote_f32_per_candidate.py (1-by-1)
   │     - 각 candidate promote → full replay → Gate 3 → keep or rollback
   │     - 8/8 PASS (2026-05-18, 예상 5-6 대비 100%)
   │
   ├─ [T2.B] compile_kb_to_ttl.py → kb-candidates.ttl
   │     - 2,192 SHACL NodeShape (severity sh:Info)
   │     - KoshaFusekiServer.java sources에 추가 → docker rebuild → container recreate
   │     - SPARQL 검증: SELECT COUNT(?s) WHERE { ?s a sh:NodeShape } → 2,216
   │
   └─ [T2.C] f3_drift_check.py + f3-weekly-cycle Makefile
         - 주간 baseline_v3 vs current replay 비교
         - 6 metric 추적, false_negative_rate +2%p 시 critical (exit 2)
         - f3_drift_log.jsonl 시계열 보존
```

## File Layout

| Path | Purpose |
|---|---|
| `data-team/05-enrichment/llm-scripts/pyshacl_shadow_validator.py` | T2.A offline batch CLI (direct lookup + pyshacl cross-check) |
| `data-team/05-enrichment/llm-scripts/compile_kb_to_ttl.py` | T2.B candidate → kb-candidates.ttl |
| `data-team/05-enrichment/llm-scripts/f3_drift_check.py` | T2.C 6 metric drift 모니터 |
| `data-team/05-enrichment/llm-scripts/promote_f32_per_candidate.py` | T2.D 1-by-1 promote + Gate 3 wrap |
| `serving-team/08-app/backend/app/services/shadow_reasoner.py` | T2.A serving runtime (lazy module cache) |
| `serving-team/08-app/backend/app/services/analysis_pipeline.py` | T2.A integration (`reasoner_rejects` kwarg) |
| `ontology-team/06-reasoning/ontology/kb-candidates.ttl` | T2.B 산출 (2,192 SHACL shapes, sh:Info) |
| `ontology-team/06-reasoning/ontology/docker/fuseki/.../KoshaFusekiServer.java` | T2.B Java sources array에 kb-candidates 추가 |
| `runtime-artifacts/shadow_reasoner_log.jsonl` | T2.A offline batch 산출 (2,580 rows → 859 reasoner_rejects) |
| `runtime-artifacts/f32_per_candidate_promotion_results.json` | T2.D 8/8 PASS summary |
| `runtime-artifacts/f3_drift_log.jsonl` | T2.C 시계열 (cron weekly append) |
| `runtime-artifacts/kb_candidates_compile_audit.json` | T2.B compile audit |

## Day 1-5 Sprint Summary (2026-05-18 저녁)

| Day | 작업 | 결과 |
|---|---|---|
| Day 1 | T2.A offline `pyshacl_shadow_validator.py` + serving `shadow_reasoner.py` + analysis_pipeline 통합 | 2,580 rows → 859 reasoner_rejects (62.8%), Gate 3 PASS, commit `93c49fe` |
| Day 2 | T2.D `promote_f32_per_candidate.py` 작성 + dry-run + 1차 실행 unicode bug → ASCII 수정 | cp949 ✓✗→— → ASCII [PASS]/[FAIL]/->/-- + PYTHONIOENCODING=utf-8 |
| Day 3 | T2.D 재실행 + 8/8 PASS verification | 예상 5-6 대비 100% (8 vetted), commit `ac98d4c` |
| Day 4 | T2.B `compile_kb_to_ttl.py` + KoshaFusekiServer.java edit + docker rebuild | docker-fuseki:latest sha256 `08837972`, commit `78886b3` + `ac98d4c` |
| Day 5 | T2.B Fuseki container recreate + SPARQL 검증 | `docker compose up -d --force-recreate fuseki` + `SELECT COUNT(?s)` → 2,216 NodeShapes (kb-candidates 2,192 + serving 24). 적용 완료. |

**Tier 2 종합** (commit chain `93c49fe` → `78886b3` → `ac98d4c` → main `325ad37`):
- Layer 4 Module 4.4 closed loop 완성
- T2.A reasoner_rejects field가 analysis_log에 누적 (shadow channel)
- T2.D 8/8 vetted (axiom mining quality 검증)
- T2.B Fuseki에 kb-candidates.ttl 적용 (SPARQL 응답)
- T2.C 주간 drift 모니터 cron-able

## Operator Cadence

### Periodic (T2.C drift detection)
- 매주 `make f3-weekly-cycle` (shadow → compile → replay → drift)
- cron: `0 2 * * 0 cd /path/to/arch-bot && make f3-weekly-cycle`
- false_negative_rate +2%p 초과 시 critical (exit 2)

### On new F.3.2 mining (수동)
- F.3.0 → F.3.2 batch → F.3.3 Gate 3 verification (이전 sprint 패턴)
- 신규 candidate가 추가되면 `make f3-promote-candidates ARGS='--apply'` 로 1-by-1 vetted 승격
- 8/8 PASS 후 자동으로 다음 cycle entry pool 확장

### Fuseki TTL 갱신 (수시)
1. `make f3-compile-kb` 으로 kb-candidates.ttl 재compile
2. (필요 시) `KoshaFusekiServer.java` sources array에 신규 TTL 추가
3. `cd ontology-team/06-reasoning/ontology/docker && docker compose build fuseki`
4. `docker compose up -d --force-recreate fuseki`
5. SPARQL 검증: `curl -G --data-urlencode "query=..." http://localhost:3030/kosha/sparql`

## Rollback

### kb-candidates.ttl 제거 (T2.B 되돌리기)
```bash
# Java sources에서 줄 제거
# KoshaFusekiServer.java line 50 {"/kb-candidates.ttl", ...} 제거
cd ontology-team/06-reasoning/ontology/docker
docker compose build fuseki
docker compose up -d --force-recreate fuseki
```

### T2.D vetted promotion rollback (8 axioms → candidate)
```bash
# audit jsonl 기반 (각 entry에 promoted_at + level 변경 기록)
# 또는 직접 KB JSON 수정
python -c "
import json
path = 'data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json'
d = json.load(open(path, encoding='utf-8'))
for e in d['incompatibilities']:
    if e.get('source') == 'f32_axiom_miner' and e.get('level') == 'vetted':
        e['level'] = 'candidate'
        e['rollback_reason'] = 'manual_rollback'
import os
tmp = path + '.tmp'
json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
os.replace(tmp, path)
"
make f1-regression  # Gate 3 검증
```

### T2.A shadow_reasoner 비활성화
- analysis_pipeline.py에서 `shadow_validate` 호출 주석 처리 → backend restart
- 또는 KB JSON 비우기 (axioms_index 0 → 모든 호출이 empty 반환)

## Acceptance Criteria

### Gate 3 hard-stop
- `make f1-regression` PASS (delta ≤ 0.02 vs replay_baseline_v3.json)
- T2.D 매 candidate 후 자동 실행 (8회), 모두 PASS 확인 후 8/8 vetted

### Manual verification
- T2.A: shadow_reasoner_log.jsonl spot-check (industry × guide_domain 페어가 axiom과 일치)
- T2.B: SPARQL `SELECT COUNT(?s) WHERE { ?s a sh:NodeShape }` ≥ 2,216
- T2.D: `f32_per_candidate_promotion_results.json` pass=8, fail=0, errors=0
- T2.C: `f3_drift_log.jsonl` 최신 row의 `overall_verdict` == "ok"

## Cost & Time Estimates

| Operation | Cost | Time |
|---|---|---|
| `f3-shadow-validator` (direct) | 0 | <1s (2,580 rows, ~76k rows/s) |
| `f3-shadow-validator --pyshacl --limit 50` | 0 | ~0.6s |
| `f3-compile-kb` | 0 | ~3s |
| `f3-drift-check` | 0 | <1s |
| `f3-promote-candidates --apply` (8 candidates) | 0 (LLM 미사용) | **~48분** (8 × 6분 full replay) |
| `f3-weekly-cycle` | 0 | ~10분 (replay 포함) |
| Fuseki container rebuild + recreate | 0 | ~5분 (build) + 즉시 시작 (HTTP healthy) |
| **Tier 2 sprint total (이번 세션)** | **~$0** | **~1시간** (T2.D replay 비중 큼) |

## Known Limitations

| 항목 | 영향 | 대응 |
|---|---|---|
| Fuseki container restart 시 openllet reload | start_period 30분 (실제 HTTP healthy는 즉시) | start_period 보호로 healthcheck 30 min 무관용 |
| T2.A pyshacl 느림 (~80 rows/s) | direct lookup 대비 1000x | shadow는 direct만 production, pyshacl는 sample cross-check 만 |
| T2.D LLM 없이 KB 변경만 | mining quality 낮으면 false vetted 가능 | Gate 3 wrap이 자동 검증, 8/8 PASS 결과로 quality 확인 |
| cp949 unicode (Windows) | promote_f32_per_candidate.py 1차 crash | ASCII-only print + PYTHONIOENCODING=utf-8 + python -u |
| T2.C drift 시계열 길이 제한 없음 | jsonl 무한 append | cron 정기적 rotate or 압축 (별도 운영 작업) |

## Related Documents

- [docs/dev-notes/F.1-auto-register-aliases.md](F.1-auto-register-aliases.md) — F.1 runbook
- [docs/dev-notes/F.2-taxonomy-discovery.md](F.2-taxonomy-discovery.md) — F.2 runbook
- [docs/dev-notes/T3.A-closed-vocab-schema-enum.md](T3.A-closed-vocab-schema-enum.md) — Tier 3.A runbook (병행 작업)
- [docs/status/t2d-per-candidate-promotion-2026-05-18.md](../status/t2d-per-candidate-promotion-2026-05-18.md) — T2.D 8/8 PASS 보고
- [docs/status/evaluation-baseline.md](../status/evaluation-baseline.md) — Gate 3 metric history
- [docs/workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md) — 전체 roadmap
- [docs/architecture/ontology-learning-layer.md](../architecture/ontology-learning-layer.md) — Module 4.4 (Axiom Discovery)

## Future Work (별도 plan)

- **T3.A 잔존 4 free-creates 조사** (THF, CO, MOBILE_EQUIPMENT, WAREHOUSE): OpenAI strict mode edge-case, normalizer hard reject 가능
- **Phase G 7단계 PG materialization** (3-4주): `guide_domain_incompatibilities` JSON → PG table
- **F.4 CQ Reverse** (3-4주): Photo persist ORM + ABox → CQ 자동 생성
- **F.5 GraphRAG** (2주): vector + SPARQL fusion
- **Phase J OBO Foundry** (1-3개월): ontology 정제 + LegalRuleML wrapper + paper
