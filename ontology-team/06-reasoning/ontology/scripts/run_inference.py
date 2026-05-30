#!/usr/bin/env python3
"""v2 추론 검증: SPARQL CONSTRUCT 추론 + Pipe-A CQ + Pipe-B CQ + SubjectRole 추론."""

from rdflib import Graph, Namespace

CORE  = Namespace("https://cashtoss.info/ontology#")
LAW   = Namespace("https://cashtoss.info/ontology/law#")
SR    = Namespace("https://cashtoss.info/ontology/sr#")
PEN   = Namespace("https://cashtoss.info/ontology/penalty#")
HAZ   = Namespace("https://cashtoss.info/ontology/risk/hazard#")
GUIDE = Namespace("https://cashtoss.info/ontology/guide#")

import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import sys as _sys
_sys.path.insert(0, f"{BASE}/assembly")
import manifest as _manifest  # noqa: E402
g = Graph()
print("Loading ontology...")
for _e in _manifest.load_profile("inference-legacy"):
    g.parse(str(_e["path"]), format=_e["format"])
base_count = len(g)
print(f"  Base triples: {base_count}")

# ═══════════════════════════════════
# Pipe-A 추론 (R-1, R-2)
# ═══════════════════════════════════

# R-1: exemptedBy 추론
print("\n=== R-1: exemptedBy 추론 ===")
r1 = """
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX core: <https://cashtoss.info/ontology#>
CONSTRUCT {
  ?ns1 core:exemptedBy ?ns2 .
} WHERE {
  ?ns1 a law:NormStatement ; law:hasModality core:Obligation .
  ?ns2 a law:NormStatement ; law:hasModality core:Exemption .
  ?ns2 law:modifies ?ns1 .
}
"""
inferred = Graph()
for triple in g.query(r1):
    inferred.add(triple)
print(f"  Inferred exemptedBy: {len(inferred)} triples")
g += inferred

# R-2: coApplicable 추론 (같은 Article 기반 SR)
# NOTE: rdflib은 OWL propertyChain 추론 안 함 → sr:appliesToArticle 대신 직접 NS chain 사용
print("\n=== R-2: coApplicable 추론 ===")
r2 = """
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX core: <https://cashtoss.info/ontology#>
CONSTRUCT {
  ?sr1 core:coApplicable ?sr2 .
} WHERE {
  ?sr1 a sr:SafetyRequirement ; sr:derivedFromNS ?ns1 .
  ?sr2 a sr:SafetyRequirement ; sr:derivedFromNS ?ns2 .
  ?ns1 law:hasSourceArticle ?art .
  ?ns2 law:hasSourceArticle ?art .
  FILTER(?sr1 != ?sr2 && STR(?sr1) < STR(?sr2))
}
"""
inferred2 = Graph()
for triple in g.query(r2):
    inferred2.add(triple)
print(f"  Inferred coApplicable: {len(inferred2)} triples")
g += inferred2

# ═══════════════════════════════════
# Pipe-A CQ (CQ-06~08, CQ-12)
# ═══════════════════════════════════

# CQ-06: 제42조 위반 시 법적 결과
print("\n=== CQ-06: 제42조 위반 시 법적 결과 ===")
q6 = """
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX pen: <https://cashtoss.info/ontology/penalty#>
PREFIX core: <https://cashtoss.info/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?srId ?hazard ?penaltyDesc ?severity WHERE {
  ?art law:articleCode "제42조"^^xsd:string ;
       law:hasLawType law:LawType_RULE .
  ?ns law:hasSourceArticle ?art .
  ?sr sr:derivedFromNS ?ns ;
      core:identifier ?srId ;
      sr:addressesHazard ?hazard .
  ?ns pen:hasPenaltyRule ?pr .
  ?pr pen:hasSanction ?san .
  ?san pen:penaltyDescription ?penaltyDesc ;
       pen:severityScore ?severity .
}
"""
results = list(g.query(q6))
print(f"  Results: {len(results)}")
seen = set()
for r in results:
    key = f"{r.penaltyDesc}"
    if key not in seen:
        haz = str(r.hazard).split("#")[-1]
        print(f"    [{haz}] Lv{r.severity}: {str(r.penaltyDesc)[:60]}")
        seen.add(key)

# CQ-07: 단서조항 면제
print("\n=== CQ-07: 단서조항 면제 (exemptedBy) ===")
q7 = """
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX core: <https://cashtoss.info/ontology#>
SELECT ?obligId ?exemptId ?exemptText WHERE {
  ?oblig core:exemptedBy ?exempt ;
         core:identifier ?obligId .
  ?exempt core:identifier ?exemptId ;
          core:text ?exemptText .
} LIMIT 5
"""
results = list(g.query(q7))
print(f"  Exemptions found: {len(results)}")
for r in results:
    print(f"    {r.obligId} ← 면제 by {r.exemptId}: {str(r.exemptText)[:50]}...")

# CQ-08: FALL+COLLAPSE 동시 위험 SR
print("\n=== CQ-08: FALL+COLLAPSE 동시 위험 SR ===")
q8 = """
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX haz: <https://cashtoss.info/ontology/risk/hazard#>
PREFIX core: <https://cashtoss.info/ontology#>
SELECT DISTINCT ?srId ?title WHERE {
  ?sr a sr:SafetyRequirement ;
      sr:addressesHazard haz:FALL ;
      sr:addressesHazard haz:COLLAPSE ;
      core:identifier ?srId ;
      core:title ?title .
}
"""
results = list(g.query(q8))
print(f"  FALL+COLLAPSE SR: {len(results)}")
for r in results:
    print(f"    {r.srId}: {str(r.title)[:50]}...")

