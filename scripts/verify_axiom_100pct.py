#!/usr/bin/env python3
"""Sprint D 마무리 — Axiom 100% Sprint 전용 검증.

기존 verify_session_docs.py는 hazard-direct/Phase G 등 이전 sprint 검증.
본 script는 axiom-100pct Sprint 전용 (Phase A-J + Sprint A-2/B/C/D).

5 step:
1. SESSION_COMMITS — 본 sprint commits가 origin/main에 push되었는지
2. NEW_SCRIPTS — 본 sprint 신규 스크립트 파일 존재
3. NEW_DOCS — 본 sprint 신규 dev-note 존재
4. METRIC_EXPECTATIONS — rdflib SPARQL count
5. COMPLETION_MARKERS — sprint 완료 표시

사용:
  PYTHONIOENCODING=utf-8 python scripts/verify_axiom_100pct.py

exit 0 = OK, 1 = FAIL.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("Cannot locate repo root")


REPO = _find_root()
ONT = REPO / "ontology-team" / "06-reasoning" / "ontology"

SESSION_COMMITS = [
    "5be7dc1",   # Phase A
    "d79a42a",   # Phase B
    "dff9738",   # Phase C-J
    "0b5d229",   # Sprint A-2
    "79185a0",   # Sprint B
    "2c3f153",   # Sprint D Gate 3
    "e348fe8",   # Sprint C/D 1+2+3 (SHACL SPARQLRule + 1,271 vetted + verify)
    "8728e42",   # 후속 1+3+4 (ABox enrichment demo + Phase K 재진단)
]

NEW_SCRIPTS = [
    "data-team/05-enrichment/llm-scripts/promote_f32_auto_batch.py",
    "data-team/05-enrichment/llm-scripts/run_shacl_rules.py",
    "scripts/verify_axiom_100pct.py",
]

NEW_DOCS = [
    "docs/workplans/ontology-axiom-100pct.md",
    "docs/dev-notes/axiom-100pct-phase-a.md",
    "docs/dev-notes/axiom-100pct-phase-b.md",
    "docs/dev-notes/axiom-100pct-phase-c-j.md",
]

NEW_TTLS = [
    "ontology-team/06-reasoning/ontology/kosha-ontology-v4-deps-patch.ttl",
    "ontology-team/06-reasoning/ontology/kosha-rules-r2-r4-swrl.ttl",
    "ontology-team/06-reasoning/ontology/kosha-ontology-v4-alethic-patch.ttl",
    "ontology-team/06-reasoning/ontology/kosha-rules-r9-r13-swrl.ttl",
    "ontology-team/06-reasoning/ontology/kosha-ontology-v4-bridge-patch.ttl",
    "ontology-team/06-reasoning/ontology/kosha-rules-r14-r18-swrl.ttl",
    "ontology-team/06-reasoning/ontology/kosha-ontology-v4-deontic-patch.ttl",
    "ontology-team/06-reasoning/ontology/kosha-rules-r19-r23-swrl.ttl",
    "ontology-team/06-reasoning/ontology/kosha-ontology-v4-violation-patch.ttl",
    "ontology-team/06-reasoning/ontology/kosha-rules-r24-r26-swrl.ttl",
    "ontology-team/06-reasoning/ontology/kosha-r27-shacl-exempted.ttl",
    "ontology-team/06-reasoning/ontology/kosha-ontology-v4-penalty-extra-patch.ttl",
    "ontology-team/06-reasoning/ontology/kosha-rules-r28-r30-swrl.ttl",
    "ontology-team/06-reasoning/ontology/kosha-ontology-v4-restrictions-patch.ttl",
    "ontology-team/06-reasoning/ontology/kosha-ontology-v4-hazard-direct-patch.ttl",
    "ontology-team/06-reasoning/ontology/kosha-instances-hazard-direct.ttl",
    "ontology-team/06-reasoning/ontology/kosha-ontology-v4-asymmetric-patch.ttl",
    "ontology-team/06-reasoning/ontology/kosha-rules-r14-r30-shacl-construct.ttl",
    "ontology-team/06-reasoning/ontology/kosha-vetted-disjoint-shapes.ttl",
    "ontology-team/06-reasoning/ontology/kosha-rules-k-general-shacl.ttl",
    "ontology-team/06-reasoning/ontology/kosha-instances-demo-chain.ttl",
]

METRIC_EXPECTATIONS = {
    "owl:Restriction": (35, "≥"),
    "owl:AsymmetricProperty": (1, "≥"),
    "swrl:Imp": (24, "≥"),
    "NaturalLanguageHazardCategory": (21, "≥"),
    "sh:NodeShape": (50, "≥"),  # 12 SHACL rules + vetted disjoint shapes + 기존
}

COMPLETION_MARKERS = [
    ("docs/workplans/ontology-axiom-100pct.md", "Phase A"),
    ("docs/workplans/ontology-axiom-100pct.md", "Phase B"),
    ("docs/workplans/ontology-axiom-100pct.md", "Phase C"),
    ("docs/workplans/ontology-axiom-100pct.md", "Phase D"),
    ("docs/dev-notes/axiom-100pct-phase-c-j.md", "Gate 3 PASS"),
    ("docs/dev-notes/axiom-100pct-phase-c-j.md", "95-97%"),
]


def check_commits():
    errors = []
    for sha in SESSION_COMMITS:
        try:
            proc = subprocess.run(["git", "branch", "-r", "--contains", sha],
                                  capture_output=True, text=True, cwd=str(REPO))
            if "origin/main" not in proc.stdout:
                errors.append(f"  commit {sha} not on origin/main")
        except Exception as e:
            errors.append(f"  git check failed for {sha}: {e}")
    return (len(errors) == 0, errors)


def check_files(file_list, category):
    errors = []
    for fp in file_list:
        if not (REPO / fp).exists():
            errors.append(f"  {category} MISSING: {fp}")
    return (len(errors) == 0, errors)


def check_metrics():
    from rdflib import Graph
    errors = []
    actuals = {}
    g = Graph()
    for f in NEW_TTLS + [
        "ontology-team/06-reasoning/ontology/kosha-ontology-v2.owl",
        "ontology-team/06-reasoning/ontology/kosha-rules-r1-r3-swrl.ttl",
    ]:
        p = REPO / f
        if not p.exists():
            continue
        fmt = "xml" if f.endswith(".owl") else "turtle"
        try:
            g.parse(str(p), format=fmt)
        except Exception:
            pass

    queries = {
        "owl:Restriction": 'SELECT (COUNT(?r) AS ?c) WHERE { ?r a <http://www.w3.org/2002/07/owl#Restriction> }',
        "owl:AsymmetricProperty": 'SELECT (COUNT(?p) AS ?c) WHERE { ?p a <http://www.w3.org/2002/07/owl#AsymmetricProperty> }',
        "swrl:Imp": 'SELECT (COUNT(?r) AS ?c) WHERE { ?r a <http://www.w3.org/2003/11/swrl#Imp> }',
        "NaturalLanguageHazardCategory": 'SELECT (COUNT(?n) AS ?c) WHERE { ?n a <https://cashtoss.info/ontology/risk#NaturalLanguageHazardCategory> }',
        "sh:NodeShape": 'SELECT (COUNT(?s) AS ?c) WHERE { ?s a <http://www.w3.org/ns/shacl#NodeShape> }',
    }

    for label, q in queries.items():
        try:
            res = list(g.query(q))
            count = int(res[0][0]) if res else 0
            actuals[label] = count
            expected, op = METRIC_EXPECTATIONS[label]
            if op == "≥":
                if count < expected:
                    errors.append(f"  {label}: got {count}, expected ≥ {expected}")
        except Exception as e:
            errors.append(f"  {label}: query failed — {e}")

    return (len(errors) == 0, errors, actuals)


def check_markers():
    errors = []
    for fp, marker in COMPLETION_MARKERS:
        p = REPO / fp
        if not p.exists():
            errors.append(f"  MISSING file for marker: {fp}")
            continue
        text = p.read_text(encoding="utf-8")
        if marker not in text:
            errors.append(f"  {fp}: marker not found: '{marker}'")
    return (len(errors) == 0, errors)


def main():
    overall_ok = True
    print("=== verify_axiom_100pct.py ===\n")

    print("Step 1/5: SESSION_COMMITS (origin/main)")
    ok, errs = check_commits()
    print(f"  {'OK' if ok else 'FAIL'} — {len(SESSION_COMMITS)} commits")
    for e in errs: print(e)
    overall_ok = overall_ok and ok

    print("\nStep 2/5: NEW_SCRIPTS")
    ok, errs = check_files(NEW_SCRIPTS, "script")
    print(f"  {'OK' if ok else 'FAIL'} — {len(NEW_SCRIPTS)} scripts")
    for e in errs: print(e)
    overall_ok = overall_ok and ok

    print("\nStep 3/5: NEW_DOCS + TTLS")
    ok1, errs1 = check_files(NEW_DOCS, "doc")
    ok2, errs2 = check_files(NEW_TTLS, "ttl")
    print(f"  {'OK' if (ok1 and ok2) else 'FAIL'} — {len(NEW_DOCS)} docs + {len(NEW_TTLS)} ttls")
    for e in errs1 + errs2: print(e)
    overall_ok = overall_ok and ok1 and ok2

    print("\nStep 4/5: METRIC_EXPECTATIONS")
    ok, errs, actuals = check_metrics()
    print(f"  {'OK' if ok else 'FAIL'}")
    for label, count in actuals.items():
        exp, op = METRIC_EXPECTATIONS[label]
        print(f"  {label}: {count} (expected {op} {exp})")
    for e in errs: print(e)
    overall_ok = overall_ok and ok

    print("\nStep 5/5: COMPLETION_MARKERS")
    ok, errs = check_markers()
    print(f"  {'OK' if ok else 'FAIL'} — {len(COMPLETION_MARKERS)} markers")
    for e in errs: print(e)
    overall_ok = overall_ok and ok

    print(f"\n=== Overall verdict: {'OK' if overall_ok else 'FAIL'} ===")
    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
