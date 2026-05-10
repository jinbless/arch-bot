#!/usr/bin/env python3
"""DB → OWL v2: PostgreSQL kosha DB (19 tables) → Turtle. Pipe-A + Pipe-B + Option-C SubjectRole."""

import json
import re
import psycopg2
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD

# ─── Namespaces ───
CORE  = Namespace("https://cashtoss.info/ontology#")
LAW   = Namespace("https://cashtoss.info/ontology/law#")
SR    = Namespace("https://cashtoss.info/ontology/sr#")
PEN   = Namespace("https://cashtoss.info/ontology/penalty#")
RISK  = Namespace("https://cashtoss.info/ontology/risk#")
HAZ   = Namespace("https://cashtoss.info/ontology/risk/hazard#")
GUIDE = Namespace("https://cashtoss.info/ontology/guide#")
AGENT = Namespace("https://cashtoss.info/ontology/risk/agent#")
CTX   = Namespace("https://cashtoss.info/ontology/risk/context#")
SHE   = Namespace("https://cashtoss.info/ontology/risk/situation#")

# ─── Faceted code → OWL individual URI mappings ───
ACCIDENT_TYPE_MAP = {
    "FALL": HAZ.Fall, "SLIP": HAZ.Slip, "COLLISION": HAZ.Collision,
    "FALLING_OBJECT": HAZ.FallingObject, "CRUSH": HAZ.Crush, "CUT": HAZ.Cut,
    "COLLAPSE": HAZ.Collapse, "ERGONOMIC": HAZ.Ergonomic,
    "REPETITIVE": HAZ.Ergonomic, "HEAVY_LIFTING": HAZ.Ergonomic, "POSTURE": HAZ.Ergonomic,
}
AGENT_MAP = {
    "CHEMICAL": AGENT.Chemical, "DUST": AGENT.Dust, "TOXIC": AGENT.Toxic,
    "CORROSION": AGENT.Corrosion, "RADIATION": AGENT.Radiation, "FIRE": AGENT.Fire,
    "ELECTRICITY": AGENT.Electricity, "ARC_FLASH": AGENT.ArcFlash,
    "NOISE": AGENT.Noise, "HEAT_COLD": AGENT.HeatCold, "BIOLOGICAL": AGENT.Biological,
}
CONTEXT_MAP = {
    "SCAFFOLD": CTX.Scaffold, "CONFINED_SPACE": CTX.ConfinedSpace,
    "EXCAVATION": CTX.Excavation, "MACHINE": CTX.Machine,
    "VEHICLE": CTX.Vehicle, "CRANE": CTX.Crane, "CONVEYOR": CTX.Conveyor,
    "ROBOT": CTX.Robot, "CONSTRUCTION_EQUIP": CTX.ConstructionEquip,
    "RAIL": CTX.Rail, "PRESSURE_VESSEL": CTX.PressureVessel,
    "STEELWORK": CTX.Steelwork, "MATERIAL_HANDLING": CTX.MaterialHandling,
}

DB_PARAMS = dict(dbname="kosha", user="kosha", password="1229", host="localhost")

# ─── Mappings ───
MODALITY_MAP = {
    "OBLIGATION": CORE.Obligation, "PROHIBITION": CORE.Prohibition,
    "PERMISSION": CORE.Permission, "EXEMPTION": CORE.Exemption,
    "DEFINITION": CORE.Definition,
}
REQTYPE_MAP = {
    "PROCEDURAL": SR.Procedural, "PHYSICAL_PROTECTION": SR.PhysicalProtection,
    "EQUIPMENT_STANDARD": SR.EquipmentStandard, "MANAGEMENT_SYSTEM": SR.ManagementSystem,
    "ENVIRONMENTAL": SR.Environmental, "PPE_REQUIREMENT": SR.PPERequirement,
    "EMERGENCY_RESPONSE": SR.EmergencyResponse, "TRAINING": SR.Training,
}
BINDING_MAP = {
    "MANDATORY": CORE.Mandatory, "RECOMMENDED": CORE.Recommended, "INFORMATIVE": CORE.Informative,
}

