#!/usr/bin/env python3
"""disjoint 충돌 오프라인 탐지 — Openllet lazy prepare()의 사각 보완.

Fuseki Openllet은 prepare() 시점에 consistency를 lazy 처리(첫 추론 쿼리에서만 검사) →
"Server Started"가 일관성을 보장하지 않는다. 이 도구는 reasoner 없이 rdflib로
disjoint 위반(개체가 서로소 두 클래스에 동시 소속 = "type and its complement")을
결정적으로 찾아낸다. type 출처: 명시 rdf:type + rdfs:domain/range 주입 + subClassOf 폐포.

사용:
  check_disjoint_consistency.py                       # serving profile 전체
  check_disjoint_consistency.py --exclude FILE [FILE]  # 단일변수 토글(파일 제외)
  check_disjoint_consistency.py --profile consistency
순수 조회 — 파일 미수정.
"""
from __future__ import annotations
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdflib import Graph, RDF, RDFS, OWL, URIRef, BNode

ONT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ONT / "assembly"))
import manifest_source as MS  # noqa: E402

PREFIXES = {
    "risk": "https://cashtoss.info/ontology/risk#",
    "haz": "https://cashtoss.info/ontology/risk/hazard#",
    "agent": "https://cashtoss.info/ontology/risk/agent#",
    "ctx": "https://cashtoss.info/ontology/risk/context#",
    "she": "https://cashtoss.info/ontology/risk/situation#",
    "sr": "https://cashtoss.info/ontology/sr#", "pen": "https://cashtoss.info/ontology/penalty#",
    "law": "https://cashtoss.info/ontology/law#", "guide": "https://cashtoss.info/ontology/guide#",
    "core": "https://cashtoss.info/ontology#", "app": "https://cashtoss.info/ontology/app#",
    "industry": "https://cashtoss.info/ontology/industry#", "bridge": "https://cashtoss.info/ontology/bridge#",
    "actor": "https://cashtoss.info/ontology/actor#",
    "owl": str(OWL), "rdfs": str(RDFS), "rdf": str(RDF),
    "obo": "http://purl.obolibrary.org/obo/",
    "lkif": "http://www.estrellaproject.org/lkif-core/lkif-core#",
}
_REV = sorted(PREFIXES.items(), key=lambda kv: -len(kv[1]))


def short(u) -> str:
    s = str(u)
    for pfx, ns in _REV:
        if s.startswith(ns):
            return f"{pfx}:{s[len(ns):]}"
    return s


def main() -> int:
    args = sys.argv[1:]
    profile = "serving"
    exclude = set()
    i = 0
    while i < len(args):
        if args[i] == "--profile":
            profile = args[i + 1]; i += 2
        elif args[i] == "--exclude":
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                exclude.add(args[i]); i += 1
        else:
            i += 1

    entries = [e for e in MS.by_profile(profile) if e["file"] not in exclude]
    print(f"profile={profile}  files={len(entries)}  excluded={sorted(exclude) or '없음'}", file=sys.stderr)
    g = Graph()
    for e in entries:
        g.parse(str(ONT / e["file"]), format=("xml" if e["format"] == "xml" else "turtle"))
        print(f"  + {e['file']:<52} (총 {len(g):,})", file=sys.stderr)
    print(f"로드 {len(g):,} triples\n", file=sys.stderr)

    # subClassOf 폐포: ancestors(C) = {C} ∪ 모든 상위
    direct_super = defaultdict(set)
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(o, URIRef):
            direct_super[s].add(o)
    _anc_cache: dict = {}

    def ancestors(c):
        if c in _anc_cache:
            return _anc_cache[c]
        seen, stack = set(), [c]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            stack.extend(direct_super.get(x, ()))
        _anc_cache[c] = seen
        return seen

    # disjoint 관계 수집: owl:disjointWith + owl:AllDisjointClasses
    disj = defaultdict(set)
    n_pairs = 0
    for s, o in g.subject_objects(OWL.disjointWith):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            disj[s].add(o); disj[o].add(s); n_pairs += 1
    for adc in g.subjects(RDF.type, OWL.AllDisjointClasses):
        for memlist in g.objects(adc, OWL.members):
            members = [m for m in g.items(memlist) if isinstance(m, URIRef)]
            for a_i in range(len(members)):
                for b_i in range(a_i + 1, len(members)):
                    a, b = members[a_i], members[b_i]
                    disj[a].add(b); disj[b].add(a); n_pairs += 1
    print(f"disjoint pairs: {n_pairs}  (서로소 관계 클래스 {len(disj)})", file=sys.stderr)

    # property domain/range
    dom = {p: [d for d in g.objects(p, RDFS.domain) if isinstance(d, URIRef)]
           for p in set(g.subjects(RDFS.domain, None))}
    rng = {p: [r for r in g.objects(p, RDFS.range) if isinstance(r, URIRef)]
           for p in set(g.subjects(RDFS.range, None))}

    # node -> {directClass: set(source)}
    node_types: dict = defaultdict(lambda: defaultdict(set))
    for s, p, o in g:
        if p == RDF.type and isinstance(o, URIRef) and o not in (OWL.NamedIndividual, OWL.Class):
            node_types[s][o].add("type")
        if p in dom and isinstance(s, (URIRef,)):
            for d in dom[p]:
                node_types[s][d].add(f"dom:{short(p)}")
        if p in rng and isinstance(o, URIRef):
            for r in rng[p]:
                node_types[o][r].add(f"rng:{short(p)}")

    # 충돌 탐지: 어떤 노드의 (direct type 폐포) 안에 서로소 두 클래스가 동시 존재
    collisions = []
    for node, dt in node_types.items():
        if isinstance(node, BNode):
            continue
        # 폐포 class -> 그것을 만든 (directType, sources)
        closed: dict = defaultdict(set)
        for d, srcs in dt.items():
            for anc in ancestors(d):
                closed[anc].add((d, frozenset(srcs)))
        cls = list(closed)
        hit = None
        for a_i in range(len(cls)):
            for b_i in range(a_i + 1, len(cls)):
                a, b = cls[a_i], cls[b_i]
                if b in disj.get(a, ()):
                    hit = (a, b); break
            if hit:
                break
        if hit:
            a, b = hit
            collisions.append((node, a, b, closed[a], closed[b]))

    print("=" * 78)
    print(f"disjoint 충돌 개체: {len(collisions)}")
    print("=" * 78)
    PATCH_PREDS = {"dom:guide:", "rng:guide:", "dom:core:", "rng:core:", "dom:law:", "rng:law:", "dom:sr:", "rng:sr:"}
    for node, a, b, sa, sb in collisions[:25]:
        print(f"\n● {short(node)}")
        print(f"    서로소: {short(a)}  ⊥  {short(b)}")
        print(f"    {short(a)} ← " + "; ".join(f"{short(d)}[{','.join(sorted(s))}]" for d, s in list(sa)[:4]))
        print(f"    {short(b)} ← " + "; ".join(f"{short(d)}[{','.join(sorted(s))}]" for d, s in list(sb)[:4]))
    if len(collisions) > 25:
        print(f"\n… (+{len(collisions)-25} more)")
    # 출처 술어 집계
    srcctr = defaultdict(int)
    for _, _, _, sa, sb in collisions:
        for _, s in list(sa) + list(sb):
            for x in s:
                srcctr[x] += 1
    print("\n── 충돌 기여 출처(type/dom/rng) 집계 ──")
    for k, v in sorted(srcctr.items(), key=lambda kv: -kv[1])[:20]:
        print(f"    {v:>6}  {k}")
    return 1 if collisions else 0


if __name__ == "__main__":
    sys.exit(main())
