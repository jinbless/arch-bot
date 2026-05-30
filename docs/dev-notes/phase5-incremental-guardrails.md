# Phase 5 incremental 가드레일 — SHACL codes∈canonical + Layer 4.7 continual

> 2026-05-30. Canonicalization + KOSHA-22 sprint(2026-05-29)의 "Deferred 후속 #2(Phase 5 incremental)" 중
> 자기완결·저위험 2건 구현. 상위 맥락: [../status/current-session.md](../status/current-session.md).

Canonicalization sprint은 imperative 게이트(`scripts/audit_code_consistency.py --gate`, `make verify-codes`)로
온톨로지 UPPER/dual-URI 재발을 차단했다. 본 증분은 그 게이트를 **선언적 SHACL**로 보완하고,
게이트가 WARN으로만 흘리던 **pending open-class 빈도**를 정식 continual 태스크로 형식화한다.

SSOT는 변함없이 [`shared/reference/canonical-code-vocabulary.json`](../../shared/reference/canonical-code-vocabulary.json)
(단일 소비자 `canonical_vocab.py`). 두 산출물 모두 이 SSOT에서 파생 — 하드코딩 없음.

---

## 2a. SHACL codes∈canonical 가드레일 (선언적)

**문제**: exporter 3종을 `code_iri_mapper` SSOT로 일원화(Phase 4-B)했으나, PG 재생성·수기 편집 시
legacy CamelCase(`haz:Crush`)·UPPER(`haz:CAUGHT_IN`)·오타 fragment가 ABox에 재유입될 위험.
audit 게이트는 regex 스캔(빠르지만 imperative). 이식 가능한 **선언적** 형식 검증이 없음.

**해결**: SSOT 파생 SHACL NodeShape 4개 — 축별 3 + polymorphic feature 1.
- 생성: [`scripts/gen_canonical_code_shape.py`](../../ontology-team/06-reasoning/ontology/scripts/gen_canonical_code_shape.py)
  → [`kosha-canonical-code-shape.ttl`](../../ontology-team/06-reasoning/ontology/kosha-canonical-code-shape.ttl) (자동 생성, 수동 편집 금지).
- 각 shape: `sh:targetObjectsOf <코드 술어>` + `sh:in (<정본 IRI 목록>)` + `sh:nodeKind sh:IRI` + `sh:severity sh:Violation`.
- 코드 술어 → 축 매핑:
  - accident_type(haz): `sr:addressesHazard`, `sr:addressesAccidentType`, `guide:addressesHazard`
  - hazardous_agent(agent): `sr:addressesAgent`, `guide:guideAddressesAgent`
  - work_context(ctx): `sr:inWorkContext`, `guide:guideAppliesToContext`
  - polymorphic union: `sr:addressesFeature` (3축 전체 허용)
- 허용 집합 = `canonical_set(axis)` ∪ `meta_set(axis)`. accident 23 / agent 10 / **work_context 36(=29 canonical + 7 wc_meta)** = **69 IRI**.
  - **wc_meta**(`SAFETY_MGMT`/`PPE_MGMT`/`OTHER`/`SPECIAL_WORKER`/`WASTE_MGMT`/`WELFARE`/`GENERAL_WORKPLACE`)는
    canonical은 아니나 rollup 항등이라 `to_canonical`이 pending으로 떨어뜨리지 않는 정당한 축 값 — SR/Guide 실사용.
    SSOT 모듈에 `canonical_vocab.meta_set(axis)` 공개 접근자 신설(additive).
  - pending bucket(`UNCLASSIFIED`/`UNKNOWN_AGENT`/`UNKNOWN_CONTEXT`)은 canonical 배열에 포함 → 허용.

**검증**: [`scripts/validate_canonical_codes.py`](../../ontology-team/06-reasoning/ontology/scripts/validate_canonical_codes.py) (pyshacl), `make verify-codes-shape`.
- 전체 ABox(`kosha-instances.ttl` 956,551 + `kosha-instances-guide-hazard.ttl` 2,115 = **958,666 triple**) → **conforms=True** (parse ~26s, pyshacl ~0s; focus node가 정본 IRI ~69개로 bounded).
- 음성 테스트: `haz:Crush`/`haz:CAUGHT_IN`/`agent:ArcFlash`/`ctx:Forklift` 합성 → **4건 적발 + exit 1**, 정본 `haz:CaughtIn`은 통과.
- → Phase 4-B 마이그레이션의 "구어휘 잔여 0"을 독립 메커니즘(SHACL allowlist)으로 재확인.

**재생성**: SSOT 변경 시 `make gen-canonical-shape` (산출 TTL은 git tracked).

---

## 2c. Layer 4.7 Continual — pending open-class 승격 후보 추적

**문제**: SSOT는 미분류 코드를 pending bucket으로 흡수(open-class, 억지 배정 금지).
`audit --gate`가 이를 `[WARN]`으로 적발하나 **빈도/추세**는 추적 못 함 → 어느 pending이 승격할 만큼
recurrent한지 신호 부재.

**해결**: [`continual_pending_promotion.py`](../../data-team/05-enrichment/llm-scripts/continual_pending_promotion.py) (읽기전용, `make continual-pending`).
- live PG(SR + CI + GUIDE) 빈도로 pending(자기 축 pending으로 떨어진) 코드를 랭킹.
- tier: **PROMOTE**(freq ≥ 8) / **WATCH**(≥ 3) / **NOISE**(< 3) — 임계 `--promote-threshold`/`--watch-threshold` 조정.
- queue 산출: `runtime-artifacts/continual_pending_promotion.json` (gitignored, 재생성 가능).
- **mutate 금지** — 승격은 사람/후속 LLM 클러스터링 결정. 승격 시: `build_canonical_vocabulary.py` 룰 보강(신규 canonical 또는 매핑) → 재생성 → `make verify-codes`.

**현재 스냅샷(2026-05-30)**: accident/agent 후보 0. work_context 7건(모두 GUIDE 출처):

| tier | code | freq |
|---|---|---|
| PROMOTE | `WET_FLOOR_WORK` | 11 |
| WATCH | `NIGHT_SOLO_WORK` | 6 |
| NOISE | `CROWD_MANAGEMENT` / `ANIMAL_FEEDING` | 2 / 2 |
| NOISE | `INTERIOR_CLEANING` / `CLEANING_WET` / `CAGE_CLEANING` | 1 / 1 / 1 |

→ `WET_FLOOR_WORK`(미끄러운 바닥 작업)는 빈도상 신규 work_context canonical 또는 기존 매핑(예: `PASSAGE`/`HEAT_COLD_WORK`?) 승격 1순위 후보. 결정은 사용자 몫.

---

## 게이트 3종 관계

| 게이트 | 메커니즘 | 대상 | 실패 |
|---|---|---|---|
| `make verify-codes` | regex 스캔 (imperative) | catalog↔SR↔CI↔GUIDE↔ontology 정합 + 온톨로지 UPPER/dual-URI | CRITICAL>0 → exit 1 |
| `make verify-codes-shape` | pyshacl (선언적) | ABox 코드 IRI ∈ canonical 69 | 비정본 IRI → exit 1 |
| `make continual-pending` | live PG 빈도 (관찰) | pending open-class 승격 신호 | (게이트 아님, queue 산출) |

세 가지 모두 동일 SSOT(`canonical-code-vocabulary.json`)에서 파생 — 어휘 드리프트를 imperative·declarative
양면에서 차단하고, open-class 성장을 정량 추적한다.
