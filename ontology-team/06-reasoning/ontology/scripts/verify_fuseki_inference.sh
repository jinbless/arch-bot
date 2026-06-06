#!/usr/bin/env bash
# Fuseki + Openllet 추론 검증 스크립트
# Usage: bash verify_fuseki_inference.sh
#
# 검증 대상:
#  V1. 트리플 카운트 (base 626K → 추론 후 증가량)
#  V2. PA-4 propertyChain: SR → Article (appliesToArticle)
#  V3. PA-5 inverseOf: SR → CI (sr:hasChecklistItem from guide:basedOnSR)
#  V4. PA-7 SymmetricProperty: referencesGuide 양방향
#  V5. SubjectRole 클래스 계층: Employer → DutyHolder → SubjectRole
#  V6. coApplicable (예상 0건 — SWRL R-2 없음)
#  V7. exemptedBy (예상 0건 — SWRL R-1 없음)

set -euo pipefail

SPARQL_EP="http://localhost:3030/kosha/sparql"
PREFIXES='PREFIX kosha: <https://cashtoss.info/ontology#>
PREFIX law:   <https://cashtoss.info/ontology/law#>
PREFIX sr:    <https://cashtoss.info/ontology/sr#>
PREFIX pen:   <https://cashtoss.info/ontology/penalty#>
PREFIX guide: <https://cashtoss.info/ontology/guide#>
PREFIX hazard:<https://cashtoss.info/ontology/risk/hazard#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>'

run_query() {
  local title="$1"
  local query="$2"
  echo ""
  echo "═══ $title ═══"
  curl -sS -G "$SPARQL_EP" \
    --data-urlencode "query=${PREFIXES}
$query" \
    -H "Accept: application/sparql-results+json" \
    | python -c 'import sys, json; r=json.load(sys.stdin); b=r["results"]["bindings"]; print(f"  rows={len(b)}"); [print(f"    {row}") for row in b[:10]]'
}

echo "▶ Fuseki: $SPARQL_EP"
echo "▶ Health check..."
curl -sS -f "http://localhost:3030/\$/ping" && echo " OK" || { echo " FAIL"; exit 1; }

# V0. Consistency (WS-GATE-4): Openllet lazy prepare()를 실제 trigger하는 라이브 ASK.
#   "Server Started"는 일관성 보장이 아니다 — consistency는 첫 추론 쿼리에서만 검사된다.
#   owl:Nothing에 귀속된 개체(disjoint 위반 등)가 있으면 비일관 → exit 1.
echo ""
echo "═══ V0. Consistency: ASK { ?x a owl:Nothing } (Openllet live, 비일관 시 exit 1) ═══"
incons=$(curl -sS -G "$SPARQL_EP" \
  --data-urlencode "query=PREFIX owl: <http://www.w3.org/2002/07/owl#>
ASK { ?x a owl:Nothing }" \
  -H "Accept: application/sparql-results+json" \
  | python -c 'import sys, json; print(str(json.load(sys.stdin).get("boolean", False)).lower())')
echo "  owl:Nothing 개체 존재? $incons"
if [ "$incons" = "true" ]; then
  echo "  ✗ INCONSISTENT — Openllet가 owl:Nothing 귀속 개체 검출. 비일관 온톨로지 → exit 1"
  exit 1
fi
echo "  ✓ CONSISTENT (owl:Nothing 0)"

run_query "V1. Total triple count (base 626K + inferred)" \
'SELECT (COUNT(*) AS ?cnt) WHERE { ?s ?p ?o }'

run_query "V2. PA-4 chain: SR → Article (appliesToArticle inferred)" \
'SELECT (COUNT(DISTINCT ?sr) AS ?srCnt) (COUNT(*) AS ?triples) WHERE {
   ?sr a sr:SafetyRequirement ; sr:appliesToArticle ?art .
 }'

run_query "V2b. PA-4 spot check: SR-001 chain expansion" \
'SELECT ?srId ?artCode WHERE {
   ?sr a sr:SafetyRequirement ;
       kosha:identifier ?srId ;
       sr:appliesToArticle ?art .
   ?art law:articleCode ?artCode .
 } LIMIT 5'

run_query "V3. PA-5 inverse: sr:hasChecklistItem (from basedOnSR)" \
'SELECT (COUNT(*) AS ?cnt) WHERE { ?sr sr:hasChecklistItem ?ci }'

run_query "V4. PA-7 symmetric: referencesGuide 양방향" \
'SELECT (COUNT(*) AS ?cnt) WHERE { ?g1 guide:referencesGuide ?g2 }'

run_query "V5. SubjectRole 계층 (Employer rdf:type DutyHolder + SubjectRole)" \
'SELECT (COUNT(?role) AS ?cnt) WHERE {
   ?role a kosha:SubjectRole .
 }'

run_query "V5b. Employer는 SubjectRole이기도 한가? (subClassOf 추론)" \
'ASK { kosha:Employer a kosha:SubjectRole }'

run_query "V6. coApplicable (SWRL R-2 — 예상: 0건, OWL에 정의 없음)" \
'SELECT (COUNT(*) AS ?cnt) WHERE { ?s kosha:coApplicable ?o }'

run_query "V7. exemptedBy (SWRL R-1 — 예상: 0건)" \
'SELECT (COUNT(*) AS ?cnt) WHERE { ?s kosha:exemptedBy ?o }'

run_query "V8. modifiedBy (PA-3 inverseOf modifies)" \
'SELECT (COUNT(*) AS ?cnt) WHERE { ?s law:modifiedBy ?o }'

run_query "V9. hasNormStatement (PA-1 inverseOf hasSourceArticle)" \
'SELECT (COUNT(*) AS ?cnt) WHERE { ?s law:hasNormStatement ?o }'

run_query "V10. hasSafetyRequirement (PA-2 inverseOf derivedFromNS)" \
'SELECT (COUNT(*) AS ?cnt) WHERE { ?s sr:hasSafetyRequirement ?o }'

echo ""
echo "═══ 끝 ═══"
