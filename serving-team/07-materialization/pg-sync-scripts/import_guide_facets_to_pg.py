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
# 큐레이션 fine ABox(gen_guide_fine_abox.py 산출, tracked + assembly manifest 등록) — SSOT.
# CI-rollup이 과광범위(항만하역 accident 8종 등)인 반면 fine ABox는 LLM 큐레이션(과대태깅 금지).
FINE_ABOX = ONT / "kosha-instances-guide-fine.ttl"
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


def build_fine_iri_to_code() -> dict[str, str]:
    """fine IRI(haz:FallFromHeight 등) → same-axis canonical UPPER code (fold).

    큐레이션 fine ABox는 fine 코드 IRI 보유 → canonical 컬럼 적재엔 fold 필요. gen_guide_fine_abox.py가
    쓸 때 쓴 fine_iri_fragment(정방향)으로 fragment 재현 → IRI 역인덱스 + to_canonical로 canonical 환원.
    """
    from app.integrations.code_iri_mapper import NAMESPACES, _AXIS_PREFIX, fine_iri_fragment
    import canonical_vocab as cv
    m: dict[str, str] = {}
    for axis in ("accident_type", "hazardous_agent", "work_context"):
        pfx = NAMESPACES[_AXIS_PREFIX[axis]]
        for fine in cv.same_axis_fine(axis):
            frag = fine_iri_fragment(axis, fine)
            if not frag:
                continue
            _a, canon = cv.to_canonical(axis, fine)
            m[pfx + frag] = canon
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-fine-curation", action="store_true",
                    help="큐레이션 fine ABox accident override 비활성(구 CI-rollup만). 기본은 적용.")
    args = ap.parse_args()

    iri2code = build_iri_to_code()
    cols = [c for c, _ in PRED_COL.values()]
    guide_facets: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))

    # ① CI-rollup 파생 TTL(recall) — gitignored·재생성형. 부재 시 graceful(큐레이션 accident만 갱신).
    derived_present = DERIVED.exists()
    if derived_present:
        g = Graph()
        g.parse(str(DERIVED), format="turtle")
        unmapped = 0
        for pred, (col, _axis) in PRED_COL.items():
            for s, _p, o in g.triples((None, pred, None)):
                gc = str(s).split("#", 1)[1]
                code = iri2code.get(str(o))
                if code:
                    guide_facets[gc][col].add(code)
                else:
                    unmapped += 1
        print(f"CI-rollup derived: {len(g)} triple → {len(guide_facets)} guide"
              + (f"  ([warn] 미매핑 {unmapped})" if unmapped else ""))
    else:
        print(f"[warn] {DERIVED.name} 부재 → CI-rollup skip. 큐레이션 accident만 갱신(agent/context 미변경).")

    # ② 큐레이션 fine ABox(SSOT) → accident override. over-tagged CI-rollup accident를 큐레이션 set으로
    #    교체(지게차→항만하역류 도메인-무관 부착의 근본 차단). fine→canonical fold(build_fine_iri_to_code).
    if not args.no_fine_curation and FINE_ABOX.exists():
        combined = {**iri2code, **build_fine_iri_to_code()}
        gf = Graph()
        gf.parse(str(FINE_ABOX), format="turtle")
        fine_acc: dict[str, set] = defaultdict(set)
        for s, _p, o in gf.triples((None, GUIDE.addressesHazard, None)):
            gc = str(s).split("#", 1)[1]
            code = combined.get(str(o))
            if code:
                fine_acc[gc].add(code)
        for gc, codes in fine_acc.items():
            guide_facets[gc]["addresses_hazard_canonical"] = set(codes)  # 큐레이션이 CI-rollup 교체
        print(f"큐레이션 fine ABox: accident override {len(fine_acc)} guide")
    elif args.no_fine_curation:
        print("[--no-fine-curation] 큐레이션 override 비활성 (CI-rollup accident 유지)")

    print(f"\n적재 대상 guide: {len(guide_facets)}")
    for col in cols:
        n = sum(1 for gf2 in guide_facets.values() if gf2.get(col))
        tot = sum(len(gf2.get(col, ())) for gf2 in guide_facets.values())
        print(f"  {col}: {n} guide, {tot} code")

    if not args.apply:
        print("\n--apply 로 ALTER + UPDATE")
        return 0

    conn = psycopg2.connect(PG)
    cur = conn.cursor()
    print("\n[apply] ALTER kosha_guides ADD facet 컬럼 (additive)...")
    for col in cols:
        cur.execute(f"ALTER TABLE kosha_guides ADD COLUMN IF NOT EXISTS {col} jsonb")
    # derived 있으면 3컬럼 모두 set(default []); 부재(큐레이션 only)면 accident 컬럼만 set(agent/context 미손상).
    target_cols = cols if derived_present else ["addresses_hazard_canonical"]
    updated = 0
    for gc, fac in guide_facets.items():
        sets = [f"{col} = %s" for col in target_cols]
        vals = [json.dumps(sorted(fac.get(col, ()))) for col in target_cols]
        vals.append(gc)
        cur.execute(f"UPDATE kosha_guides SET {', '.join(sets)} WHERE guide_code = %s", vals)
        updated += cur.rowcount
    conn.commit()
    cur.execute("SELECT count(*) FROM kosha_guides WHERE addresses_hazard_canonical IS NOT NULL "
                "AND addresses_hazard_canonical::text NOT IN ('[]','null')")
    print(f"  UPDATE {updated} rows (cols={target_cols}); addresses_hazard 보유 guide: {cur.fetchone()[0]}")
    conn.close()
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
