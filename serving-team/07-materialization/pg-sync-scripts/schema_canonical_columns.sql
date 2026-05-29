-- 위험 코드 정본화(canonicalization) — Additive 듀얼 태깅용 canonical 컬럼.
-- fine 컬럼(accident_types/hazardous_agents/work_contexts)은 보존, canonical 병기.
-- 채움: data-team/05-enrichment/llm-scripts/apply_canonical_tags.py (canonical_vocab.to_canonical).
-- 정본 SSOT: shared/reference/canonical-code-vocabulary.json (KOSHA-22 accident backbone).
-- 멱등(IF NOT EXISTS) — 재실행 안전.

ALTER TABLE safety_requirements ADD COLUMN IF NOT EXISTS accident_types_canonical jsonb;
ALTER TABLE safety_requirements ADD COLUMN IF NOT EXISTS hazardous_agents_canonical jsonb;
ALTER TABLE safety_requirements ADD COLUMN IF NOT EXISTS work_contexts_canonical jsonb;

ALTER TABLE checklist_items ADD COLUMN IF NOT EXISTS accident_types_canonical jsonb;
ALTER TABLE checklist_items ADD COLUMN IF NOT EXISTS hazardous_agents_canonical jsonb;
ALTER TABLE checklist_items ADD COLUMN IF NOT EXISTS work_contexts_canonical jsonb;

-- guide_entity_feature_candidates: feature_code(fine) 보존 + canonical 병기(교차축 canonical_axis).
ALTER TABLE guide_entity_feature_candidates ADD COLUMN IF NOT EXISTS canonical_code text;
ALTER TABLE guide_entity_feature_candidates ADD COLUMN IF NOT EXISTS canonical_axis text;
