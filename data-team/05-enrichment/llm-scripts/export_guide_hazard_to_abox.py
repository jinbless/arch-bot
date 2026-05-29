#!/usr/bin/env python3
"""P3 — Guide 직접 위험 매핑을 ontology ABox로 정합.

guide_entity_feature_candidates(entity_type='GUIDE', method='guide_hazard_weighted_majority')
→ guide:addressesHazard / guideAddressesAgent / guideAppliesToContext triple.

TBox: kosha-ontology-v4-guide-hazard-patch.ttl. "온톨로지가 사실 보유, 서비스 랭킹은 런타임".

사용: PYTHONIOENCODING=utf-8 python export_guide_hazard_to_abox.py
산출: ontology-team/06-reasoning/ontology/kosha-instances-guide-hazard.ttl
"""
from __future__ import annotations

import sys
from pathlib import Path
import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "serving-team" / "08-app" / "backend"))
from app.integrations.code_iri_mapper import iri_fragment  # noqa: E402  KOSHA-22 CamelCase 정본

PG = "dbname=kosha user=kosha password=1229 host=localhost"
OUT = Path(__file__).resolve().parents[3] / "ontology-team/06-reasoning/ontology/kosha-instances-guide-hazard.ttl"

AXIS_MAP = {
    "accident_type": ("guide:addressesHazard", "haz"),
    "hazardous_agent": ("guide:guideAddressesAgent", "agent"),
    "work_context": ("guide:guideAppliesToContext", "ctx"),
}

HEADER = """# P3 — Guide 직접 위험 매핑 ABox (export_guide_hazard_to_abox.py 산출).
# guide_entity_feature_candidates GUIDE feature → guide:addressesHazard 등. PG primary, ontology 정합.

@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix guide: <https://cashtoss.info/ontology/guide#> .
@prefix haz: <https://cashtoss.info/ontology/risk/hazard#> .
@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .
@prefix ctx: <https://cashtoss.info/ontology/risk/context#> .

"""


def main():
    conn = psycopg2.connect(PG)
    cur = conn.cursor()
    cur.execute("""
        SELECT guide_code, axis, feature_code
        FROM guide_entity_feature_candidates
        WHERE entity_type='GUIDE' AND method='guide_hazard_weighted_majority'
        ORDER BY guide_code, axis
    """)
    lines = [HEADER]
    n = 0
    by_guide: dict = {}
    for guide_code, axis, code in cur.fetchall():
        prop_ns = AXIS_MAP.get(axis)
        if not prop_ns:
            continue
        prop, ns = prop_ns
        frag = iri_fragment(axis, code)  # UPPER fine → KOSHA-22 CamelCase 정본
        if not frag:
            continue
        by_guide.setdefault(guide_code, []).append(f"    {prop} {ns}:{frag}")
        n += 1
    for guide_code, triples in by_guide.items():
        lines.append(f"guide:{guide_code}")
        lines.append(" ;\n".join(triples) + " .")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.name}: {len(by_guide)} guides, {n} direct-hazard triples")
    conn.close()


if __name__ == "__main__":
    main()
