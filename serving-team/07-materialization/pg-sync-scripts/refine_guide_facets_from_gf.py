#!/usr/bin/env python3
"""Guide canonical facet 정밀화 — 큐레이션된 GF로 kosha_guides JSONB facet 재생성.

문제: kosha_guides.{addresses_hazard,work_contexts,hazardous_agents}_canonical(JSONB)는
run_guide_hazard_rules.py의 비-boilerplate CI rollup에서 유도돼 **과광범위**(over-tagged).
예: 항만하역(A-G-18)이 COLLISION/SLIP_TRIP까지 태깅 → 지게차 창고 사진이 query_guide_for_facets
(@> OR 매칭)로 항만하역을 표준개선절차에 올림. (work_context는 avg 4.56/max 19로 특히 bloated.)

반면 guide_entity_feature_candidates(GF, entity_type='GUIDE')는 weighted-majority + LLM fine
proposals(tag_guides_*_fine.py)로 **큐레이션**돼 정밀(A-G-18 accident = FALL/STRUCK_BY/COLLAPSE/
CRUSHED_OVERTURNED/CUT_LACERATION, COLLISION 없음). get_guides_by_hazard_features(P2)는 이미 GF를
써서 항만하역을 올바르게 배제. 본 스크립트는 **두 표현을 일치**시켜 query_guide_for_facets(match_fusion)도
P2처럼 정확하게 만든다 — 서빙 스코어링 무변경, 데이터 정밀화만.

전략(무회귀 보수):
  - 축별로 GF(entity_type='GUIDE') 행이 ≥1인 guide만 JSONB = sorted(distinct GF canonical_code)로 교체.
  - GF 행이 0인 guide(accident 63 / agent 130 / wc 1)는 **기존 JSONB 유지**(빈 태그 → recall 회귀 방지).
  - --apply 전 현재 3컬럼을 kosha_guides_facet_backup 테이블로 백업(롤백용).

durability: kosha_guides JSONB는 import_guide_facets_to_pg.py(ontology TTL→PG)가 채운다. 그 스크립트를
재실행하면 본 정밀화가 덮어쓰여진다 → 물질화 순서상 import_guide_facets_to_pg.py **다음에** 실행하거나,
근본적으로는 TTL 유도(run_guide_hazard_rules.py)를 GF 큐레이션 반영하도록 고쳐야 한다(후속 결정).

사용:
  PYTHONIOENCODING=utf-8 python refine_guide_facets_from_gf.py            # dry-run(통계+샘플)
  PYTHONIOENCODING=utf-8 python refine_guide_facets_from_gf.py --apply    # 백업 후 UPDATE
"""
import argparse
import json
import sys

import psycopg2

PG = "dbname=kosha user=kosha password=1229 host=localhost"

# kosha_guides JSONB 컬럼 → GF canonical_axis
COL_AXIS = [
    ("addresses_hazard_canonical", "accident_type"),
    ("hazardous_agents_canonical", "hazardous_agent"),
    ("work_contexts_canonical", "work_context"),
]


def fetch_gf_sets(cur) -> dict[str, dict[str, list[str]]]:
    """guide_code → axis → sorted(distinct canonical_code) (entity_type='GUIDE')."""
    cur.execute(
        "SELECT guide_code, canonical_axis, canonical_code "
        "FROM guide_entity_feature_candidates "
        "WHERE entity_type='GUIDE' AND canonical_code IS NOT NULL"
    )
    acc: dict[str, dict[str, set]] = {}
    for gc, axis, code in cur.fetchall():
        acc.setdefault(gc, {}).setdefault(axis, set()).add(code)
    return {gc: {ax: sorted(s) for ax, s in d.items()} for gc, d in acc.items()}


