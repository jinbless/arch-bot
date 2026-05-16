#!/usr/bin/env python3
"""Validate the current KOSHA ontology and instance graph."""

from pathlib import Path
import sys

from rdflib import Graph, Namespace, RDF, RDFS


CORE = Namespace("https://cashtoss.info/ontology#")
LAW = Namespace("https://cashtoss.info/ontology/law#")
SR = Namespace("https://cashtoss.info/ontology/sr#")
PEN = Namespace("https://cashtoss.info/ontology/penalty#")
GUIDE = Namespace("https://cashtoss.info/ontology/guide#")
RISK = Namespace("https://cashtoss.info/ontology/risk#")
HAZ = Namespace("https://cashtoss.info/ontology/risk/hazard#")
AGENT = Namespace("https://cashtoss.info/ontology/risk/agent#")
CTX = Namespace("https://cashtoss.info/ontology/risk/context#")
SHE = Namespace("https://cashtoss.info/ontology/risk/situation#")
APP = Namespace("https://cashtoss.info/ontology/app#")

BASE = Path(__file__).resolve().parents[1]


def count_type(g: Graph, cls) -> int:
    return len(set(g.subjects(RDF.type, cls)))


def scalar_count(g: Graph, query: str) -> int:
    row = next(iter(g.query(query)))
    return int(row.cnt)


