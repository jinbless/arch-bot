#!/usr/bin/env python3
"""온톨로지 노드 인스펙터 — 한 IRI(class/individual)의 '전체 데이터'를 한 화면에 모아 보여준다.

온톨로지는 한 엔티티의 사실이 여러 파일에 흩어져 로드 시 합쳐진다. 이 도구는 top-level
.ttl/.owl을 파일별로 파싱해 머지한 뒤, 대상 노드에 관한 모든 triple(주어/목적어 양방향)을
구조화해 출력하고 + 각 사실이 '어느 파일'에서 왔는지(출처)까지 보여준다 = 수정할 위치 파악.

사용:
  inspect_node.py haz:Fall                # 한 노드 카드
  inspect_node.py haz:Fall agent:Chemical # 여러 노드
  inspect_node.py --list haz              # haz prefix의 전체 class/individual 목록(scope 개요)
  inspect_node.py --full haz:Fall         # 대용량 kosha-instances.ttl까지 포함(느림)
순수 조회 — 파일 미수정.
"""
from __future__ import annotations
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdflib import Graph, RDF, RDFS, OWL, URIRef, Literal
from rdflib.namespace import split_uri

ONT = Path(__file__).resolve().parents[1]
BIG_ABOX = "kosha-instances.ttl"  # 956K 텍스트 코퍼스 — 기본 제외(--full로 포함)

PREFIXES = {
    "risk": "https://cashtoss.info/ontology/risk#",
    "haz": "https://cashtoss.info/ontology/risk/hazard#",
    "agent": "https://cashtoss.info/ontology/risk/agent#",
    "ctx": "https://cashtoss.info/ontology/risk/context#",
    "she": "https://cashtoss.info/ontology/risk/situation#",
    "sr": "https://cashtoss.info/ontology/sr#",
    "pen": "https://cashtoss.info/ontology/penalty#",
    "law": "https://cashtoss.info/ontology/law#",
    "guide": "https://cashtoss.info/ontology/guide#",
    "core": "https://cashtoss.info/ontology#",
    "app": "https://cashtoss.info/ontology/app#",
    "industry": "https://cashtoss.info/ontology/industry#",
    "bridge": "https://cashtoss.info/ontology/bridge#",
    "actor": "https://cashtoss.info/ontology/actor#",
    "owl": str(OWL), "rdfs": str(RDFS), "rdf": str(RDF),
}
_REV = sorted(PREFIXES.items(), key=lambda kv: -len(kv[1]))


def short(u) -> str:
    s = str(u)
    for pfx, ns in _REV:
        if s.startswith(ns):
            return f"{pfx}:{s[len(ns):]}"
    if isinstance(u, Literal):
        lang = f"@{u.language}" if u.language else ""
        return f'"{u}"{lang}'
    return s


def expand(name: str) -> URIRef:
    if name.startswith("http"):
        return URIRef(name)
    if ":" in name:
        pfx, frag = name.split(":", 1)
        if pfx in PREFIXES:
            return URIRef(PREFIXES[pfx] + frag)
    return URIRef(name)


def load(full: bool):
    """top-level .ttl/.owl을 파일별로 로드. 반환: (merged, {filename: graph})."""
    files = sorted([p for p in ONT.glob("*.ttl")] + [p for p in ONT.glob("*.owl")])
    merged = Graph()
    by_file: dict[str, Graph] = {}
    for p in files:
        if p.name == BIG_ABOX and not full:
            continue
        fmt = "xml" if p.suffix == ".owl" else "turtle"
        g = Graph()
        try:
            g.parse(str(p), format=fmt)
        except Exception as e:  # noqa: BLE001
            print(f"  [parse skip] {p.name}: {e}", file=sys.stderr)
            continue
        by_file[p.name] = g
        merged += g
    return merged, by_file


def provenance(triple, by_file) -> str:
    hits = [name for name, g in by_file.items() if triple in g]
    return ", ".join(h.replace("kosha-", "").replace(".ttl", "").replace(".owl", "") for h in hits)


