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
import re
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

# WS-GATE-8 per-rule fire-coverage용 prefix map (rules ttl의 krs:CommonPrefixes 미러).
_PREFIXES = {
    "risk": "https://cashtoss.info/ontology/risk#",
    "haz": "https://cashtoss.info/ontology/risk/hazard#",
    "agent": "https://cashtoss.info/ontology/risk/agent#",
    "ctx": "https://cashtoss.info/ontology/risk/context#",
    "app": "https://cashtoss.info/ontology/app#",
    "sr": "https://cashtoss.info/ontology/sr#",
    "pen": "https://cashtoss.info/ontology/penalty#",
    "law": "https://cashtoss.info/ontology/law#",
    "guide": "https://cashtoss.info/ontology/guide#",
    "core": "https://cashtoss.info/ontology#",
    "bridge": "https://cashtoss.info/ontology/bridge#",
    "actor": "https://cashtoss.info/ontology/actor#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}
_REVP = sorted(_PREFIXES.items(), key=lambda kv: -len(kv[1]))


def _short(u) -> str:
    s = str(u)
    for pfx, ns in _REVP:
        if s.startswith(ns):
            return f"{pfx}:{s[len(ns):]}"
    return s


def _per_rule_fire_coverage(gate: bool) -> int:
    """WS-GATE-8 — 룰별 fire-coverage detector.

    docstring이 "rule별 inferred triple count"를 약속하나 main()은 aggregate after-before만
    emit한다(A10). 이 모드는 demo-chain fixture(R-10~R-30 fire 입증용 정본)에 전 룰을 적용한
    closure를 만든 뒤, 각 룰의 CONSTRUCT를 개별 평가해 inferred triple 수를 산출한다.

    closure 기준인 이유: R-24(→core:hasViolation)는 R-15(→bridge:appliesTo)의 산출에 의존하는
    체인 룰이라, base demo-chain에 룰을 "개별" 적용하면 의존 미충족으로 거짓 0-fire가 난다.
    전 룰 closure에서 개별 CONSTRUCT를 재평가하면 각 룰의 body가 (체인 포함) 충족 가능한지
    정확히 측정된다. demo-chain은 전 룰 fire 설계이므로 0-fire = dead clause 회귀(R-14류).
    F5 check_data_coverage의 '스키마 있는데 fire 0' 패턴을 룰 차원으로 미러."""
    from rdflib import Graph, RDFS, Namespace
    from pyshacl import validate

    SH = Namespace("http://www.w3.org/ns/shacl#")
    tbox = ONT / "kosha-ontology-v2.owl"
    demo = ONT / "kosha-instances-demo-chain.ttl"
    rules_ttl = ONT / SHACL_RULES_TTL

    base = Graph()
    base.parse(str(tbox), format="xml")
    base.parse(str(demo), format="turtle")
    print(f"[per-rule] fixture: {tbox.name} + {demo.name} = {len(base)} triples")

    rules_g = Graph()
    rules_g.parse(str(rules_ttl), format="turtle")

    closure = Graph()
    for t in base:
        closure.add(t)
    validate(closure, shacl_graph=rules_g, advanced=True, inplace=True,
             iterate_rules=True, inference="none", allow_infos=True, allow_warnings=True)
    print(f"[per-rule] closure: {len(closure)} triples (+{len(closure) - len(base)} inferred)\n")

    prefix_header = "\n".join(f"PREFIX {p}: <{ns}>" for p, ns in _PREFIXES.items())

    rows = []
    for shape in rules_g.subjects(SH.targetClass, None):
        rule_node = rules_g.value(shape, SH.rule)
        if rule_node is None:
            continue
        construct = rules_g.value(rule_node, SH.construct)
        if construct is None:
            continue
        label = str(rules_g.value(shape, RDFS.label) or _short(shape))
        tc_uri = rules_g.value(shape, SH.targetClass)
        tc = _short(tc_uri)
        # $this 는 SPARQL 변수($x≡?x)지만 rdflib 호환 위해 ?this 로 통일.
        body = str(construct).replace("$this", "?this")
        # SHACL 타겟팅 의미 복원: $this 는 targetClass 인스턴스로 바인딩된다. body가 $this 를
        # 참조하지 않는 룰(R-25/R-28 등)은 직접 CONSTRUCT 시 ?this unbound → head triple 누락
        # (거짓 0-fire). targetClass 타입 트리플을 WHERE에 주입해 SHACL 바인딩을 재현.
        q = prefix_header + "\n" + re.sub(
            r"(WHERE\s*\{)", rf"\1 ?this a <{tc_uri}> .", body, count=1)
        try:
            fire = len(list(closure.query(q)))
            status = "OK" if fire > 0 else "DEAD"
        except Exception as exc:
            fire, status = -1, f"QUERY-ERR: {str(exc)[:40]}"
        rows.append((label, tc, fire, status))

    rows.sort(key=lambda r: r[0])
    dead = [r for r in rows if r[3] == "DEAD"]
    err = [r for r in rows if r[2] == -1]

    print(f"{'rule':<46} {'targetClass':<20} {'fire':>5}  status")
    print("-" * 84)
    for label, tc, fire, status in rows:
        fr = "ERR" if fire == -1 else str(fire)
        print(f"{label[:46]:<46} {tc[:20]:<20} {fr:>5}  {status}")
    print("-" * 84)
    print(f"rules={len(rows)}  fired={len(rows) - len(dead) - len(err)}  DEAD={len(dead)}  ERR={len(err)}")

    if dead:
        print("\n[DEAD] 0-fire 룰 (demo-chain body 미충족 = dead clause 의심):")
        for label, tc, _, _ in dead:
            print(f"   ✗ {label}  (targetClass {tc})")
    if err:
        print("\n[ERR] CONSTRUCT 평가 실패:")
        for label, _, _, status in err:
            print(f"   ! {label}  {status}")

    if gate and (dead or err):
        print("\n[GATE FAIL] dead/errored 룰 존재 → exit 1")
        return 1
    if dead or err:
        print("\n[WARN] dead/errored 룰 존재 (gate 아님 — --gate 로 exit 1)")
        return 0
    print("\n[OK] 전 룰 fire (0-fire 없음)")
    return 0


def main():
    parser = argparse.ArgumentParser(description="SHACL SPARQLRule 실행 (Sprint A-2 Final 후속)")
    parser.add_argument("--output", type=str, default=None, help="inferred triples ttl 출력 경로")
    parser.add_argument("--skip-instances", action="store_true", help="kosha-instances.ttl skip (TBox만)")
    parser.add_argument("--per-rule", action="store_true",
                        help="WS-GATE-8: demo-chain fixture에서 룰별 fire-coverage 측정 (0-fire dead 탐지)")
    parser.add_argument("--gate", action="store_true",
                        help="--per-rule 와 함께: 0-fire(dead)/errored 룰 존재 시 exit 1")
    args = parser.parse_args()

    if args.per_rule:
        return _per_rule_fire_coverage(gate=args.gate)

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
