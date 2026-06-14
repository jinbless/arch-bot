#!/usr/bin/env python3
"""A5 — 위험 코드 어휘(canonical-code-vocabulary.json)를 표준 SKOS ConceptScheme로 emit.

SoT(shared/reference/canonical-code-vocabulary.json) 하나에서 축별 SKOS를 자동 생성한다.
수동 편집 금지 — 코드 추가 시 이 생성기를 재실행(make gen-skos)하면 SKOS도 갱신된다.

축별(accident_type/hazardous_agent/work_context) ConceptScheme:
  - canonical 코드 → skos:topConceptOf + rdfs:seeAlso OWL 클래스(haz:/agent:/ctx:)
  - rollup(fine→canonical) → skos:broader canonical  (rollup 맵이 곧 계층)
  - 교차축 rollup(agent→accident 등) → skos:relatedMatch (연관, 비계층)
  - skos:prefLabel(@en, 코드 humanize) + skos:notation(원 코드)

한글 prefLabel / KOSHA-22 skos:exactMatch는 SoT에 해당 데이터가 생기면 자동 반영(현재 미보유).

사용:
  python gen_skos_scheme.py            # dry (카운트만)
  python gen_skos_scheme.py --write    # kosha-codes-skos.ttl 산출
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS, DCTERMS, XSD

SCRIPT_DIR = Path(__file__).resolve().parent
ONT_DIR = SCRIPT_DIR.parent
REPO_ROOT = next((p for p in SCRIPT_DIR.parents if (p / "shared" / "reference").exists()), None)
DEFAULT_SOT = (REPO_ROOT / "shared" / "reference" / "canonical-code-vocabulary.json") if REPO_ROOT else None
DEFAULT_OUT = ONT_DIR / "kosha-codes-skos.ttl"

# 축별 namespace — 코드명이 축 간 중복될 수 있어 단일 namespace는 IRI 충돌(같은 코드가 한 축에선
# canonical, 다른 축에선 fine). 축별로 분리해 충돌 제거. A2에서 w3id로 마이그레이션.
CODE_BASE = "https://cashtoss.info/ontology/code/"


def _axis_ns(axis: str) -> Namespace:
    return Namespace(f"{CODE_BASE}{axis.replace('_', '-')}#")


# code_iri_mapper.NAMESPACES와 동일 — canonical 코드의 OWL 클래스(facet punning) exactMatch 대상.
AXIS_OWL_NS = {
    "accident_type": Namespace("https://cashtoss.info/ontology/risk/hazard#"),
    "hazardous_agent": Namespace("https://cashtoss.info/ontology/risk/agent#"),
    "work_context": Namespace("https://cashtoss.info/ontology/risk/context#"),
}
AXIS_LABEL = {
    "accident_type": ("사고유형 코드 체계", "Accident type code scheme"),
    "hazardous_agent": ("위험원 코드 체계", "Hazardous agent code scheme"),
    "work_context": ("작업맥락 코드 체계", "Work context code scheme"),
}


def _camel(code: str) -> str:
    """UPPER_SNAKE → CamelCase (code_iri_mapper와 동일). FALL→Fall, CUT_LACERATION→CutLaceration."""
    return "".join(p.capitalize() for p in str(code).split("_") if p)


def _humanize(code: str) -> str:
    return str(code).replace("_", " ").title()


def build(sot: Path) -> tuple[Graph, dict]:
    vocab = json.loads(sot.read_text(encoding="utf-8"))
    axes = vocab.get("axes", {})
    ns = {axis: _axis_ns(axis) for axis in axes}

    g = Graph()
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    g.bind("haz", AXIS_OWL_NS["accident_type"])      # 정본 짧은 이름(validate_prefixes)
    g.bind("agent", AXIS_OWL_NS["hazardous_agent"])
    g.bind("ctx", AXIS_OWL_NS["work_context"])
    for axis, n in ns.items():
        g.bind(f"code-{axis.replace('_', '-')}", n)

    counts = {"schemes": 0, "canonical": 0, "rollup": 0, "relatedMatch": 0,
              "grouping": 0, "seeAlso": 0}

    def _concept(axis: str, code: str, scheme: URIRef) -> URIRef:
        """concept를 (멱등) 생성하고 IRI 반환. 중복 add는 set 그래프라 무해."""
        c = ns[axis][code]
        g.add((c, RDF.type, SKOS.Concept))
        g.add((c, SKOS.inScheme, scheme))
        g.add((c, SKOS.prefLabel, Literal(_humanize(code), lang="en")))
        g.add((c, SKOS.notation, Literal(code, datatype=XSD.token)))
        return c

    schemes = {axis: URIRef(f"{ns[axis]}scheme") for axis in axes}

    for axis, spec in axes.items():
        owl_ns = AXIS_OWL_NS.get(axis)
        scheme = schemes[axis]
        ko, en = AXIS_LABEL.get(axis, (axis, axis))
        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        g.add((scheme, SKOS.prefLabel, Literal(ko, lang="ko")))
        g.add((scheme, SKOS.prefLabel, Literal(en, lang="en")))
        g.add((scheme, DCTERMS.source, URIRef("file:canonical-code-vocabulary.json")))
        counts["schemes"] += 1

        canonical = set(spec.get("canonical", []))
        # canonical → top concept (+ OWL 클래스 exactMatch)
        for code in sorted(canonical):
            c = _concept(axis, code, scheme)
            g.add((c, SKOS.topConceptOf, scheme))
            g.add((scheme, SKOS.hasTopConcept, c))
            if owl_ns is not None:
                # SKOS 매핑 술어 대신 rdfs:seeAlso로 OWL 클래스 연결 — exactMatch(range skos:Concept)는
                # owl:Class를 Concept로 펀닝시키므로 부적합. seeAlso는 range 무제약(표준 안전).
                g.add((c, RDFS.seeAlso, owl_ns[_camel(code)]))
                counts["seeAlso"] += 1
            counts["canonical"] += 1

        # rollup(fine → target). identity(fine==target) skip.
        for fine, target in sorted(spec.get("rollup", {}).items()):
            if fine == target:
                continue
            c = _concept(axis, fine, scheme)
            if ":" in target:
                # 교차축 "target_axis:CODE" → relatedMatch (연관, 비계층). cause→effect는 genus-species가
                # 아니므로 broadMatch(broader 함의 → broaderTransitive 오염) 부적합.
                t_axis, t_code = target.split(":", 1)
                if t_axis in ns:
                    g.add((c, SKOS.relatedMatch, ns[t_axis][t_code]))
                    counts["relatedMatch"] += 1
            elif target in canonical:
                g.add((c, SKOS.broader, ns[axis][target]))  # 같은 축 canonical
                counts["rollup"] += 1
            else:
                # 같은 축 비canonical 그룹핑 타깃 — concept로 생성(top, 부모 없음) 후 broader
                t = _concept(axis, target, scheme)
                g.add((t, SKOS.topConceptOf, scheme))
                g.add((scheme, SKOS.hasTopConcept, t))
                g.add((c, SKOS.broader, t))
                counts["rollup"] += 1
                counts["grouping"] += 1

    return g, counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sot", type=Path, default=DEFAULT_SOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    if not args.sot or not args.sot.exists():
        print(f"ERROR: SoT not found: {args.sot}", file=sys.stderr)
        return 1

    g, counts = build(args.sot)
    print(f"SKOS: schemes={counts['schemes']} canonical={counts['canonical']} "
          f"rollup={counts['rollup']} relatedMatch={counts['relatedMatch']} "
          f"seeAlso={counts['seeAlso']} grouping={counts['grouping']} triples={len(g)}")

    if not args.write:
        print("(산출하려면 --write)")
        return 0

    header = (
        "# A5 — KOSHA OHS 위험 코드 SKOS ConceptScheme (자동 생성: gen_skos_scheme.py).\n"
        "# SoT: shared/reference/canonical-code-vocabulary.json. 수동 편집 금지 — make gen-skos 재실행.\n"
        "# canonical=topConcept(+OWL rdfs:seeAlso), rollup=broader, 교차축=relatedMatch. namespace는 A2에서 w3id.\n"
    )
    args.out.write_text(header + g.serialize(format="turtle"), encoding="utf-8")
    print(f"→ {args.out.name}: {len(g)} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