def card(node: URIRef, g: Graph, by_file: dict):
    print("=" * 78)
    print(f"  {short(node)}")
    print(f"  IRI: {node}")
    print("=" * 78)

    labels = [o for o in g.objects(node, RDFS.label)]
    comments = [o for o in g.objects(node, RDFS.comment)]
    if labels:
        print("  label   : " + " / ".join(short(l) for l in labels))
    if comments:
        print("  comment : " + " / ".join(str(c)[:80] for c in comments))

    types = [o for o in g.objects(node, RDF.type)]
    print("  rdf:type: " + (", ".join(short(t) for t in types) or "(없음)"))
    is_class = OWL.Class in types or (node, RDFS.subClassOf, None) in g
    is_ind = OWL.NamedIndividual in types

    # ── 클래스로서 ──
    if is_class:
        print("\n  ── 클래스 구조 ──")
        sup = [o for o in g.objects(node, RDFS.subClassOf) if isinstance(o, URIRef)]
        print(f"    ⊑ 상위(superClassOf) : {', '.join(short(s) for s in sup) or '(없음=root)'}")
        # 루트까지 체인
        chain, cur, seen = [], node, set()
        while True:
            ups = [o for o in g.objects(cur, RDFS.subClassOf) if isinstance(o, URIRef)]
            ups = [u for u in ups if u not in seen]
            if not ups:
                break
            cur = ups[0]; seen.add(cur); chain.append(short(cur))
            if len(chain) > 12:
                break
        if chain:
            print(f"    ↑ 루트까지 체인        : {short(node)} ⊑ " + " ⊑ ".join(chain))
        subs = sorted([s for s in g.subjects(RDFS.subClassOf, node) if isinstance(s, URIRef)], key=str)
        print(f"    ⊒ 직속 하위(subClass)  : {len(subs)}개" +
              (f" — {', '.join(short(s) for s in subs[:8])}" + (" …" if len(subs) > 8 else "") if subs else ""))
        disj = [o for o in g.objects(node, OWL.disjointWith)] + [s for s in g.subjects(OWL.disjointWith, node)]
        if disj:
            print(f"    ⊥ disjointWith         : {len(disj)}개 — {', '.join(short(d) for d in disj[:8])}" + (" …" if len(disj) > 8 else ""))
        equiv = [o for o in g.objects(node, OWL.equivalentClass)]
        if equiv:
            print(f"    ≡ equivalentClass      : {', '.join(short(e) for e in equiv)}")
        # 이 클래스가 등장하는 restriction (range/allValuesFrom/someValuesFrom)
        used_in = set()
        for p in (OWL.someValuesFrom, OWL.allValuesFrom, OWL.onClass, RDFS.range, RDFS.domain):
            for s in g.subjects(p, node):
                used_in.add((short(p), s))
        if used_in:
            print(f"    ↪ 제약/도메인레인지에 사용: {len(used_in)}곳 — " +
                  ", ".join(sorted({u[0] for u in used_in})))

    # ── 개체로서 ──
    if is_ind:
        print("\n  ── 개체(individual)로서 ──")
        cls = [o for o in types if o != OWL.NamedIndividual]
        print(f"    소속 클래스(rdf:type) : {', '.join(short(c) for c in cls) or '(없음)'}")

    # ── 나가는 속성 (주어 위치, 구조 술어 제외) ──
    SKIP = {RDF.type, RDFS.subClassOf, RDFS.label, RDFS.comment, OWL.disjointWith, OWL.equivalentClass}
    out = [(p, o) for p, o in g.predicate_objects(node) if p not in SKIP]
    if out:
        print("\n  ── 나가는 속성 (이 노드가 주어) ──")
        for p, o in sorted(out, key=lambda x: str(x[0]))[:20]:
            print(f"    {short(p)} → {short(o)}")
        if len(out) > 20:
            print(f"    … (+{len(out) - 20})")

    # ── 들어오는 참조 (목적어 위치) — 누가 이 노드를 가리키나 ──
    inc = defaultdict(list)
    for s, p in g.subject_predicates(node):
        inc[short(p)].append(s)
    if inc:
        print("\n  ── 들어오는 참조 (이 노드가 목적어) ──")
        for p in sorted(inc, key=lambda k: -len(inc[k])):
            ss = inc[p]
            samp = ", ".join(short(x) for x in ss[:4]) + (" …" if len(ss) > 4 else "")
            print(f"    {p} ← {len(ss)}건  ({samp})")

    # ── 출처 파일 (수정 위치) ──
    prov = defaultdict(int)
    for trip in set(g.triples((node, None, None))) | set(g.triples((None, None, node))):
        for name, fg in by_file.items():
            if trip in fg:
                prov[name] += 1
    if prov:
        print("\n  ── 출처 파일 (이 노드 관련 triple이 정의된 곳 = 수정 위치) ──")
        for name in sorted(prov, key=lambda k: -prov[k]):
            print(f"    {name:<48} {prov[name]} triple")
    print()


def list_prefix(pfx: str, g: Graph):
    ns = PREFIXES.get(pfx)
    if not ns:
        print(f"알 수 없는 prefix: {pfx} (가능: {', '.join(PREFIXES)})")
        return
    classes = sorted([s for s in g.subjects(RDF.type, OWL.Class)
                      if isinstance(s, URIRef) and str(s).startswith(ns)], key=str)
    inds = sorted([s for s in g.subjects(RDF.type, OWL.NamedIndividual)
                   if isinstance(s, URIRef) and str(s).startswith(ns)], key=str)
    print(f"=== {pfx}: ({ns}) — class {len(classes)} / individual {len(inds)} ===")
    print("\n[클래스]")
    for c in classes:
        sub = len([1 for _ in g.subjects(RDFS.subClassOf, c)])
        lab = next((short(o) for o in g.objects(c, RDFS.label)), "")
        print(f"  {short(c):<34} 하위{sub:<3} {lab}")
    if inds:
        print(f"\n[개체] {len(inds)}개 (표본 30)")
        for i in inds[:30]:
            lab = next((short(o) for o in g.objects(i, RDFS.label)), "")
            print(f"  {short(i):<34} {lab}")


def main() -> int:
    args = sys.argv[1:]
    full = "--full" in args
    args = [a for a in args if a != "--full"]
    if not args:
        print(__doc__)
        return 0
    if args[0] == "--list":
        merged, _ = load(full)
        for pfx in args[1:]:
            list_prefix(pfx, merged)
        return 0
    merged, by_file = load(full)
    print(f"(로드: {len(by_file)} 파일, {len(merged)} triple" + (", +대용량ABox" if full else "") + ")\n")
    for name in args:
        node = expand(name)
        if not (set(merged.triples((node, None, None))) or set(merged.triples((None, None, node)))):
            print(f"[없음] {name} — 그래프에 관련 triple 없음 (이름/prefix 확인)\n")
            continue
        card(node, merged, by_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