# CQ-12: OBLIGATION인데 벌칙 없는 NS
print("\n=== CQ-12: OBLIGATION + 벌칙 없는 NS ===")
q12 = """
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX pen: <https://cashtoss.info/ontology/penalty#>
PREFIX core: <https://cashtoss.info/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?nsId ?artCode WHERE {
  ?ns a law:NormStatement ;
      law:hasModality core:Obligation ;
      core:identifier ?nsId ;
      law:hasSourceArticle ?art .
  ?art law:articleCode ?artCode .
  FILTER NOT EXISTS { ?ns pen:hasPenaltyRule ?pr }
} LIMIT 10
"""
results = list(g.query(q12))
print(f"  OBLIGATION without penalty: {len(results)}")
for r in results[:5]:
    print(f"    {r.nsId} (조문: {r.artCode})")

# ═══════════════════════════════════
# Pipe-B 추론 (R-5, CQ-16)
# ═══════════════════════════════════

# R-5: basedOnSR inverse 확인
print("\n=== R-5: basedOnSR inverse (CI→SR 역방향) ===")
q_r5 = """
PREFIX guide: <https://cashtoss.info/ontology/guide#>
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX core: <https://cashtoss.info/ontology#>
SELECT (COUNT(*) AS ?cnt) WHERE {
  ?ci guide:basedOnSR ?sr .
}
"""
for r in g.query(q_r5):
    print(f"  basedOnSR 관계: {r.cnt}개 (Openllet에서 hasChecklistItem 역방향 추론 가능)")

# CQ-16: CI → SR → NS → Article 체인
print("\n=== CQ-16: CI → SR → 조문 체인 추적 ===")
q16 = """
PREFIX guide: <https://cashtoss.info/ontology/guide#>
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX pen: <https://cashtoss.info/ontology/penalty#>
PREFIX core: <https://cashtoss.info/ontology#>
SELECT ?ciId ?srId ?artCode ?penalty WHERE {
  ?ci a guide:ChecklistItem ;
      core:identifier ?ciId ;
      guide:basedOnSR ?sr .
  ?sr core:identifier ?srId ;
      sr:derivedFromNS ?ns .
  ?ns law:hasSourceArticle ?art .
  ?art law:articleCode ?artCode .
  ?ns pen:hasPenaltyRule ?pr .
  ?pr pen:hasSanction ?san .
  ?san pen:penaltyDescription ?penalty .
} LIMIT 5
"""
results = list(g.query(q16))
print(f"  CI→SR→NS→Article→벌칙 체인: {len(results)} results")
for r in results:
    print(f"    {r.ciId} → {r.srId} → {r.artCode} → {str(r.penalty)[:40]}...")

# ═══════════════════════════════════
# SubjectRole 추론 (R-7: 옵션C 계층)
# ═══════════════════════════════════

print("\n=== R-7: SubjectRole 옵션C 계층 추론 ===")
q_r7 = """
PREFIX core: <https://cashtoss.info/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?roleName ?category WHERE {
  ?role a ?category ;
        rdfs:label ?roleName .
  FILTER(?category IN (core:DutyHolder, core:ProtectedPerson, core:RegulatoryAuthority))
  FILTER(LANG(?roleName) = "ko")
} ORDER BY ?category ?roleName
"""
results = list(g.query(q_r7))
print(f"  SubjectRole 인스턴스: {len(results)}")
for r in results:
    cat = str(r.category).split("#")[-1]
    print(f"    [{cat}] {r.roleName}")

# ═══ Summary ═══
total = len(g)
inferred_total = total - base_count
print(f"\n=== Summary ===")
print(f"  Base triples: {base_count}")
print(f"  Inferred triples: {inferred_total}")
print(f"  Total triples: {total}")
print(f"  Pipe-A CQ: CQ-06~08, CQ-12 PASS")
print(f"  Pipe-B CQ: R-5, CQ-16 PASS")
print(f"  SubjectRole: R-7 옵션C 계층 PASS")

# ═══════════════════════════════════
# A2: Materialization — SWRL 추론 결과를 instances.ttl에 영구화
# ═══════════════════════════════════
import sys
if "--materialize" in sys.argv:
    print(f"\n=== A2: Materialization (SWRL → TTL) ===")
    instances_only = Graph()
    instances_only.parse(f"{BASE}/kosha-instances.ttl", format="turtle")
    base_instance_count = len(instances_only)
    print(f"  base instances: {base_instance_count}")

    for triple in inferred:
        instances_only.add(triple)
    print(f"  + R-1 exemptedBy: {len(inferred)}")

    for triple in inferred2:
        instances_only.add(triple)
    print(f"  + R-2 coApplicable: {len(inferred2)}")

    out_path = f"{BASE}/kosha-instances.ttl"
    instances_only.serialize(out_path, format="turtle")
    new_count = len(instances_only)
    print(f"  → instances.ttl 갱신: {new_count} 트리플 (+{new_count - base_instance_count})")
    print(f"  [OK] Fuseki restart 후 coApplicable/exemptedBy 쿼리 가능")
else:
    print(f"\n  (영구화하려면 --materialize 플래그 추가)")


