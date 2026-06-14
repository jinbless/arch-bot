-- Track A ② / WS-DRIFT-1(lite) — materialization_runs
-- 물질화 run의 출처(PROV-O wasGeneratedBy)를 보존하는 run-tracking 테이블.
-- 추론 산출 → PG 적재 1회 = 1 run. ontology_commit(git rev) + source_ttl_sha256로
-- "어느 온톨로지 상태에서 어떤 규칙으로 적재됐는가"를 재현 가능하게 박제한다.
--
-- 적재: serving-team/07-materialization/pg-sync-scripts/import_sr_inferred_relations_to_pg.py
-- 소비: sr_inferred_relations.run_id → materialization_runs.run_id (행 단위 wasGeneratedBy)
--
-- 적용: make phase-g5-schema (materialization_runs 먼저, 그 다음 sr_inferred_relations).

CREATE TABLE IF NOT EXISTS materialization_runs (
    run_id            SERIAL PRIMARY KEY,
    rule_set          VARCHAR(80) NOT NULL,        -- 예: 'reasoning-slice R-1/R-2'
    ontology_commit   VARCHAR(40),                 -- git rev-parse HEAD (적재 시점)
    source_ttl        TEXT,                         -- 입력 TTL 경로(상대)
    source_ttl_sha256 CHAR(64),                     -- 입력 TTL sha256 (재현성)
    triple_count      INTEGER,                      -- 적재된 행(트리플) 수
    status            VARCHAR(20) NOT NULL DEFAULT 'running',  -- running | completed | failed
    started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at       TIMESTAMPTZ,
    notes             TEXT,
    CONSTRAINT chk_mr_status CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_mr_rule_set ON materialization_runs (rule_set);
CREATE INDEX IF NOT EXISTS idx_mr_started ON materialization_runs (started_at);

COMMENT ON TABLE materialization_runs IS 'WS-DRIFT-1 — 물질화 run 출처(PROV-O wasGeneratedBy). 추론→PG 적재 1건 = 1 run. ontology_commit(git rev) + source_ttl_sha256로 재현성 박제.';
COMMENT ON COLUMN materialization_runs.ontology_commit IS '적재 시점 git rev-parse HEAD';
COMMENT ON COLUMN materialization_runs.source_ttl_sha256 IS '입력 TTL sha256 — 동일 입력 재적재 검증';
COMMENT ON COLUMN materialization_runs.status IS 'running(시작) → completed(정상 종료) | failed';
