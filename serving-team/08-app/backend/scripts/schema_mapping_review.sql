-- HITL Golden-Set Review — mapping_review_verdicts schema
--
-- GPT 인식 현장 → SR-위반 / Guide 매핑에 대한 reviewer 개별 판정(의견)을 저장한다.
-- 이 테이블은 **개별 의견의 원자료**이며 서빙을 절대 직접 변경하지 않는다(she_catalog.status /
-- v_she_active / PgGuideSrLinkCandidate.review_status 등 governance 게이트와는 분리). 합의→golden
-- (gold-truth-v2.jsonl)·서빙 반영은 build_gold_truth_v2.py + promote_*.py 게이트 단계에서만 일어난다.
--
-- 적재: import_mapping_review_xlsx.py (source='excel'), review_web/verdict_store.py (source='online')
--       둘 다 동일 upsert(ON CONFLICT(mapping_key, reviewer)) → 한 합의 계산으로 수렴.

BEGIN;

CREATE TABLE IF NOT EXISTS mapping_review_verdicts (
    verdict_id      BIGSERIAL PRIMARY KEY,
    analysis_id     VARCHAR(36) NOT NULL,        -- ohs_analysis_records.id (hard FK 미설정: 레코드 삭제 가능)
    mapping_kind    VARCHAR(8)  NOT NULL,        -- 'SR' | 'GUIDE'
    target_id       VARCHAR(60) NOT NULL,        -- sr_id 또는 guide_code
    -- 제안 pair의 안정 식별자: 재export/재import 시 중복 방지 키
    mapping_key     VARCHAR(160) NOT NULL,       -- '{analysis_id}:{mapping_kind}:{target_id}' (recall/scene은 별도 suffix)
    row_kind        VARCHAR(16) NOT NULL DEFAULT 'candidate',  -- 'candidate' | 'recall_addition' | 'scene'
    reviewer        VARCHAR(100) NOT NULL,       -- Excel 파일명 또는 online 세션에서
    verdict         VARCHAR(16),                 -- 'approve'|'reject'|'partial'|'uncertain' (recall/scene 행은 NULL 가능)
    corrected_value TEXT,                        -- 교정 sr_id/guide_code(들), 콤마구분 (verdict∈{reject,partial})
    reason_code     VARCHAR(40),                 -- domain_mismatch/wrong_section/over_broad/... (evaluation-baseline 분류 재사용)
    notes           TEXT,
    source          VARCHAR(12) NOT NULL DEFAULT 'excel',  -- 'excel' | 'online'
    source_file     TEXT,                        -- reviewer별 xlsx 파일명 또는 세션 id
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_mrv_kind    CHECK (mapping_kind IN ('SR', 'GUIDE', 'SCENE')),
    CONSTRAINT chk_mrv_rowkind CHECK (row_kind IN ('candidate', 'recall_addition', 'scene')),
    CONSTRAINT chk_mrv_verdict CHECK (verdict IS NULL OR verdict IN ('approve', 'reject', 'partial', 'uncertain')),
    -- reviewer×pair 1건 (재import = UPSERT)
    CONSTRAINT uq_mrv_key_reviewer UNIQUE (mapping_key, reviewer)
);

CREATE INDEX IF NOT EXISTS idx_mrv_analysis ON mapping_review_verdicts (analysis_id);
CREATE INDEX IF NOT EXISTS idx_mrv_key      ON mapping_review_verdicts (mapping_key);
CREATE INDEX IF NOT EXISTS idx_mrv_kind     ON mapping_review_verdicts (mapping_kind);
CREATE INDEX IF NOT EXISTS idx_mrv_reviewer ON mapping_review_verdicts (reviewer);

COMMIT;
