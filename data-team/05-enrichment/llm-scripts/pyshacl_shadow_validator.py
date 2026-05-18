#!/usr/bin/env python3
"""T2.A — F.3.1 pyshacl reasoner shadow channel.

F.3.2가 mining한 2240 incompatibility axiom이 KB JSON에 누적되어 있지만 dormant
(matcher가 application 안 함). 이 스크립트는 axiom을 SHACL+SPARQL shape으로
표현하고 pyshacl로 *shadow validation* 한다 — 실제 reject 안 함, 어떤 candidate
guide가 axiom 위반이었을지 log만.

사용:
  # Offline batch — analysis_log.jsonl 전체 shadow run
  python pyshacl_shadow_validator.py \\
    --input runtime-artifacts/analysis_log.jsonl \\
    --output runtime-artifacts/shadow_reasoner_log.jsonl \\
    --level all

  # Limit + verbose (디버깅)
  python pyshacl_shadow_validator.py --limit 50 --verbose

산출:
- shadow_reasoner_log.jsonl: per-row {scene_hash, industry_ko, industry_en,
  candidate_count, reasoner_rejects: [{guide_code, guide_domain, axiom_pair,
  confidence, reason}], skipped_reason?}

T2.B/C 후속:
- T2.B: 본 script가 in-memory로 빌드하는 SHACL을 TTL로 persist
- T2.C: cron에서 weekly run + drift detection input
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO = _find_repo_root()
ARTIFACTS = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"

AXIOMS_PATH = ARTIFACTS / "guide_domain_incompatibilities.json"
INDUSTRY_MAP_PATH = ARTIFACTS / "industry_ko_to_en_map.json"
GUIDE_DOMAINS_PATH = ARTIFACTS / "guide_llm_domains.json"
DEFAULT_INPUT = ARTIFACTS / "analysis_log.jsonl"
DEFAULT_OUTPUT = ARTIFACTS / "shadow_reasoner_log.jsonl"

# Local namespace for in-memory ABox
NS = "https://kosha.example/shadow#"


def load_axioms(level_filter: str = "all") -> dict[tuple[str, str], dict]:
    """Read F.3.2 incompatibility axioms.

    level_filter: 'all' / 'vetted' / 'candidate' / 'high_conf' (conf >= 0.8)
    Returns: {(domain_a, domain_b): {confidence, level, reason}} — both
    orderings inserted for fast lookup.
    """
    data = json.loads(AXIOMS_PATH.read_text(encoding="utf-8"))
    raw = data.get("incompatibilities", [])

    index: dict[tuple[str, str], dict] = {}
    for entry in raw:
        if not entry.get("incompatible"):
            continue
        level = entry.get("level", "candidate")
        conf = float(entry.get("confidence", 0) or 0)
        a = entry.get("domain_a")
        b = entry.get("domain_b")
        if not a or not b:
            continue
        if level_filter == "vetted" and level != "vetted":
            continue
        if level_filter == "candidate" and level != "candidate":
            continue
        if level_filter == "high_conf" and conf < 0.8:
            continue
        meta = {
            "confidence": conf,
            "level": level,
            "reason": entry.get("reason", ""),
        }
        # Both orderings (symmetric incompatibility)
        index[(a, b)] = meta
        index[(b, a)] = meta
    return index


def load_industry_map() -> dict[str, str]:
    """Read industry KO → EN mapping. Returns {ko: en}."""
    data = json.loads(INDUSTRY_MAP_PATH.read_text(encoding="utf-8"))
    mappings = data.get("mappings", {})
    return mappings


def load_guide_domains() -> dict[str, str]:
    """Read guide_code → primary_domain. Returns {guide_code: en_domain}."""
    data = json.loads(GUIDE_DOMAINS_PATH.read_text(encoding="utf-8"))
    classifications = data.get("classifications", {})
    out: dict[str, str] = {}
    for code, info in classifications.items():
        pd = info.get("primary_domain")
        if pd:
            out[code] = pd
    return out


def validate_direct(
    industry_en: str,
    guide_code_domain_pairs: list[tuple[str, str]],
    axioms_index: dict[tuple[str, str], dict],
) -> list[dict]:
    """Direct dict lookup (fast path).

    For each (guide_code, guide_domain): check (industry_en, guide_domain) ∈ axioms.
    Returns list of violation records.
    """
    rejects: list[dict] = []
    for guide_code, guide_domain in guide_code_domain_pairs:
        if not guide_domain:
            continue
        meta = axioms_index.get((industry_en, guide_domain))
        if meta is None:
            continue
        rejects.append({
            "guide_code": guide_code,
            "guide_domain": guide_domain,
            "axiom_pair": [industry_en, guide_domain],
            "confidence": meta["confidence"],
            "level": meta["level"],
            "reason": (meta.get("reason") or "")[:200],
        })
    return rejects


def validate_pyshacl(
    industry_en: str,
    guide_code_domain_pairs: list[tuple[str, str]],
    axioms_index: dict[tuple[str, str], dict],
) -> list[dict]:
    """pyshacl SHACL+SPARQL constraint validation (cross-check path).

    Builds in-memory rdflib graph with:
      - ABox: photo + candidate guides + their domains
      - TBox/SHACL: NodeShape with sh:sparql that finds incompatible pairs
      - Data: axioms as triples

    Returns list of violation records (same shape as validate_direct).
    """
    from rdflib import Graph, Literal, URIRef, Namespace
    from rdflib.namespace import RDF, SH
    from pyshacl import validate

    ns = Namespace(NS)
    g = Graph()
    g.bind("ks", ns)
    g.bind("sh", SH)

    # ABox: photo
    photo = ns["photo1"]
    g.add((photo, RDF.type, ns.Photo))
    g.add((photo, ns.hasIndustry, Literal(industry_en)))

    # ABox: candidate guides
    for i, (gc, gd) in enumerate(guide_code_domain_pairs):
        guide_uri = ns[f"guide_{i}"]
        g.add((guide_uri, RDF.type, ns.Guide))
        g.add((guide_uri, ns.guideCode, Literal(gc)))
        g.add((guide_uri, ns.hasDomain, Literal(gd or "")))
        g.add((photo, ns.hasCandidateGuide, guide_uri))

    # Data: axioms (only relevant ones to keep graph small)
    relevant_axioms = set()
    for gc, gd in guide_code_domain_pairs:
        if not gd:
            continue
        if (industry_en, gd) in axioms_index:
            relevant_axioms.add((industry_en, gd))
            relevant_axioms.add((gd, industry_en))  # symmetric
    for a, b in relevant_axioms:
        axiom_uri = ns[f"axiom_{abs(hash((a, b)))}"]
        g.add((axiom_uri, RDF.type, ns.Incompatibility))
        g.add((axiom_uri, ns.domainA, Literal(a)))
        g.add((axiom_uri, ns.domainB, Literal(b)))

    # Shapes: SHACL+SPARQL constraint
    shapes_g = Graph()
    shapes_g.bind("ks", ns)
    shapes_g.bind("sh", SH)

    shape_uri = ns["IncompatibilityShape"]
    constraint_node = ns["IncompatibilityConstraint"]

    shapes_g.add((shape_uri, RDF.type, SH.NodeShape))
    shapes_g.add((shape_uri, SH.targetClass, ns.Photo))
    shapes_g.add((shape_uri, SH.sparql, constraint_node))

    shapes_g.add((constraint_node, RDF.type, SH.SPARQLConstraint))
    shapes_g.add((constraint_node, SH.message,
                  Literal("Photo industry incompatible with candidate guide domain")))
    # SHACL spec: ?value variable auto-maps to sh:value in ValidationResult.
    # Use ?value (not ?guide) so violations carry the offending guide URI.
    select_query = f"""
    PREFIX ks: <{NS}>
    SELECT $this ?value ?gd WHERE {{
      $this ks:hasIndustry ?industry .
      $this ks:hasCandidateGuide ?value .
      ?value ks:hasDomain ?gd .
      ?axiom a ks:Incompatibility ;
             ks:domainA ?industry ;
             ks:domainB ?gd .
    }}
    """
    shapes_g.add((constraint_node, SH.select, Literal(select_query)))

    # Run pyshacl
    conforms, results_graph, _results_text = validate(
        g,
        shacl_graph=shapes_g,
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
        meta_shacl=False,
        advanced=True,
        debug=False,
    )

    if conforms:
        return []

    # Parse violations: extract focus + value from results_graph
    rejects: list[dict] = []
    # pyshacl reports validation results with sh:result → ValidationResult
    # ValidationResult.sh:focusNode = photo, sh:value = guide URI
    for vr in results_graph.subjects(RDF.type, SH.ValidationResult):
        guide_uri = results_graph.value(vr, SH.value)
        if guide_uri is None:
            continue
        # Look up guide_code and guide_domain from data graph
        gc = g.value(guide_uri, ns.guideCode)
        gd = g.value(guide_uri, ns.hasDomain)
        if gc is None or gd is None:
            continue
        meta = axioms_index.get((industry_en, str(gd)))
        if meta is None:
            continue
        rejects.append({
            "guide_code": str(gc),
            "guide_domain": str(gd),
            "axiom_pair": [industry_en, str(gd)],
            "confidence": meta["confidence"],
            "level": meta["level"],
            "reason": (meta.get("reason") or "")[:200],
            "via": "pyshacl",
        })
    return rejects


def process_row(
    row: dict,
    axioms_index: dict[tuple[str, str], dict],
    industry_map: dict[str, str],
    guide_domains: dict[str, str],
    use_pyshacl: bool = False,
) -> dict:
    """Process a single analysis_log row → shadow_reasoner_log row.

    Returns dict with at minimum {scene_hash, industry_ko, industry_en,
    candidate_count, reasoner_rejects, mode}. Includes skipped_reason if
    bypassed (e.g., empty candidates, unmapped industry).
    """
    scene_hash = row.get("scene_hash", "")
    industry_ko = row.get("industry", "") or ""
    mode = row.get("mode", "")
    candidates_raw = row.get("excluded", [])  # we look at LLM-excluded too
    # But the "candidate_codes" need to come from candidate_count + actual list — analysis_log doesn't store
    # full list, only count. We can shadow against what we have.
    # For F.3.2 shadow we need the actual candidate codes — fallback: skip if no codes
    candidate_count = row.get("candidate_count", 0)

    # analysis_log doesn't store full candidate code list — work from excluded list
    # (LLM-rejected ones) as proxy: shadow check whether axiom would have
    # additionally rejected anything.
    # Better: in T2.C live integration we can hook before exclusion.
    excluded_codes = [
        e.get("guide_code") for e in candidates_raw
        if isinstance(e, dict) and e.get("guide_code")
    ]

    out: dict = {
        "scene_hash": scene_hash,
        "industry_ko": industry_ko,
        "mode": mode,
        "candidate_count": candidate_count,
        "excluded_count": len(excluded_codes),
        "reasoner_rejects": [],
    }

    industry_en = industry_map.get(industry_ko)
    if not industry_en:
        out["skipped_reason"] = f"unmapped_industry:{industry_ko}"
        out["industry_en"] = None
        return out
    out["industry_en"] = industry_en

    if not excluded_codes:
        out["skipped_reason"] = "no_candidate_codes_in_log"
        return out

    pairs: list[tuple[str, str]] = []
    for gc in excluded_codes:
        gd = guide_domains.get(gc, "")
        pairs.append((gc, gd))

    # Always run direct lookup (fast, deterministic)
    direct_rejects = validate_direct(industry_en, pairs, axioms_index)
    out["reasoner_rejects"] = direct_rejects

    if use_pyshacl and pairs:
        try:
            pyshacl_rejects = validate_pyshacl(industry_en, pairs, axioms_index)
            # Compare: should match direct_rejects (sanity check)
            direct_keys = {(r["guide_code"], r["guide_domain"]) for r in direct_rejects}
            pyshacl_keys = {(r["guide_code"], r["guide_domain"]) for r in pyshacl_rejects}
            if direct_keys != pyshacl_keys:
                out["pyshacl_disagreement"] = {
                    "direct_only": sorted(direct_keys - pyshacl_keys),
                    "pyshacl_only": sorted(pyshacl_keys - direct_keys),
                }
        except Exception as exc:
            out["pyshacl_error"] = str(exc)[:200]

    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--input", default=str(DEFAULT_INPUT),
                    help="analysis_log.jsonl path (default: runtime-artifacts/analysis_log.jsonl)")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT),
                    help="shadow_reasoner_log.jsonl path")
    ap.add_argument("--level", choices=["all", "vetted", "candidate", "high_conf"],
                    default="all", help="axiom level filter")
    ap.add_argument("--limit", type=int, default=0,
                    help="process at most N rows (0 = all)")
    ap.add_argument("--pyshacl", action="store_true",
                    help="cross-check via pyshacl (slower; default off for speed)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 1

    print(f"Loading axioms (level={args.level})...")
    axioms_index = load_axioms(args.level)
    print(f"  axiom pairs (both orderings): {len(axioms_index)}")
    if not axioms_index:
        print("WARN: 0 axioms after filter → reasoner_rejects always []", file=sys.stderr)

    print(f"Loading industry KO→EN map...")
    industry_map = load_industry_map()
    print(f"  mapped industries: {len(industry_map)}")

    print(f"Loading guide_code → primary_domain...")
    guide_domains = load_guide_domains()
    print(f"  mapped guides: {len(guide_domains)}")

    print(f"\nProcessing {input_path.name} → {output_path.name}")
    start = time.time()
    processed = 0
    with_rejects = 0
    skipped = 0
    pyshacl_disagreements = 0
    pyshacl_errors = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as fin, \
         output_path.open("w", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                if args.verbose:
                    print(f"  L{line_no}: JSON decode fail: {exc}", file=sys.stderr)
                continue
            try:
                result = process_row(row, axioms_index, industry_map, guide_domains,
                                     use_pyshacl=args.pyshacl)
            except Exception as exc:
                if args.verbose:
                    import traceback
                    print(f"  L{line_no}: process_row failed: {exc}", file=sys.stderr)
                    traceback.print_exc()
                continue

            result["_processed_at"] = datetime.now(timezone.utc).isoformat()
            fout.write(json.dumps(result, ensure_ascii=False) + "\n")

            processed += 1
            if result.get("reasoner_rejects"):
                with_rejects += 1
            if result.get("skipped_reason"):
                skipped += 1
            if result.get("pyshacl_disagreement"):
                pyshacl_disagreements += 1
            if result.get("pyshacl_error"):
                pyshacl_errors += 1

            if args.verbose and processed <= 5:
                print(f"  [{processed}] industry_ko={row.get('industry','')!r} → "
                      f"en={result.get('industry_en')!r}, "
                      f"rejects={len(result['reasoner_rejects'])}, "
                      f"skip={result.get('skipped_reason')}")

            if args.limit and processed >= args.limit:
                break

    elapsed = time.time() - start
    print(f"\n=== Summary ===")
    print(f"Processed: {processed} rows in {elapsed:.1f}s "
          f"({processed/max(elapsed,0.01):.0f} rows/s)")
    print(f"  with reasoner_rejects: {with_rejects}")
    print(f"  skipped (unmapped/no-codes): {skipped}")
    if args.pyshacl:
        print(f"  pyshacl disagreements: {pyshacl_disagreements}")
        print(f"  pyshacl errors: {pyshacl_errors}")
    print(f"Output: {output_path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
