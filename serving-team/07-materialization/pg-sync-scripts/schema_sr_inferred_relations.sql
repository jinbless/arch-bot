-- Track A ② — sr_inferred_relations (추론 관계 PG 물질화)
-- 리즈너(SWRL/Pellet 동치 CONSTRUCT) 산출을 SR 단위로 비정규화해 서빙에 직결.
--   exemptedBy : SR이 파생된 의무 NS가 면제 NS에 의해 면제됨 (R-1, 현재 107행/95 SR)
--   coApplicable: 같은 조문 기반 관련 SR 쌍 (R-2, 현재 0행 — SR↔Article 1:1)
--
-- 서빙 경로(Fuseki 비의존): app/services/sr_inferred_service.py가 이 테이블을 SELECT,
--   /api/v1/sparql/sr/{id}/{exemptions,co-applicable} 및 /article/{}/inferred-graph 소비.
-- 출처: ontology-team/06-reasoning/ontology/kosha-inferred-relations.ttl (emit_inferred_relations.py 산출)
-- 적재: serving-team/07-materialization/pg-sync-scripts/import_sr_inferred_relations_to_pg.py
-- 행 단위 PROV: run_id → materialization_runs.run_id (wasGeneratedBy)
--
-- 적용: make phase-g5-schema (materialization_runs 적용 후 실행 — run_id FK 의존).

CREATE TABLE IF NOT EXISTS sr_inferred_relations (
    id          SERIAL PRIMARY KEY,
    sr_id       VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    rel_type    VARCHAR(40) NOT NULL,           -- exemptedBy | coApplicable
    target_id   VARCHAR(60) NOT NULL,           -- 면제 NS id | co-applicable SR id
    target_kind VARCHAR(20) NOT NULL,           -- norm_statement | safety_requirement
    rule_id     VARCHAR(50) NOT NULL,           -- R-1 | R-2 (향후 K-R2 등 확장 가능)
    attrs       JSONB,                          -- 서빙 렌더용 비정규화 {article_code, condition, title}
    run_id      INTEGER REFERENCES materialization_runs(run_id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_sir_triple UNIQUE (sr_id, rel_type, target_id, rule_id),
    CONSTRAINT chk_sir_rel_type CHECK (rel_type IN ('exemptedBy', 'coApplicable', 'dependsOn')),
    CONSTRAINT chk_sir_target_kind CHECK (target_kind IN ('norm_statement', 'safety_requirement'))
);

-- 기존 테이블 마이그레이션: rel_type CHECK에 'dependsOn' 추가(K-R4). CREATE TABLE IF NOT EXISTS는
-- 기존 제약을 갱신하지 않으므로 idempotent DROP+ADD로 반영.
ALTER TABLE sr_inferred_relations DROP CONSTRAINT IF EXISTS chk_sir_rel_type;
ALTER TABLE sr_inferred_relations ADD CONSTRAINT chk_sir_rel_type
    CHECK (rel_type IN ('exemptedBy', 'coApplicable', 'dependsOn'));

CREATE INDEX IF NOT EXISTS idx_sir_sr ON sr_inferred_relations (sr_id);
CREATE INDEX IF NOT EXISTS idx_sir_rel ON sr_inferred_relations (rel_type);
CREATE INDEX IF NOT EXISTS idx_sir_target ON sr_inferred_relations (target_id);
CREATE INDEX IF NOT EXISTS idx_sir_run ON sr_inferred_relations (run_id);
CREATE INDEX IF NOT EXISTS idx_sir_sr_rel ON sr_inferred_relations (sr_id, rel_type);

COMMENT ON TABLE sr_inferred_relations IS 'Track A ② — 리즈너(R-1 exemptedBy / R-2 coApplicable) 산출의 SR-단위 PG 물질화. 서빙 Fuseki 비의존 경로. 출처: kosha-inferred-relations.ttl.';
COMMENT ON COLUMN sr_inferred_relations.rel_type IS 'exemptedBy(R-1 면제) | coApplicable(R-2/K-R2 동시적용) | dependsOn(K-R4 같은 Hazard 의존)';
COMMENT ON COLUMN sr_inferred_relations.target_id IS 'exemptedBy면 면제 NS id, coApplicable/dependsOn면 상대 SR id';
COMMENT ON COLUMN sr_inferred_relations.attrs IS '서빙 렌더 비정규화: exemptedBy={article_code,condition}, coApplicable={title,article_code}';
COMMENT ON COLUMN sr_inferred_relations.run_id IS 'PROV-O wasGeneratedBy → materialization_runs.run_id';

-- updated_at trigger (penalty_rule_index 패턴 복제, prefix sir)
CREATE OR REPLACE FUNCTION update_sir_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sir_updated_at ON sr_inferred_relations;
CREATE TRIGGER trg_sir_updated_at
    BEFORE UPDATE ON sr_inferred_relations
    FOR EACH ROW EXECUTE FUNCTION update_sir_updated_at();
