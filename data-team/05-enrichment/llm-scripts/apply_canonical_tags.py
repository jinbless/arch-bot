#!/usr/bin/env python3
"""Phase 2 — 기존 fine 태그 → canonical 컬럼 populate (Additive 듀얼 태깅).

fine 컬럼(accident_types/hazardous_agents/work_contexts)은 보존하고,
canonical_vocab.to_canonical()로 환원한 값을 *_canonical 컬럼에 채운다(교차축 반영).
컬럼은 아직 어떤 서빙 쿼리도 안 읽음 → inert·가역(회귀 0).

사용: PYTHONIOENCODING=utf-8 python data-team/05-enrichment/llm-scripts/apply_canonical_tags.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch, Json

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "shared" / "reference"))
import canonical_vocab as cv  # noqa: E402

PG = "dbname=kosha user=kosha password=1229 host=localhost"
AXES = ["accident_type", "hazardous_agent", "work_context"]


def canon_row(at, ha, wc) -> dict[str, list[str]]:
    """row의 3 fine 배열 → 축별 canonical 집합(교차축 재배치 반영)."""
    acc = {a: set() for a in AXES}
    for axis, codes in (("accident_type", at), ("hazardous_agent", ha), ("work_context", wc)):
        for tgt, clist in cv.canonicalize_list(axis, codes or []).items():
            if tgt in acc:
                acc[tgt].update(clist)
    return {a: sorted(acc[a]) for a in AXES}


def do_faceted(cur, table) -> int:
    cur.execute(f"SELECT ctid, accident_types, hazardous_agents, work_contexts FROM {table}")
    rows = cur.fetchall()
    upd = []
    for ctid, at, ha, wc in rows:
        c = canon_row(at, ha, wc)
        upd.append((Json(c["accident_type"]), Json(c["hazardous_agent"]), Json(c["work_context"]), ctid))
    execute_batch(
        cur,
        f"UPDATE {table} SET accident_types_canonical=%s, hazardous_agents_canonical=%s, "
        f"work_contexts_canonical=%s WHERE ctid=%s",
        upd, page_size=1000,
    )
    return len(upd)


def do_guide_feat(cur) -> int:
    cur.execute(
        "SELECT ctid, axis, feature_code FROM guide_entity_feature_candidates WHERE axis = ANY(%s)",
        (AXES,),
    )
    rows = cur.fetchall()
    upd = []
    for ctid, axis, code in rows:
        a2, c2 = cv.to_canonical(axis, code)
        upd.append((c2, a2, ctid))
    execute_batch(
        cur,
        "UPDATE guide_entity_feature_candidates SET canonical_code=%s, canonical_axis=%s WHERE ctid=%s",
        upd, page_size=1000,
    )
    return len(upd)


def main():
    conn = psycopg2.connect(PG)
    cur = conn.cursor()
    n_sr = do_faceted(cur, "safety_requirements")
    n_ci = do_faceted(cur, "checklist_items")
    n_gf = do_guide_feat(cur)
    conn.commit()
    # 검증: canonical 컬럼 distinct 코드 수
    print(f"populated: SR={n_sr} CI={n_ci} guide_feat={n_gf}")
    for col in ("accident_types_canonical", "hazardous_agents_canonical", "work_contexts_canonical"):
        cur.execute(f"SELECT count(DISTINCT v) FROM safety_requirements, jsonb_array_elements_text({col}) v")
        print(f"  SR {col}: {cur.fetchone()[0]} distinct")
    conn.close()


if __name__ == "__main__":
    main()
