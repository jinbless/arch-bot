#!/usr/bin/env python3
"""T2.B — F.3.4 KB compile to TTL (SHACL candidates) + Fuseki reload prep.

기존 build_disjoint_axioms.py는 vetted+candidate 모두 owl:disjointWith로
같은 TTL에 emit → Fuseki/Openllet은 둘 다 hard reject. candidate는
"실험 상태"임을 ontology level에서도 표현해야 하므로:

  - build_disjoint_axioms.py: vetted → hard owl:DisjointClasses (production)
  - 본 script:               candidate → SHACL NodeShape sh:Info (shadow)

산출 분리:
  - ontology-team/06-reasoning/ontology/kosha-disjoint-axioms.ttl (vetted hard)
  - ontology-team/06-reasoning/ontology/kb-candidates.ttl         (candidate shadow)

Fuseki Java server는 read-only (allowUpdate=false, /ontology mounted :ro).
신규 TTL 적용 시 container restart 필요 (~30 min 부팅, openllet reasoner 재load).

사용:
  # Default: candidate (level=candidate, min_conf=0.7) → kb-candidates.ttl
  python compile_kb_to_ttl.py

  # min confidence 조정
  python compile_kb_to_ttl.py --min-conf 0.8

  # scope 전환 (검증용)
  python compile_kb_to_ttl.py --scope vetted --out kb-vetted-shacl.ttl
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO = _find_repo_root()
ONTOLOGY_DIR = REPO / "ontology-team" / "06-reasoning" / "ontology"
ARTIFACTS = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"

KB_PATH = ARTIFACTS / "guide_domain_incompatibilities.json"
IND_MAP_PATH = ARTIFACTS / "industry_ko_to_en_map.json"
DEFAULT_OUT = ONTOLOGY_DIR / "kb-candidates.ttl"
AUDIT_PATH = ARTIFACTS / "kb_candidates_compile_audit.json"

IND_NS = "https://cashtoss.info/ontology/industry#"
CORE_NS = "https://cashtoss.info/ontology#"
SH_NS = "http://www.w3.org/ns/shacl#"
KB_NS = "https://kosha.example/kb-candidate#"


def load_industry_map() -> dict[str, str]:
    if not IND_MAP_PATH.exists():
        raise FileNotFoundError(f"{IND_MAP_PATH} missing.")
    payload = json.loads(IND_MAP_PATH.read_text(encoding="utf-8"))
    return payload.get("mappings", {})


def sanitize_local_name(name: str, industry_map: dict[str, str], en_codes: set[str]) -> str | None:
    """Resolve name → Industry_{EN} URI local name.

    KB JSON entries may carry either:
      - KO industry name (early vetted entries): map via industry_ko_to_en_map
      - EN code already (F.3.2 candidate entries): use directly if in en_codes set

    Returns None for unrecognized inputs (skipped, not hard-error like
    build_disjoint_axioms.py which serves production-strict vetted path).
    """
    name = name.strip()
    # First try KO → EN map
    en = industry_map.get(name)
    if en:
        return f"Industry_{en}"
    # Then check if name already is a known EN code
    if name in en_codes:
        return f"Industry_{name}"
    return None  # unmapped


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--scope", choices=("vetted", "candidate", "both"),
                    default="candidate",
                    help="default: candidate (shadow shapes only)")
    ap.add_argument("--min-conf", type=float, default=0.7,
                    help="min confidence threshold (default 0.7)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"output TTL path (default: {DEFAULT_OUT.relative_to(REPO)})")
    ap.add_argument("--severity", choices=("Info", "Warning", "Violation"),
                    default="Info",
                    help="SHACL severity for candidates (default Info)")
    args = ap.parse_args()

    if not KB_PATH.exists():
        print(f"ERROR: KB not found: {KB_PATH}", file=sys.stderr)
        return 1

    from rdflib import Graph, Namespace, URIRef, Literal, BNode
    from rdflib.namespace import RDF, RDFS, OWL, SH

    industry_map = load_industry_map()
    en_codes_set = set(industry_map.values())
    print(f"Loaded industry map: {len(industry_map)} KO → {len(en_codes_set)} EN")

    payload = json.loads(KB_PATH.read_text(encoding="utf-8"))
    entries = payload.get("incompatibilities", [])

    # Filter
    selected = []
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
        selected.append(e)
    print(f"Filtered: {len(selected)} entries (scope={args.scope}, min_conf={args.min_conf})")

    # Build graph
    g = Graph()
    g.bind("industry", Namespace(IND_NS))
    g.bind("core", Namespace(CORE_NS))
    g.bind("sh", SH)
    g.bind("owl", OWL)
    g.bind("kb", Namespace(KB_NS))

    kb_ns = Namespace(KB_NS)
    sh_ns = Namespace(SH_NS)
    sh_severity_iri = {
        "Info": SH.Info,
        "Warning": SH.Warning,
        "Violation": SH.Violation,
    }[args.severity]

    industries_declared: set[URIRef] = set()
    audit: list[dict] = []
    skipped_unmapped: list[dict] = []

    def declare_industry(name: str) -> URIRef | None:
        local = sanitize_local_name(name, industry_map, en_codes_set)
        if local is None:
            return None
        iri = URIRef(f"{IND_NS}{local}")
        if iri not in industries_declared:
            industries_declared.add(iri)
            g.add((iri, RDF.type, OWL.Class))
            g.add((iri, RDFS.subClassOf, URIRef(f"{CORE_NS}Industry")))
            # Label language: ko if name is KO (in industry_map), en otherwise
            label_lang = "ko" if name in industry_map else "en"
            g.add((iri, RDFS.label, Literal(name, lang=label_lang)))
        return iri

    # KB header
    kb_meta = kb_ns["KbCandidatesGraph"]
    g.add((kb_meta, RDF.type, OWL.Ontology))
    g.add((kb_meta, RDFS.comment, Literal(
        f"F.3.2 candidate incompatibilities — shadow shapes (sh:{args.severity}). "
        f"Generated at {datetime.now(timezone.utc).isoformat()}. "
        "Vetted axioms live separately in kosha-disjoint-axioms.ttl.",
        lang="en"
    )))

    # Emit one SHACL NodeShape per axiom pair.
    # Shape semantics: a Photo with industry=A SHOULD NOT have candidate guide
    # whose domain=B (sh:not + sh:hasValue path). Severity Info = shadow.
    added = 0
    for idx, e in enumerate(selected):
        a_name = e.get("domain_a", "").strip()
        b_name = e.get("domain_b", "").strip()
        if not a_name or not b_name or a_name == b_name:
            continue
        a_iri = declare_industry(a_name)
        b_iri = declare_industry(b_name)
        if a_iri is None:
            skipped_unmapped.append({"reason": "unmapped_a", "name": a_name})
            continue
        if b_iri is None:
            skipped_unmapped.append({"reason": "unmapped_b", "name": b_name})
            continue

        conf = float(e.get("confidence") or 0)
        reason = str(e.get("reason") or "")[:300]

        shape_iri = kb_ns[f"Shape_{idx:05d}_{a_iri.split('#')[-1]}_x_{b_iri.split('#')[-1]}"]
        g.add((shape_iri, RDF.type, SH.NodeShape))
        # Note: we don't set sh:targetClass because we want this shape to be
        # picked up by validators that explicitly load this graph (e.g.,
        # local_consistency_check.py with --shapes kb-candidates.ttl).
        # Production runtime uses shadow_reasoner.py directly.
        g.add((shape_iri, SH.severity, sh_severity_iri))
        g.add((shape_iri, SH.message, Literal(
            f"Candidate incompatibility (conf={conf:.2f}): {a_name} x {b_name}",
            lang="ko"
        )))
        # Annotate as RDFS comment for human review
        g.add((shape_iri, RDFS.comment, Literal(f"reason: {reason}", lang="ko")))
        g.add((shape_iri, kb_ns.domainA, a_iri))
        g.add((shape_iri, kb_ns.domainB, b_iri))
        g.add((shape_iri, kb_ns.confidence, Literal(conf)))
        g.add((shape_iri, kb_ns.level, Literal(str(e.get("level") or "candidate"))))
        added += 1

        audit.append({
            "shape_iri": str(shape_iri),
            "a": a_name, "b": b_name,
            "a_iri": str(a_iri), "b_iri": str(b_iri),
            "confidence": conf, "level": e.get("level"),
        })

    print(f"Industries declared: {len(industries_declared)}")
    print(f"SHACL NodeShapes added: {added} (severity=sh:{args.severity})")
    if skipped_unmapped:
        print(f"Skipped (unmapped industries): {len(skipped_unmapped)}")
    print(f"Total triples: {len(g)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(args.out), format="turtle")
    print(f"\nSaved: {args.out.relative_to(REPO)}")

    AUDIT_PATH.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": args.scope,
        "min_conf": args.min_conf,
        "severity": args.severity,
        "out": str(args.out.relative_to(REPO)),
        "industries_declared": len(industries_declared),
        "shapes_added": added,
        "skipped_unmapped": skipped_unmapped[:20],
        "audit_sample": audit[:30],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Audit: {AUDIT_PATH.relative_to(REPO)}")

    # Fuseki reload notes
    print("\n=== Fuseki reload (T2.B) ===")
    print("Java v2 server: read-only (allowUpdate=false), /ontology mounted :ro.")
    print("To activate this TTL in Fuseki:")
    print("  1. Edit ontology-team/06-reasoning/ontology/docker/fuseki/src/main/java/")
    print("     kr/or/kosha/KoshaFusekiServer.java → ontology load list 추가")
    print(f"     ex: {{\"/{args.out.name}\", \"TURTLE\", \"F.3.2 SHACL candidates\"}}")
    print("  2. Rebuild + restart container (cd docker && docker compose build fuseki &&")
    print("     docker compose restart fuseki)")
    print("  3. Wait ~30 min for Openllet reasoner reload")
    print("  4. Verify via SPARQL: SELECT * WHERE { ?s a sh:NodeShape } LIMIT 5")
    print()
    print("Alternative (dev iteration): use shadow_reasoner.py runtime module")
    print("  (already integrated in T2.A — no Fuseki restart needed).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
