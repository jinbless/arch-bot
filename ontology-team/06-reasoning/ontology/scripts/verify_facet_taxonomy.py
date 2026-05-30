#!/usr/bin/env python3
"""P3.3 explained-delta — 구 subclass-patch(catalog) vs 신 facet-taxonomy(vocab) 그래프 diff.

단일변수(생성기 SSOT를 catalog sub→vocab rollup으로 전환)의 그래프 영향을 정확히 보고한다:
  - canonical owl:Class punning (신규)
  - subClassOf 추가/삭제 + '부모 변경'(catalog↔vocab 구조 차이의 실체)
  - haz casing(UPPER 삭제→Camel 추가), ctx 계층(신규)
순수 진단(파일 미수정).
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdflib import Graph, RDF, OWL, RDFS  # noqa: E402


def _root() -> Path:
    for a in Path(__file__).resolve().parents:
        if (a / "shared" / "reference" / "canonical-code-vocabulary.json").exists():
            return a
    raise RuntimeError("root not found")


ONT = _root() / "ontology-team" / "06-reasoning" / "ontology"
OLD = ONT / "kosha-ontology-v3-subclass-patch.ttl"
NEW = ONT / "kosha-facet-taxonomy.ttl"
NS = {"haz": "https://cashtoss.info/ontology/risk/hazard#",
      "agent": "https://cashtoss.info/ontology/risk/agent#",
      "ctx": "https://cashtoss.info/ontology/risk/context#"}


def _pfx(iri: str) -> str:
    for p, ns in NS.items():
        if iri.startswith(ns):
            return f"{p}:{iri[len(ns):]}"
    return iri


def _load(p: Path) -> Graph:
    g = Graph()
    g.parse(str(p), format="turtle")
    return g


def main() -> int:
    go, gn = _load(OLD), _load(NEW)
    so, sn = set(go), set(gn)
    added, removed = sn - so, so - sn

    # punning (X a owl:Class)
    pun_old = {s for s, p, o in go if p == RDF.type and o == OWL.Class}
    pun_new = {s for s, p, o in gn if p == RDF.type and o == OWL.Class}

    # subClassOf 엣지: child -> parent
    def edges(g):
        return {(str(s), str(o)) for s, p, o in g if p == RDFS.subClassOf}
    eo, en = edges(go), edges(gn)
    child_old = {c: par for c, par in eo}
    child_new = {c: par for c, par in en}

    print("=" * 64)
    print("EXPLAINED-DELTA: v3-subclass-patch(catalog) → facet-taxonomy(vocab)")
    print("=" * 64)
    print(f"triples: old {len(so)} | new {len(sn)} | +{len(added)} / -{len(removed)}")
    print(f"\n[1] canonical owl:Class punning: old {len(pun_old)} → new {len(pun_new)} "
          f"(+{len(pun_new - pun_old)})  ← 신규(individual→class 격상)")

    # subClassOf 분류
    only_new = en - eo
    only_old = eo - en
    common = eo & en
    moved = {c for c in (set(child_old) & set(child_new)) if child_old[c] != child_new[c]}
    print(f"\n[2] subClassOf 엣지: old {len(eo)} | new {len(en)} | 공통 {len(common)} "
          f"| 신규 {len(only_new)} | 삭제 {len(only_old)}")
    print(f"    부모 변경(catalog↔vocab 구조차): {len(moved)}")
    for c in sorted(moved)[:12]:
        print(f"      {_pfx(c)}: {_pfx(child_old[c])} → {_pfx(child_new[c])}")
    if len(moved) > 12:
        print(f"      ... +{len(moved) - 12} more")

    # 축별 신규/삭제 분포
    def axis_of(iri):
        return _pfx(iri).split(":", 1)[0]
    from collections import Counter
    print("\n[3] 축별 subClassOf 신규/삭제:")
    for ax in ("haz", "agent", "ctx"):
        a_new = sum(1 for c, _ in only_new if axis_of(c) == ax)
        a_old = sum(1 for c, _ in only_old if axis_of(c) == ax)
        print(f"    {ax:5}: +{a_new} / -{a_old}")

    # 핵심 단언
    print("\n[4] 핵심 단언:")
    fork = ("https://cashtoss.info/ontology/risk/context#ForkliftOperation",
            "https://cashtoss.info/ontology/risk/context#Vehicle")
    upper_haz_new = [c for c, _ in en if c.startswith(NS["haz"]) and c[len(NS["haz"]):].isupper()]
    print(f"    forklift ⊑ vehicle 신규: {'OK' if fork in only_new else 'MISSING'}")
    print(f"    신 taxonomy에 UPPER haz(끊긴 IRI): {len(upper_haz_new)} (0이어야 함)")
    print(f"    구 patch가 ABox/base 건드림? — 이 파일은 patch이므로 삭제는 전부 구 patch 내부 엣지")
    return 0


if __name__ == "__main__":
    sys.exit(main())
