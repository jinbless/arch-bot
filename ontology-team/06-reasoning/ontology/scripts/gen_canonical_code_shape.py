#!/usr/bin/env python3
"""Phase 5 가드레일 — 코드 어휘 canonical 강제 SHACL shape 생성 (SSOT 파생).

근본: ABox(SR/Guide)가 참조하는 위험축 코드 IRI는 KOSHA-22 정본(canonical) 어휘
안에만 있어야 한다. Phase 4-B에서 exporter 3종을 code_iri_mapper SSOT로 일원화했으나,
재발(legacy CamelCase·UPPER·오타 fragment) 방지를 위해 *선언적* SHACL 가드레일을 둔다.

audit_code_consistency.py(imperative regex 게이트)의 보완재:
- audit: 빠른 regex 스캔으로 UPPER 코드/PG orphan 적발 (make verify-codes, CI hard-gate).
- 본 shape: pyshacl로 ABox 객체 코드 IRI ∈ canonical 집합을 sh:in으로 형식 검증
  (이식 가능한 SHACL 산출물 — ontology-team 오픈소스 공개 대상).

생성물(자동 — 수동 편집 금지, 본 스크립트를 고친다):
  ontology-team/06-reasoning/ontology/kosha-canonical-code-shape.ttl
검증 실행:
  python ontology-team/06-reasoning/ontology/scripts/validate_canonical_codes.py --gate
재생성:
  python ontology-team/06-reasoning/ontology/scripts/gen_canonical_code_shape.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "shared" / "reference"))
sys.path.insert(0, str(ROOT / "serving-team" / "08-app" / "backend"))
import canonical_vocab as cv  # noqa: E402
from app.integrations.code_iri_mapper import _camel  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "kosha-canonical-code-shape.ttl"

# 코드를 객체로 갖는 ABox 술어 → 위험축. exporter(export_owl/export_guide_hazard_to_abox)가
# 산출하는 정본 술어 집합. 축별 shape의 sh:targetObjectsOf로 사용.
# (kosha-instances.ttl: sr:*, kosha-instances-guide-hazard.ttl: guide:*)
AXIS_PREDICATES = {
    "accident_type": ["sr:addressesAccidentType", "guide:addressesHazard"],  # F20: sr:addressesHazard 폐지(→addressesAccidentType)
    "hazardous_agent": ["sr:addressesAgent", "guide:guideAddressesAgent"],
    "work_context": ["sr:inWorkContext", "guide:guideAppliesToContext"],
}
# sr:addressesFeature 는 3축 polymorphic — 정본 62 전체(union) 허용.
FEATURE_PREDICATES = ["sr:addressesFeature"]

AXIS_PREFIX = {"accident_type": "haz", "hazardous_agent": "agent", "work_context": "ctx"}
AXIS_KO = {"accident_type": "사고유형(KOSHA-22)", "hazardous_agent": "위험인자", "work_context": "작업맥락"}
SHAPE_NAME = {
    "accident_type": "CanonicalAccidentTypeCode",
    "hazardous_agent": "CanonicalHazardousAgentCode",
    "work_context": "CanonicalWorkContextCode",
}


def axis_iris(axis: str) -> list[str]:
    """축의 허용 코드 → prefixed IRI 정렬 리스트.

    허용 집합 = canonical(pending bucket 포함) ∪ meta ∪ same-axis fine(WC-A/B: LLM-enriched guide fine
    ABox가 guide:addressesHazard 등 객체로 fine 코드를 쓰므로 허용). fine은 fine⊑canonical(taxonomy)이라
    canonical의 IS-A — range/축 정합. cross-axis/UNKNOWN fine은 same_axis_fine에서 제외(드리프트 차단).
    """
    pfx = AXIS_PREFIX[axis]
    allowed = cv.canonical_set(axis) | cv.meta_set(axis) | cv.same_axis_fine(axis)
    return [f"{pfx}:{_camel(c)}" for c in sorted(allowed)]


def fmt_in_list(iris: list[str], indent: str = "        ") -> str:
    """sh:in RDF 리스트를 가독성 있게 wrap (한 줄 4개)."""
    rows = []
    for i in range(0, len(iris), 4):
        rows.append(indent + " ".join(iris[i : i + 4]))
    return "\n".join(rows)


def node_shape(name: str, comment: str, predicates: list[str], iris: list[str], msg: str) -> str:
    targets = " ;\n    ".join(f"sh:targetObjectsOf {p}" for p in predicates)
    return (
        f"# {comment}\n"
        f"shape:{name} a sh:NodeShape ;\n"
        f"    {targets} ;\n"
        f"    sh:nodeKind sh:IRI ;\n"
        f"    sh:in (\n{fmt_in_list(iris)}\n    ) ;\n"
        f'    sh:message "{msg}" ;\n'
        f"    sh:severity sh:Violation .\n"
    )


def main() -> int:
    per_axis = {a: axis_iris(a) for a in AXIS_PREFIX}
    feature_iris = per_axis["accident_type"] + per_axis["hazardous_agent"] + per_axis["work_context"]
    counts = {a: len(v) for a, v in per_axis.items()}
    total = sum(counts.values())

    lines = [
        "# Phase 5 가드레일 — 위험축 코드 IRI ∈ KOSHA-22 정본 어휘 SHACL shape.",
        "# 자동 생성(SSOT 파생) — 수동 편집 금지. 재생성: scripts/gen_canonical_code_shape.py",
        f"# SSOT: shared/reference/canonical-code-vocabulary.json  (accident {counts['accident_type']}"
        f" / agent {counts['hazardous_agent']} / work_context {counts['work_context']} = {total})",
        "# 검증: scripts/validate_canonical_codes.py --gate  (pyshacl)",
        "@prefix sh: <http://www.w3.org/ns/shacl#> .",
        "@prefix shape: <https://cashtoss.info/ontology/shape#> .",
        "@prefix haz: <https://cashtoss.info/ontology/risk/hazard#> .",
        "@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .",
        "@prefix ctx: <https://cashtoss.info/ontology/risk/context#> .",
        "@prefix sr: <https://cashtoss.info/ontology/sr#> .",
        "@prefix guide: <https://cashtoss.info/ontology/guide#> .",
        "",
    ]
    for axis in ("accident_type", "hazardous_agent", "work_context"):
        msg = (
            f"{AXIS_KO[axis]} 코드 IRI는 KOSHA-22 정본 {counts[axis]}개 안에만 허용됩니다 "
            f"(legacy/UPPER/오타 fragment = 드리프트)."
        )
        lines.append(
            node_shape(
                SHAPE_NAME[axis],
                f"=== {axis} ({counts[axis]}) — {', '.join(AXIS_PREDICATES[axis])} ===",
                AXIS_PREDICATES[axis],
                per_axis[axis],
                msg,
            )
        )
    # polymorphic feature 술어 — 62 union 허용.
    lines.append(
        node_shape(
            "CanonicalRiskFeatureCode",
            f"=== risk feature (polymorphic, {total} union) — {', '.join(FEATURE_PREDICATES)} ===",
            FEATURE_PREDICATES,
            feature_iris,
            f"sr:addressesFeature 코드 IRI는 3축 정본 {total}개(union) 안에만 허용됩니다.",
        )
    )

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"생성: {OUT.name}")
    print(f"  accident {counts['accident_type']} / agent {counts['hazardous_agent']} "
          f"/ work_context {counts['work_context']} = {total} canonical IRIs")
    print(f"  shapes: {len(SHAPE_NAME)} axis NodeShape + 1 feature union = {len(SHAPE_NAME) + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
