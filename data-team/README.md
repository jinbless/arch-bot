# Data Team

데이터팀은 1~5단계를 담당한다. **향후 private `kosha-data-pipeline` repo로 분리 예정**.

## 단계

| 단계 | 디렉토리 | 역할 |
|---|---|---|
| 1. Parsing | [01-parsing/](01-parsing/) | 법령(legalize-kr) + KOSHA Guide PDF → JSON 파싱 |
| 2. Extraction | [02-extraction/](02-extraction/) | LLM으로 NS/SR/CI 추출 (pipe-A, pipe-B) |
| 3. Validation | [03-validation/](03-validation/) | PG 적재로 적합성/FK 규칙 검증 (pipe-C) |
| 4. Ontology Export | [04-ontology-export/](04-ontology-export/) | PG → 온톨로지 export |
| 5. Enrichment (임시) | [05-enrichment/](05-enrichment/) | LLM으로 서빙 부족 온톨로지 레이어 보강 — 6번 완성 시 폐지 |

## 주기성

- 1~4번은 **1회성** (새 데이터/Guide 추가 시에만 재실행)
- 5번은 **현재 집중 작업** — 6번(온톨로지 리즈너 기반 보정)이 안정화되면 자연 폐지

## 5단계 enrichment 진행 상황 (2026-05-18 저녁)

Layer 4 자율 학습 modules 진척:

| Module | 상태 | Runbook |
|---|---|---|
| 4.1 Term Extraction (F.1) | ✅ closed loop (5 vetted aliases) | [F.1-auto-register-aliases.md](../docs/dev-notes/F.1-auto-register-aliases.md) |
| 4.2 Taxonomy Discovery (F.2) | ✅ catalog v3.3 (481 codes × 5 axes) | [F.2-taxonomy-discovery.md](../docs/dev-notes/F.2-taxonomy-discovery.md) |
| 4.3 Relation Mining | ✅ 운영 중 (2,240 vetted incompatibilities) | (F.3.2 mining) |
| **4.4 Axiom Discovery (Tier 2 F.3 closing)** | ✅ **closed loop 완성 (2026-05-18)** | [F.3-axiom-discovery.md](../docs/dev-notes/F.3-axiom-discovery.md) |
| 4.5 CQ Reverse | ⏳ Tier 3 후속 (3B) | — |
| 4.6 GraphRAG | ⏳ Tier 4 | — |
| 4.7 Continual Adapt | ✅ partial (T2.C drift monitor + T2.A reasoner shadow) | [F.3-axiom-discovery.md](../docs/dev-notes/F.3-axiom-discovery.md) T2.C section |

**최근 sprint** (2026-05-18 저녁, main `b237e78`):
- **Tier 1 재포함** (`93c49fe`): T1.A promote_she_review rollback fix + T1.B npz cache 87% 축소 + T1.C step 4.5 usage tracking
- **Tier 2 T2.A** (`93c49fe`): pyshacl reasoner shadow channel (offline + serving runtime)
- **Tier 2 T2.B** (`ac98d4c`): kb-candidates.ttl 2192 SHACL shapes + Fuseki SPARQL 2216 NodeShapes 검증
- **Tier 2 T2.C** (`78886b3`): f3_drift_check + Makefile f3-* targets
- **Tier 2 T2.D** (`ac98d4c`): 8 F.3.2 candidates 1-by-1 promote (**8/8 PASS**, 예상 5-6 대비 100% 통과)
- **Tier 3.A** (`b237e78`): Closed Vocab Schema Enum 529 codes (free-creates 76→4 = **-94.7%**)

**Makefile 통합 인터페이스**:
```bash
make f1-help / f2-help / f3-help     # 각 phase 사용법
make f3-weekly-cycle                  # T2.C cron-able (shadow → compile → replay → drift)
```

신규 scripts (이번 세션):
- `data-team/05-enrichment/llm-scripts/pyshacl_shadow_validator.py` (T2.A)
- `data-team/05-enrichment/llm-scripts/compile_kb_to_ttl.py` (T2.B)
- `data-team/05-enrichment/llm-scripts/f3_drift_check.py` (T2.C)
- `data-team/05-enrichment/llm-scripts/promote_f32_per_candidate.py` (T2.D)
- `data-team/05-enrichment/llm-scripts/_migrate_embedding_cache_to_npz.py` (T1.B 1회성)

## 다음 팀과의 인터페이스

- **→ 온톨로지팀 (6단계)**: 4단계가 만든 TBox/ABox TTL을 [ontology-team/06-reasoning/](../ontology-team/06-reasoning/)에서 읽어 추론·SHACL 검증
- **→ 서빙팀 (7~8단계)**: 5단계의 runtime artifacts (`05-enrichment/runtime-artifacts/` 또는 현재는 `serving-team/08-app/backend/app/data/`)를 [serving-team/08-app/backend](../serving-team/08-app/backend)가 직접 import

## 공통 reference

- [shared/reference/hazard-taxonomy-unified.json](../shared/reference/hazard-taxonomy-unified.json) — 위험 분류 통합 데이터

## 향후 repo 분리 계획

[docs/architecture/repo-split-plan.md](../docs/architecture/repo-split-plan.md) 참조.
