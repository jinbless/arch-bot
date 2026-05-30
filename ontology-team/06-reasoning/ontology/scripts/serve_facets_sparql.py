"""온톨로지 facet 직접 탐색용 로컬 SPARQL 엔드포인트 (PG 아님 — 온톨로지 TTL 직접).

현재 ontology TTL(특히 Three-Worlds CI/Guide facet)을 rdflib로 로드하고 SPARQL UI(YASGUI)를
서빙한다. 브라우저 http://localhost:3031 에서 CI/Guide/SR facet을 직접 쿼리해 확인.
PG는 이 온톨로지의 특정시점 스냅샷일 뿐이므로, 진짜 확인은 여기(온톨로지)에서 한다.

사용(Windows python — 브라우저가 직접 접근):
  python ontology-team/06-reasoning/ontology/scripts/serve_facets_sparql.py
필요: pip install rdflib-endpoint uvicorn fastapi
"""
from pathlib import Path

import uvicorn
from rdflib import Graph
from rdflib_endpoint import SparqlEndpoint

ONT = Path(__file__).resolve().parents[1]

# 로드 대상 — TBox(속성 정의) + ABox(facet). 새 Three-Worlds 파일 포함.
FILES = [
    # ── 스키마(TBox): 클래스/속성 정의 전체 ──
    "kosha-ontology.formatted.ttl",                 # 베이스 TBox(클래스/속성 + 62 facet 개체)
    "kosha-ontology-v4-kosha22-vocab-patch.ttl",    # facet 값 정의(한글 라벨)
    "kosha-ontology-v4-guide-hazard-patch.ttl",     # guide:addressesHazard 등
    "kosha-ontology-v4-canonical-ci-patch.ttl",     # CanonicalChecklistItem/realizesControl/bundlesControl
    "kosha-ontology-v4-deps-patch.ttl",             # core:dependsOn
    "kosha-ontology-v4-alethic-patch.ttl",          # guide:Equipment 등
    "kosha-ontology-v4-bridge-patch.ttl",           # bridge:*
    "kosha-ontology-v4-deontic-patch.ttl",          # deontic
    "kosha-ontology-v4-violation-patch.ttl",        # violation
    "kosha-ontology-v4-penalty-extra-patch.ttl",    # penalty 확장
    "kosha-ontology-v4-restrictions-patch.ttl",     # owl:Restriction
    "kosha-ontology-v4-hazard-direct-patch.ttl",    # risk:NaturalLanguageHazardCategory
    "kosha-ontology-v4-asymmetric-patch.ttl",       # law:modifiesAsymmetric
    # ── ABox: 데이터 + Three-Worlds + open-world ──
    "kosha-instances.ttl",                          # SR/CI/Guide/law/penalty 데이터 (대용량)
    "kosha-instances-canonical-ci.ttl",             # canonical CI facet + 구조 [NEW]
    "kosha-instances-ci-guide-hazard-derived.ttl",  # Guide 유도 facet [NEW]
    "kosha-instances-hazard-direct.ttl",            # risk: NLH (open→closed 다리)
    "kosha-instances-production-8photo.ttl",        # app:VisualObservation (open-world 사진)
]
PREFIXES = {
    # cashtoss.info 정본 — validate_prefixes.py CANONICAL과 동일 (SSOT)
    "core": "https://cashtoss.info/ontology#",
    "risk": "https://cashtoss.info/ontology/risk#",
    "haz": "https://cashtoss.info/ontology/risk/hazard#",
    "agent": "https://cashtoss.info/ontology/risk/agent#",     # 위험원 전용
    "ctx": "https://cashtoss.info/ontology/risk/context#",
    "she": "https://cashtoss.info/ontology/risk/situation#",
    "sr": "https://cashtoss.info/ontology/sr#",
    "guide": "https://cashtoss.info/ontology/guide#",
    "law": "https://cashtoss.info/ontology/law#",
    "pen": "https://cashtoss.info/ontology/penalty#",
    "app": "https://cashtoss.info/ontology/app#",
    "bridge": "https://cashtoss.info/ontology/bridge#",
    "industry": "https://cashtoss.info/ontology/industry#",
    "actor": "https://cashtoss.info/ontology/actor#",          # 신규 — 행위자(Worker)
    "prod": "https://cashtoss.info/ontology/production#",
    "kr": "https://cashtoss.info/ontology/swrl-rules#",
    "krs": "https://cashtoss.info/ontology/shacl-rules#",
    "shape": "https://cashtoss.info/ontology/shape#",
    "demo": "https://cashtoss.info/ontology/demo#",
    # 표준
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "sh": "http://www.w3.org/ns/shacl#",
}

EXAMPLE = """# 고유 control(CI)별 facet — 지게차 관련 CI 찾기
PREFIX guide: <https://cashtoss.info/ontology/guide#>
PREFIX ctx: <https://cashtoss.info/ontology/risk/context#>
PREFIX core: <https://cashtoss.info/ontology#>
SELECT ?ci ?text ?ctx WHERE {
  ?ci a guide:CanonicalChecklistItem ;
      core:text ?text ;
      guide:ciInWorkContext ?ctx .
  FILTER(CONTAINS(?text, "지게차"))
} LIMIT 20"""


def main() -> None:
    g = Graph()
    for p, ns in PREFIXES.items():
        g.bind(p, ns)
    print("=== 온톨로지 TTL 로드 (PG 아님) ===")
    for f in FILES:
        path = ONT / f
        if not path.exists():
            print(f"  SKIP(없음): {f}")
            continue
        pre = len(g)
        g.parse(str(path), format="turtle")
        print(f"  +{len(g) - pre:>8}  {f}", flush=True)
    print(f"총 {len(g)} triples — http://localhost:3031 에서 SPARQL 쿼리 (YASGUI)", flush=True)

    app = SparqlEndpoint(
        graph=g,
        title="KOSHA Ontology Facet Explorer",
        description="CI/Guide/SR facet을 온톨로지에서 직접 SPARQL 조회 (PG 스냅샷 아님). 예시: " + EXAMPLE.replace(chr(10), " "),
        version="1.0",
        enable_update=False,
        cors_enabled=True,
    )
    uvicorn.run(app, host="127.0.0.1", port=3031, log_level="warning")


if __name__ == "__main__":
    main()
