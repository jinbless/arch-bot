#!/usr/bin/env python3
"""Phase 3a — 온톨로지 유도 Guide facet → PG 물질화 (올바른 방향: ontology→PG).

kosha-instances-ci-guide-hazard-derived.ttl(run_guide_hazard_rules.py 산출)의
guide:addressesHazard/guideAddressesAgent/guideAppliesToContext(non-boilerplate CI rollup)를
kosha_guides의 canonical facet 컬럼으로 적재. 서빙 query_guide_for_facets가 SR처럼 JSONB @> 매칭.

기존 PG-side 인버전(derive_guide_hazard_features.py + export_guide_hazard_to_abox.py)을 대체.
IRI→canonical code 역변환은 code_iri_mapper.all_canonical_iris() SSOT에서 파생.

사용:
  PYTHONIOENCODING=utf-8 python import_guide_facets_to_pg.py            # dry-run
  PYTHONIOENCODING=utf-8 python import_guide_facets_to_pg.py --apply
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import psycopg2
from rdflib import Graph, Namespace

REPO = Path(__file__).resolve().parents[3]
ONT = REPO / "ontology-team" / "06-reasoning" / "ontology"
DERIVED = ONT / "kosha-instances-ci-guide-hazard-derived.ttl"
PG = "dbname=kosha user=kosha password=1229 host=localhost"

sys.path.insert(0, str(REPO / "serving-team" / "08-app" / "backend"))
from app.integrations.code_iri_mapper import all_canonical_iris  # noqa: E402

GUIDE = Namespace("https://cashtoss.info/ontology/guide#")
# 유도 술어 → kosha_guides 컬럼 + 축
PRED_COL = {
    GUIDE.addressesHazard: ("addresses_hazard_canonical", "accident_type"),
    GUIDE.guideAddressesAgent: ("hazardous_agents_canonical", "hazardous_agent"),
    GUIDE.guideAppliesToContext: ("work_contexts_canonical", "work_context"),
}


def build_iri_to_code() -> dict[str, str]:
    """full IRI → canonical UPPER code (SSOT 역변환). work_context wc_meta(SAFETY_MGMT 등) 포함."""
    from app.integrations.code_iri_mapper import NAMESPACES, _AXIS_PREFIX, _camel
    import canonical_vocab as cv
    m = {}
    for axis, code, prefixed in all_canonical_iris():
        pfx = _AXIS_PREFIX[axis]
        full = NAMESPACES[pfx] + prefixed.split(":", 1)[1]
        m[full] = code
    # wc_meta(canonical 외 정당 축값) — IRI는 export가 산출하나 all_canonical_iris엔 없음.
    for code in cv.meta_set("work_context"):
        m[NAMESPACES["context"] + _camel(code)] = code
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    iri2code = build_iri_to_code()
    g = Graph()
    g.parse(str(DERIVED), format="turtle")

    # guide_code → col → set(codes)
    guide_facets: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    unmapped = 0
    for pred, (col, _axis) in PRED_COL.items():
        for s, _p, o in g.triples((None, pred, None)):
            gc = str(s).split("#", 1)[1]
            code = iri2code.get(str(o))
            if code:
                guide_facets[gc][col].add(code)
            else:
                unmapped += 1

    cols = [c for c, _ in PRED_COL.values()]
    print(f"derived 파싱: {len(g)} triple → {len(guide_facets)} guide")
    for col in cols:
        n = sum(1 for gf in guide_facets.values() if gf.get(col))
        tot = sum(len(gf.get(col, ())) for gf in guide_facets.values())
        print(f"  {col}: {n} guide, {tot} code")
    if unmapped:
        print(f"  [warn] IRI→code 미매핑 {unmapped}")

    if not args.apply:
        print("\n--apply 로 ALTER + UPSERT")
        return 0

    conn = psycopg2.connect(PG)
    cur = conn.cursor()
    print("\n[apply] ALTER kosha_guides ADD facet 컬럼 (additive)...")
    for col in cols:
        cur.execute(f"ALTER TABLE kosha_guides ADD COLUMN IF NOT EXISTS {col} jsonb")
    updated = 0
    for gc, fac in guide_facets.items():
        sets, vals = [], []
        for col in cols:
            codes = sorted(fac.get(col, ()))
            sets.append(f"{col} = %s")
            vals.append(json.dumps(codes))
        vals.append(gc)
        cur.execute(f"UPDATE kosha_guides SET {', '.join(sets)} WHERE guide_code = %s", vals)
        updated += cur.rowcount
    conn.commit()
    cur.execute("SELECT count(*) FROM kosha_guides WHERE addresses_hazard_canonical IS NOT NULL "
                "AND addresses_hazard_canonical::text NOT IN ('[]','null')")
    print(f"  UPDATE matched {updated} rows; addresses_hazard 보유 guide: {cur.fetchone()[0]}")
    conn.close()
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
