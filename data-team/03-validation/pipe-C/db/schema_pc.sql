-- Pipe-C: 교차검증 추가 테이블

-- 가이드 간 상호참조
CREATE TABLE IF NOT EXISTS guide_inter_links (
    source_guide    VARCHAR(20) NOT NULL,
    referenced_guide VARCHAR(20) NOT NULL,
    reference_type  VARCHAR(15) NOT NULL CHECK(reference_type IN ('explicit','implicit')),
    reference_text  TEXT,
    raw_match       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_guide, referenced_guide)
);

CREATE INDEX IF NOT EXISTS idx_gil_source ON guide_inter_links(source_guide);
CREATE INDEX IF NOT EXISTS idx_gil_ref ON guide_inter_links(referenced_guide);

-- DT canonical_id (ALTER)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'domain_terms' AND column_name = 'canonical_id'
    ) THEN
        ALTER TABLE domain_terms ADD COLUMN canonical_id VARCHAR(30);
    END IF;
END $$;