# GF에 섞인 placeholder/junk canonical 코드 — facet으로 물질화 금지.
_JUNK_CODES = {"UNKNOWN_CONTEXT", "UNKNOWN_AGENT", "UNKNOWN_ACCIDENT", "UNKNOWN", "NONE", ""}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--mode", choices=["trim", "replace"], default="replace",
                    help="replace=GF 큐레이션 set 통째(기본·검증완료: A-G-18 COLLISION 제거 + B-M-36 "
                         "CRUSHED_OVERTURNED 확보) / trim=old∩GF(스퓨리어스만 제거, 누락 코드 보완 불가)")
    ap.add_argument("--axes", default="accident_type",
                    help="콤마구분 대상 축. 기본 accident_type만(GF 신뢰 高·COLLISION 스퓨리어스 위치). "
                         "예: accident_type,hazardous_agent")
    args = ap.parse_args()
    target_axes = {a.strip() for a in args.axes.split(",") if a.strip()}
    active_cols = [(c, ax) for c, ax in COL_AXIS if ax in target_axes]
    print(f"mode={args.mode}  axes={sorted(target_axes)}  cols={[c for c, _ in active_cols]}")

    conn = psycopg2.connect(PG)
    cur = conn.cursor()

    gf = fetch_gf_sets(cur)
    # junk 코드 제거
    for d in gf.values():
        for ax in list(d):
            d[ax] = [c for c in d[ax] if c not in _JUNK_CODES]
    print(f"GF(entity_type=GUIDE) guides: {len(gf)} (junk 코드 필터 적용)")

    # 현재 JSONB 로드(비교/통계)
    cur.execute("SELECT guide_code, addresses_hazard_canonical, hazardous_agents_canonical, "
                "work_contexts_canonical FROM kosha_guides")
    cur_rows = {r[0]: {COL_AXIS[0][0]: r[1] or [], COL_AXIS[1][0]: r[2] or [],
                       COL_AXIS[2][0]: r[3] or []} for r in cur.fetchall()}
    print(f"kosha_guides: {len(cur_rows)}")

    # 변경 계획 계산
    plans: dict[str, dict[str, list[str]]] = {}  # guide → col → new list
    stats = {col: {"changed": 0, "shrunk": 0, "grew": 0, "kept_uncovered": 0,
                   "kept_empty_guard": 0, "old_codes": 0, "new_codes": 0} for col, _ in active_cols}
    for gc, cols in cur_rows.items():
        gfd = gf.get(gc, {})
        for col, axis in active_cols:
            old = sorted(cols[col])
            gf_codes = set(gfd.get(axis) or [])
            if gf_codes:  # GF 커버
                if args.mode == "trim":
                    new = sorted(set(old) & gf_codes)  # 스퓨리어스만 제거, 무추가
                else:  # replace
                    new = sorted(gf_codes)
                if not new:  # 빈 결과 가드 — GF와 완전 불일치 시 기존 유지(recall 보호)
                    stats[col]["kept_empty_guard"] += 1
                    new = old
                if new != old:
                    plans.setdefault(gc, {})[col] = new
                    stats[col]["changed"] += 1
                    stats[col]["shrunk"] += int(len(new) < len(old))
                    stats[col]["grew"] += int(len(new) > len(old))
                stats[col]["old_codes"] += len(old)
                stats[col]["new_codes"] += len(new)
            else:  # GF 미커버 → 유지(빈 태그 방지)
                stats[col]["kept_uncovered"] += 1
                stats[col]["old_codes"] += len(old)
                stats[col]["new_codes"] += len(old)

    print("\n=== 변경 계획(축별) ===")
    for col, _ in active_cols:
        s = stats[col]
        print(f"  {col}: 변경 {s['changed']} (축소 {s['shrunk']}/확장 {s['grew']}), "
              f"미커버 유지 {s['kept_uncovered']}, 빈가드 유지 {s['kept_empty_guard']} | "
              f"총 코드 {s['old_codes']}→{s['new_codes']}")

    # 샘플(과태깅 대표) 표시
    print("\n=== 샘플 before→after ===")
    for gc in ["A-G-18-2026", "A-G-10-2025", "B-5-2011", "B-M-36-2026", "A-G-9-2025"]:
        if gc in cur_rows:
            for col, axis in active_cols:
                old = sorted(cur_rows[gc][col])
                new = plans.get(gc, {}).get(col, old)
                tag = "  *변경*" if new != old else ""
                print(f"  {gc} {col}: {len(old)}→{len(new)}{tag}")
                if new != old:
                    print(f"      old={old}")
                    print(f"      new={new}")

    if not args.apply:
        print("\n--apply 로 백업 후 UPDATE")
        conn.close()
        return 0

    # 백업 테이블(롤백용) — 멱등 재생성
    print("\n[apply] 백업 → kosha_guides_facet_backup ...")
    cur.execute("DROP TABLE IF EXISTS kosha_guides_facet_backup")
    cur.execute("CREATE TABLE kosha_guides_facet_backup AS "
                "SELECT guide_code, addresses_hazard_canonical, hazardous_agents_canonical, "
                "work_contexts_canonical FROM kosha_guides")
    updated = 0
    for gc, cols in plans.items():
        sets = [f"{col} = %s" for col in cols]
        vals = [json.dumps(v) for v in cols.values()] + [gc]
        cur.execute(f"UPDATE kosha_guides SET {', '.join(sets)} WHERE guide_code = %s", vals)
        updated += cur.rowcount
    conn.commit()
    print(f"  UPDATE {updated} guide 행 적용 (백업: kosha_guides_facet_backup).")
    # 검증: 새 평균
    cur.execute("SELECT round(avg(jsonb_array_length(addresses_hazard_canonical))::numeric,2), "
                "round(avg(jsonb_array_length(work_contexts_canonical))::numeric,2) FROM kosha_guides")
    a, w = cur.fetchone()
    print(f"  새 평균: addresses_hazard={a}, work_contexts={w}")
    conn.close()
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
