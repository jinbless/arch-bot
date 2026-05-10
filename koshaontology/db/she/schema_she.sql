-- Phase 1 — SHE PG Schema (사용자 비판 #6 — draft/reviewed/approved/deprecated governance)
--
-- Tables:
--   she_catalog       SHE 카탈로그 본체 (status workflow)
--   she_sr_mapping    SHE × SR many-to-many (with confidence)
--   she_ci_mapping    SHE × CI many-to-many (with confidence)
--
-- 적재 흐름:
--   1. Phase 2.1 LLM inversion → she-draft-v1.jsonl (status='draft')
--   2. Phase 2.1.5 validator + broadness gate → status='approved_auto' or reject
--   3. Phase 2.2 pilot 3 wc 필터 → 150 SHE
--   4. Phase 2.3 PG/Fuseki 적재
--   5. Production search: WHERE status IN ('approved_auto', 'approved_manual')

BEGIN;

-- ────────────────────────────────────────────────────────────────────────
-- 1. she_catalog (SHE 본체)
-- ────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS she_catalog (
    she_id              VARCHAR(60) PRIMARY KEY,             -- SHE-{wc}-{hash10}
    name                TEXT NOT NULL,                        -- 한국어 name (50자 이내)
    name_pattern        VARCHAR(200),                         -- 영문 underscore pattern
    features            JSONB NOT NULL,                       -- 8 dim feature 값
    visual_triggers     JSONB,                                -- 사진에서 관찰 가능한 SHE 매칭 단서
    rationale           TEXT,                                 -- LLM이 생성한 근거

    -- Status workflow (사용자 비판 #6/#7)
    status              VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft/approved_auto/approved_manual/rejected/deprecated
    broadness_score     NUMERIC(4,3),                         -- 0.0~1.0 (1.0 = 8 dim 모두 specific)

    -- Source tracking (재현성)
    source_model        VARCHAR(50),                          -- "openai/gpt-4o" 등
    source_prompt_hash  CHAR(32),                             -- prompt md5
    source_sr_ids       JSONB,                                -- inversion 대상 SR list

    -- Lifecycle
    valid_from          DATE,                                 -- 법령 시행일
    valid_until         DATE,                                 -- deprecate 시점
    superseded_by       VARCHAR(60) REFERENCES she_catalog(she_id),

    -- Audit
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    reviewed_by         VARCHAR(100),
    reviewed_at         TIMESTAMP,
    approved_at         TIMESTAMP,
    notes               TEXT
);

ALTER TABLE she_catalog
    ADD COLUMN IF NOT EXISTS visual_triggers JSONB;

CREATE INDEX IF NOT EXISTS idx_she_status            ON she_catalog(status);
CREATE INDEX IF NOT EXISTS idx_she_features_gin      ON she_catalog USING GIN (features);
CREATE INDEX IF NOT EXISTS idx_she_visual_triggers_gin ON she_catalog USING GIN (visual_triggers);
CREATE INDEX IF NOT EXISTS idx_she_broadness         ON she_catalog(broadness_score) WHERE broadness_score >= 0.5;
CREATE INDEX IF NOT EXISTS idx_she_source_sr_ids_gin ON she_catalog USING GIN (source_sr_ids);

-- ────────────────────────────────────────────────────────────────────────
-- 2. she_sr_mapping (SHE × SR many-to-many)
-- ────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS she_sr_mapping (
    she_id      VARCHAR(60) NOT NULL REFERENCES she_catalog(she_id) ON DELETE CASCADE,
    sr_id       VARCHAR(40) NOT NULL,  -- SR-FALL-001 또는 SR-PILOT_X-001 (v2 격리 호환)
    confidence  NUMERIC(4,3) DEFAULT 1.0,
    source      VARCHAR(20) DEFAULT 'inversion',  -- "inversion" | "manual" | "audit"
    PRIMARY KEY (she_id, sr_id)
);
CREATE INDEX IF NOT EXISTS idx_she_sr_sr ON she_sr_mapping(sr_id);

-- ────────────────────────────────────────────────────────────────────────
-- 3. she_ci_mapping (SHE × CI many-to-many)
-- ────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS she_ci_mapping (
    she_id      VARCHAR(60) NOT NULL REFERENCES she_catalog(she_id) ON DELETE CASCADE,
    ci_id       VARCHAR(40) NOT NULL,
    confidence  NUMERIC(4,3) DEFAULT 1.0,
    source      VARCHAR(20) DEFAULT 'inferred_from_sr',  -- "inferred_from_sr" | "manual" | "embedding"
    PRIMARY KEY (she_id, ci_id)
);
CREATE INDEX IF NOT EXISTS idx_she_ci_ci ON she_ci_mapping(ci_id);

-- ────────────────────────────────────────────────────────────────────────
-- 4. View: 활성 SHE (production search 용)
-- ────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW v_she_active AS
SELECT she_id, name, features, broadness_score, status, valid_from, valid_until
FROM she_catalog
WHERE status IN ('approved_auto', 'approved_manual')
  AND (valid_until IS NULL OR valid_until > CURRENT_DATE)
  AND superseded_by IS NULL;

COMMIT;
