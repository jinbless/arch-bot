# arch-bot

`arch-bot` is the top-level planning and coordination repository for the ontology-based KOSHA workplace-risk assistant.

The service goal is:

> When a business owner uploads a workplace photo, the system identifies visible risk factors, recommends corrective actions, and explains possible penalty paths if the risk is not corrected.

## Repository Role

This repository is a meta repository. It keeps the current design documents, decision logs, evaluation summaries, and synthetic observation testsets.

The implementation repositories remain separate:

| Area | Repository |
|---|---|
| Ontology and extraction pipelines | <https://github.com/jinbless/koshaontology> |
| Backend/frontend service | <https://github.com/jinbless/OHS> |
| Legal source dependency | <https://github.com/legalize-kr/legalize-kr> |

## Current Design Baseline

- `risk:` is the shared abstraction layer for risk knowledge.
- `haz:`, `agent:`, and `ctx:` provide concrete risk-feature vocabularies under `risk:RiskFeature`.
- `she:` models reusable situational hazard patterns, not per-photo events.
- `KOSHA Guide / WorkProcess` is the center of standard corrective procedures.
- `ChecklistItem` is used for immediate actions, visual cues, search indexing, and supporting evidence.
- `PenaltyPath` presents three business-facing penalty routes:
  - general violation or general incident
  - death
  - serious accident
- Runtime serving uses materialized triples/search results rather than requiring an OWL reasoner in the request path.

## Key Documents

- `온톨로지_통합구조_및_흐름도.md`
- `온톨로지_법령레이어_상세도.md`
- `온톨로지_SR레이어_상세도.md`
- `온톨로지_위험상황레이어_상세도.md`
- `온톨로지_가이드레이어_상세도.md`
- `온톨로지_벌칙레이어_상세도.md`
- `needToChangeCode.md`
- `PROJECT_CLEANUP_LOG.md`
- `최종보고서_온톨로지_AI시스템_핵심요약.md`

## Latest Synthetic Evaluation

Latest aggregate report:

- `pictures-json/reports/synthetic_observations_v1_v10_v10fix6_confusion_matrix.md`

Summary:

```text
v1~v10 total cases: 2360
SHE TP/FN/FP/TN: 2016/0/67/277
SHE recall: 100.0%
SHE precision: 96.8%
SHE specificity: 80.5%
normal suppression: 276/276 (100.0%)
```

The remaining priority is not SHE recall. It is the boundary between confirmed risk and confirmation-needed candidate results.
