#!/usr/bin/env python3
"""Facet state 패치 생성기 — CAT-4 Stage 2 (F13 후속).

전량 SHE export(--scope active)에서 드러난 비주축 차원(ppe_state/environmental/
work_activity/agent_state/temporal_stage)의 구체값 중 TBox에 OWL 백킹이 없는
것(gap)을 부모 클래스 하위 NamedIndividual로 선언하는 패치 TTL을 생성한다.

3개 주축(accident/agent/context)은 canonical-code-vocabulary.json SSOT로
facet-taxonomy가 자동 모델링하지만, ppe/env/activity 등 비주축은 SSOT 축이 아니라
부모 클래스(ctx:PPEState 등, v2.owl 선언)만 있고 구체값 개체는 누락돼 있었다
(기존 L2 37패턴이 전부 OTHER였어서 비가시 → full export로 표면화).

결정적: PG 서빙 패턴의 distinct (dim, value) → snake_to_pascal → TBox(부모)
하위 NamedIndividual. 이미 정의된 값·OTHER는 skip. 부모 클래스는 TBox에 반드시
존재해야 함(없으면 에러 — dangling 방지).

출력: ontology-team/06-reasoning/ontology/kosha-facet-state-patch.ttl
사용: python gen_facet_state_patch.py [--apply]   (기본 dry-run)
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
from rdflib import Graph, RDF, RDFS, OWL

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
ONT = ROOT / "ontology-team" / "06-reasoning" / "ontology"
sys.path.insert(0, str(ONT / "assembly"))
import manifest_source as MS  # noqa: E402

OUT = ONT / "kosha-facet-state-patch.ttl"
PG_DSN = (os.environ.get("PG_DSN") or os.environ.get("DATABASE_URL")
          or "dbname=kosha user=kosha password=1229 host=localhost port=5432")
CTX_NS = "https://cashtoss.info/ontology/risk/context#"

# 비주축 dim → (부모 클래스 local, OTHER 개체 local). 주축(work_context/accident/agent)은 제외.
DIM_PARENT = {
    "ppe_state":      ("PPEState", "OtherPPEState"),
    "environmental":  ("EnvironmentalFactor", "OtherEnvironmental"),
    "work_activity":  ("WorkActivity", "OtherActivity"),
    "agent_state":    ("AgentState", "OtherAgentState"),
    "temporal_stage": ("TemporalStage", "OtherTemporal"),
}


def snake_to_pascal(code: str) -> str:
    return "".join(seg.capitalize() for seg in code.split("_"))


def defined_facets() -> set:
    """serving profile 비-instances 파일의 owl:Class/NamedIndividual/subClassOf 주어 IRI."""
    defined = set()
    for e in MS.by_profile("serving"):
        if "instances" in e["file"]:
            continue
        g = Graph()
        g.parse(str(ONT / e["file"]), format=("xml" if e["format"] == "xml" else "turtle"))
        for s in g.subjects(RDF.type, OWL.Class):
            defined.add(str(s))
        for s in g.subjects(RDF.type, OWL.NamedIndividual):
            defined.add(str(s))
        for s, _o in g.subject_objects(RDFS.subClassOf):
            defined.add(str(s))
    return defined


def fetch_dim_values() -> tuple[dict[str, set[str]], set[str]]:
    """서빙 패턴 features의 비주축 dim별 distinct 값(비-OTHER) + work_context Pascal 집합.

    work_context는 주축이라 ctx:Pascal이 owl:Class(⊑ WorkContext)로 정의된다.
    비주축 값이 같은 Pascal이면 한 IRI가 WorkContext와 (예) WorkActivity 양쪽에 속해
    axis-disjoint 위반 → 리즈너 비일관. 그 충돌 검출용으로 wc Pascal을 함께 반환.
    """
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT features FROM she_catalog
        WHERE status IN ('approved_auto', 'approved_manual')
    """)
    out: dict[str, set[str]] = {d: set() for d in DIM_PARENT}
    wc_pascals: set[str] = set()
    for (features,) in cur.fetchall():
        if not isinstance(features, dict):
            continue
        wc = features.get("work_context")
        if wc and wc != "OTHER":
            wc_pascals.add(snake_to_pascal(wc))
        for dim in DIM_PARENT:
            v = features.get(dim)
            if v and v != "OTHER":
                out[dim].add(v)
    cur.close()
    conn.close()
    return out, wc_pascals


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="파일 기록(기본 dry-run)")
    args = ap.parse_args()

    defined = defined_facets()
    # 부모 클래스 존재 검증 (dangling 방지)
    missing_parents = [p for (p, _o) in DIM_PARENT.values() if CTX_NS + p not in defined]
    if missing_parents:
        print(f"[FAIL] 부모 클래스가 TBox에 없음: {missing_parents}", file=sys.stderr)
        return 1

    dim_values, wc_pascals = fetch_dim_values()
    rows: list[tuple[str, str, str, str]] = []  # (pascal, parent, original, dim)
    seen: set[str] = set()
    conflicts: list[tuple[str, str, str]] = []  # (pascal, dim, parent) — wc와 disjoint 충돌
    for dim, (parent, _other) in DIM_PARENT.items():
        for val in sorted(dim_values[dim]):
            pascal = snake_to_pascal(val)
            iri = CTX_NS + pascal
            if pascal in wc_pascals:
                # 같은 코드가 work_context(주축, ⊑WorkContext)로도 쓰임 → 한 IRI가 두
                # disjoint 축 멤버가 되면 비일관. 비주축 개체 선언 금지(카탈로그 정정 대상).
                conflicts.append((pascal, dim, parent))
                continue
            if iri in defined or pascal in seen:
                continue
            seen.add(pascal)
            rows.append((pascal, parent, val, dim))

    if conflicts:
        print(f"[WARN] cross-axis 충돌 {len(conflicts)}건 — work_context와 같은 ctx Pascal이라 "
              f"비주축 개체 미선언(axis-disjoint 비일관 방지, 카탈로그 정정 대상):",
              file=sys.stderr)
        for pascal, dim, parent in sorted(conflicts):
            print(f"    ctx:{pascal} ({dim}→{parent} vs work_context)", file=sys.stderr)
    print(f"  서빙 패턴 비주축 값 → 신규 개체 {len(rows)}종 (이미 정의/OTHER/충돌 제외)")
    by_parent: dict[str, int] = {}
    for _p, parent, _o, _d in rows:
        by_parent[parent] = by_parent.get(parent, 0) + 1
    for parent, n in sorted(by_parent.items()):
        print(f"    {parent}: {n}")

    if not rows:
        print("  gap 0 — 패치 불요")
        return 0

    lines = [
        "# kosha-facet-state-patch.ttl — 비주축 차원(ppe/env/activity/agent_state/temporal) 구체값 OWL 백킹",
        "# (AUTO-GENERATED by data-team/04-ontology-export/export-scripts/gen_facet_state_patch.py — 수동편집 금지)",
        "# 소스: PG she_catalog 서빙 패턴 features. 부모 클래스(ctx:PPEState 등)는 v2.owl 선언.",
        "@prefix owl:  <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix ctx:  <https://cashtoss.info/ontology/risk/context#> .",
        "",
    ]
    cur_parent = None
    for pascal, parent, original, dim in sorted(rows, key=lambda r: (r[1], r[0])):
        if parent != cur_parent:
            lines.append(f"\n# ── {parent} ({dim} 외) ──")
            cur_parent = parent
        label = original.replace("_", " ").lower()
        lines.append(
            f'ctx:{pascal} a owl:NamedIndividual, ctx:{parent} ; '
            f'rdfs:label "{label}"@en .'
        )
    ttl = "\n".join(lines) + "\n"

    if args.apply:
        OUT.write_text(ttl, encoding="utf-8")
        print(f"[OK] wrote {OUT.name} ({len(rows)} 개체)")
    else:
        print("[DRY-RUN] --apply로 기록. 미리보기(첫 8):")
        for ln in [x for x in lines if x.startswith("ctx:")][:8]:
            print("   ", ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
