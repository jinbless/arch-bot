#!/usr/bin/env python3
"""WC-A/B — LLM-enriched guide fine 태그(PG GF)를 온톨로지 ABox로 정합(emit).

PG guide_entity_feature_candidates(method LIKE 'llm_enriched_%', entity_type='GUIDE')의
fine 태그를 guide:addressesHazard/guideAddressesAgent/guideAppliesToContext + **fine 코드**
(fold 안 함)로 emit → kosha-instances-guide-fine.ttl. fine⊑canonical taxonomy가 있으므로
리즈너가 canonical도 추론(range 충족). 서빙은 PG를 보지만, 온톨로지가 동일 fine 지식을 정본 보유.

same-axis fine만(cv.same_axis_fine = taxonomy·allowlist와 동일 정의). cross-axis/UNKNOWN-rollup은
skip(타 disjoint 안전 + 미선언 클래스 회피) → 별도 rollup 큐레이션 대상.

사용: PYTHONIOENCODING=utf-8 python scripts/gen_guide_fine_abox.py
산출: ontology-team/06-reasoning/ontology/kosha-instances-guide-fine.ttl
"""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg2

ONT = Path(__file__).resolve().parents[1]
ROOT = next(a for a in ONT.parents if (a / "shared" / "reference").is_dir())
sys.path.insert(0, str(ROOT / "serving-team" / "08-app" / "backend"))
from app.integrations.code_iri_mapper import fine_iri_fragment  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PG = "dbname=kosha user=kosha password=1229 host=localhost"
OUT = ONT / "kosha-instances-guide-fine.ttl"
AXIS_MAP = {
    "accident_type": ("guide:addressesHazard", "haz"),
    "hazardous_agent": ("guide:guideAddressesAgent", "agent"),
    "work_context": ("guide:guideAppliesToContext", "ctx"),
}
HEADER = """# WC-A/B — LLM-enriched guide fine 태그 ABox (gen_guide_fine_abox.py 산출, 수동편집 금지).
# PG guide_entity_feature_candidates(method=llm_enriched_*) → guide:addressesHazard/guideAddressesAgent/
# guideAppliesToContext + fine 코드(fold 안 함). fine⊑canonical(kosha-facet-taxonomy)로 canonical 추론.
# same-axis fine만(cv.same_axis_fine); cross-axis/UNKNOWN은 skip(rollup 큐레이션 대상).

@prefix guide: <https://cashtoss.info/ontology/guide#> .
@prefix haz: <https://cashtoss.info/ontology/risk/hazard#> .
@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .
@prefix ctx: <https://cashtoss.info/ontology/risk/context#> .

"""


def main() -> int:
    conn = psycopg2.connect(PG)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT guide_code, axis, feature_code
        FROM guide_entity_feature_candidates
        WHERE entity_type='GUIDE' AND method LIKE 'llm_enriched_%'
        ORDER BY guide_code, axis, feature_code
    """)
    by_guide: dict = {}
    n = skipped = 0
    for guide_code, axis, code in cur.fetchall():
        prop_ns = AXIS_MAP.get(axis)
        if not prop_ns:
            skipped += 1
            continue
        prop, ns = prop_ns
        frag = fine_iri_fragment(axis, code)  # same-axis fine만, fold 안 함
        if not frag:
            skipped += 1
            continue
        by_guide.setdefault(guide_code, set()).add(f"    {prop} {ns}:{frag}")
        n += 1
    conn.close()

    lines = [HEADER]
    for guide_code in sorted(by_guide):
        lines.append(f"guide:{guide_code}")
        lines.append(" ;\n".join(sorted(by_guide[guide_code])) + " .")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.name}: {len(by_guide)} guides, {n} fine triples (skipped cross-axis/UNKNOWN {skipped})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