# ─── Option-C SubjectRole 3-tier mapping ───
SUBJECT_MAP = {
    "사업주": CORE.Employer,
    "근로자": CORE.Worker,
    "감시인": CORE.Supervisor,
    "화재감시자": CORE.FireWatcher,
    "운전자": CORE.Driver,
    "굴착기계등의 운전자": CORE.ExcavationDriver,
    "고용노동부장관": CORE.GovernmentOfficial,
    "건축물·설비의 소유주 또는 임차인 등": CORE.BuildingOwner,
    "물건의 수거ㆍ배달 등을 중개하는 자": CORE.DeliveryBroker,
    "이동통신단말장치로 물건의 수거ㆍ배달 등을 중개하는 자": CORE.DeliveryBroker,
    "특수형태근로종사자의 노무를 제공받는 자": CORE.SpecialEmployer,
    "금지유해물질을 시험ㆍ연구 또는 검사 목적으로 제조하거나 사용하는 자": CORE.DutyHolder,
}

SEVERITY_KEYWORDS = {
    "5년 이하의 징역 또는 5천만원": 5, "3년 이하의 징역 또는 3천만원": 4,
    "7년 이하의 징역 또는 1억원": 6, "1년 이상의 징역 또는 10억원": 7,
}

PENALTY_CONDITION_MAP = {
    "violation_employer": (PEN.SimpleViolation, CORE.Employer),
    "violation_contractor": (PEN.SimpleViolation, CORE.Contractor),
    "death": (PEN.Death, CORE.Employer),
    "seriousAccident": (PEN.SeriousAccident, CORE.Employer),
}

def severity_from_text(text):
    if not text: return None
    for kw, score in SEVERITY_KEYWORDS.items():
        if kw in text: return score
    return 3

def first_article_ref(text):
    if not text:
        return None
    match = re.search(r"제\d+조", text)
    return match.group(0) if match else None

def penalty_article_from_law_text(text):
    article_ref = first_article_ref(text)
    if not article_ref:
        return None
    if "중대재해" in text:
        return LAW[safe_uri_part(f"SADA_{article_ref}")]
    if "산업안전보건법" in text:
        return LAW[safe_uri_part(f"OSHA_{article_ref}")]
    return None

def delegated_from_law_text(text):
    if not text:
        return None
    for article_ref in ["제38조", "제39조", "제63조"]:
        if article_ref in text:
            return LAW[safe_uri_part(f"OSHA_{article_ref}")]
    return None

def add_penalty_condition(add, rule_uri, ident, san_type_key):
    outcome_uri, subject_role_uri = PENALTY_CONDITION_MAP[san_type_key]
    condition_uri = PEN[safe_uri_part(f"Condition_{ident}_{san_type_key}")]
    add(condition_uri, RDF.type, PEN.PenaltyCondition)
    add(rule_uri, PEN.hasCondition, condition_uri)
    add(condition_uri, PEN.requiresAccidentOutcome, outcome_uri)
    add(condition_uri, PEN.requiresSubjectRole, subject_role_uri)
    return condition_uri

def safe_uri_part(s):
    return re.sub(r"[^\w-]", "_", s)

def parse_section(section_str):
    if not section_str: return []
    parts = [p.strip() for p in section_str.split(">")]
    result = []
    for p in parts:
        m = re.match(r"(편|장|절|관)(\d+)\s*(.*)", p)
        if m:
            level, num, label = m.groups()
            result.append((level, num, label.strip()))
    return result

def build_structure_uri(parsed, idx):
    parts = []
    for i in range(idx + 1):
        level, num, _ = parsed[i]
        parts.append(f"{level}{num}")
    return LAW[safe_uri_part("_".join(parts))]

LEVEL_TO_CLASS = {"편": LAW.Part, "장": LAW.Chapter, "절": LAW.Section, "관": LAW.Subsection}
LEVEL_TO_PROP = {"편": LAW.belongsToPart, "장": LAW.belongsToChapter, "절": LAW.belongsToSection, "관": LAW.belongsToSubsection}


