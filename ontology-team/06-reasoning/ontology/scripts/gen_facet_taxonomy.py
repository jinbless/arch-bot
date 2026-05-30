#!/usr/bin/env python3
"""kosha-facet-taxonomy.ttl 생성 — facet(haz/agent/ctx) class/individual 통합 taxonomy.

SSOT = shared/reference/canonical-code-vocabulary.json 의 rollup(완전·정본 fine→canonical).
구 catalog `sub` 기반 생성(regenerate_subclass_patch.py)을 대체한다. 진단 결과 catalog sub는
불완전 중복(canonical 미도달 다수, work_context 계층 부재)이라 vocab rollup으로 단일화.

emit 3종:
  1. canonical owl:Class punning — 62개(23+10+29). 기존 NamedIndividual을 owl:Class로도 선언
     (OWL 2 DL punning). 기존 individual 선언은 그대로 두므로 ABox facet assertion 전부 보존.
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
    data = json.loads((SHARED_REF / "canonical-code-vocabulary.json").read_text(encoding="utf-8"))

    punning: list[tuple[str, str]] = []      # (prefix, fragment)
    subclass: list[tuple[str, str, str]] = []  # (prefix, child_frag, parent_frag)
    skipped_cross: list[str] = []
    skipped_identity = 0

    canon_iris: set[str] = set()  # 교차검증용 full IRI

    # 1. canonical punning (전 축)
    for axis in AXES:
        prefix = AXIS_PREFIX[axis]
        for code in sorted(cv.canonical_set(axis)):
            frag = _camel(code)
            punning.append((prefix, frag))
            canon_iris.add(NS[prefix] + frag)

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
        "# 1) canonical owl:Class punning  2) fine ⊑ canonical(same-axis)  3) ctx 계층(rollup 자동)",
        f"# cross-axis 제외(Python canonical_vocab 재라우팅): {len(skipped_cross)}건, identity skip: {skipped_identity}건",
        "",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix haz: <https://cashtoss.info/ontology/risk/hazard#> .",
        "@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .",
        "@prefix ctx: <https://cashtoss.info/ontology/risk/context#> .",
        "",
        f"# ════════ 1. canonical owl:Class punning ({len(punning)}) ════════",
    ]
    for axis in AXES:
        prefix = AXIS_PREFIX[axis]
        L.append(f"# -- {axis} ({prefix}) --")
        for p, frag in punning:
            if p == prefix:
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
    print(f"  fine ⊑ canonical  : {stats['subclass']}")
    print(f"  cross-axis 제외    : {len(stats['skipped_cross'])}")
    print(f"  identity skip     : {stats['skipped_identity']}")
    print(f"  [교차검증] 생성 canonical IRI ⊆ 기존 NamedIndividual: {'OK' if ok else 'FAIL'}")
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
