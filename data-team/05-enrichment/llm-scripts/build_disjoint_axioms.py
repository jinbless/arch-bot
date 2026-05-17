#!/usr/bin/env python3
"""Phase E Step 3a — incompatibility KB → DisjointClasses OWL axiom (결정론).

`guide_domain_incompatibilities.json`의 페어를 OWL DisjointClasses axiom으로 변환.
asymmetric trust: vetted hard 적용, candidate는 별도 graph + soft annotation.

산출:
- ontology-team/06-reasoning/ontology/kosha-disjoint-axioms.ttl
- data-team/05-enrichment/runtime-artifacts/disjoint_axioms_audit.json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
ONTOLOGY_DIR = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
INCOMPAT_PATH = ARTIFACTS_DIR / "guide_domain_incompatibilities.json"
OUT_TTL = ONTOLOGY_DIR / "kosha-disjoint-axioms.ttl"
AUDIT_PATH = ARTIFACTS_DIR / "disjoint_axioms_audit.json"

IND_NS = "https://cashtoss.info/ontology/industry#"
CORE_NS = "https://cashtoss.info/ontology#"


def sanitize_local_name(name: str) -> str:
    """한국어/공백/특수문자를 URI-safe local name으로."""
    # 공백, slash, dot 등 제거
    safe = name.strip().replace(" ", "_").replace("/", "_").replace(".", "_")
    safe = safe.replace("·", "_").replace("(", "").replace(")", "")
    # 만약 한국어가 있으면 percent-encode
    if any(ord(c) > 127 for c in safe):
        safe = urllib.parse.quote(safe, safe="_")
    return f"Industry_{safe}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("vetted", "candidate", "both"), default="both")
    parser.add_argument("--min-conf", type=float, default=0.7)
    args = parser.parse_args()

    if not INCOMPAT_PATH.exists():
        print(f"ERROR: {INCOMPAT_PATH} 없음", file=sys.stderr)
        return 2

    from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal, BNode

    payload = json.loads(INCOMPAT_PATH.read_text(encoding="utf-8"))
    entries = payload.get("incompatibilities") or []

    # Filter
    filtered = []
    for e in entries:
        if not e.get("incompatible"):
            continue
        if float(e.get("confidence") or 0) < args.min_conf:
            continue
        level = str(e.get("level") or "candidate")
        if args.scope == "vetted" and level != "vetted":
            continue
        if args.scope == "candidate" and level != "candidate":
            continue
        filtered.append(e)
    print(f"Filtered {len(filtered)} entries (scope={args.scope}, min_conf={args.min_conf})")

    # Build graph
    g = Graph()
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("industry", Namespace(IND_NS))
    g.bind("core", Namespace(CORE_NS))

    industries: dict[str, URIRef] = {}

    def get_industry_iri(name: str) -> URIRef:
        if name not in industries:
            iri = URIRef(f"{IND_NS}{sanitize_local_name(name)}")
            industries[name] = iri
            # Declare as class with label
            g.add((iri, RDF.type, OWL.Class))
            g.add((iri, RDFS.label, Literal(name, lang="ko")))
            g.add((iri, RDFS.subClassOf, URIRef(f"{CORE_NS}Industry")))
        return industries[name]

    # core:Industry parent class
    core_industry = URIRef(f"{CORE_NS}Industry")
    g.add((core_industry, RDF.type, OWL.Class))
    g.add((core_industry, RDFS.label, Literal("산업 분류", lang="ko")))

    # Disjoint axioms
    added_vetted = 0
    added_candidate = 0
    audit = []
    for e in filtered:
        a_name = e.get("domain_a", "")
        b_name = e.get("domain_b", "")
        if not a_name or not b_name or a_name == b_name:
            continue
        a_iri = get_industry_iri(a_name)
        b_iri = get_industry_iri(b_name)
        level = str(e.get("level") or "candidate")
        confidence = float(e.get("confidence") or 0)
        reason = str(e.get("reason") or "")[:200]

        if level == "vetted":
            # Hard DisjointClasses
            g.add((a_iri, OWL.disjointWith, b_iri))
            added_vetted += 1
        else:
            # Soft: disjointWith pair + level annotation (rdfs:comment)
            # 과거에 owl:AllDisjointClasses + owl:members BNode placeholder를
            # 동시에 emit하던 dead code가 있었으나 빈 rdf:List를 만들어
            # Openllet에서 "Invalid _list structure" WARNING의 원인이었음.
            # disjointWith pair-form만으로 동일 의미를 표현하므로 제거.
            g.add((a_iri, OWL.disjointWith, b_iri))
            g.add((a_iri, RDFS.comment, Literal(f"disjoint:candidate {b_name} conf={confidence:.2f}", lang="ko")))
            added_candidate += 1

        audit.append(
            {
                "a": a_name,
                "b": b_name,
                "level": level,
                "confidence": confidence,
                "a_iri": str(a_iri),
                "b_iri": str(b_iri),
            }
        )

    print(f"Industries declared: {len(industries)}")
    print(f"Disjoint axioms added: vetted={added_vetted}, candidate={added_candidate}")
    print(f"Triples total: {len(g)}")

    OUT_TTL.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(OUT_TTL), format="turtle")
    print(f"\nSaved: {OUT_TTL.relative_to(REPO_ROOT)}")

    AUDIT_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "scope": args.scope,
                "min_conf": args.min_conf,
                "industries_count": len(industries),
                "vetted_disjoint_count": added_vetted,
                "candidate_disjoint_count": added_candidate,
                "audit_sample": audit[:20],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved audit: {AUDIT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
