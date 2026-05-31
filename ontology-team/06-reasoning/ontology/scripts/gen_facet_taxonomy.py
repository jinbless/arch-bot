#!/usr/bin/env python3
"""kosha-facet-taxonomy.ttl 생성 — facet(haz/agent/ctx) class/individual 통합 taxonomy.

SSOT = shared/reference/canonical-code-vocabulary.json 의 rollup(완전·정본 fine→canonical).
구 catalog `sub` 기반 생성(regenerate_subclass_patch.py)을 대체한다. 진단 결과 catalog sub는
불완전 중복(canonical 미도달 다수, work_context 계층 부재)이라 vocab rollup으로 단일화.

emit 3종:
  1. canonical owl:Class punning + ⊑ axis — 62개(23+10+29). 기존 NamedIndividual을 owl:Class로도 선언
     (OWL 2 DL punning). 기존 individual 선언은 그대로 두므로 ABox facet assertion 전부 보존.
     추가로 각 canonical의 기존 rdf:type 축(haz:AccidentType/agent:HazardousAgent/ctx 6 하위축)을
     읽어 rdfs:subClassOf 로 승격 — canonical이 risk:RiskFeature까지 이어지도록(floating 해소).
  2. fine ⊑ canonical (same-axis) — rollup의 각 fine을 canonical_vocab.to_canonical로 정본화 후
     같은 축이면 owl:Class + rdfs:subClassOf canonical emit. haz casing 재연결 + agent 정합.
  3. ctx 계층 — work_context rollup이 2번에서 자동 산출 (ForkliftOperation ⊑ Vehicle 등). forklift 변별 복원.

cross-axis(agent→haz 21건, to_canonical이 타축 반환)는 제외 — Python canonical_vocab가 서빙/물질화
시점에 재라우팅하므로(hazard_rule_engine.py 등) 온톨로지 subClassOf로 불필요. identity/wc_meta self도 skip.

IRI casing = code_iri_mapper._camel와 동일 규약(UPPER_SNAKE→CamelCase). 교차검증 gate로 드리프트 차단:
  생성 canonical IRI 62 ⊆ kosha-ontology-v4-kosha22-vocab-patch.ttl의 기존 NamedIndividual.

생성물은 수동편집 금지 — 본 스크립트를 고친다.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _root() -> Path:
    for a in Path(__file__).resolve().parents:
        if (a / "shared" / "reference" / "canonical-code-vocabulary.json").exists():
            return a
    raise RuntimeError("repo root not found")


ROOT = _root()
SHARED_REF = ROOT / "shared" / "reference"
ONT = ROOT / "ontology-team" / "06-reasoning" / "ontology"
OUT = ONT / "kosha-facet-taxonomy.ttl"
VOCAB_PATCH = ONT / "kosha-ontology-v4-kosha22-vocab-patch.ttl"  # 기존 canonical individual 선언처

sys.path.insert(0, str(SHARED_REF))
import canonical_vocab as cv  # noqa: E402

AXES = ["accident_type", "hazardous_agent", "work_context"]
AXIS_PREFIX = {"accident_type": "haz", "hazardous_agent": "agent", "work_context": "ctx"}
NS = {
    "haz": "https://cashtoss.info/ontology/risk/hazard#",
    "agent": "https://cashtoss.info/ontology/risk/agent#",
    "ctx": "https://cashtoss.info/ontology/risk/context#",
}


def _camel(code: str) -> str:
    """UPPER_SNAKE → CamelCase (code_iri_mapper._camel와 동일). FALL→Fall, CUT_LACERATION→CutLaceration."""
    return "".join(p.capitalize() for p in str(code).split("_") if p)


def build() -> tuple[list[str], dict]:
    import json
    from rdflib import Graph as _G, RDF as _RDF, RDFS as _RDFS, URIRef as _U
    data = json.loads((SHARED_REF / "canonical-code-vocabulary.json").read_text(encoding="utf-8"))

    # canonical의 기존 축 rdf:type을 데이터에서 읽기 위한 소스:
    #   VOCAB_PATCH = canonical 개체 선언처(예: haz:Fall a owl:NamedIndividual, haz:AccidentType)
    #   v2.owl      = 축⊑risk:RiskFeature 선언처(축 클래스 집합 산출)
    # → canonical의 축 부모를 하드코딩 없이 끌어옴(haz의 AccidentType/Hazard 분기, ctx 6 하위축 자동).
    RISK_IRI = "https://cashtoss.info/ontology/risk#RiskFeature"
    src = _G()
    src.parse(str(VOCAB_PATCH), format="turtle")
    src.parse(str(ONT / "kosha-ontology-v2.owl"), format="xml")
    axis_classes = {str(s) for s in src.subjects(_RDFS.subClassOf, _U(RISK_IRI))}

    def _axis_parents(iri: str) -> tuple[str, ...]:
        """canonical 개체의 rdf:type 중 risk:RiskFeature 직속 축만 → parent fragment 정렬 목록."""
        out = {str(t).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
               for t in src.objects(_U(iri), _RDF.type) if str(t) in axis_classes}
        return tuple(sorted(out))

    punning: list[tuple[str, str, tuple]] = []  # (prefix, fragment, parent_frags)
    subclass: list[tuple[str, str, str]] = []   # (prefix, child_frag, parent_frag)
    skipped_cross: list[str] = []
    skipped_identity = 0
    no_axis: list[str] = []   # 축 부모를 못 찾은 canonical (있으면 안 됨)
    axis_links = 0

    canon_iris: set[str] = set()  # 교차검증용 full IRI

    # 1. canonical punning + canonical ⊑ axis (전 축)
    for axis in AXES:
        prefix = AXIS_PREFIX[axis]
        for code in sorted(cv.canonical_set(axis)):
            frag = _camel(code)
            iri = NS[prefix] + frag
            parents = _axis_parents(iri)
            if not parents:
                no_axis.append(f"{prefix}:{frag}")
            axis_links += len(parents)
            punning.append((prefix, frag, parents))
            canon_iris.add(iri)

    # 2. fine ⊑ canonical (same-axis only)
    for axis in AXES:
        prefix = AXIS_PREFIX[axis]
        rollup = data["axes"][axis].get("rollup", {}) or {}
        canon = cv.canonical_set(axis)
        for fine in sorted(rollup):
            if fine in canon:
                continue  # canonical 자체(identity) — 이미 punning됨
            a2, c2 = cv.to_canonical(axis, fine)  # 교차축 인지
            if a2 != axis:
                skipped_cross.append(f"{prefix}:{_camel(fine)} -> {a2}:{_camel(c2)}")
                continue
            child = _camel(fine)
            parent = _camel(c2)
            if child == parent:
                skipped_identity += 1
                continue
            subclass.append((prefix, child, parent))

    # ── TTL 직렬화 ──
    ts = datetime.now(timezone.utc).isoformat()
    L: list[str] = [
        "# kosha-facet-taxonomy.ttl — AUTO-GENERATED, 수동편집 금지 (scripts/gen_facet_taxonomy.py)",
        f"# Generated: {ts}",
        "# SSOT: shared/reference/canonical-code-vocabulary.json (rollup)",
        "# 1) canonical owl:Class punning + ⊑ axis(기존 rdf:type 축)  2) fine ⊑ canonical(same-axis)  3) ctx 계층(rollup 자동)",
        f"# cross-axis 제외(Python canonical_vocab 재라우팅): {len(skipped_cross)}건, identity skip: {skipped_identity}건",
        f"# canonical⊑axis 링크: {axis_links}건 (축 부모 못 찾음: {len(no_axis)}건)",
        "",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix haz: <https://cashtoss.info/ontology/risk/hazard#> .",
        "@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .",
        "@prefix ctx: <https://cashtoss.info/ontology/risk/context#> .",
        "",
        f"# ════════ 1. canonical owl:Class punning + ⊑ axis ({len(punning)} class, {axis_links} link) ════════",
    ]
    for axis in AXES:
        prefix = AXIS_PREFIX[axis]
        L.append(f"# -- {axis} ({prefix}) --")
        for p, frag, parents in punning:
            if p == prefix:
                if parents:
                    sup = ", ".join(f"{p}:{pp}" for pp in parents)
                    L.append(f"{p}:{frag} a owl:Class ; rdfs:subClassOf {sup} .")
                else:
                    L.append(f"{p}:{frag} a owl:Class .")
        L.append("")
    L.append(f"# ════════ 2. fine ⊑ canonical (same-axis, {len(subclass)}) ════════")
    for axis in AXES:
        prefix = AXIS_PREFIX[axis]
        axis_subs = [s for s in subclass if s[0] == prefix]
        L.append(f"# -- {axis} ({prefix}): {len(axis_subs)} --")
        for p, child, parent in sorted(axis_subs, key=lambda x: (x[2], x[1])):
            L.append(f"{p}:{child} a owl:Class ; rdfs:subClassOf {p}:{parent} .")
        L.append("")

    stats = {
        "punning": len(punning),
        "axis_links": axis_links,
        "no_axis": no_axis,
        "subclass": len(subclass),
        "skipped_cross": skipped_cross,
        "skipped_identity": skipped_identity,
        "canon_iris": canon_iris,
    }
    return L, stats


def cross_check(canon_iris: set[str]) -> tuple[bool, set[str]]:
    """생성 canonical IRI ⊆ vocab-patch의 기존 NamedIndividual? (casing 드리프트 차단)."""
    from rdflib import Graph, RDF, OWL
    g = Graph()
    g.parse(str(VOCAB_PATCH), format="turtle")
    existing = {str(s) for s in g.subjects(RDF.type, OWL.NamedIndividual)
                if any(str(s).startswith(ns) for ns in NS.values())}
    missing = canon_iris - existing
    return (not missing), missing


def main() -> int:
    lines, stats = build()
    ok, missing = cross_check(stats["canon_iris"])

    print("=== gen_facet_taxonomy ===")
    print(f"  canonical punning : {stats['punning']}")
    print(f"  canonical ⊑ axis  : {stats['axis_links']}  (축 부모 못 찾음: {len(stats['no_axis'])})")
    print(f"  fine ⊑ canonical  : {stats['subclass']}")
    print(f"  cross-axis 제외    : {len(stats['skipped_cross'])}")
    print(f"  identity skip     : {stats['skipped_identity']}")
    print(f"  [교차검증] 생성 canonical IRI ⊆ 기존 NamedIndividual: {'OK' if ok else 'FAIL'}")
    if stats["no_axis"]:
        print(f"  [WARN] 축 부모 못 찾은 canonical {len(stats['no_axis'])}건: {stats['no_axis'][:10]}")
    if not ok:
        print(f"  [FAIL] 기존 individual에 없는 canonical IRI {len(missing)}건 (casing 드리프트):")
        for m in sorted(missing):
            print(f"      {m}")
        return 1
    if stats["skipped_cross"]:
        print(f"  cross-axis 제외 목록(샘플): {stats['skipped_cross'][:8]}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
