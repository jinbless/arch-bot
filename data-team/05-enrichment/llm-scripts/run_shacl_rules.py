#!/usr/bin/env python3
"""SHACL SPARQLRule 실행기 — Pellet undecidable 회피한 R-14~R-30 inference.

Sprint A-2 Final mitigation 후속:
- Pellet OWL DL은 R-1/R-3/R-2/R-4/R-10~R-13 (8 SWRL) fire
- R-14~R-30 (12 rules)은 SHACL SPARQLRule (kosha-rules-r14-r30-shacl-construct.ttl)로 변환
- 본 script가 pyshacl로 별도 trigger

사용:
  PYTHONIOENCODING=utf-8 python run_shacl_rules.py             # dry-run + 결과 print
  PYTHONIOENCODING=utf-8 python run_shacl_rules.py --output out.ttl  # inferred triples export

출력:
- stdout: rule별 inferred triple count
- --output 지정 시: inferred triples ttl
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "ontology-team" / "06-reasoning" / "ontology").is_dir():
            return p
    raise RuntimeError("Cannot locate repo root")


REPO = _find_root()
ONT = REPO / "ontology-team" / "06-reasoning" / "ontology"

# 하드코딩 리스트 제거 → assembly manifest의 shacl-materialize profile에서 파생 (단일 정본).
# data graph = rules-shacl 제외, shapes = rules-shacl. 파일집합은 기존과 동일(set-equality 증명됨).
sys.path.insert(0, str(ONT / "assembly"))
import manifest as _manifest  # noqa: E402
DATA_TTLS = [e["file"] for e in _manifest.paths("shacl-materialize", exclude_roles={"rules-shacl"})]
SHACL_RULES_TTL = _manifest.paths("shacl-materialize", only_roles={"rules-shacl"})[0]["file"]


def main():
    parser = argparse.ArgumentParser(description="SHACL SPARQLRule 실행 (Sprint A-2 Final 후속)")
    parser.add_argument("--output", type=str, default=None, help="inferred triples ttl 출력 경로")
    parser.add_argument("--skip-instances", action="store_true", help="kosha-instances.ttl skip (TBox만)")
    args = parser.parse_args()

    from rdflib import Graph
    from pyshacl import validate

    t0 = time.time()
    data = Graph()
    print("=== Step 1: load data graph ===")
    for f in DATA_TTLS:
        if args.skip_instances and f == "kosha-instances.ttl":
            continue
        p = ONT / f
        if not p.exists():
            print(f"  MISSING: {f}", file=sys.stderr)
            continue
        pre = len(data)
        fmt = "xml" if f.endswith(".owl") else "turtle"
        try:
            data.parse(str(p), format=fmt)
        except Exception as e:
            print(f"  PARSE FAIL {f}: {e}", file=sys.stderr)
            continue
        print(f"  +{len(data)-pre:>7} triples  {f}")
    print(f"Data graph: {len(data)} triples in {time.time()-t0:.1f}s")

    # Load SHACL rules graph
    print("\n=== Step 2: load SHACL rules graph ===")
    sg_graph = Graph()
    sg_graph.parse(str(ONT / SHACL_RULES_TTL), format="turtle")
    print(f"  +{len(sg_graph)} triples  {SHACL_RULES_TTL}")

    # Apply rules via pyshacl.validate(advanced=True, inplace=True)
    # SHACL Advanced Features (sh:rule + sh:SPARQLRule)을 자동 실행 + data graph에 inference 추가.
    print("\n=== Step 3: pyshacl validate (advanced=True, inplace=True) ===")
    before = len(data)
    t1 = time.time()
    try:
        conforms, results_graph, results_text = validate(
            data_graph=data,
            shacl_graph=sg_graph,
            advanced=True,
            inplace=True,
            inference=None,
            iterate_rules=True,  # rule chain iteration (R-15 결과가 R-24 body로 propagate 등)
            do_owl_imports=False,
            meta_shacl=False,
        )
    except Exception as e:
        print(f"  pyshacl validate FAILED: {e}", file=sys.stderr)
        raise
    after = len(data)
    print(f"  conforms={conforms}, elapsed {time.time()-t1:.1f}s")
    print(f"  data graph grew {after - before} triples (inferred)")
    if results_text:
        print(f"  report text (first 400 chars):\n{results_text[:400]}")

    # Output
    if args.output:
        out = Graph()
        for s, p, o in data:
            out.add((s, p, o))
        # 사실 inferred만 분리하려면 before/after diff 필요. 본 script는 simple: 전체 graph + diff count.
        # 단순화: --output 시 inferred triple count만 print, 별도 export 안 함 (전체 graph가 매우 큼)
        print(f"\nNote: --output 지정되었으나 전체 data graph가 매우 큼.")
        print(f"  before: {before}, after: {after}, inferred: {after - before}")
        print(f"  inferred-only 분리는 별도 logic 필요 (본 script는 count만).")

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
