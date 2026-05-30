#!/usr/bin/env python3
"""Phase 5 가드레일 — ABox 코드 IRI ∈ canonical SHACL 검증 (pyshacl).

kosha-canonical-code-shape.ttl(gen_canonical_code_shape.py 산출)를 ABox에 적용해
SR/Guide가 참조하는 위험축 코드 IRI가 KOSHA-22 정본 62개 안에 있는지 형식 검증.
audit_code_consistency.py(regex 게이트)의 선언적 SHACL 보완재.

사용:
  python scripts/validate_canonical_codes.py            # 기본 ABox, 리포트
  python scripts/validate_canonical_codes.py --gate     # 위반 시 exit 1 (CI)
  python scripts/validate_canonical_codes.py --data a.ttl b.ttl   # 대상 파일 지정
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ONT = Path(__file__).resolve().parents[1]
SHAPE = ONT / "kosha-canonical-code-shape.ttl"
# 코드 술어(sr:* / guide:*)를 포함하는 ABox 기본 대상.
DEFAULT_DATA = ["kosha-instances.ttl", "kosha-instances-guide-hazard.ttl"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", action="store_true", help="위반(sh:Violation) 발견 시 exit 1")
    ap.add_argument("--data", nargs="*", default=None, help="검증 대상 TTL (기본: ABox 코드 파일)")
    ap.add_argument("--max-show", type=int, default=20, help="위반 샘플 표시 개수")
    args = ap.parse_args()

    from rdflib import Graph
    from rdflib.namespace import SH
    from pyshacl import validate

    if not SHAPE.exists():
        print(f"shape 없음: {SHAPE} — 먼저 gen_canonical_code_shape.py 실행", file=sys.stderr)
        return 2

    data_files = args.data if args.data else DEFAULT_DATA
    data = Graph()
    t0 = time.time()
    print("=== 데이터 그래프 로드 ===")
    for f in data_files:
        p = Path(f)
        if not p.is_absolute():
            p = ONT / f
        if not p.exists():
            print(f"  MISSING: {p}", file=sys.stderr)
            continue
        pre = len(data)
        data.parse(str(p), format="turtle")
        print(f"  +{len(data)-pre:>8} triples  {p.name}")
    print(f"  total {len(data)} triples in {time.time()-t0:.1f}s")

    sg = Graph()
    sg.parse(str(SHAPE), format="turtle")

    print("\n=== pyshacl validate ===")
    t1 = time.time()
    conforms, results_graph, results_text = validate(
        data_graph=data, shacl_graph=sg,
        advanced=False, inference=None, do_owl_imports=False, meta_shacl=False,
    )
    print(f"  conforms={conforms}  ({time.time()-t1:.1f}s)")

    # 위반 집계 — (offending IRI, source shape) 별 focusNode 카운트.
    violations: list[tuple[str, str]] = []
    for res in results_graph.subjects(SH.resultSeverity, SH.Violation):
        val = results_graph.value(res, SH.value)
        src = results_graph.value(res, SH.sourceShape)
        violations.append((str(val) if val else "?", str(src).rsplit("#", 1)[-1] if src else "?"))

    if violations:
        print(f"\n  [FAIL] 비정본 코드 IRI {len(violations)}건:")
        seen = {}
        for val, src in violations:
            seen.setdefault((val, src), 0)
            seen[(val, src)] += 1
        for (val, src), n in sorted(seen.items(), key=lambda x: -x[1])[: args.max_show]:
            print(f"    {val}  (shape:{src}) ×{n}")
        extra = len(seen) - args.max_show
        if extra > 0:
            print(f"    … (+{extra} distinct)")
    else:
        print("  [OK] 모든 위험축 코드 IRI가 KOSHA-22 정본 어휘 안에 있습니다.")

    if args.gate and not conforms:
        print(f"\nGATE FAIL — 비정본 코드 IRI {len(violations)}건. (exit 1)")
        return 1
    print(f"\nGATE {'PASS' if conforms else 'PASS(비-gate 모드, 위반 존재)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
