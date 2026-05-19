-- Phase G Sprint G.3 — penalty_rule_index PG materialization
-- Source: ontology-team/06-reasoning/ontology/kosha-instances.ttl (Pellet TTL ABox)
-- Ontology TBox: penalty:PenaltyRule + appliesTo/penaltyType/maxFine
--                (kosha-ontology-v3-penalty-relations-patch.ttl)
--
-- 적재: serving-team/07-materialization/pg-sync-scripts/import_penalty_to_pg.py
-- 운영: hazard_rule_engine._load_penalty_index() PG SELECT (G.3 전환)
--
-- 기존 penalty_routes (article-level) 와 별도. penalty_rule_index는 sr-level
-- denormalized index (1 sr → N penalty rules).

CREATE TABLE IF NOT EXISTS penalty_rule_index (
    id                    SERIAL PRIMARY KEY,
    sr_id                 VARCHAR(30) NOT NULL,
    penalty_rule_id       VARCHAR(50) NOT NULL,
    article_code          VARCHAR(20),
    sanction_type         VARCHAR(40),       -- CriminalSanction | AdministrativeFine | ...
    penalty_description   TEXT,
    severity_score        INTEGER,
    subject_role          VARCHAR(50),
    accident_outcome      VARCHAR(50),
    violated_norm_id      VARCHAR(50),
    violated_article_id   VARCHAR(20),
    delegated_from_article_id VARCHAR(20),
    penalty_article_id    VARCHAR(20),
    basis_text            TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_pri_sr_rule UNIQUE (sr_id, penalty_rule_id)
);

CREATE INDEX IF NOT EXISTS idx_pri_sr ON penalty_rule_index (sr_id);
CREATE INDEX IF NOT EXISTS idx_pri_rule ON penalty_rule_index (penalty_rule_id);
CREATE INDEX IF NOT EXISTS idx_pri_article ON penalty_rule_index (article_code);
CREATE INDEX IF NOT EXISTS idx_pri_sanction_type ON penalty_rule_index (sanction_type);

COMMENT ON TABLE penalty_rule_index IS 'Phase G.3 — SR-level penalty index materialized from kosha-instances.ttl. Ontology-backed (penalty:PenaltyRule). Backend: hazard_rule_engine._load_penalty_index.';
COMMENT ON COLUMN penalty_rule_index.sanction_type IS 'CriminalSanction (징역) | AdministrativeFine (과태료)';
COMMENT ON COLUMN penalty_rule_index.severity_score IS '심각도 점수 (TTL pen:severityScore)';

-- updated_at trigger
CREATE OR REPLACE FUNCTION update_pri_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pri_updated_at ON penalty_rule_index;
CREATE TRIGGER trg_pri_updated_at
    BEFORE UPDATE ON penalty_rule_index
    FOR EACH ROW EXECUTE FUNCTION update_pri_updated_at();
