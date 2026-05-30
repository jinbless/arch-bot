#!/usr/bin/env python3
"""Phase E Step 5b — Local consistency check (rdflib + pyshacl + owlrl).

Fuseki container Java code가 v1 ontology만 load하므로 Openllet OWL DL 직접 사용 곤란.
대신 Python 기반 reasoner로:
1. rdflib parse — v2 ontology + disjoint + SWRL + SHACL 모두 load
2. owlrl OWL RL inference — OWL DL의 subset이지만 충분
3. pyshacl SHACL validation — instance 검증
4. SPARQL CQ 자동 실행 — coverage 측정

산출:
- local_consistency_report.json
- updated sparql_cq_coverage.json (in-memory query 결과)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
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

# 하드코딩 리스트 제거 → assembly manifest의 consistency profile에서 파생 (단일 정본).
sys.path.insert(0, str(ONTOLOGY_DIR / "assembly"))
import manifest as _manifest  # noqa: E402
_CONS = {e["id"]: e for e in _manifest.load_profile("consistency")}
V2_OWL = _CONS["base-v2-owl"]["path"]
DISJOINT_TTL = _CONS["disjoint-axioms"]["path"]
SHAPES_V2 = _CONS["shapes-serving-v3"]["path"]  # SHACL 검증용(merged graph 아님)
INSTANCES_TTL = _CONS["abox-instances"]["path"]
CQ_PATH = ARTIFACTS_DIR / "sparql_cq_coverage.json"

OUT_REPORT = ARTIFACTS_DIR / "local_consistency_report.json"

# Phase A-J merged graph = consistency profile에서 (base/disjoint/shapes/instances 제외) 나머지.
# SHAPES_V2(serving-v3)는 별도 SHACL 검증용이라 제외, vetted-disjoint-shapes 등은 포함(g 병합).
_MERGED_SPECIAL = {"base-v2-owl", "disjoint-axioms", "shapes-serving-v3", "abox-instances"}
PHASE_AJ_TTLS = [e["path"] for e in _manifest.load_profile("consistency")
                 if e["id"] not in _MERGED_SPECIAL]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-instances", action="store_true", help="ABox 1M lines skip (빠른 TBox만 검증)")
    parser.add_argument("--skip-shacl", action="store_true")
    parser.add_argument("--skip-sparql", action="store_true")
    args = parser.parse_args()

    from rdflib import Graph

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "steps": [],
    }

    # Step 1 — Load all v2 artifacts
    print("=== Step 1: rdflib parse ===")
    start = time.time()
    g = Graph()
    try:
        g.parse(str(V2_OWL), format="xml")
        print(f"  {V2_OWL.name}: {len(g)} triples")
    except Exception as exc:
        print(f"  FAIL {V2_OWL.name}: {exc}", file=sys.stderr)
        report["steps"].append({"step": "parse_v2_owl", "status": "fail", "error": str(exc)})
        return 1
    initial = len(g)

    try:
        g.parse(str(DISJOINT_TTL), format="turtle")
        print(f"  + {DISJOINT_TTL.name}: {len(g)} triples total (+{len(g) - initial})")
        initial = len(g)
    except Exception as exc:
        print(f"  WARN {DISJOINT_TTL.name}: {exc}")

    # Sprint D 확장: Phase A-J 신규 ttl 모두 load
    for tpath in PHASE_AJ_TTLS:
        if not tpath.exists():
            continue
        try:
            g.parse(str(tpath), format="turtle")
            added = len(g) - initial
            initial = len(g)
            if added > 0:
                print(f"  + {tpath.name}: +{added} triples (total {len(g)})")
        except Exception as exc:
            print(f"  WARN {tpath.name}: {exc}")

    if not args.skip_instances:
        print(f"  Loading {INSTANCES_TTL.name} (1.06M lines, ~30s)...", flush=True)
        try:
            g.parse(str(INSTANCES_TTL), format="turtle")
            print(f"  + {INSTANCES_TTL.name}: {len(g)} triples total (+{len(g) - initial})")
        except Exception as exc:
            print(f"  WARN {INSTANCES_TTL.name}: {exc}")

    parse_time = time.time() - start
    print(f"  parse elapsed: {parse_time:.1f}s")
    report["steps"].append(
        {"step": "parse", "status": "ok", "triples": len(g), "elapsed_s": round(parse_time, 1)}
    )

    # Step 2 — OWL RL inference (skip if too large)
    if not args.skip_instances and len(g) < 200000:
        print("\n=== Step 2: OWL RL inference ===")
        try:
            from owlrl import DeductiveClosure, OWLRL_Semantics

            start = time.time()
            DeductiveClosure(OWLRL_Semantics).expand(g)
            elapsed = time.time() - start
            print(f"  triples after inference: {len(g)} (+{len(g) - initial}), elapsed {elapsed:.1f}s")
            report["steps"].append(
                {"step": "owl_rl_inference", "status": "ok", "triples_after": len(g), "elapsed_s": round(elapsed, 1)}
            )
        except Exception as exc:
            print(f"  FAIL: {exc}", file=sys.stderr)
            report["steps"].append({"step": "owl_rl_inference", "status": "fail", "error": str(exc)})
    else:
        print("\n=== Step 2: OWL RL inference SKIPPED (too large or instances skipped) ===")
        report["steps"].append({"step": "owl_rl_inference", "status": "skipped"})

    # Step 3 — SHACL validation
    if not args.skip_shacl and SHAPES_V2.exists():
        print("\n=== Step 3: SHACL validation ===")
        try:
            from pyshacl import validate

            start = time.time()
            shapes_g = Graph()
            shapes_g.parse(str(SHAPES_V2), format="turtle")
            conforms, results_graph, results_text = validate(
                g,
                shacl_graph=shapes_g,
                ont_graph=None,
                inference="none",
                abort_on_first=False,
                allow_infos=True,
                allow_warnings=True,
                meta_shacl=False,
                advanced=True,
                js=False,
                debug=False,
            )
            elapsed = time.time() - start
            n_violations = sum(1 for _ in results_graph.subjects(predicate=None, object=None)) if not conforms else 0
            print(f"  conforms={conforms}, elapsed {elapsed:.1f}s")
            print(f"  result text (first 800 chars):\n{results_text[:800]}")
            report["steps"].append(
                {
                    "step": "shacl_validation",
                    "status": "ok",
                    "conforms": bool(conforms),
                    "elapsed_s": round(elapsed, 1),
                    "summary": results_text[:1500],
                }
            )
        except Exception as exc:
            import traceback

            print(f"  FAIL: {exc}", file=sys.stderr)
            report["steps"].append(
                {"step": "shacl_validation", "status": "fail", "error": str(exc), "tb": traceback.format_exc(limit=3)}
            )
    else:
        print("\n=== Step 3: SHACL SKIPPED ===")

    # Step 4 — SPARQL CQ coverage
    if not args.skip_sparql and CQ_PATH.exists():
        print("\n=== Step 4: SPARQL CQ coverage (in-memory rdflib) ===")
        payload = json.loads(CQ_PATH.read_text(encoding="utf-8"))
        queries = payload.get("queries") or []
        print(f"  {len(queries)} queries to run")
        answered = 0
        errored = 0
        details = []
        for q in queries:
            sparql = q.get("sparql", "")
            try:
                res = g.query(sparql)
                rows = list(res)
                n = len(rows)
                if n > 0:
                    answered += 1
                details.append({"cq_id": q.get("cq_id"), "rows": n, "status": "ok"})
            except Exception as exc:
                errored += 1
                details.append({"cq_id": q.get("cq_id"), "status": "error", "error": str(exc)[:200]})
        coverage = answered / len(queries) if queries else 0
        print(f"  answered={answered}/{len(queries)} = {coverage:.1%}, errored={errored}")
        report["steps"].append(
            {
                "step": "sparql_cq",
                "status": "ok",
                "total": len(queries),
                "answered": answered,
                "errored": errored,
                "coverage": round(coverage, 4),
                "details_sample": details[:10],
            }
        )

        # Update sparql_cq_coverage.json
        payload["local_coverage"] = round(coverage, 4)
        payload["local_answered"] = answered
        payload["local_errored"] = errored
        payload["local_details"] = details
        CQ_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  updated {CQ_PATH.relative_to(REPO_ROOT)}")
    else:
        print("\n=== Step 4: SPARQL SKIPPED ===")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUT_REPORT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
