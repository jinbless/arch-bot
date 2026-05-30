#!/usr/bin/env python3
"""Phase 1 — CI/Guide facet 유도 SHACL CONSTRUCT 실행 (Three-Worlds).

kosha-rules-guide-hazard-shacl.ttl의 sh:construct 6개를 ABox(kosha-instances.ttl +
kosha-instances-canonical-ci.ttl)에 fixpoint로 적용. pyshacl 대신 rdflib CONSTRUCT
fast-path(set-based, 51k+ target에 빠름). 신규(유도) triple만 분리 export.

규칙은 self-contained WHERE($this 타입 명시)라 $this→?this 치환만으로 rdflib 실행.
산출: kosha-instances-ci-guide-hazard-derived.ttl (gitignored, 재생성 가능).

사용: PYTHONIOENCODING=utf-8 python run_guide_hazard_rules.py
"""
import sys
import time
from pathlib import Path

from rdflib import Graph

ONT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ONT / "assembly"))
import manifest as _manifest  # noqa: E402
DATA = [e["file"] for e in _manifest.paths("guide-hazard-rules", exclude_roles={"rules-shacl"})]
RULES = _manifest.paths("guide-hazard-rules", only_roles={"rules-shacl"})[0]["file"]
OUT = ONT / "kosha-instances-ci-guide-hazard-derived.ttl"
PREFIX = (
    "PREFIX guide: <https://cashtoss.info/ontology/guide#>\n"
    "PREFIX sr: <https://cashtoss.info/ontology/sr#>\n"
    "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
)


def extract_constructs(rules_path: Path) -> list[str]:
    from rdflib import Namespace
    SH = Namespace("http://www.w3.org/ns/shacl#")
    g = Graph()
    g.parse(str(rules_path), format="turtle")
    out = []
    for _shape, _p, rule in g.triples((None, SH.rule, None)):
        c = g.value(rule, SH.construct)
        if c:
            out.append(str(c))
    return out


def main() -> int:
    t0 = time.time()
    data = Graph()
    print("=== load ABox ===")
    for f in DATA:
        p = ONT / f
        pre = len(data)
        data.parse(str(p), format="turtle")
        print(f"  +{len(data)-pre:>8}  {f}")
    print(f"  total {len(data)} ({time.time()-t0:.1f}s)")

    constructs = extract_constructs(ONT / RULES)
    print(f"\n=== {len(constructs)} CONSTRUCT rules, fixpoint ===")
    derived = Graph()
    it = 0
    while True:
        it += 1
        before = len(derived)
        for c in constructs:
            q = PREFIX + c.replace("$this", "?this")
            for trip in data.query(q):
                if trip not in data:
                    data.add(trip)
                    derived.add(trip)
        gained = len(derived) - before
        print(f"  iter {it}: +{gained} (총 derived {len(derived)})")
        if gained == 0 or it >= 6:
            break

    # breakdown
    from rdflib import Namespace
    G = Namespace("https://cashtoss.info/ontology/guide#")
    counts = {}
    for p in (G.ciAddressesAccidentType, G.ciAddressesAgent, G.ciInWorkContext,
              G.addressesHazard, G.guideAddressesAgent, G.guideAppliesToContext):
        counts[p.split("#")[-1]] = sum(1 for _ in derived.triples((None, p, None)))
    print("\n  유도 breakdown:")
    for k, v in counts.items():
        print(f"    {k}: {v}")

    derived.bind("guide", G)
    derived.serialize(destination=str(OUT), format="turtle")
    print(f"\nDone. {len(derived)} 유도 triple → {OUT.name} ({time.time()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
