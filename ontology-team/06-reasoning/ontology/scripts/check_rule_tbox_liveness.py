#!/usr/bin/env python3
"""WS-GATE-8 (part 3) — SHACL CONSTRUCT 룰의 TBox-liveness 정적 가드.

R-14류 dead clause(폐지된 `haz:Hazard`를 body type-test로 매칭 → 영구 0-fire)를 fixture·
reasoner 없이 정적으로 적발한다. 각 SHACL SPARQLRule의 CONSTRUCT **WHERE 본문**에서
`?x a prefix:Class` 형태의 type-test를 추출해, 그 클래스가 현행 TBox(consistency profile의
tbox-base/patch/taxonomy/disjoint)에 선언/사용된 live class인지 검사한다.

- CONSTRUCT head의 `a Class`(룰 산출 타입, 예 bridge:ViolationCandidate)는 제외 — 그것은
  생성되는 타입이라 TBox 선언이 없을 수 있다(거짓양성 방지). dead-clause 위험은 body의
  type-test에만 있다(매칭 대상이 폐지되면 영구 0-fire).
- property liveness는 advisory(WARN)만 — 추론 산출 속성(bridge:*)이 다른 룰 body의 입력으로
  쓰여 TBox 미선언이 정상이라 hard-fail 부적합.

비-live type-test 클래스 1개 이상 → exit 1. 순수 조회(파일 미수정). make verify-manifest 계열.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdflib import Graph, RDF, RDFS, OWL, URIRef

ONT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ONT / "assembly"))
import manifest_source as MS  # noqa: E402

PREFIXES = {
    "risk": "https://cashtoss.info/ontology/risk#",
    "haz": "https://cashtoss.info/ontology/risk/hazard#",
    "agent": "https://cashtoss.info/ontology/risk/agent#",
    "ctx": "https://cashtoss.info/ontology/risk/context#",
    "she": "https://cashtoss.info/ontology/risk/situation#",
    "app": "https://cashtoss.info/ontology/app#",
    "sr": "https://cashtoss.info/ontology/sr#",
    "pen": "https://cashtoss.info/ontology/penalty#",
    "law": "https://cashtoss.info/ontology/law#",
    "guide": "https://cashtoss.info/ontology/guide#",
    "core": "https://cashtoss.info/ontology#",
    "bridge": "https://cashtoss.info/ontology/bridge#",
    "actor": "https://cashtoss.info/ontology/actor#",
    "industry": "https://cashtoss.info/ontology/industry#",
}
_REV = sorted(PREFIXES.items(), key=lambda kv: -len(kv[1]))

# TBox 선언 출처 role (ABox/rules/shapes 제외 → 빠르고 클래스 선언만)
TBOX_ROLES = {"tbox-base", "tbox-patch", "tbox-taxonomy", "axioms-disjoint"}
# 검사 대상 룰 파일 (R-14~R-30 + R-27; CON/MAT 운영 경로)
RULE_ROLES = {"rules-shacl"}
SH = "http://www.w3.org/ns/shacl#"

# body의 `?x a prefix:Local` / `$x a prefix:Local` type-test
_TYPE_TEST = re.compile(r"[?$]\w+\s+a\s+([A-Za-z][\w]*):([A-Za-z][\w-]*)")


def _short(u) -> str:
    s = str(u)
    for pfx, ns in _REV:
        if s.startswith(ns):
            return f"{pfx}:{s[len(ns):]}"
    return s


def _live_classes(g: Graph) -> set:
    """TBox에서 '존재하는 클래스'로 간주되는 URI 집합."""
    live: set = set()
    for c in g.subjects(RDF.type, OWL.Class):
        if isinstance(c, URIRef):
            live.add(c)
    for c in g.subjects(RDF.type, RDFS.Class):
        if isinstance(c, URIRef):
            live.add(c)
    # subClassOf 양변, domain/range, restriction filler, disjoint, equivalentClass
    for pred in (RDFS.subClassOf, OWL.equivalentClass, OWL.disjointWith):
        for s, o in g.subject_objects(pred):
            if isinstance(s, URIRef):
                live.add(s)
            if isinstance(o, URIRef):
                live.add(o)
    for pred in (RDFS.domain, RDFS.range, OWL.someValuesFrom, OWL.allValuesFrom, OWL.onClass):
        for o in g.objects(None, pred):
            if isinstance(o, URIRef):
                live.add(o)
    for adc in g.subjects(RDF.type, OWL.AllDisjointClasses):
        for memlist in g.objects(adc, OWL.members):
            for m in g.items(memlist):
                if isinstance(m, URIRef):
                    live.add(m)
    return live


def main() -> int:
    # 1. TBox 로드 (클래스 선언 출처)
    tbox = Graph()
    n = 0
    for e in MS.by_profile("consistency"):
        if e["role"] not in TBOX_ROLES:
            continue
        tbox.parse(str(ONT / e["file"]), format=("xml" if e["format"] == "xml" else "turtle"))
        n += 1
    print(f"TBox 로드: {n} files / {len(tbox):,} triples", file=sys.stderr)
    live = _live_classes(tbox)
    print(f"live class: {len(live)}", file=sys.stderr)

    # 2. 룰 파일에서 body type-test 클래스 추출
    rule_files = [e["file"] for e in MS.by_profile("consistency") if e["role"] in RULE_ROLES]
    refs: list[tuple] = []   # (file, rule_label, class_uri)
    for rf in rule_files:
        rg = Graph()
        rg.parse(str(ONT / rf), format="turtle")
        for shape in rg.subjects(URIRef(SH + "targetClass"), None):
            rule_node = rg.value(shape, URIRef(SH + "rule"))
            if rule_node is None:
                continue
            construct = rg.value(rule_node, URIRef(SH + "construct"))
            if construct is None:
                continue
            label = str(rg.value(shape, RDFS.label) or _short(shape))
            text = str(construct)
            body = text.split("WHERE", 1)[1] if "WHERE" in text else ""
            for pfx, local in _TYPE_TEST.findall(body):
                if pfx not in PREFIXES:
                    continue
                refs.append((rf, label, URIRef(PREFIXES[pfx] + local)))

    # 3. liveness 판정
    dead = [(rf, lbl, c) for (rf, lbl, c) in refs if c not in live]
    checked = sorted({_short(c) for (_, _, c) in refs})
    print("=" * 72)
    print(f"룰 body type-test 클래스 참조: {len(refs)} (distinct {len(checked)})")
    print(f"  검사된 클래스: {', '.join(checked)}")
    print("=" * 72)
    if dead:
        print(f"[FAIL] 비-live(TBox 미선언) type-test 클래스 {len(dead)}건 — dead clause:")
        for rf, lbl, c in dead:
            print(f"   ✗ {_short(c)}  ←  {lbl}   [{rf}]")
        print("\n폐지된 클래스를 매칭하는 룰은 영구 0-fire. 현행 TBox 어휘로 repoint 필요.")
        return 1
    print("[OK] 모든 body type-test 클래스가 현행 TBox에 live (dead clause 없음)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
