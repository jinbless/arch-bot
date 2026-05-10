-- Pipe-B: Layer 5 KOSHA 가이드 구조
-- 12개 신규 테이블 + 9개 인덱스

-- 가이드 메타데이터
CREATE TABLE IF NOT EXISTS kosha_guides (
    guide_code      VARCHAR(20) NOT NULL PRIMARY KEY,
    short_code      VARCHAR(10) NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    domain          VARCHAR(1) NOT NULL CHECK(domain IN ('A','B','C','D','E')),
    sub_category    TEXT,
    total_pages     INTEGER,
    pdf_path        TEXT,
    parsed_json_path TEXT,
    ci_count        INTEGER NOT NULL DEFAULT 0,
    dt_count        INTEGER NOT NULL DEFAULT 0,
    wp_count        INTEGER NOT NULL DEFAULT 0,
    es_count        INTEGER NOT NULL DEFAULT 0,
    dr_count        INTEGER NOT NULL DEFAULT 0,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 체크리스트 항목 (Layer 5 핵심)
CREATE TABLE IF NOT EXISTS checklist_items (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^CI-[A-Z0-9]+-[0-9]+$'),
    text            TEXT NOT NULL CHECK(length(text) > 0),
    guide_context   TEXT,
    additional_detail TEXT,
    work_process_phase VARCHAR(100),
    binding_force   VARCHAR(15) NOT NULL
                    CHECK(binding_force IN ('MANDATORY','RECOMMENDED')),
    requirement_type VARCHAR(25)
                    CHECK(requirement_type IS NULL OR requirement_type IN (
                        'PHYSICAL_PROTECTION','PPE_REQUIREMENT','PROCEDURAL','TRAINING',
                        'EQUIPMENT_STANDARD','ENVIRONMENTAL','MANAGEMENT_SYSTEM','EMERGENCY_RESPONSE'
                    )),
    source_section  TEXT NOT NULL,
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    accident_types   JSONB,
    hazardous_agents JSONB,
    work_contexts    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- L5→L4: basedOn (CI → SR) N:N 매핑
CREATE TABLE IF NOT EXISTS ci_sr_mapping (
    ci_id   VARCHAR(30) NOT NULL REFERENCES checklist_items(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (ci_id, sr_id)
);

-- 도메인 용어
CREATE TABLE IF NOT EXISTS domain_terms (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^DT-[A-Z0-9]+-[0-9]+$'),
    term            TEXT NOT NULL CHECK(length(term) > 0),
    definition      TEXT NOT NULL CHECK(length(definition) > 0),
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    source_section  TEXT,
    hazardous_agents JSONB,
    work_contexts    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- DT → SR 연결 (선택적)
CREATE TABLE IF NOT EXISTS dt_sr_mapping (
    dt_id   VARCHAR(30) NOT NULL REFERENCES domain_terms(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (dt_id, sr_id)
);

-- 작업공정
CREATE TABLE IF NOT EXISTS work_processes (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^WP-[A-Z0-9]+-[0-9]+$'),
    process_order   INTEGER NOT NULL,
    process_name    TEXT NOT NULL CHECK(length(process_name) > 0),
    safety_measures TEXT,
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    source_section  TEXT,
    accident_types   JSONB,
    work_contexts    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- WP → SR 연결
CREATE TABLE IF NOT EXISTS wp_sr_mapping (
    wp_id   VARCHAR(30) NOT NULL REFERENCES work_processes(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (wp_id, sr_id)
);

-- WP → PPE 연결
CREATE TABLE IF NOT EXISTS wp_ppe (
    wp_id       VARCHAR(30) NOT NULL REFERENCES work_processes(identifier),
    ppe_type    VARCHAR(50) NOT NULL,
    PRIMARY KEY (wp_id, ppe_type)
);

-- 장비규격
CREATE TABLE IF NOT EXISTS equipment_specs (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^ES-[A-Z0-9]+-[0-9]+$'),
    equipment_name  TEXT NOT NULL CHECK(length(equipment_name) > 0),
    specifications  JSONB NOT NULL,
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    source_section  TEXT,
    work_contexts    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ES → SR 연결
CREATE TABLE IF NOT EXISTS es_sr_mapping (
    es_id   VARCHAR(30) NOT NULL REFERENCES equipment_specs(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (es_id, sr_id)
);

-- 문서요구사항
CREATE TABLE IF NOT EXISTS document_requirements (
    identifier      VARCHAR(30) NOT NULL PRIMARY KEY
                    CHECK(identifier ~ '^DR-[A-Z0-9]+-[0-9]+$'),
    document_type   VARCHAR(25) NOT NULL CHECK(document_type IN (
        'WORK_PLAN','RISK_ASSESSMENT','SAFETY_CHECKLIST',
        'MSDS','INCIDENT_REPORT','TRAINING_RECORD'
    )),
    title           TEXT NOT NULL CHECK(length(title) > 0),
    required_sections JSONB,
    source_guide    VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    source_section  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- DR → SR 연결
CREATE TABLE IF NOT EXISTS dr_sr_mapping (
    dr_id   VARCHAR(30) NOT NULL REFERENCES document_requirements(identifier),
    sr_id   VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    PRIMARY KEY (dr_id, sr_id)
);

-- 온톨로지 보강 후보: Guide/CI/WP/ES/DR/DT → risk:RiskFeature
-- LLM/규칙/교차증거 결과를 asserted 매핑과 분리해 저장한다.
CREATE TABLE IF NOT EXISTS guide_entity_feature_candidates (
    candidate_id    BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(10) NOT NULL CHECK(entity_type IN ('GUIDE','CI','WP','ES','DR','DT')),
    entity_id       VARCHAR(30) NOT NULL,
    guide_code      VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    axis            VARCHAR(25) NOT NULL CHECK(axis IN ('accident_type','hazardous_agent','work_context')),
    feature_code    VARCHAR(50) NOT NULL,
    confidence      NUMERIC(5,4) NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    evidence        TEXT NOT NULL CHECK(length(evidence) > 0),
    source_fields   JSONB NOT NULL DEFAULT '[]'::jsonb,
    method          VARCHAR(40) NOT NULL,
    review_status   VARCHAR(20) NOT NULL DEFAULT 'candidate'
                    CHECK(review_status IN ('candidate','asserted','rejected','needs_review')),
    non_llm_evidence_count INTEGER NOT NULL DEFAULT 0 CHECK(non_llm_evidence_count >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(entity_type, entity_id, axis, feature_code, method)
);

-- 온톨로지 보강 후보: Guide/CI/WP/ES/DR/DT → SafetyRequirement
-- confidence 0.88 이상 + 비LLM 증거 2개 이상만 asserted materialization 후보로 본다.
CREATE TABLE IF NOT EXISTS guide_sr_link_candidates (
    candidate_id    BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(10) NOT NULL CHECK(entity_type IN ('GUIDE','CI','WP','ES','DR','DT')),
    entity_id       VARCHAR(30) NOT NULL,
    guide_code      VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    sr_id           VARCHAR(30) NOT NULL REFERENCES safety_requirements(identifier),
    confidence      NUMERIC(5,4) NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    evidence        TEXT NOT NULL CHECK(length(evidence) > 0),
    source_fields   JSONB NOT NULL DEFAULT '[]'::jsonb,
    method          VARCHAR(40) NOT NULL,
    review_status   VARCHAR(20) NOT NULL DEFAULT 'candidate'
                    CHECK(review_status IN ('candidate','asserted','rejected','needs_review')),
    non_llm_evidence_count INTEGER NOT NULL DEFAULT 0 CHECK(non_llm_evidence_count >= 0),
    asserted        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(entity_type, entity_id, sr_id, method)
);

-- 온톨로지 보강 후보: 사진에서 실제로 보여야 하는 she:VisualTrigger 후보
CREATE TABLE IF NOT EXISTS guide_visual_trigger_candidates (
    trigger_id      BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(10) NOT NULL CHECK(entity_type IN ('GUIDE','CI','WP','ES','DR','DT')),
    entity_id       VARCHAR(30) NOT NULL,
    guide_code      VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    trigger_text    TEXT NOT NULL CHECK(length(trigger_text) > 0),
    cue_type        VARCHAR(30) NOT NULL DEFAULT 'other',
    confidence      NUMERIC(5,4) NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    evidence        TEXT NOT NULL CHECK(length(evidence) > 0),
    source_fields   JSONB NOT NULL DEFAULT '[]'::jsonb,
    method          VARCHAR(40) NOT NULL,
    review_status   VARCHAR(20) NOT NULL DEFAULT 'candidate'
                    CHECK(review_status IN ('candidate','asserted','rejected','needs_review')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(entity_type, entity_id, trigger_text, method)
);

-- Guide 사용경계 프로파일: 추천 후보/가드 신호용 materialized metadata
-- 법적 asserted 근거가 아니라 Guide-specific signal과 domain guard에만 사용한다.
CREATE TABLE IF NOT EXISTS guide_usage_profiles (
    guide_code                 VARCHAR(20) PRIMARY KEY REFERENCES kosha_guides(guide_code),
    profile_level              VARCHAR(20) NOT NULL DEFAULT 'general',
    domain_family              TEXT,
    usage_summary              TEXT NOT NULL CHECK(length(usage_summary) > 0),
    intended_workplaces        JSONB NOT NULL DEFAULT '[]'::jsonb,
    intended_tasks             JSONB NOT NULL DEFAULT '[]'::jsonb,
    observable_required_cues   JSONB NOT NULL DEFAULT '[]'::jsonb,
    negative_boundaries        JSONB NOT NULL DEFAULT '[]'::jsonb,
    procedure_role             VARCHAR(40) NOT NULL DEFAULT 'field_control',
    primary_work_process_ids   JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence                   TEXT NOT NULL CHECK(length(evidence) > 0),
    source_fields              JSONB NOT NULL DEFAULT '[]'::jsonb,
    method                     VARCHAR(40) NOT NULL,
    review_status              VARCHAR(20) NOT NULL DEFAULT 'candidate'
                              CHECK(review_status IN ('candidate','asserted','rejected','needs_review')),
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 가이드 인용 조문 매핑
CREATE TABLE IF NOT EXISTS guide_article_mapping (
    guide_code   VARCHAR(20) NOT NULL REFERENCES kosha_guides(guide_code),
    law_type     VARCHAR(10) NOT NULL,
    article_code VARCHAR(20) NOT NULL,
    PRIMARY KEY (guide_code, law_type, article_code),
    FOREIGN KEY (law_type, article_code) REFERENCES articles(law_type, article_code)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_ci_guide ON checklist_items(source_guide);
CREATE INDEX IF NOT EXISTS idx_ci_binding ON checklist_items(binding_force);
CREATE INDEX IF NOT EXISTS idx_ci_accident_types ON checklist_items USING GIN(accident_types);
CREATE INDEX IF NOT EXISTS idx_ci_hazardous_agents ON checklist_items USING GIN(hazardous_agents);
CREATE INDEX IF NOT EXISTS idx_ci_work_contexts ON checklist_items USING GIN(work_contexts);
CREATE INDEX IF NOT EXISTS idx_ci_sr_sr ON ci_sr_mapping(sr_id);
CREATE INDEX IF NOT EXISTS idx_dt_guide ON domain_terms(source_guide);
CREATE INDEX IF NOT EXISTS idx_dt_hazardous_agents ON domain_terms USING GIN(hazardous_agents);
CREATE INDEX IF NOT EXISTS idx_dt_work_contexts ON domain_terms USING GIN(work_contexts);
CREATE INDEX IF NOT EXISTS idx_wp_guide ON work_processes(source_guide);
CREATE INDEX IF NOT EXISTS idx_wp_accident_types ON work_processes USING GIN(accident_types);
CREATE INDEX IF NOT EXISTS idx_wp_work_contexts ON work_processes USING GIN(work_contexts);
CREATE INDEX IF NOT EXISTS idx_es_guide ON equipment_specs(source_guide);
CREATE INDEX IF NOT EXISTS idx_es_work_contexts ON equipment_specs USING GIN(work_contexts);
CREATE INDEX IF NOT EXISTS idx_dr_guide ON document_requirements(source_guide);
CREATE INDEX IF NOT EXISTS idx_guide_domain ON kosha_guides(domain);
CREATE INDEX IF NOT EXISTS idx_guide_art_art ON guide_article_mapping(law_type, article_code);
CREATE INDEX IF NOT EXISTS idx_gefc_entity ON guide_entity_feature_candidates(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_gefc_guide ON guide_entity_feature_candidates(guide_code);
CREATE INDEX IF NOT EXISTS idx_gefc_feature ON guide_entity_feature_candidates(axis, feature_code);
CREATE INDEX IF NOT EXISTS idx_gefc_status ON guide_entity_feature_candidates(review_status, confidence);
CREATE INDEX IF NOT EXISTS idx_gslc_entity ON guide_sr_link_candidates(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_gslc_guide ON guide_sr_link_candidates(guide_code);
CREATE INDEX IF NOT EXISTS idx_gslc_sr ON guide_sr_link_candidates(sr_id);
CREATE INDEX IF NOT EXISTS idx_gslc_status ON guide_sr_link_candidates(review_status, confidence);
CREATE INDEX IF NOT EXISTS idx_gvtc_entity ON guide_visual_trigger_candidates(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_gvtc_guide ON guide_visual_trigger_candidates(guide_code);
CREATE INDEX IF NOT EXISTS idx_gvtc_status ON guide_visual_trigger_candidates(review_status, confidence);
CREATE INDEX IF NOT EXISTS idx_gup_role ON guide_usage_profiles(procedure_role);
CREATE INDEX IF NOT EXISTS idx_gup_status ON guide_usage_profiles(review_status);
CREATE INDEX IF NOT EXISTS idx_gup_profile ON guide_usage_profiles(profile_level);
