-- KOSHA 온톨로지 v2 — Pipe A PostgreSQL 스키마
-- SQLite schema.sql → PostgreSQL 변환
-- 5개 법령 지원: RULE, OSHA, SADA, DECREE, ENFORCE
-- v2: criminal/administrative 분리 구조

-- 조문 원문
CREATE TABLE IF NOT EXISTS articles (
    law_type        VARCHAR(10) NOT NULL CHECK(law_type IN ('RULE','OSHA','SADA','DECREE','ENFORCE')),
    article_code    VARCHAR(20) NOT NULL,
    title           TEXT NOT NULL,
    full_text       TEXT NOT NULL,
    deleted         BOOLEAN NOT NULL DEFAULT FALSE,
    section         TEXT,
    paragraph_count INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (law_type, article_code)
);

-- 벌칙 경로 (RULE 조문만 대상)
CREATE TABLE IF NOT EXISTS penalty_routes (
    law_type                VARCHAR(10) NOT NULL DEFAULT 'RULE'
                            CHECK(law_type = 'RULE'),
    article_code            VARCHAR(20) NOT NULL PRIMARY KEY,
    title                   TEXT NOT NULL,
    delegated_from          VARCHAR(20),
    has_penalty             BOOLEAN NOT NULL DEFAULT FALSE,
    has_administrative_fine BOOLEAN NOT NULL DEFAULT FALSE,
    -- criminal (형사벌)
    criminal_employer_law       TEXT,
    criminal_employer_penalty   TEXT,
    criminal_contractor_law     TEXT,
    criminal_contractor_penalty TEXT,
    criminal_death_law          TEXT,
    criminal_death_penalty      TEXT,
    criminal_serious_law        TEXT,
    criminal_serious_death      TEXT,
    criminal_serious_injury     TEXT,
    -- administrative (과태료)
    admin_law               TEXT,
    admin_max_fine           TEXT,
    admin_fine_table_ref     TEXT,
    admin_osha_article_ref   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (law_type, article_code) REFERENCES articles(law_type, article_code)
);

-- 규범문장 (Step 2 이후 적재)
CREATE TABLE IF NOT EXISTS norm_statements (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY,
    article_code    VARCHAR(20) NOT NULL,
    law_id          VARCHAR(10) NOT NULL CHECK(law_id IN ('RULE','OSHA','SADA','DECREE','ENFORCE')),
    paragraph_ref   TEXT NOT NULL,
    text            TEXT NOT NULL CHECK(length(text) > 0),
    has_modality    VARCHAR(15) NOT NULL CHECK(has_modality IN (
        'OBLIGATION','PROHIBITION','PERMISSION','POWER','EXEMPTION','DEFINITION'
    )),
    has_subject_role TEXT,
    has_action       TEXT,
    has_object       TEXT,
    has_condition    JSONB,
    has_sanction     JSONB,
    has_modification_link JSONB,
    role_guidance    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (law_id, article_code) REFERENCES articles(law_type, article_code)
);

-- ══════════════════════════════════════════════════════════
-- Phase 2: 안전요구사항 (Layer 4 허브)
-- ══════════════════════════════════════════════════════════

-- 안전요구사항
CREATE TABLE IF NOT EXISTS safety_requirements (
    identifier              VARCHAR(30) NOT NULL PRIMARY KEY
                            CHECK(identifier ~ '^SR-[A-Z_]+-[0-9]+$'),
    title                   TEXT NOT NULL,
    text                    TEXT NOT NULL CHECK(length(text) > 0),
    requirement_type        VARCHAR(25) NOT NULL CHECK(requirement_type IN (
        'PHYSICAL_PROTECTION','PPE_REQUIREMENT','PROCEDURAL','TRAINING',
        'EQUIPMENT_STANDARD','ENVIRONMENTAL','MANAGEMENT_SYSTEM','EMERGENCY_RESPONSE'
    )),
    binding_force           VARCHAR(15) NOT NULL DEFAULT 'MANDATORY'
                            CHECK(binding_force IN ('MANDATORY','RECOMMENDED')),
    addresses_hazard        JSONB,
    structural_requirements JSONB,
    has_sanction            JSONB,
    has_modification_link   JSONB,
    -- Phase 3 예약 (Layer 4 전방 호환, 모두 nullable)
    requires_ppe            JSONB,       -- PPERequirement[]
    has_corrective_action   JSONB,       -- CorrectiveAction[]
    has_incident_response   JSONB,       -- IncidentResponse[]
    applicable_industry     JSONB,       -- IndustryType[]
    hazard_assessment       JSONB,       -- HazardFactor[] with severity/likelihood/riskScore
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- L3→L4: mandatedBy (NS → SR) N:N 매핑
CREATE TABLE IF NOT EXISTS sr_ns_mapping (
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    ns_id   VARCHAR(30) NOT NULL REFERENCES norm_statements(identifier),
    PRIMARY KEY (sr_id, ns_id)
);

-- L4→L2: referencesArticle (SR → Article) N:N 매핑
CREATE TABLE IF NOT EXISTS sr_article_mapping (
    sr_id        VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    law_type     VARCHAR(10) NOT NULL,
    article_code VARCHAR(20) NOT NULL,
    PRIMARY KEY (sr_id, law_type, article_code),
    FOREIGN KEY (law_type, article_code) REFERENCES articles(law_type, article_code)
);

-- ══════════════════════════════════════════════════════════
-- 인덱스
-- ══════════════════════════════════════════════════════════

-- Phase 1 인덱스
CREATE INDEX IF NOT EXISTS idx_articles_law ON articles(law_type);
CREATE INDEX IF NOT EXISTS idx_articles_deleted ON articles(deleted);
CREATE INDEX IF NOT EXISTS idx_penalty_has ON penalty_routes(has_penalty);
CREATE INDEX IF NOT EXISTS idx_penalty_admin ON penalty_routes(has_administrative_fine);
CREATE INDEX IF NOT EXISTS idx_ns_article ON norm_statements(law_id, article_code);
CREATE INDEX IF NOT EXISTS idx_ns_modality ON norm_statements(has_modality);

-- Phase 2 인덱스
CREATE INDEX IF NOT EXISTS idx_sr_type ON safety_requirements(requirement_type);
CREATE INDEX IF NOT EXISTS idx_sr_ns_ns ON sr_ns_mapping(ns_id);
CREATE INDEX IF NOT EXISTS idx_sr_art_art ON sr_article_mapping(law_type, article_code);
