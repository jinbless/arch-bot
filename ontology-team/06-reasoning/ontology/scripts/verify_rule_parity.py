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
# WS-GATE-8: 경로를 manifest SSOT에서 파생. SWRL 4파일은 B3에서 archive/ 로 물리이동(은퇴)됐는데
#   기존 하드코딩 top-level 경로가 그대로라 FileNotFoundError로 crash했다(stale path 버그).
sys.path.insert(0, str(ONT / "assembly"))
import manifest_source as MS  # noqa: E402
_FILE = {e["id"]: ONT / e["file"] for e in MS.ENTRIES}
DEMO = _FILE["abox-demo-chain"]
TBOX = _FILE["base-v2-owl"]
SWRL_FILES = [_FILE[i] for i in
              ("arc-swrl-r14-r18", "arc-swrl-r19-r23", "arc-swrl-r24-r26", "arc-swrl-r28-r30")]
SHACL_FILES = [_FILE["shacl-r14-r30"], _FILE["shacl-r27-exempted"]]

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
    show("SHACL-only", only_shacl)

    # WS-GATE-8 비-vacuous 가드 (1급 판정). 과거 verify는 빈/부적합 fixture에서 양측 0≡0이면
    #   [PARITY] PASS를 줘 죽은 룰(R-14류 dead clause)을 정당화했다. demo-chain은 canonical
    #   AccidentType-typed individual을 포함해 R-14~R-30 fire를 입증하는 정본 fixture이므로,
    #   SHACL(운영 경로) 추론이 0이면 그것은 parity가 아니라 dead-rule 회귀다 → hard-fail.
    if len(shacl_inf) == 0:
        print("\n  [VACUOUS-FAIL] SHACL 운영 추론 0 — demo-chain fire 설계 위반(dead rule) → exit 1")
        return 1
    print(f"\n  [NON-VACUOUS OK] SHACL 운영 추론 {len(shacl_inf)} triples (>0 — dead rule 없음)")

    # SWRL twin parity는 advisory. SWRL 4파일은 archive/ 은퇴본(어떤 운영 소비자도 미실행)이며
    #   폐지 어휘(haz:Hazard 클래스 / sr:addressesHazard 속성)를 일부 보유해 현행 SHACL과 drift
    #   가능. 운영 정본은 SHACL(현행 vocab). 따라서 drift는 게이트 무관 정보로만 보고한다.
    if not only_swrl and not only_shacl:
        print("  [PARITY] archived SWRL twin ≡ SHACL (drift 없음)")
    else:
        print(f"  [DRIFT-ADVISORY] archived SWRL twin이 현행 SHACL과 불일치 "
              f"(SWRL-only {len(only_swrl)} / SHACL-only {len(only_shacl)}). "
              f"SWRL 은퇴본이 폐지 어휘 보유 — 운영 경로 SHACL이 정본. 게이트 무관.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
