-- Phase G Sprint G.4 — she_patterns_reasoner_derived materialized view
-- Purpose: F.2 Day 5 pending_review SHE patterns (77건, v3.1 code 링크에서 도출됨)을
-- "reasoner-derived candidates" layer로 노출. 매칭에 직접 사용 안 됨 (status=pending_review),
-- 미래 SHACL/OWL reasoner 통합 시 활용 가능.
--
-- Phase G.4 분기 B (reasoner 미작동): 명시적 추론 대신 mining + LLM 도출 결과를 동등 표현.
-- Openllet `inferred=0` 이슈 (law:modifies AsymmetricProperty + law:modifiedBy inverseOf 충돌)는
-- 별도 Tier 4 sprint에서 ontology 패치로 해결 예정.

CREATE OR REPLACE VIEW she_patterns_reasoner_derived AS
SELECT
    she_id,
    name,
    features,
    visual_triggers,
    broadness_score,
    source_sr_ids,
    -- derivation provenance
    'F.2_v31_code_link' AS derivation_source,
    'pending_matcher_integration' AS integration_status,
    created_at
FROM she_catalog
WHERE status = 'pending_review';

COMMENT ON VIEW she_patterns_reasoner_derived IS 'Phase G.4 — reasoner-derived SHE pattern candidates (currently F.2 Day 5 v3.1 link, status=pending_review). Read-only architectural layer. 향후 ontology reasoner inferred=0 fix 후 동일 view에 추론 결과 통합 가능.';
