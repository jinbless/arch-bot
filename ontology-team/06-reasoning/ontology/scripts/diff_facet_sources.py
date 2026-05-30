#!/usr/bin/env python3
"""catalog `sub` vs vocab `rollup` — facet 계층 '지식 내용' 비교 (구조 무관).

질문(사용자): 두 소스가 같은 지식인데 구조만 다른가, 아니면 지식 내용이 다른가?
  - 같으면 → 구조 하나로 통일(완전통합 안전)
  - 다르면 → 지식은 합집합, 구조만 통일

방법: 각 소스에서 fine_code -> ultimate_canonical 매핑을 계산해 비교한다.
  - catalog: axes[axis].codes[code].sub  (parent code -> children sub)
             → child->parent 역전 → 루트(=부모 없는 노드)까지 transitive 해소
  - vocab  : axes[axis].rollup  (fine -> canonical, cross-axis는 "axis:CODE")
  canonical 판정의 ground-truth = vocab의 axes[axis].canonical 리스트.

출력: 축별 coverage(양쪽/한쪽), ultimate canonical 일치/충돌, catalog intermediate, vocab cross-axis.
순수 진단(어떤 파일도 수정하지 않음).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _root() -> Path:
    for a in Path(__file__).resolve().parents:
        if (a / "shared" / "reference" / "canonical-code-vocabulary.json").exists():
            return a
    raise RuntimeError("repo root not found")


ROOT = _root()
CATALOG = ROOT / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
VOCAB = ROOT / "shared/reference/canonical-code-vocabulary.json"
AXES = ["accident_type", "hazardous_agent", "work_context"]


def roots_of(code: str, parent: dict[str, set[str]], seen: set[str] | None = None) -> set[str]:
    """parent 맵을 따라 위로 올라가 루트(부모 없는 노드) 집합 반환. cycle 안전."""
    seen = set() if seen is None else seen
    if code in seen:
        return set()
    seen.add(code)
    ps = parent.get(code)
    if not ps:
        return {code}
    out: set[str] = set()
    for p in ps:
        out |= roots_of(p, parent, seen)
    return out


def main() -> int:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    voc = json.loads(VOCAB.read_text(encoding="utf-8"))

    overall_same = True
    for axis in AXES:
        print(f"\n{'=' * 70}\n=== AXIS: {axis} ===\n{'=' * 70}")
        canon = set(voc["axes"][axis]["canonical"])
        canon |= set(voc["axes"][axis].get("wc_meta") or [])
        pending_bucket = voc["axes"][axis].get("pending_bucket")

        # ---- catalog: child->parent, then transitive roots ----
        cat_codes = (cat.get("axes", {}).get(axis, {}) or {}).get("codes", {}) or {}
        parent: dict[str, set[str]] = {}
        cat_universe: set[str] = set()
        for code, info in cat_codes.items():
            cat_universe.add(code)
            for sub in (info.get("sub") or []):
                parent.setdefault(sub, set()).add(code)
                cat_universe.add(sub)
        # intermediate = 부모도 있고 자식도 있는 노드
        has_children = {c for c, info in cat_codes.items() if (info.get("sub"))}
        intermediates = sorted({n for n in cat_universe if n in parent and n in has_children})
        cat_map: dict[str, set[str]] = {}
        for code in cat_universe:
            if code in canon:
                continue  # canonical 자체는 fine 아님
            cat_map[code] = roots_of(code, parent)

        # ---- vocab: rollup fine->canonical (cross-axis 분리) ----
        rollup = voc["axes"][axis].get("rollup", {}) or {}
        voc_map: dict[str, str] = {}      # same-axis fine -> canonical
        cross_axis: dict[str, str] = {}   # fine -> "axis:CODE"
        for fine, target in rollup.items():
            if fine in canon and fine == target:
                continue  # identity(canonical->self)
            if ":" in target:
                cross_axis[fine] = target
            else:
                voc_map[fine] = target

        cat_fines = set(cat_map)
        voc_fines = set(voc_map) | set(cross_axis)
        both = cat_fines & voc_fines
        cat_only = sorted(cat_fines - voc_fines)
        voc_only = sorted(voc_fines - cat_fines)

        print(f"catalog fine: {len(cat_fines)} | vocab fine: {len(voc_fines)} "
              f"| both: {len(both)} | catalog-only: {len(cat_only)} | vocab-only: {len(voc_only)}")
        print(f"catalog intermediates (다단계): {len(intermediates)}  {intermediates[:20]}")
        if cross_axis:
            print(f"vocab cross-axis ({len(cross_axis)}): "
                  + ", ".join(f"{k}->{v}" for k, v in list(cross_axis.items())[:12])
                  + (" ..." if len(cross_axis) > 12 else ""))

        # ---- 양쪽에 있는 fine: ultimate canonical 일치? ----
        conflicts = []
        cross_conflicts = []
        agree = 0
        for f in sorted(both):
            cat_roots = cat_map[f]
            if f in cross_axis:
                cross_conflicts.append((f, sorted(cat_roots), cross_axis[f]))
                continue
            vc = voc_map[f]
            if cat_roots == {vc}:
                agree += 1
            else:
                conflicts.append((f, sorted(cat_roots), vc))

        print(f"\n[일치] ultimate canonical 동일: {agree}/{len(both) - len(cross_conflicts)}")
        if conflicts:
            overall_same = False
            print(f"[충돌] catalog vs vocab canonical 다름: {len(conflicts)}")
            for f, cr, vc in conflicts[:25]:
                print(f"    {f}: catalog->{cr}  vocab->{vc}")
            if len(conflicts) > 25:
                print(f"    ... +{len(conflicts) - 25} more")
        else:
            print("[충돌] 없음 — 양쪽 공통 fine은 전부 같은 canonical로 수렴")

        if cross_conflicts:
            print(f"[cross-axis] catalog는 in-axis 유지, vocab는 타축 이동: {len(cross_conflicts)}")
            for f, cr, vt in cross_conflicts[:25]:
                print(f"    {f}: catalog->{cr}  vocab->{vt}")

        # catalog 내부에서 canonical까지 못 닿는 fine(루트가 canonical 아님) = 끊긴 intermediate
        dangling = {f: sorted(r) for f, r in cat_map.items()
                    if not (r & canon) and not (r & {pending_bucket})}
        if dangling:
            print(f"[catalog dangling] 루트가 canonical 아님: {len(dangling)}  "
                  + ", ".join(f"{k}->{v}" for k, v in list(dangling.items())[:10]))

        if cat_only:
            print(f"\ncatalog-only fine ({len(cat_only)}): {cat_only[:25]}"
                  + (" ..." if len(cat_only) > 25 else ""))
        if voc_only:
            print(f"vocab-only fine ({len(voc_only)}): {voc_only[:25]}"
                  + (" ..." if len(voc_only) > 25 else ""))

    print(f"\n{'=' * 70}")
    print("VERDICT:", "공통 fine 충돌 없음 → '구조만 다른 같은 지식'(통합 안전, 합집합)"
          if overall_same else "충돌 존재 → 내용 차이 있음(합집합 + 충돌 수동 판정 필요)")
    print('=' * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
