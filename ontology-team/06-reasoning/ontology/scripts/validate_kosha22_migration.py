#!/usr/bin/env python3
"""Phase 4-B Stage 6 — 마이그레이션 논리 검증 (rdflib, Openllet 불필요).

1. 마이그레이션된 ABox + disjoint + vocab 패치 parse.
2. disjoint 위반: 한 인스턴스가 disjoint accident 쌍을 동시 보유하는지(she:hasAccidentType 등).
3. KOSHA-22 개체 사용 현황 + 구 어휘 잔여 0 확인.
실행: python validate_kosha22_migration.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from rdflib import Graph, RDF, Namespace

ONTO = Path(__file__).resolve().parents[1]
HAZ = Namespace("https://cashtoss.info/ontology/risk/hazard#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")

FILES = [
    "kosha-ontology-v4-kosha22-vocab-patch.ttl",
    "kosha-accident22-disjoint.ttl",
    "kosha-instances.ttl",
    "kosha-instances-guide-hazard.ttl",
    "kosha-instances-production-8photo.ttl",
]


def main() -> int:
    g = Graph()
    for f in FILES:
        p = ONTO / f
        if p.exists():
            g.parse(str(p), format="turtle")
            print(f"  parsed {f}: total {len(g)} triples")

    # disjoint 쌍 추출
    pairs = set()
    for a, _, b in g.triples((None, OWL.disjointWith, None)):
        if str(a).startswith(str(HAZ)) and str(b).startswith(str(HAZ)):
            pairs.add(frozenset((a, b)))
    print(f"\ndisjoint accident 쌍: {len(pairs)}")

    # 진짜 OWL 위반 = 한 개체가 두 disjoint accident 클래스로 rdf:type (punning class membership).
    # 주의: addressesHazard/addressesAccidentType 같은 '집계' 술어로 여러 사고유형을 '참조'하는
    # SR/Guide는 정상(disjoint는 클래스 멤버십에만 적용) → 위반 아님.
    typed_by_subj: dict = {}
    for s, _, o in g.triples((None, RDF.type, None)):
        if str(o).startswith(str(HAZ)):
            typed_by_subj.setdefault(s, set()).add(o)

    violations = []
    for subj, vals in typed_by_subj.items():
        for pr in pairs:
            if pr <= vals:
                violations.append((subj, tuple(pr)))

    print(f"accident 클래스로 rdf:type된 개체: {len(typed_by_subj)}")
    print(f"disjoint 위반(rdf:type 두 disjoint 클래스 동시): {len(violations)}")
    for subj, pr in violations[:10]:
        print(f"  VIOLATION {subj} : {[str(x).split('#')[-1] for x in pr]}")

    # KOSHA-22 개체 사용 분포 (addressesAccidentType 등 값으로)
    from collections import Counter
    ACC = Namespace("https://cashtoss.info/ontology/risk/")
    use = Counter()
    acc_individuals = set(g.subjects(RDF.type, HAZ.AccidentType))
    for s, p, o in g:
        if o in acc_individuals and "AccidentType" in str(p):
            use[str(o).split("#")[-1]] += 1
    print(f"\n사용된 accident 개체 top: {dict(use.most_common(8))}")

    # 구 어휘 잔여(개체로 사용)
    OLD = {"Crush", "Cut", "FallingObject", "Slip", "Ergonomic", "CRUSH", "CAUGHT_IN", "STRUCK_BY"}
    residual = {k: v for k, v in use.items() if k in OLD}
    print(f"구 어휘 잔여(값 사용): {residual if residual else '0 (clean)'}")

    ok = (len(violations) == 0 and not residual)
    print(f"\nVERDICT: {'PASS — disjoint 위반 0 + 구어휘 0' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
