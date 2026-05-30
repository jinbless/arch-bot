#!/usr/bin/env python3
"""B3 — SWRL/SHACL 규칙 parity harness.

목적: R-14~R-30(SHACL twin 보유)을 demo-chain fixture에 두 엔진으로 적용해 추론 동치를 검증.
동치면 SWRL 4파일(r14-r18/r19-r23/r24-r26/r28-r30) 은퇴 가능.

1차(이 스크립트): SHACL 측 — pyshacl로 demo-chain에 R-14~R-30 SHACL CONSTRUCT 적용, 추론 산출 캡처.
2차(TODO): SWRL 측 — Openllet(Fuseki 컨테이너)로 demo-chain+TBox+R-14~R-30 SWRL 추론 export.
3차: compare_graphs로 두 산출 동치 비교.

순수 진단(소스 파일 미수정).
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdflib import Graph  # noqa: E402

ONT = Path(__file__).resolve().parents[1]
DEMO = ONT / "kosha-instances-demo-chain.ttl"
TBOX = ONT / "kosha-ontology-v2.owl"  # 클래스/속성 정의(prefix 해석)
SHACL_FILES = [
    ONT / "kosha-rules-r14-r30-shacl-construct.ttl",
    ONT / "kosha-r27-shacl-exempted.ttl",
]


def _short(uri: str) -> str:
    return uri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def shacl_side() -> set:
    """demo-chain에 SHACL R-14~R-30 적용 → 추론 triple 집합."""
    from pyshacl import validate

    data = Graph()
    data.parse(str(TBOX), format="xml")
    data.parse(str(DEMO), format="turtle")
    before = set(data)

    shapes = Graph()
    for s in SHACL_FILES:
        shapes.parse(str(s), format="turtle")

    validate(
        data, shacl_graph=shapes, ont_graph=None, advanced=True,
        inplace=True, iterate_rules=True, inference="none",
        allow_infos=True, allow_warnings=True,
    )
    return set(data) - before


def main() -> int:
    print("=== B3 parity harness — SHACL 측 (demo-chain) ===")
    print(f"  fixture: {DEMO.name}")
    inferred = shacl_side()
    print(f"  SHACL 추론 triple 수: {len(inferred)}")
    by_pred = Counter(_short(str(p)) for _s, p, _o in inferred)
    print("  술어별 분포(=어느 규칙이 발화했나):")
    for pred, n in by_pred.most_common():
        print(f"    {n:3}  {pred}")
    print("\n  (SWRL/Pellet 측은 Openllet harness 필요 — 2차 TODO. 이후 compare_graphs로 동치.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