def main():
    g = Graph()
    for prefix, ns in [
        ("core", CORE), ("law", LAW), ("sr", SR), ("pen", PEN),
        ("risk", RISK), ("haz", HAZ), ("agent", AGENT), ("ctx", CTX),
        ("she", SHE), ("guide", GUIDE), ("owl", OWL),
    ]:
        g.bind(prefix, ns)

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    triple_count = 0
    structure_cache = {}

    def add(s, p, o):
        nonlocal triple_count
        g.add((s, p, o))
        triple_count += 1

    # ═══════════════════════════════════════════
    # PIPE-A TABLES (1~6)
    # ═══════════════════════════════════════════

    # 1. Articles
    print("[1/15] Articles...")
    cur.execute("SELECT law_type, article_code, title, full_text, deleted, section, paragraph_count FROM articles")
    for row in cur.fetchall():
        law_type, art_code, title, full_text, deleted, section, para_count = row
        uri = LAW[safe_uri_part(f"{law_type}_{art_code}")]
        add(uri, RDF.type, LAW.Article)
        add(uri, LAW.articleCode, Literal(art_code, datatype=XSD.string))
        add(uri, LAW.hasLawType, LAW[safe_uri_part(f"LawType_{law_type}")])
        if title: add(uri, CORE.title, Literal(title, datatype=XSD.string))
        if full_text: add(uri, LAW.fullText, Literal(full_text, datatype=XSD.string))
        if deleted is not None: add(uri, LAW.isDeleted, Literal(deleted, datatype=XSD.boolean))
        if para_count is not None: add(uri, LAW.paragraphCount, Literal(para_count, datatype=XSD.integer))
        if section:
            parsed = parse_section(section)
            for idx, (level, num, label) in enumerate(parsed):
                struct_uri = build_structure_uri(parsed, idx)
                if struct_uri not in structure_cache:
                    structure_cache[struct_uri] = True
                    add(struct_uri, RDF.type, LEVEL_TO_CLASS[level])
                    add(struct_uri, LAW.structureLabel, Literal(f"{level}{num} {label}", datatype=XSD.string))
                    add(struct_uri, RDFS.label, Literal(f"{level}{num} {label}", lang="ko"))
                    if idx > 0: add(struct_uri, LAW.hasParentStructure, build_structure_uri(parsed, idx - 1))
                prop = LEVEL_TO_PROP.get(level)
                if prop: add(uri, prop, struct_uri)

    # 2. NormStatements
    print("[2/15] NormStatements...")
    cur.execute("SELECT identifier, article_code, law_id, paragraph_ref, text, has_modality, has_subject_role, has_action, has_object, has_condition, has_sanction, has_modification_link FROM norm_statements")
    for row in cur.fetchall():
        ident, art_code, law_id, para_ref, text, modality, subject_role, action, obj, condition, sanction, mod_link = row
        uri = LAW[safe_uri_part(ident)]
        add(uri, RDF.type, LAW.NormStatement)
        add(uri, CORE.identifier, Literal(ident, datatype=XSD.string))
        if text: add(uri, CORE.text, Literal(text, datatype=XSD.string))
        if para_ref: add(uri, LAW.paragraphRef, Literal(para_ref, datatype=XSD.string))
        source_article_uri = LAW[safe_uri_part(f"{law_id}_{art_code}")] if art_code and law_id else None
        if source_article_uri: add(uri, LAW.hasSourceArticle, source_article_uri)
        if modality and modality in MODALITY_MAP: add(uri, LAW.hasModality, MODALITY_MAP[modality])
        if subject_role:
            role_uri = SUBJECT_MAP.get(subject_role)
            if role_uri:
                add(uri, LAW.hasSubjectRole, role_uri)
            else:
                role_ind = CORE[safe_uri_part(f"Role_{subject_role}")]
                add(role_ind, RDF.type, CORE.SubjectRole)
                add(role_ind, RDFS.label, Literal(subject_role, lang="ko"))
                add(role_ind, RDFS.comment, Literal("자동 추출된 주체 역할. DutyHolder/ProtectedPerson/RegulatoryAuthority 분류 검토 필요.", lang="ko"))
                add(uri, LAW.hasSubjectRole, role_ind)
        if action: add(uri, LAW.hasAction, Literal(action, datatype=XSD.string))
        if obj: add(uri, LAW.hasObject, Literal(obj, datatype=XSD.string))
        if condition:
            cond = condition if isinstance(condition, dict) else json.loads(condition)
            if cond.get("text"): add(uri, LAW.conditionText, Literal(cond["text"], datatype=XSD.string))
            if cond.get("conditionType"): add(uri, LAW.conditionType, Literal(cond["conditionType"], datatype=XSD.string))
        if sanction:
            san = sanction if isinstance(sanction, dict) else json.loads(sanction)
            crim = san.get("criminal")
            if crim:
                for san_type_key in ["violation_employer", "violation_contractor", "death", "seriousAccident"]:
                    san_data = crim.get(san_type_key)
                    if san_data and isinstance(san_data, dict):
                        san_uri = PEN[safe_uri_part(f"Sanction_{ident}_{san_type_key}")]
                        add(san_uri, RDF.type, PEN.CriminalSanction)
                        penalty_text = san_data.get("penalty") or san_data.get("death") or san_data.get("injury")
                        if penalty_text:
                            add(san_uri, PEN.penaltyDescription, Literal(penalty_text, datatype=XSD.string))
                            sev = severity_from_text(penalty_text)
                            if sev: add(san_uri, PEN.severityScore, Literal(sev, datatype=XSD.integer))
                        basis_text = san_data.get("law")
                        rule_uri = PEN[safe_uri_part(f"PenaltyRule_{ident}_{san_type_key}")]
                        add(rule_uri, RDF.type, PEN.PenaltyRule)
                        add(rule_uri, PEN.violatedNorm, uri)
                        add(uri, PEN.hasPenaltyRule, rule_uri)
                        add(rule_uri, PEN.hasSanction, san_uri)
                        add_penalty_condition(add, rule_uri, ident, san_type_key)
                        if source_article_uri: add(rule_uri, PEN.violatedArticle, source_article_uri)
                        delegated_from = delegated_from_law_text(basis_text)
                        if delegated_from: add(rule_uri, PEN.delegatedFrom, delegated_from)
                        penalty_article = penalty_article_from_law_text(basis_text)
                        if penalty_article: add(rule_uri, PEN.penaltyArticle, penalty_article)
                        if basis_text: add(rule_uri, PEN.penaltyBasisText, Literal(basis_text, datatype=XSD.string))
        if mod_link:
            ml = mod_link if isinstance(mod_link, dict) else json.loads(mod_link)
            target_ns = ml.get("modifiesNS")
            if target_ns: add(uri, LAW.modifies, LAW[safe_uri_part(target_ns)])

    # 4. SafetyRequirements
    print("[3/15] SafetyRequirements...")
    cur.execute("SELECT identifier, title, text, requirement_type, binding_force, addresses_hazard, accident_types, hazardous_agents, work_contexts FROM safety_requirements")
    for row in cur.fetchall():
        ident, title, text, req_type, binding, hazards, acc_types, haz_agents, work_ctxs = row
        uri = SR[safe_uri_part(ident)]
        add(uri, RDF.type, SR.SafetyRequirement)
        add(uri, CORE.identifier, Literal(ident, datatype=XSD.string))
        if title: add(uri, CORE.title, Literal(title, datatype=XSD.string))
        if text: add(uri, CORE.text, Literal(text, datatype=XSD.string))
        if req_type and req_type in REQTYPE_MAP: add(uri, SR.hasRequirementType, REQTYPE_MAP[req_type])
        if binding and binding in BINDING_MAP: add(uri, SR.hasBindingForce, BINDING_MAP[binding])
        if hazards:
            h_list = hazards if isinstance(hazards, list) else json.loads(hazards)
            for h in h_list:
                feature_uri = HAZ[h]
                add(uri, SR.addressesHazard, feature_uri)
                add(uri, SR.addressesFeature, feature_uri)
        # Faceted axes
        if acc_types:
            a_list = acc_types if isinstance(acc_types, list) else json.loads(acc_types)
            for a in a_list:
                if a in ACCIDENT_TYPE_MAP:
                    feature_uri = ACCIDENT_TYPE_MAP[a]
                    add(uri, SR.addressesAccidentType, feature_uri)
                    add(uri, SR.addressesFeature, feature_uri)
        if haz_agents:
            ag_list = haz_agents if isinstance(haz_agents, list) else json.loads(haz_agents)
            for ag in ag_list:
                if ag in AGENT_MAP:
                    feature_uri = AGENT_MAP[ag]
                    add(uri, SR.addressesAgent, feature_uri)
                    add(uri, SR.addressesFeature, feature_uri)
        if work_ctxs:
            c_list = work_ctxs if isinstance(work_ctxs, list) else json.loads(work_ctxs)
            for c in c_list:
                if c in CONTEXT_MAP:
                    feature_uri = CONTEXT_MAP[c]
                    add(uri, SR.inWorkContext, feature_uri)
                    add(uri, SR.addressesFeature, feature_uri)

    # 5. SR-NS Mapping
    print("[4/15] SR-NS Mapping...")
    cur.execute("SELECT sr_id, ns_id FROM sr_ns_mapping")
    for sr_id, ns_id in cur.fetchall():
        add(SR[safe_uri_part(sr_id)], SR.derivedFromNS, LAW[safe_uri_part(ns_id)])

    # 6. SR-Article Mapping
    print("[5/15] SR-Article Mapping...")
    cur.execute("SELECT sr_id, law_type, article_code FROM sr_article_mapping")
    for sr_id, law_type, art_code in cur.fetchall():
        add(SR[safe_uri_part(sr_id)], SR.appliesToArticle, LAW[safe_uri_part(f"{law_type}_{art_code}")])

    # ═══════════════════════════════════════════
    # PIPE-B TABLES (7~15)
    # ═══════════════════════════════════════════

    # 7. KoshaGuides
    print("[6/15] KoshaGuides...")
    cur.execute("SELECT guide_code, short_code, title, domain FROM kosha_guides")
    for row in cur.fetchall():
        guide_code, short_code, title, domain = row
        uri = GUIDE[safe_uri_part(guide_code)]
        add(uri, RDF.type, GUIDE.KoshaGuide)
        add(uri, GUIDE.guideCode, Literal(guide_code, datatype=XSD.string))
        if short_code: add(uri, GUIDE.shortCode, Literal(short_code, datatype=XSD.string))
        if title: add(uri, CORE.title, Literal(title, datatype=XSD.string))
        if domain: add(uri, GUIDE.domain, Literal(domain, datatype=XSD.string))

    # 8. ChecklistItems
    print("[7/15] ChecklistItems...")
    cur.execute("SELECT identifier, text, guide_context, additional_detail, work_process_phase, binding_force, requirement_type, source_section, source_guide, accident_types, hazardous_agents, work_contexts FROM checklist_items")
    for row in cur.fetchall():
        ident, text, guide_ctx, detail, wp_phase, binding, req_type, src_section, src_guide, ci_acc, ci_agents, ci_ctxs = row
        uri = GUIDE[safe_uri_part(ident)]
        add(uri, RDF.type, GUIDE.ChecklistItem)
        add(uri, CORE.identifier, Literal(ident, datatype=XSD.string))
        if text: add(uri, CORE.text, Literal(text, datatype=XSD.string))
        if guide_ctx: add(uri, GUIDE.guideContext, Literal(guide_ctx, datatype=XSD.string))
        if detail: add(uri, GUIDE.additionalDetail, Literal(detail, datatype=XSD.string))
        if wp_phase: add(uri, GUIDE.workProcessPhase, Literal(wp_phase, datatype=XSD.string))
        if binding and binding in BINDING_MAP: add(uri, SR.hasBindingForce, BINDING_MAP[binding])
        if req_type and req_type in REQTYPE_MAP: add(uri, SR.hasRequirementType, REQTYPE_MAP[req_type])
        if src_section: add(uri, GUIDE.sourceSection, Literal(src_section, datatype=XSD.string))
        if src_guide:
            add(uri, GUIDE.sourceGuide, Literal(src_guide, datatype=XSD.string))
            add(GUIDE[safe_uri_part(src_guide)], GUIDE.hasChecklistItem, uri)
        # CI faceted axes
        if ci_acc:
            a_list = ci_acc if isinstance(ci_acc, list) else json.loads(ci_acc)
            for a in a_list:
                if a in ACCIDENT_TYPE_MAP: add(uri, GUIDE.ciAddressesAccidentType, ACCIDENT_TYPE_MAP[a])
        if ci_agents:
            ag_list = ci_agents if isinstance(ci_agents, list) else json.loads(ci_agents)
            for ag in ag_list:
                if ag in AGENT_MAP: add(uri, GUIDE.ciAddressesAgent, AGENT_MAP[ag])
        if ci_ctxs:
            c_list = ci_ctxs if isinstance(ci_ctxs, list) else json.loads(ci_ctxs)
            for c in c_list:
                if c in CONTEXT_MAP: add(uri, GUIDE.ciInWorkContext, CONTEXT_MAP[c])

    # 9. CI-SR Mapping
    print("[8/15] CI-SR Mapping...")
    cur.execute("SELECT ci_id, sr_id FROM ci_sr_mapping")
    for ci_id, sr_id in cur.fetchall():
        add(GUIDE[safe_uri_part(ci_id)], GUIDE.basedOnSR, SR[safe_uri_part(sr_id)])

    # 10. DomainTerms
    print("[9/15] DomainTerms...")
    cur.execute("SELECT identifier, term, definition, source_guide, source_section FROM domain_terms")
    for row in cur.fetchall():
        ident, term, defn, src_guide, src_section = row
        uri = GUIDE[safe_uri_part(ident)]
        add(uri, RDF.type, GUIDE.DomainTerm)
        add(uri, CORE.identifier, Literal(ident, datatype=XSD.string))
        if term: add(uri, GUIDE.termName, Literal(term, datatype=XSD.string))
        if defn: add(uri, GUIDE.definition, Literal(defn, datatype=XSD.string))
        if src_guide:
            add(uri, GUIDE.sourceGuide, Literal(src_guide, datatype=XSD.string))
            add(GUIDE[safe_uri_part(src_guide)], GUIDE.hasDomainTerm, uri)
        if src_section: add(uri, GUIDE.sourceSection, Literal(src_section, datatype=XSD.string))

    # 11. WorkProcesses
    print("[10/15] WorkProcesses...")
    cur.execute("SELECT identifier, process_order, process_name, safety_measures, source_guide, source_section FROM work_processes")
    for row in cur.fetchall():
        ident, order, name, measures, src_guide, src_section = row
        uri = GUIDE[safe_uri_part(ident)]
        add(uri, RDF.type, GUIDE.WorkProcess)
        add(uri, CORE.identifier, Literal(ident, datatype=XSD.string))
        if order is not None: add(uri, GUIDE.processOrder, Literal(order, datatype=XSD.integer))
        if name: add(uri, GUIDE.processName, Literal(name, datatype=XSD.string))
        if measures: add(uri, GUIDE.safetyMeasures, Literal(measures, datatype=XSD.string))
        if src_guide:
            add(uri, GUIDE.sourceGuide, Literal(src_guide, datatype=XSD.string))
            add(GUIDE[safe_uri_part(src_guide)], GUIDE.hasWorkProcess, uri)
        if src_section: add(uri, GUIDE.sourceSection, Literal(src_section, datatype=XSD.string))

    # 12. WP-SR Mapping + WP-PPE
    print("[11/15] WP-SR Mapping + WP-PPE...")
    cur.execute("SELECT wp_id, sr_id FROM wp_sr_mapping")
    for wp_id, sr_id in cur.fetchall():
        add(GUIDE[safe_uri_part(wp_id)], GUIDE.relatedSR, SR[safe_uri_part(sr_id)])
    cur.execute("SELECT wp_id, ppe_type FROM wp_ppe")
    for wp_id, ppe_type in cur.fetchall():
        add(GUIDE[safe_uri_part(wp_id)], GUIDE.ppeType, Literal(ppe_type, datatype=XSD.string))

    # 13. EquipmentSpecs + ES-SR
    print("[12/15] EquipmentSpecs + ES-SR...")
    cur.execute("SELECT identifier, equipment_name, source_guide, source_section FROM equipment_specs")
    for row in cur.fetchall():
        ident, eq_name, src_guide, src_section = row
        uri = GUIDE[safe_uri_part(ident)]
        add(uri, RDF.type, GUIDE.EquipmentSpec)
        add(uri, CORE.identifier, Literal(ident, datatype=XSD.string))
        if eq_name: add(uri, GUIDE.equipmentName, Literal(eq_name, datatype=XSD.string))
        if src_guide:
            add(uri, GUIDE.sourceGuide, Literal(src_guide, datatype=XSD.string))
            add(GUIDE[safe_uri_part(src_guide)], GUIDE.hasEquipmentSpec, uri)
        if src_section: add(uri, GUIDE.sourceSection, Literal(src_section, datatype=XSD.string))
    cur.execute("SELECT es_id, sr_id FROM es_sr_mapping")
    for es_id, sr_id in cur.fetchall():
        add(GUIDE[safe_uri_part(es_id)], GUIDE.specForSR, SR[safe_uri_part(sr_id)])

    # 14. DocumentRequirements + DR-SR
    print("[13/15] DocumentRequirements + DR-SR...")
    cur.execute("SELECT identifier, document_type, title, source_guide, source_section FROM document_requirements")
    for row in cur.fetchall():
        ident, doc_type, title, src_guide, src_section = row
        uri = GUIDE[safe_uri_part(ident)]
        add(uri, RDF.type, GUIDE.DocumentRequirement)
        add(uri, CORE.identifier, Literal(ident, datatype=XSD.string))
        if doc_type: add(uri, GUIDE.documentType, Literal(doc_type, datatype=XSD.string))
        if title: add(uri, CORE.title, Literal(title, datatype=XSD.string))
        if src_guide:
            add(uri, GUIDE.sourceGuide, Literal(src_guide, datatype=XSD.string))
            add(GUIDE[safe_uri_part(src_guide)], GUIDE.hasDocumentRequirement, uri)
        if src_section: add(uri, GUIDE.sourceSection, Literal(src_section, datatype=XSD.string))
    cur.execute("SELECT dr_id, sr_id FROM dr_sr_mapping")
    for dr_id, sr_id in cur.fetchall():
        add(GUIDE[safe_uri_part(dr_id)], GUIDE.docForSR, SR[safe_uri_part(sr_id)])

    # 15. DT-SR Mapping
    print("[14/15] DT-SR Mapping...")
    cur.execute("SELECT dt_id, sr_id FROM dt_sr_mapping")
    for dt_id, sr_id in cur.fetchall():
        add(GUIDE[safe_uri_part(dt_id)], GUIDE.termNameForSR, SR[safe_uri_part(sr_id)])

    # 16. GuideInterLinks
    print("[15/15] GuideInterLinks...")
    cur.execute("SELECT source_guide, referenced_guide, reference_type, reference_text FROM guide_inter_links")
    for row in cur.fetchall():
        src_guide, ref_guide, ref_type, ref_text = row
        src_uri = GUIDE[safe_uri_part(src_guide)]
        ref_uri = GUIDE[safe_uri_part(ref_guide)]
        add(src_uri, GUIDE.referencesGuide, ref_uri)
        link_uri = GUIDE[safe_uri_part(f"link_{src_guide}_{ref_guide}")]
        add(link_uri, RDF.type, GUIDE.GuideInterLink)
        add(link_uri, GUIDE.linkSource, src_uri)
        add(link_uri, GUIDE.linkTarget, ref_uri)
        add(link_uri, GUIDE.referenceType, Literal(ref_type, datatype=XSD.string))
        if ref_text:
            add(link_uri, GUIDE.referenceText, Literal(ref_text, datatype=XSD.string))

    cur.close()
    conn.close()

    import os
    output = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kosha-instances.ttl")
    g.serialize(destination=output, format="turtle")
    print(f"\nDone. {triple_count} triples → {output}")


if __name__ == "__main__":
    main()


