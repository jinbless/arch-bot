#!/usr/bin/env python3
"""Phase 0 — Canonical-CI ABox export (Three-Worlds 재설계).

derive_canonical_ci.py가 PG staging(canonical_checklist_items / guide_control_bundle /
checklist_items.canonical_ci_id)으로 만든 고유 control 계층을 ABox로 author.
별도 파일(kosha-instances-canonical-ci.ttl) — 58MB kosha-instances.ttl 재생성 회피, additive.

canonical CI에 basedOnSR(집계) + facet(집계)을 직접 부여 → Phase 1 SHACL 규칙이 inverse 링크
없이 canonical 계층에서 바로 유도(CI-H1: basedOnSR→SR→hazard, G-H1: Guide bundlesControl→CI).

산출: ontology-team/06-reasoning/ontology/kosha-instances-canonical-ci.ttl
사용: PYTHONIOENCODING=utf-8 python export_canonical_ci_abox.py
"""
import json
import re
import sys
from pathlib import Path

import psycopg2
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "serving-team" / "08-app" / "backend"))
from app.integrations.code_iri_mapper import to_iri as _to_iri  # noqa: E402

CORE = Namespace("https://cashtoss.info/ontology#")
SR = Namespace("https://cashtoss.info/ontology/sr#")
GUIDE = Namespace("https://cashtoss.info/ontology/guide#")
DB = dict(dbname="kosha", user="kosha", password="1229", host="localhost")
OUT = Path(__file__).resolve().parents[1] / "kosha-instances-canonical-ci.ttl"

AXIS_COL = {
    "accident_type": "accident_types_canonical",
    "hazardous_agent": "hazardous_agents_canonical",
    "work_context": "work_contexts_canonical",
}
AXIS_PROP = {
    "accident_type": GUIDE.ciAddressesAccidentType,
    "hazardous_agent": GUIDE.ciAddressesAgent,
    "work_context": GUIDE.ciInWorkContext,
}


def safe(s: str) -> str:
    return re.sub(r"[^\w-]", "_", s)


def axis_uri(axis: str, code: str):
    iri = _to_iri(axis, code)
    return URIRef(iri) if iri else None


def _arr(v):
    if not v:
        return []
    return v if isinstance(v, list) else json.loads(v)


def main() -> int:
    g = Graph()
    for p, ns in [("core", CORE), ("sr", SR), ("guide", GUIDE), ("owl", OWL)]:
        g.bind(p, ns)
    n = 0

    def add(s, p, o):
        nonlocal n
        g.add((s, p, o))
        n += 1

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # 1) canonical CI 개체 + facet(집계) + degree + boilerplate
    cur.execute(
        "SELECT canonical_ci_id, rep_text, guide_degree, is_boilerplate, "
        "accident_types_canonical, hazardous_agents_canonical, work_contexts_canonical "
        "FROM canonical_checklist_items"
    )
    n_canon = 0
    for cid, rep, degree, boiler, acc, agt, ctx in cur.fetchall():
        u = GUIDE[safe(cid)]
        add(u, RDF.type, GUIDE.CanonicalChecklistItem)
        add(u, CORE.identifier, Literal(cid, datatype=XSD.string))
        if rep:
            add(u, CORE.text, Literal(rep, datatype=XSD.string))
        add(u, GUIDE.ciGuideFrequency, Literal(int(degree), datatype=XSD.integer))
        add(u, GUIDE.isBoilerplate, Literal(bool(boiler), datatype=XSD.boolean))
        for axis, vals in (("accident_type", acc), ("hazardous_agent", agt), ("work_context", ctx)):
            for code in _arr(vals):
                fu = axis_uri(axis, code)
                if fu is not None:
                    add(u, AXIS_PROP[axis], fu)
        n_canon += 1

    # 2) instance → canonical (realizesControl)
    cur.execute("SELECT identifier, canonical_ci_id FROM checklist_items WHERE canonical_ci_id IS NOT NULL")
    n_real = 0
    for ident, cid in cur.fetchall():
        add(GUIDE[safe(ident)], GUIDE.realizesControl, GUIDE[safe(cid)])
        n_real += 1

    # 3) Guide → canonical (bundlesControl)
    cur.execute("SELECT guide_code, canonical_ci_id FROM guide_control_bundle")
    n_bundle = 0
    for gc, cid in cur.fetchall():
        add(GUIDE[safe(gc)], GUIDE.bundlesControl, GUIDE[safe(cid)])
        n_bundle += 1

    # 4) canonical → SR (basedOnSR, 집계: 멤버 instance의 ci_sr_mapping union)
    cur.execute(
        "SELECT DISTINCT ci.canonical_ci_id, m.sr_id "
        "FROM checklist_items ci JOIN ci_sr_mapping m ON m.ci_id = ci.identifier "
        "WHERE ci.canonical_ci_id IS NOT NULL"
    )
    n_sr = 0
    for cid, sr_id in cur.fetchall():
        add(GUIDE[safe(cid)], GUIDE.basedOnSR, SR[safe(sr_id)])
        n_sr += 1

    conn.close()
    g.serialize(destination=str(OUT), format="turtle")
    print(f"Done. {n} triples → {OUT.name}")
    print(f"  CanonicalChecklistItem: {n_canon}")
    print(f"  realizesControl: {n_real}  bundlesControl: {n_bundle}  basedOnSR(canonical): {n_sr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
