# Inter-Stage Interfaces

단계 간 인터페이스 contract. 향후 repo 분리 시점에 이 contract가 repo 간 의존 정의가 된다.

## 의존 방향 그래프

```text
[1. Parsing]
  └─ files: kosha-guides/parsed/*.json, kosha-guides/manifest/guides-manifest.json
     │
     ▼
[2. Extraction]
  └─ files: pipe-A NS/SR JSON, pipe-B CI/DT/WP/ES/DR JSON
     │
     ▼
[3. Validation]
  └─ DB: PG tables (NS, SR, articles, checklist_items, domain_terms, sr_*_mapping, ci_sr_mapping)
     │
     ▼
[4. Ontology Export]
  └─ files: TBox/ABox TTL (ontology-team/06-reasoning/ontology/*.ttl, *.owl)
     │
     ▼
[6. Reasoning (오픈소스)]            [5. Enrichment (임시, 6번이 대체)]
  ├─ in:  TBox/ABox/SWRL/SHACL        ├─ in: PG + parsed JSON + manual review
  ├─ proc: Reasoner (Openllet 등)      ├─ proc: LLM augmentation
  └─ out: 보정된 ABox + validation     └─ out: runtime artifacts (guide_*.json, situation_context_taxonomy.*.json)
       │                                        │
       └─────────────┬──────────────────────────┘
                     ▼
              [7. Materialization]
                ├─ in: 보정 ABox + runtime artifacts
                ├─ proc: PG sync scripts (import_*_to_pg.py)
                └─ out: PG materialized tables (guide_usage_profiles, guide_sr_link_candidates, ci_sr_mapping 등)
                     │
                     ▼
              [8. App]
                ├─ in: PG materialized tables + runtime artifacts
                └─ out: HTTP API + React UI
```

## File Contract

| Contract | Producer | Consumer | 위치 |
|---|---|---|---|
| Parsed Guide JSON | Stage 1 | Stage 2 (pipe-B), Stage 5 | `data-team/01-parsing/kosha-guides/parsed/guide-*.json` |
| Guide manifest | Stage 1 | Stage 5, Stage 7 | `data-team/01-parsing/kosha-guides/manifest/guides-manifest.json` |
| pipe-A NS/SR/Penalty JSON | Stage 2 | Stage 3 | `data-team/02-extraction/pipe-A/data/*.json` |
| pipe-B CI JSON | Stage 2 | Stage 3 | `data-team/02-extraction/pipe-B/data/ci-output/*.json` |
| TBox OWL | Stage 4 | Stage 6 | `ontology-team/06-reasoning/ontology/kosha-ontology.owl` |
| ABox TTL | Stage 4 | Stage 6 | `ontology-team/06-reasoning/ontology/kosha-instances.ttl` |
| SHACL shapes | Stage 6 | Stage 6 / Stage 7 | `ontology-team/06-reasoning/ontology/serving-validation-shapes.ttl` |
| Serving snapshot TTL | Stage 6 / Stage 7 | Stage 7 검증 | `ontology-team/06-reasoning/ontology/serving-snapshot-*.ttl` |
| Validation report (자동) | Stage 6 / Stage 7 | review only | `ontology-team/06-reasoning/ontology/serving-validation-report-*.{md,csv,json}` |
| Runtime artifacts | Stage 5 | Stage 8 (직접 import) | `serving-team/08-app/backend/app/data/*.json, *.jsonl` |
| Synthetic eval input | Stage 5 | Stage 5 evaluation | `data-team/05-enrichment/eval-data/synthetic_observations_v*.jsonl` |
| Eval reports manifest | Stage 5 | review only | `data-team/05-enrichment/eval-data/reports-manifest.json` |

## PG Schema Contract

PG schema는 단계별로 누적된다. 한 팀이 다른 팀이 만든 테이블을 수정하지 않는다.

| Owner Stage | 주요 테이블 | 후속 단계가 읽음 |
|---|---|---|
| Stage 3 (pipe-A) | `articles`, `norm_statements`, `safety_requirements`, `sr_article_mapping`, `sr_ns_mapping`, `penalty_rules`, `penalty_conditions` | Stage 3 (pipe-B), 7, 8 |
| Stage 3 (pipe-B) | `kosha_guides`, `checklist_items`, `work_processes`, `equipment_specs`, `document_requirements`, `domain_terms`, `ci_sr_mapping`, `wp_sr_mapping` | Stage 3 (pipe-C), 4, 7, 8 |
| Stage 3 (pipe-C) | `guide_inter_links`, `guide_sr_link_candidates`, `guide_entity_feature_candidates`, `guide_visual_trigger_candidates` | Stage 7, 8 |
| Stage 5 | (Stage 3 후보 테이블 갱신) | Stage 7, 8 |
| Stage 7 | `guide_usage_profiles`, materialized views | Stage 8 |

자세한 schema 위치: 각 단계의 `db/schema_*.sql`.

## API Contract (Stage 8)

OHS HTTP API는 다음 정책을 따른다:
- LLM은 관찰사실/시각단서 추출에만 사용
- 응답은 PG materialized table 조회 결과 + LLM observation
- 온톨로지/리즈너 직접 호출 안 함
- 결과 필드: `risk_overview`, `immediate_actions`, `standard_procedures`, `penalty_paths`, `reasoning_trace`

자세한 API 명세: [serving-team/08-app/README.md](../../serving-team/08-app/README.md).
