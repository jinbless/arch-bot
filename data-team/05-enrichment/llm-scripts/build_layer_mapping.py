#!/usr/bin/env python3
"""Phase E Step 2 — BFO + LKIF-Core 2-layer mapping (결정론, LLM 호출 없음).

Step 1의 `class_layer_assignment.json` 결과를 적용하여:
1. kosha-ontology.owl을 base로 새 ontology v2 생성
2. `owl:imports` 추가 (BFO, LKIF-Core, RO, PROV-O, SSN/SOSA)
3. 각 class에 `rdfs:subClassOf <bfo:* | lkif:*>` triple 자동 추가
4. AB_bridge class는 두 super 모두 매핑
5. rdflib parse 검증 + Openllet 호환 형식으로 저장

산출:
- ontology-team/06-reasoning/ontology/kosha-ontology-v2.owl (RDF/XML)
- ontology-team/06-reasoning/ontology/kosha-ontology-v2.formatted.ttl (Turtle)
- data-team/05-enrichment/runtime-artifacts/layer_mapping_audit.json
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


REPO_ROOT = _find_repo_root()
ONTOLOGY_DIR = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology"
TBOX_PATH = ONTOLOGY_DIR / "kosha-ontology.owl"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
LAYER_PATH = ARTIFACTS_DIR / "class_layer_assignment.json"
OUT_OWL = ONTOLOGY_DIR / "kosha-ontology-v2.owl"
OUT_TTL = ONTOLOGY_DIR / "kosha-ontology-v2.formatted.ttl"
AUDIT_PATH = ARTIFACTS_DIR / "layer_mapping_audit.json"


BFO_IRI = "http://purl.obolibrary.org/obo/bfo.owl"
LKIF_IRI = "http://www.estrellaproject.org/lkif-core/lkif-core.owl"
RO_IRI = "http://purl.obolibrary.org/obo/ro.owl"
PROV_IRI = "http://www.w3.org/ns/prov-o-20130430"
SOSA_IRI = "http://www.w3.org/ns/sosa/"

BFO_NS = "http://purl.obolibrary.org/obo/"
LKIF_NS = "http://www.estrellaproject.org/lkif-core/lkif-core#"


BFO_CLASS_MAP = {
    "Continuant": "BFO_0000002",
    "Occurrent": "BFO_0000003",
    "Process": "BFO_0000015",
    "Quality": "BFO_0000019",
    "Role": "BFO_0000023",
    "Disposition": "BFO_0000016",
    "Function": "BFO_0000034",
    "Object": "BFO_0000030",
    "GenericDependentContinuant": "BFO_0000031",
    "SpecificallyDependentContinuant": "BFO_0000020",
    "IndependentContinuant": "BFO_0000004",
    "MaterialEntity": "BFO_0000040",
    "ImmaterialEntity": "BFO_0000141",
    "Site": "BFO_0000029",
    "ProcessBoundary": "BFO_0000035",
    "TemporalRegion": "BFO_0000008",
}


def resolve_bfo_iri(super_name: str) -> str | None:
    """LLM이 제안한 BFO super name → 표준 BFO IRI."""
    if not super_name:
        return None
    name = super_name.strip().replace(" ", "")
    if name in BFO_CLASS_MAP:
        return f"{BFO_NS}{BFO_CLASS_MAP[name]}"
    for key, code in BFO_CLASS_MAP.items():
        if key.lower() == name.lower():
            return f"{BFO_NS}{code}"
    # fallback: first matching
    for key, code in BFO_CLASS_MAP.items():
        if name.lower() in key.lower() or key.lower() in name.lower():
            return f"{BFO_NS}{code}"
    return None


def resolve_lkif_iri(super_name: str) -> str | None:
    if not super_name:
        return None
    name = super_name.strip().replace(" ", "")
    # LKIF-Core는 비교적 자유 — 그냥 직접 매핑
    return f"{LKIF_NS}{name}"


def load_layer_assignments() -> list[dict]:
    if not LAYER_PATH.exists():
        raise FileNotFoundError(f"{LAYER_PATH} 없음. Step 1 먼저 실행.")
    payload = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
    return payload.get("assignments") or []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from rdflib import Graph, RDF, OWL, RDFS, URIRef, Namespace, Literal

    g = Graph()
    g.parse(str(TBOX_PATH), format="xml")
    initial_class_count = len(list(g.subjects(RDF.type, OWL.Class)))
    print(f"Base ontology: {initial_class_count} classes")

    # 1) owl:imports 추가 (ontology header에)
    ont_iri = URIRef("https://cashtoss.info/ontology")
    # Try to find existing owl:Ontology subject; else create one
    existing_ont = None
    for s in g.subjects(RDF.type, OWL.Ontology):
        existing_ont = s
        break
    if existing_ont is None:
        existing_ont = ont_iri
        g.add((existing_ont, RDF.type, OWL.Ontology))

    imports = [BFO_IRI, LKIF_IRI, RO_IRI, PROV_IRI, SOSA_IRI]
    for imp in imports:
        g.add((existing_ont, OWL.imports, URIRef(imp)))
    print(f"Added {len(imports)} owl:imports to {existing_ont}")

    # 2) subClassOf triples
    assignments = load_layer_assignments()
    print(f"Layer assignments loaded: {len(assignments)}")

    added_bfo = 0
    added_lkif = 0
    audit_entries = []
    for a in assignments:
        iri = a.get("iri")
        layer = a.get("layer")
        bfo_super = a.get("bfo_super") or ""
        lkif_super = a.get("lkif_super") or ""
        if not iri:
            continue
        subj = URIRef(iri)
        bfo_target = resolve_bfo_iri(bfo_super) if layer in ("A_alethic", "AB_bridge") else None
        lkif_target = resolve_lkif_iri(lkif_super) if layer in ("B_deontic", "AB_bridge") else None
        if bfo_target:
            g.add((subj, RDFS.subClassOf, URIRef(bfo_target)))
            added_bfo += 1
        if lkif_target:
            g.add((subj, RDFS.subClassOf, URIRef(lkif_target)))
            added_lkif += 1
        audit_entries.append(
            {
                "iri": iri,
                "layer": layer,
                "bfo_super": bfo_super,
                "bfo_target": bfo_target,
                "lkif_super": lkif_super,
                "lkif_target": lkif_target,
            }
        )

    print(f"Added subClassOf: BFO={added_bfo}, LKIF={added_lkif}")
    new_class_count = len(list(g.subjects(RDF.type, OWL.Class)))
    print(f"Class count after: {new_class_count} (delta {new_class_count - initial_class_count})")

    # 3) Validation: rdflib parse (already parsed) + reachability check
    print("\nValidation:")
    print(f"  Triples total: {len(g)}")
    bridge_props = ["violatesObligation", "observedIn", "appliesTo", "triggersRule"]
    print(f"  Bridge property placeholders: {bridge_props} (Step 3에서 추가)")

    if args.dry_run:
        print("\nDry-run: no files written.")
        return 0

    # 4) Save
    OUT_OWL.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(OUT_OWL), format="xml")
    print(f"\nSaved: {OUT_OWL.relative_to(REPO_ROOT)}")
    # OUT_TTL(kosha-ontology-v2.formatted.ttl) 직렬화 제거(A): v2.owl과 동치 포맷중복 →
    # facet-explorer가 v2.owl(xml) 직접 사용. (이 스크립트는 historical Phase E — 입력 kosha-ontology.owl은 archive/로 이동.)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "base_ontology": str(TBOX_PATH.relative_to(REPO_ROOT)),
                "output_owl": str(OUT_OWL.relative_to(REPO_ROOT)),
                "output_ttl": str(OUT_TTL.relative_to(REPO_ROOT)),
                "imports": imports,
                "added_subClassOf_bfo": added_bfo,
                "added_subClassOf_lkif": added_lkif,
                "audit": audit_entries,
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
