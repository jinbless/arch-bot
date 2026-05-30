#!/usr/bin/env python3
"""B3 — SWRL/SHACL 규칙 parity harness (R-14~R-30).

demo-chain fixture에 두 형식을 적용해 추론 산출 동치를 검증한다:
- SHACL 측: pyshacl로 R-14~R-30 SHACL SPARQLRule(CONSTRUCT) 적용.
- SWRL 측: SWRL-RDF(swrl:Imp) → SPARQL CONSTRUCT 충실 변환 후 fixpoint 적용.
  (host Java 없어 Pellet 불가. R-14~R-30은 ClassAtom/IndividualPropertyAtom/
   DatavaluedPropertyAtom + swrlb:greaterThanOrEqual 뿐 = 부정·개체빌트인 없는 DL-safe Horn
   규칙 → SPARQL 변환이 의미 충실. 규칙 chaining은 fixpoint로.)

동치면 SWRL 4파일(r14-r18/r19-r23/r24-r26/r28-r30) 은퇴 가능(SHACL twin이 운영 경로).
순수 진단 — 소스 파일 미수정.
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdflib import Graph, RDF, Literal, Namespace  # noqa: E402
from rdflib.collection import Collection  # noqa: E402

ONT = Path(__file__).resolve().parents[1]
DEMO = ONT / "kosha-instances-demo-chain.ttl"
TBOX = ONT / "kosha-ontology-v2.owl"
SWRL_FILES = [ONT / f"kosha-rules-{r}-swrl.ttl" for r in ("r14-r18", "r19-r23", "r24-r26", "r28-r30")]
SHACL_FILES = [ONT / "kosha-rules-r14-r30-shacl-construct.ttl", ONT / "kosha-r27-shacl-exempted.ttl"]

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = Namespace("http://www.w3.org/2003/11/swrlb#")
_OPS = {SWRLB.greaterThanOrEqual: ">=", SWRLB.greaterThan: ">",
        SWRLB.lessThanOrEqual: "<=", SWRLB.lessThan: "<", SWRLB.equal: "="}


def _ln(u) -> str:
    return str(u).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _base() -> Graph:
    g = Graph()
    g.parse(str(TBOX), format="xml")
    g.parse(str(DEMO), format="turtle")
    return g


# ── SWRL-RDF → SPARQL ────────────────────────────────────────────────────────
def _term(node, varset) -> str:
    if node in varset:
        return "?" + _ln(node)
    if isinstance(node, Literal):
        return node.n3()
    return f"<{node}>"


def _atom(g: Graph, atom, varset) -> str:
    t = g.value(atom, RDF.type)
    if t == SWRL.ClassAtom:
        return f"{_term(g.value(atom, SWRL.argument1), varset)} a <{g.value(atom, SWRL.classPredicate)}> ."
    if t in (SWRL.IndividualPropertyAtom, SWRL.DatavaluedPropertyAtom):
        return (f"{_term(g.value(atom, SWRL.argument1), varset)} "
                f"<{g.value(atom, SWRL.propertyPredicate)}> "
                f"{_term(g.value(atom, SWRL.argument2), varset)} .")
    if t == SWRL.BuiltinAtom:
        b = g.value(atom, SWRL.builtin)
        args = list(Collection(g, g.value(atom, SWRL.arguments)))
        op = _OPS.get(b)
        if op is None:
            raise ValueError(f"unhandled builtin {b}")
        return f"FILTER({_term(args[0], varset)} {op} {_term(args[1], varset)})"
    raise ValueError(f"unhandled atom type {t}")


def _construct(g: Graph, imp, varset) -> str:
    body = list(Collection(g, g.value(imp, SWRL.body)))
    head = list(Collection(g, g.value(imp, SWRL.head)))
    where = "\n  ".join(_atom(g, a, varset) for a in body)
    cons = "\n  ".join(_atom(g, a, varset) for a in head)  # head = triple-pattern atoms only
    return f"CONSTRUCT {{\n  {cons}\n}} WHERE {{\n  {where}\n}}"


def swrl_side() -> set:
    sg = Graph()
    for f in SWRL_FILES:
        sg.parse(str(f), format="turtle")
    varset = set(sg.subjects(RDF.type, SWRL.Variable))
    queries = [_construct(sg, imp, varset) for imp in sg.subjects(RDF.type, SWRL.Imp)]
    g = _base()
    base0 = set(g)
    for _ in range(12):  # fixpoint (rule chaining: R-28→R-30 등)
        n = len(g)
        for q in queries:
            for tr in g.query(q):
                g.add(tr)
        if len(g) == n:
            break
    return set(g) - base0


# ── SHACL (pyshacl) ──────────────────────────────────────────────────────────
def shacl_side() -> set:
    from pyshacl import validate
    g = _base()
    base0 = set(g)
    shapes = Graph()
    for f in SHACL_FILES:
        shapes.parse(str(f), format="turtle")
    validate(g, shacl_graph=shapes, advanced=True, inplace=True, iterate_rules=True,
             inference="none", allow_infos=True, allow_warnings=True)
    return set(g) - base0


def main() -> int:
    print("=== B3 parity: SWRL(SPARQL 변환) vs SHACL(pyshacl) on demo-chain ===")
    swrl_inf = swrl_side()
    shacl_inf = shacl_side()
    print(f"  SWRL 추론: {len(swrl_inf)}  /  SHACL 추론: {len(shacl_inf)}")
    only_swrl = swrl_inf - shacl_inf
    only_shacl = shacl_inf - swrl_inf
    print(f"  공통: {len(swrl_inf & shacl_inf)}  /  SWRL-only: {len(only_swrl)}  /  SHACL-only: {len(only_shacl)}")

    def show(label, s):
        if s:
            print(f"  [{label}]")
            for st, p, o in sorted(s, key=lambda x: (str(x[1]), str(x[0]))):
                print(f"    {_ln(st)}  {_ln(p)}  {_ln(o)}")

    show("SWRL-only", only_swrl)
    show("SHACL-only (R-27은 SWRL-twin 없음=정상)", only_shacl)
    if not only_swrl and not only_shacl:
        print("\n  [PARITY] SWRL ≡ SHACL — SWRL 4파일 은퇴 가능 ✅")
        return 0
    print("\n  [DIFFER] 차이 존재 — 분석 필요(R-27 SHACL-only는 예외)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
