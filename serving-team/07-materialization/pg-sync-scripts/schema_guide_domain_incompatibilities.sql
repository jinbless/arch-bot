-- Phase G Sprint G.1 — guide_domain_incompatibilities PG materialization
-- Source: data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json
-- Ontology TBox source: ontology-team/06-reasoning/ontology/kosha-ontology-v3-incompat-patch.ttl
--                       (core:Incompatibility class + 5 metadata properties)
--
-- 적재 방식: import_domain_incompatibilities_to_pg.py (UPSERT idempotent)
-- 운영: shadow_reasoner.py가 매 사진 분석 요청 시 PG SELECT (~50μs cache hit, ~10ms cache miss)

CREATE TABLE IF NOT EXISTS guide_domain_incompatibilities (
    id           SERIAL PRIMARY KEY,
    domain_a     VARCHAR(100) NOT NULL,        -- industry EN code (예: CONSTRUCTION)
    domain_b     VARCHAR(100) NOT NULL,        -- industry EN code (예: METAL_MACHINING)
    level        VARCHAR(20)  NOT NULL,        -- 'vetted' | 'candidate' (ontology core:axiomLevel)
    confidence   NUMERIC(4,3),                 -- 0.000 ~ 1.000 (ontology core:axiomConfidence)
    source       VARCHAR(50),                  -- 'f32_axiom_miner' | 'manual' | 'self_refine' (ontology core:axiomSource)
    reason       TEXT,                         -- LLM verify rationale (ontology core:axiomReason)
    promoted_at  TIMESTAMPTZ,                  -- candidate→vetted 전환 시각 (ontology core:axiomPromotedAt)
    rollback_at  TIMESTAMPTZ,                  -- vetted→candidate rollback 시각 (운영 audit)
    rollback_reason TEXT,                      -- rollback 원인 (T2.D defensive rollback 등)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_gdi_pair_source UNIQUE (domain_a, domain_b, source),
    CONSTRAINT chk_gdi_level CHECK (level IN ('vetted', 'candidate'))
);

CREATE INDEX IF NOT EXISTS idx_gdi_pair ON guide_domain_incompatibilities (domain_a, domain_b);
CREATE INDEX IF NOT EXISTS idx_gdi_level ON guide_domain_incompatibilities (level);
CREATE INDEX IF NOT EXISTS idx_gdi_source ON guide_domain_incompatibilities (source);

COMMENT ON TABLE  guide_domain_incompatibilities IS 'Industry pair mutual exclusion KB. Phase G.1 materialization of guide_domain_incompatibilities.json. Ontology backed: core:Incompatibility class (n-ary relation with metadata).';
COMMENT ON COLUMN guide_domain_incompatibilities.level IS 'asymmetric trust level. vetted=hard reject (-0.18), candidate=soft warning (-0.05)';
COMMENT ON COLUMN guide_domain_incompatibilities.source IS 'mining provenance. f32_axiom_miner / manual / self_refine';

-- updated_at trigger (PG 14+)
CREATE OR REPLACE FUNCTION update_gdi_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_gdi_updated_at ON guide_domain_incompatibilities;
CREATE TRIGGER trg_gdi_updated_at
    BEFORE UPDATE ON guide_domain_incompatibilities
    FOR EACH ROW EXECUTE FUNCTION update_gdi_updated_at();
