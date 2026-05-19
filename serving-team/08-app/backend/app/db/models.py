import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.database import Base


class PgKoshaGuide(Base):
    __tablename__ = "kosha_guides"
    __table_args__ = {"extend_existing": True}

    guide_code = Column(String(20), primary_key=True)
    short_code = Column(String(10), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    domain = Column(String(1), nullable=False)
    sub_category = Column(Text)
    total_pages = Column(Integer)
    ci_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgChecklistItem(Base):
    __tablename__ = "checklist_items"
    __table_args__ = {"extend_existing": True}

    identifier = Column(String(30), primary_key=True)
    text = Column(Text, nullable=False)
    guide_context = Column(Text)
    additional_detail = Column(Text)
    work_process_phase = Column(String(100))
    binding_force = Column(String(15), nullable=False)
    requirement_type = Column(String(25))
    source_section = Column(Text, nullable=False)
    source_guide = Column(String(20), nullable=False)
    accident_types = Column(JSONB)
    hazardous_agents = Column(JSONB)
    work_contexts = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgNormStatement(Base):
    __tablename__ = "norm_statements"
    __table_args__ = {"extend_existing": True}

    identifier = Column(String(30), primary_key=True)
    article_code = Column(String(20), nullable=False)
    law_id = Column(String(10), nullable=False)
    paragraph_ref = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    has_modality = Column(String(15), nullable=False)
    has_subject_role = Column(Text)
    has_action = Column(Text)
    has_object = Column(Text)
    has_condition = Column(JSONB)
    has_sanction = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgSafetyRequirement(Base):
    __tablename__ = "safety_requirements"
    __table_args__ = {"extend_existing": True}

    identifier = Column(String(30), primary_key=True)
    title = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    requirement_type = Column(String(25), nullable=False)
    binding_force = Column(String(15), nullable=False)
    addresses_hazard = Column(JSONB)
    has_sanction = Column(JSONB)
    applicable_industry = Column(JSONB)
    accident_types = Column(JSONB)
    hazardous_agents = Column(JSONB)
    work_contexts = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgArticle(Base):
    __tablename__ = "articles"
    __table_args__ = {"extend_existing": True}

    law_type = Column(String(10), primary_key=True)
    article_code = Column(String(20), primary_key=True)
    title = Column(Text, nullable=False)
    full_text = Column(Text, nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)
    section = Column(Text)
    paragraph_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgCiSrMapping(Base):
    __tablename__ = "ci_sr_mapping"
    __table_args__ = {"extend_existing": True}

    ci_id = Column(String(30), primary_key=True)
    sr_id = Column(String(30), primary_key=True)


class PgWorkProcess(Base):
    __tablename__ = "work_processes"
    __table_args__ = {"extend_existing": True}

    identifier = Column(String(30), primary_key=True)
    process_order = Column(Integer, nullable=False)
    process_name = Column(Text, nullable=False)
    safety_measures = Column(Text)
    source_guide = Column(String(20), nullable=False)
    source_section = Column(Text)
    accident_types = Column(JSONB)
    work_contexts = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgWpSrMapping(Base):
    __tablename__ = "wp_sr_mapping"
    __table_args__ = {"extend_existing": True}

    wp_id = Column(String(30), primary_key=True)
    sr_id = Column(String(30), primary_key=True)


class PgGuideUsageProfile(Base):
    __tablename__ = "guide_usage_profiles"
    __table_args__ = {"extend_existing": True}

    guide_code = Column(String(20), primary_key=True)
    baseline_id = Column(String(80), nullable=False, default="unknown")
    profile_level = Column(String(20), nullable=False, default="general")
    domain_family = Column(Text)
    usage_summary = Column(Text, nullable=False)
    intended_workplaces = Column(JSONB, nullable=False, default=list)
    intended_tasks = Column(JSONB, nullable=False, default=list)
    observable_required_cues = Column(JSONB, nullable=False, default=list)
    negative_boundaries = Column(JSONB, nullable=False, default=list)
    procedure_role = Column(String(40), nullable=False, default="field_control")
    photo_matchability = Column(String(40), nullable=False, default="photo_actionable")
    top_procedure_policy = Column(String(40), nullable=False, default="allow_photo_top")
    followup_policy = Column(String(40), nullable=False, default="none")
    primary_work_process_ids = Column(JSONB, nullable=False, default=list)
    classification_reason = Column(Text)
    evidence = Column(Text, nullable=False)
    source_fields = Column(JSONB, nullable=False, default=list)
    method = Column(String(40), nullable=False)
    review_status = Column(String(20), nullable=False, default="candidate")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PgGuideEntityFeatureCandidate(Base):
    __tablename__ = "guide_entity_feature_candidates"
    __table_args__ = {"extend_existing": True}

    candidate_id = Column(BigInteger, primary_key=True)
    entity_type = Column(String(10), nullable=False)
    entity_id = Column(String(30), nullable=False)
    guide_code = Column(String(20), nullable=False)
    axis = Column(String(25), nullable=False)
    feature_code = Column(String(50), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    evidence = Column(Text, nullable=False)
    source_fields = Column(JSONB)
    method = Column(String(40), nullable=False)
    review_status = Column(String(20), nullable=False)
    non_llm_evidence_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgGuideSrLinkCandidate(Base):
    __tablename__ = "guide_sr_link_candidates"
    __table_args__ = {"extend_existing": True}

    candidate_id = Column(BigInteger, primary_key=True)
    entity_type = Column(String(10), nullable=False)
    entity_id = Column(String(30), nullable=False)
    guide_code = Column(String(20), nullable=False)
    sr_id = Column(String(30), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    evidence = Column(Text, nullable=False)
    source_fields = Column(JSONB)
    method = Column(String(40), nullable=False)
    review_status = Column(String(20), nullable=False)
    non_llm_evidence_count = Column(Integer, nullable=False, default=0)
    asserted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgGuideVisualTriggerCandidate(Base):
    __tablename__ = "guide_visual_trigger_candidates"
    __table_args__ = {"extend_existing": True}

    trigger_id = Column(BigInteger, primary_key=True)
    entity_type = Column(String(10), nullable=False)
    entity_id = Column(String(30), nullable=False)
    guide_code = Column(String(20), nullable=False)
    trigger_text = Column(Text, nullable=False)
    cue_type = Column(String(30), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    evidence = Column(Text, nullable=False)
    source_fields = Column(JSONB)
    method = Column(String(40), nullable=False)
    review_status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PgSrArticleMapping(Base):
    __tablename__ = "sr_article_mapping"
    __table_args__ = {"extend_existing": True}

    sr_id = Column(String(30), primary_key=True)
    law_type = Column(String(10), primary_key=True)
    article_code = Column(String(20), primary_key=True)


class PgGuideArticleMapping(Base):
    __tablename__ = "guide_article_mapping"
    __table_args__ = {"extend_existing": True}

    guide_code = Column(String(20), primary_key=True)
    law_type = Column(String(10), primary_key=True)
    article_code = Column(String(20), primary_key=True)


class OhsAnalysisRecord(Base):
    __tablename__ = "ohs_analysis_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_type = Column(String(10), nullable=False)
    overall_risk_level = Column(String(20), nullable=False)
    summary = Column(Text, nullable=False)
    input_preview = Column(Text)
    image_path = Column(Text)
    result_json = Column(JSONB)
    gpt_free_hazards = Column(JSONB)
    coded_hazards = Column(JSONB)
    divergence_report = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OhsHazardCodeGap(Base):
    __tablename__ = "ohs_hazard_code_gaps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gap_type = Column(String(20), nullable=False)
    gpt_free_label = Column(Text)
    nearest_code = Column(String(30))
    forced_fit_note = Column(Text)
    occurrence_count = Column(Integer, nullable=False, default=1)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    sample_analysis_ids = Column(JSONB)
    promoted_to_code = Column(String(30))
    promoted_at = Column(DateTime(timezone=True))


class PgPenaltyRuleIndex(Base):
    """Phase G Sprint G.3 — penalty_rule_index materialized from kosha-instances.ttl.

    Ontology TBox: penalty:PenaltyRule + appliesTo/penaltyType/maxFine
    Source: ontology-team/06-reasoning/ontology/kosha-instances.ttl (TTL ABox)
    적재: import_penalty_to_pg.py (rdflib parse → PG UPSERT)
    Runtime: hazard_rule_engine._load_penalty_index PG SELECT 전환
    """
    __tablename__ = "penalty_rule_index"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    sr_id = Column(String(30), nullable=False, index=True)
    penalty_rule_id = Column(String(50), nullable=False, index=True)
    article_code = Column(String(20))
    sanction_type = Column(String(40))
    penalty_description = Column(Text)
    severity_score = Column(Integer)
    subject_role = Column(String(50))
    accident_outcome = Column(String(50))
    violated_norm_id = Column(String(50))
    violated_article_id = Column(String(20))
    delegated_from_article_id = Column(String(20))
    penalty_article_id = Column(String(20))
    basis_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PgPenaltyRoute(Base):
    """Phase G Sprint G.3 — penalty_routes (이미 PG에 존재, ORM 추가).

    Source: data-team/02-extraction/pipe-A/db/schema_pg.sql (Pipe-A 적재)
    Ontology TBox: penalty:PenaltyRule + appliesTo/penaltyType/maxFine
    Runtime 사용: app/services/hazard_rule_engine.py:_load_penalty_index (G.3 PG 전환)
    """
    __tablename__ = "penalty_routes"
    __table_args__ = {"extend_existing": True}

    article_code = Column(String(20), primary_key=True)
    has_penalty = Column(Boolean)
    criminal_employer_penalty = Column(Text)
    admin_max_fine = Column(Text)
    admin_fine_table_ref = Column(Text)


class PgGuideDomainIncompatibility(Base):
    """Phase G Sprint G.1 — guide_domain_incompatibilities materialized table.

    Ontology TBox: core:Incompatibility class + 5 metadata properties
    (kosha-ontology-v3-incompat-patch.ttl).

    Source JSON: data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json
    적재: serving-team/07-materialization/pg-sync-scripts/import_domain_incompatibilities_to_pg.py
    Runtime 사용: app/services/shadow_reasoner.py (PG SELECT, JSON fallback 유지)
    """
    __tablename__ = "guide_domain_incompatibilities"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_a = Column(String(100), nullable=False)            # industry EN code
    domain_b = Column(String(100), nullable=False)
    level = Column(String(20), nullable=False)                # 'vetted' | 'candidate'
    confidence = Column(Numeric(4, 3))                        # 0.000 ~ 1.000
    source = Column(String(50))                               # 'f32_axiom_miner' | 'manual' | ...
    reason = Column(Text)
    promoted_at = Column(DateTime(timezone=True))
    rollback_at = Column(DateTime(timezone=True))
    rollback_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


AnalysisRecord = OhsAnalysisRecord
KoshaGuide = PgKoshaGuide
NormStatement = PgNormStatement
