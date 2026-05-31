#!/usr/bin/env python3
"""property domain/range 코퍼스-aware 도출 — B4(F10/F15/F17) 근거 산출기.

domain/range는 추론 술어다(rdfs:domain P C ⇒ 모든 P-주어가 type C로 추론). 잘못 박으면
B3a 축 disjoint와 충돌해 KB가 비일관이 된다. 따라서 '실제 코퍼스에서 그 속성의 주어/목적어가
어떤 타입으로 쓰이는가'를 먼저 전수 집계해야 안전한 domain/range를 결정할 수 있다.

이 스크립트는 manifest의 **비-archive 전체 union**(대용량 kosha-instances.ttl 포함)을 로드해,
지정 namespace(guide/core/bridge 기본)의 속성 중 **domain 또는 range 누락**인 것을 골라
각각의 주어-타입 / 목적어-타입(또는 리터럴 datatype) 히스토그램 + 미타입 수 + 표본을 출력한다.

사용:
  derive_property_domain_range.py                  # guide/core/bridge 기본
  derive_property_domain_range.py guide core bridge sr   # namespace 추가 지정
순수 조회 — 파일 미수정.
"""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdflib import Graph, RDF, RDFS, OWL, URIRef, Literal, BNode

ONT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ONT / "assembly"))
import manifest_source as MS  # noqa: E402

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
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "obo": "http://purl.obolibrary.org/obo/",
    "lkif": "http://www.estrellaproject.org/lkif-core/lkif-core#",
    "sosa": "http://www.w3.org/ns/sosa/",
}
_REV = sorted(PREFIXES.items(), key=lambda kv: -len(kv[1]))


def short(u) -> str:
    if isinstance(u, Literal):
        dt = f"^^{short(u.datatype)}" if u.datatype else (f"@{u.language}" if u.language else "")
        return f'lit{dt}'
    if isinstance(u, BNode):
        return "_:bnode"
    s = str(u)
    for pfx, ns in _REV:
        if s.startswith(ns):
            return f"{pfx}:{s[len(ns):]}"
    return s


def load_union() -> Graph:
    """manifest 비-archive 전체 union 로드 (대용량 ABox 포함)."""
    g = Graph()
    seen = set()
    for e in MS.ENTRIES:
        if e["role"] == "archive":
            continue
        if e["file"] in seen:
            continue
        seen.add(e["file"])
        p = ONT / e["file"]
        if not p.exists():
            print(f"  [MISSING] {e['file']}", file=sys.stderr)
            continue
        fmt = "xml" if e["format"] == "xml" else "turtle"
        try:
            before = len(g)
            g.parse(str(p), format=fmt)
            print(f"  loaded {e['file']:<52} +{len(g)-before:>8,}  (총 {len(g):,})", file=sys.stderr)
        except Exception as ex:  # noqa: BLE001
            print(f"  [SKIP] {e['file']}: {ex}", file=sys.stderr)
    return g


def main() -> int:
    ns_keys = sys.argv[1:] or ["guide", "core", "bridge"]
    target_ns = tuple(PREFIXES[k] for k in ns_keys)

    print("로딩 중 (대용량 ABox 포함, 수 분 소요)...", file=sys.stderr)
    g = load_union()
    print(f"\n로드 완료: {len(g):,} triples\n", file=sys.stderr)

    obj_props = {p for p in g.subjects(RDF.type, OWL.ObjectProperty) if str(p).startswith(target_ns)}
    dat_props = {p for p in g.subjects(RDF.type, OWL.DatatypeProperty) if str(p).startswith(target_ns)}

    # node -> declared rdf:type set (전수 1-pass: 타입 맵)
    types: dict = defaultdict(set)
    for s, o in g.subject_objects(RDF.type):
        types[s].add(o)

    def type_hist(nodes) -> tuple[Counter, int]:
        """노드 집합의 rdf:type 히스토그램 + 미타입 수."""
        hist = Counter()
        untyped = 0
        for n in nodes:
            ts = [t for t in types.get(n, ()) if t != OWL.NamedIndividual]
            if not ts:
                untyped += 1
            for t in ts:
                hist[t] += 1
        return hist, untyped

    def fmt_hist(hist: Counter, untyped: int, total_nodes: int) -> str:
        parts = [f"{short(t)}={c}" for t, c in hist.most_common(8)]
        tail = f"  (+{len(hist)-8} more)" if len(hist) > 8 else ""
        ut = f"  ⟨untyped {untyped}⟩" if untyped else ""
        return (", ".join(parts) or "(none)") + tail + ut

    def analyze(props, kind):
        print(f"\n{'='*90}\n  {kind} — {len(props)}개 (domain/range 누락만)\n{'='*90}")
        for p in sorted(props, key=short):
            dom = list(g.objects(p, RDFS.domain))
            rng = list(g.objects(p, RDFS.range))
            if dom and rng:
                continue  # 둘 다 있으면 대상 아님
            triples = list(g.subject_objects(p))
            subs = [s for s, _ in triples]
            objs = [o for _, o in triples]
            uniq_subs = set(subs)
            uniq_objs = set(objs)
            sh, su = type_hist(uniq_subs)
            print(f"\n● {short(p)}   used={len(triples):,}  distinct subj={len(uniq_subs):,} obj={len(uniq_objs):,}")
            print(f"    declared domain: {[short(d) for d in dom] or '— (누락)'}")
            print(f"    declared range : {[short(r) for r in rng] or '— (누락)'}")
            print(f"    SUBJ types: {fmt_hist(sh, su, len(uniq_subs))}")
            if kind == "ObjectProperty":
                oh, ou = type_hist(uniq_objs)
                print(f"    OBJ  types: {fmt_hist(oh, ou, len(uniq_objs))}")
            else:
                lit = Counter()
                nonlit = 0
                for o in objs:
                    if isinstance(o, Literal):
                        lit[o.datatype or (f"@{o.language}" if o.language else "plain")] += 1
                    else:
                        nonlit += 1
                lp = ", ".join(f"{short(URIRef(d)) if isinstance(d, URIRef) else d}={c}"
                               for d, c in lit.most_common(6))
                print(f"    OBJ  literals: {lp or '(none)'}" + (f"  ⟨non-literal {nonlit}⟩" if nonlit else ""))
            # 표본 (타입 파악 보조)
            samp_s = ", ".join(short(s) for s in list(uniq_subs)[:3])
            print(f"    subj 표본: {samp_s}")

    analyze(obj_props, "ObjectProperty")
    analyze(dat_props, "DatatypeProperty")
    return 0


if __name__ == "__main__":
    sys.exit(main())