def main() -> int:
    g = Graph()
    print("Loading T-Box (OWL)...")
    g.parse(BASE / "kosha-ontology.owl", format="xml")
    print(f"  T-Box triples: {len(g)}")

    print("Loading A-Box (Turtle)...")
    g.parse(BASE / "kosha-instances.ttl", format="turtle")
    print(f"  Total triples: {len(g)}")

    she_data_path = BASE.parent / "data" / "she" / "she-instances-v1.ttl"
    if she_data_path.exists():
        print("Loading SHE patterns (Turtle)...")
        g.parse(she_data_path, format="turtle")
        print(f"  Total triples with SHE patterns: {len(g)}")

    all_pass = True

    print("\n=== Instance Counts ===")
    expected = {
        "Article": (LAW.Article, 1227),
        "NormStatement": (LAW.NormStatement, 1229),
        "SafetyRequirement": (SR.SafetyRequirement, 626),
        "PenaltyRule": (PEN.PenaltyRule, 4772),
        "KoshaGuide": (GUIDE.KoshaGuide, None),
        "ChecklistItem": (GUIDE.ChecklistItem, None),
        "DomainTerm": (GUIDE.DomainTerm, None),
        "WorkProcess": (GUIDE.WorkProcess, None),
        "EquipmentSpec": (GUIDE.EquipmentSpec, None),
        "DocumentRequirement": (GUIDE.DocumentRequirement, None),
    }
    for cls_name, (cls_uri, exp) in expected.items():
        actual = count_type(g, cls_uri)
        if exp is None:
            print(f"  [INFO] {cls_name}: {actual}")
            continue
        ok = actual == exp
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {cls_name}: {actual} (expected {exp})")

    print("\n=== Retired PenaltyRoute Model ===")
    retired_checks = {
        "PenaltyRoute instances": count_type(g, PEN.PenaltyRoute),
        "penaltyForArticle triples": len(list(g.triples((None, PEN.penaltyForArticle, None)))),
    }
    for name, actual in retired_checks.items():
        ok = actual == 0
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {actual} (expected 0)")

    print("\n=== Retired SeverityLevel Model ===")
    retired_severity_checks = {
        "SeverityLevel instances": count_type(g, PEN.SeverityLevel),
        "hasSeverityLevel triples": len(list(g.triples((None, PEN.hasSeverityLevel, None)))),
    }
    for name, actual in retired_severity_checks.items():
        ok = actual == 0
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {actual} (expected 0)")

    print("\n=== Schema Additions ===")
    schema_requirements = {
        "RISK RiskFeature class": (RISK.RiskFeature, RDF.type, None),
        "RISK RiskPattern class": (RISK.RiskPattern, RDF.type, None),
        "RISK hasFeature property": (RISK.hasFeature, RDF.type, None),
        "SR addressesFeature property": (SR.addressesFeature, RDF.type, None),
        "SHE SituationalHazardPattern class": (SHE.SituationalHazardPattern, RDF.type, None),
        "SHE VisualTrigger class": (SHE.VisualTrigger, RDF.type, None),
        "SHE hasVisualTrigger property": (SHE.hasVisualTrigger, RDF.type, None),
        "SHE relatedGuide property": (SHE.relatedGuide, RDF.type, None),
        "SHE relatedChecklistCue property": (SHE.relatedChecklistCue, RDF.type, None),
        "PenaltyCondition class": (PEN.PenaltyCondition, RDF.type, None),
        "AccidentOutcome class": (PEN.AccidentOutcome, RDF.type, None),
        "hasCondition property": (PEN.hasCondition, RDF.type, None),
        "requiresSubjectRole property": (PEN.requiresSubjectRole, RDF.type, None),
        "requiresAccidentOutcome property": (PEN.requiresAccidentOutcome, RDF.type, None),
        "APP FindingStatus class": (APP.FindingStatus, RDF.type, None),
        "APP PenaltyExposureStatus class": (APP.PenaltyExposureStatus, RDF.type, None),
        "APP ActionRecommendation class": (APP.ActionRecommendation, RDF.type, None),
        "APP hasFindingStatus property": (APP.hasFindingStatus, RDF.type, None),
        "APP hasPenaltyExposureStatus property": (APP.hasPenaltyExposureStatus, RDF.type, None),
        "APP hasActionRecommendation property": (APP.hasActionRecommendation, RDF.type, None),
        "APP recommendedRequirement property": (APP.recommendedRequirement, RDF.type, None),
        "APP recommendationRank property": (APP.recommendationRank, RDF.type, None),
    }
    for name, pattern in schema_requirements.items():
        ok = any(g.triples(pattern))
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")

    print("\n=== Retired SHE Context Model ===")
    retired_she_checks = {
        "old she:ContextFeature triples": len([
            t for t in g
            if str(t[0]) == "https://cashtoss.info/ontology/she#ContextFeature"
            or str(t[1]) == "https://cashtoss.info/ontology/she#ContextFeature"
            or str(t[2]) == "https://cashtoss.info/ontology/she#ContextFeature"
        ]),
        "old she:SituationalHazardEvent triples": len([
            t for t in g
            if str(t[0]) == "https://cashtoss.info/ontology/she#SituationalHazardEvent"
            or str(t[1]) == "https://cashtoss.info/ontology/she#SituationalHazardEvent"
            or str(t[2]) == "https://cashtoss.info/ontology/she#SituationalHazardEvent"
        ]),
    }
    for name, actual in retired_she_checks.items():
        ok = actual == 0
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {actual} (expected 0)")

    print("\n=== Risk Feature Structure ===")
    risk_classes = {
        "haz:Hazard": HAZ.Hazard,
        "haz:AccidentType": HAZ.AccidentType,
        "agent:HazardousAgent": AGENT.HazardousAgent,
        "ctx:WorkContext": CTX.WorkContext,
        "ctx:WorkActivity": CTX.WorkActivity,
        "ctx:PPEState": CTX.PPEState,
        "ctx:EnvironmentalFactor": CTX.EnvironmentalFactor,
        "ctx:AgentState": CTX.AgentState,
        "ctx:TemporalStage": CTX.TemporalStage,
    }
    for name, cls in risk_classes.items():
        ok = (cls, RDFS.subClassOf, RISK.RiskFeature) in g
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {name} subClassOf risk:RiskFeature")

    print("\n=== Risk Feature Properties ===")
    she_feature_properties = {
        "she:hasAccidentType": SHE.hasAccidentType,
        "she:hasHazardousAgent": SHE.hasHazardousAgent,
        "she:hasWorkContext": SHE.hasWorkContext,
        "she:hasWorkActivity": SHE.hasWorkActivity,
        "she:hasPPEState": SHE.hasPPEState,
        "she:hasEnvironmental": SHE.hasEnvironmental,
        "she:hasAgentState": SHE.hasAgentState,
        "she:hasTemporalStage": SHE.hasTemporalStage,
    }
    for name, prop in she_feature_properties.items():
        ok = (prop, RDFS.subPropertyOf, RISK.hasFeature) in g
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {name} subPropertyOf risk:hasFeature")

    sr_feature_properties = {
        "sr:addressesHazard": SR.addressesHazard,
        "sr:addressesAccidentType": SR.addressesAccidentType,
        "sr:addressesAgent": SR.addressesAgent,
        "sr:inWorkContext": SR.inWorkContext,
    }
    for name, prop in sr_feature_properties.items():
        ok = (prop, RDFS.subPropertyOf, SR.addressesFeature) in g
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {name} subPropertyOf sr:addressesFeature")

    print("\n=== Materialized Risk Feature Data ===")
    patterns = set(g.subjects(RDF.type, SHE.SituationalHazardPattern))
    print(f"  [INFO] SHE patterns: {len(patterns)}")
    for label, predicate in {
        "risk:hasFeature": RISK.hasFeature,
        "she:hasVisualTrigger": SHE.hasVisualTrigger,
        "she:appliesSR": SHE.appliesSR,
    }.items():
        missing = sum(1 for pattern in patterns if not list(g.objects(pattern, predicate)))
        ok = missing == 0
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] patterns missing {label}: {missing}")

    sr_missing_feature = scalar_count(
        g,
        """
PREFIX sr: <https://cashtoss.info/ontology/sr#>
SELECT (COUNT(?sr) AS ?cnt) WHERE {
  ?sr a sr:SafetyRequirement .
  FILTER NOT EXISTS { ?sr sr:addressesFeature ?feature }
}
""",
    )
    print(f"  [INFO] SafetyRequirements missing sr:addressesFeature: {sr_missing_feature}")

    print("\n=== PenaltyRule Integrity ===")
    prefixes = """
PREFIX pen: <https://cashtoss.info/ontology/penalty#>
"""
    required_predicates = {
        "violatedArticle": "pen:violatedArticle",
        "violatedNorm": "pen:violatedNorm",
        "penaltyArticle": "pen:penaltyArticle",
        "hasSanction": "pen:hasSanction",
        "hasCondition": "pen:hasCondition",
    }
    for label, predicate in required_predicates.items():
        missing = scalar_count(
            g,
            prefixes
            + f"""
SELECT (COUNT(?pr) AS ?cnt) WHERE {{
  ?pr a pen:PenaltyRule .
  FILTER NOT EXISTS {{ ?pr {predicate} ?value }}
}}
""",
        )
        ok = missing == 0
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] missing {label}: {missing}")

    print("\n=== PenaltyCondition Integrity ===")
    condition_count = count_type(g, PEN.PenaltyCondition)
    ok = condition_count == 4772
    all_pass = all_pass and ok
    print(f"  [{'OK' if ok else 'FAIL'}] PenaltyCondition: {condition_count} (expected 4772)")

    condition_required_predicates = {
        "requiresAccidentOutcome": "pen:requiresAccidentOutcome",
        "requiresSubjectRole": "pen:requiresSubjectRole",
    }
    for label, predicate in condition_required_predicates.items():
        missing = scalar_count(
            g,
            prefixes
            + f"""
SELECT (COUNT(?cond) AS ?cnt) WHERE {{
  ?cond a pen:PenaltyCondition .
  FILTER NOT EXISTS {{ ?cond {predicate} ?value }}
}}
""",
        )
        ok = missing == 0
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] missing {label}: {missing}")

    print("\n=== NS-RULE100-0 PenaltyRules ===")
    expected_suffixes = [
        "death",
        "seriousAccident",
        "violation_contractor",
        "violation_employer",
    ]
    ns = LAW["NS-RULE100-0"]
    article = LAW["RULE_제100조"]
    rules = set(g.subjects(PEN.violatedNorm, ns))
    expected_rules = {PEN[f"PenaltyRule_NS-RULE100-0_{suffix}"] for suffix in expected_suffixes}
    ok = rules == expected_rules
    all_pass = all_pass and ok
    print(f"  [{'OK' if ok else 'FAIL'}] rule set: {len(rules)} (expected 4)")
    for rule in sorted(expected_rules, key=str):
        has_article = (rule, PEN.violatedArticle, article) in g
        all_pass = all_pass and has_article
        print(f"  [{'OK' if has_article else 'FAIL'}] {rule.split('#')[-1]} violatedArticle RULE_제100조")

    expected_conditions = {
        "death": (PEN.Death, CORE.Employer),
        "seriousAccident": (PEN.SeriousAccident, CORE.Employer),
        "violation_contractor": (PEN.SimpleViolation, CORE.Contractor),
        "violation_employer": (PEN.SimpleViolation, CORE.Employer),
    }
    for suffix, (outcome, role) in expected_conditions.items():
        rule = PEN[f"PenaltyRule_NS-RULE100-0_{suffix}"]
        cond = PEN[f"Condition_NS-RULE100-0_{suffix}"]
        ok = (
            (rule, PEN.hasCondition, cond) in g
            and (cond, PEN.requiresAccidentOutcome, outcome) in g
            and (cond, PEN.requiresSubjectRole, role) in g
        )
        all_pass = all_pass and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {rule.split('#')[-1]} condition")

    print("\n=== Summary ===")
    print(f"  Validation: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
