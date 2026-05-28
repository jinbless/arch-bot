#!/usr/bin/env python3
"""P2 — Guide 직접 위험 매핑 레이어 (guide_entity_feature_candidates GUIDE 적재).

Guide 추천 정확도 개선 plan P2 (근본 해결):
- 각 Guide의 SR집합(Guide→CI→ci_sr_mapping→SR)의 hazard facet(accident_types)을
  **CI 변별력 가중(ci_weight=1/log2(1+guide_frequency)) 다수결**로 집계.
- boilerplate CI는 weight 낮아 자동 배제 → Guide의 "진짜 대표 위험" 상위 N개만 추출.
- guide_entity_feature_candidates 에 entity_type="GUIDE" 행으로 적재.
- 런타임(hazard_to_guide_service)이 hazard코드 → GUIDE feature 직접 조회로 CI 경유 없이 Guide 매칭.

선행: compute_ci_guide_frequency.py --apply (checklist_items.guide_frequency 필요).

사용:
  PYTHONIOENCODING=utf-8 python derive_guide_hazard_features.py            # dry-run
  PYTHONIOENCODING=utf-8 python derive_guide_hazard_features.py --apply    # 적재
  옵션: --top-n 3 --min-conf 0.15
"""
from __future__ import annotations

import argparse
import math
from collections import defaultdict

import psycopg2

PG = "dbname=kosha user=kosha password=1229 host=localhost"
AXES = [("accident_types", "accident_type"), ("hazardous_agents", "hazardous_agent"), ("work_contexts", "work_context")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--top-n", type=int, default=3, help="Guide당 axis별 상위 hazard 수")
    ap.add_argument("--min-conf", type=float, default=0.15, help="정규화 confidence 하한")
    args = ap.parse_args()

    conn = psycopg2.connect(PG)
    cur = conn.cursor()

    # Guide → CI(가중) → SR → facet. accident_types/hazardous_agents/work_contexts는 JSONB array.
    # ci_weight = 1/log2(1+guide_frequency). Guide×axis×code 별 가중합.
    # (guide, axis, code) -> weighted sum
    agg: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))  # guide -> axis -> code -> w
    guide_axis_total: dict = defaultdict(lambda: defaultdict(float))         # guide -> axis -> total w

    for col, axis in AXES:
        cur.execute(f"""
            SELECT c.source_guide,
                   elem.code,
                   sum(1.0 / log(2.0, 1.0 + c.guide_frequency)) AS w
            FROM checklist_items c
            JOIN ci_sr_mapping m ON m.ci_id = c.identifier
            JOIN safety_requirements sr ON sr.identifier = m.sr_id
            CROSS JOIN LATERAL jsonb_array_elements_text(
                CASE WHEN jsonb_typeof(sr.{col})='array' THEN sr.{col} ELSE '[]'::jsonb END
            ) AS elem(code)
            GROUP BY c.source_guide, elem.code
        """)
        for guide, code, w in cur.fetchall():
            if not guide or not code:
                continue
            agg[guide][axis][code] += float(w)
            guide_axis_total[guide][axis] += float(w)

    # 적재 대상 생성: Guide×axis 별 상위 top_n, confidence = code_w / axis_total
    rows = []
    for guide, axes in agg.items():
        for axis, codes in axes.items():
            total = guide_axis_total[guide][axis] or 1.0
            ranked = sorted(codes.items(), key=lambda kv: -kv[1])[:args.top_n]
            for code, w in ranked:
                conf = w / total
                if conf < args.min_conf:
                    continue
                rows.append((guide, axis, code, round(conf, 4), round(w, 3)))

    print(f"=== Guide 직접 위험 매핑 도출 ===")
    print(f"Guide 수: {len(agg)}, 적재 후보 행: {len(rows)} (top-{args.top_n}, min-conf {args.min_conf})")
    # 샘플
    print("샘플 (상위 conf):")
    for guide, axis, code, conf, w in sorted(rows, key=lambda r: -r[3])[:10]:
        print(f"  {guide:12} {axis:16} {code:24} conf={conf:.2f} w={w}")

    if not args.apply:
        print("\n--apply 로 guide_entity_feature_candidates 적재")
        return

    # 기존 method='guide_hazard_weighted_majority' 행 제거 후 재적재 (idempotent)
    cur.execute("DELETE FROM guide_entity_feature_candidates WHERE method='guide_hazard_weighted_majority'")
    deleted = cur.rowcount
    # candidate_id가 BigInteger PK (auto?). 확인: nextval 또는 max+1. 안전하게 max+1 시퀀스.
    cur.execute("SELECT COALESCE(MAX(candidate_id),0) FROM guide_entity_feature_candidates")
    next_id = cur.fetchone()[0] + 1
    ins = 0
    for guide, axis, code, conf, w in rows:
        cur.execute("""
            INSERT INTO guide_entity_feature_candidates
              (candidate_id, entity_type, entity_id, guide_code, axis, feature_code,
               confidence, evidence, source_fields, method, review_status, non_llm_evidence_count)
            VALUES (%s,'GUIDE',%s,%s,%s,%s,%s,%s,%s,'guide_hazard_weighted_majority','candidate',%s)
        """, (next_id, guide, guide, axis, code, conf,
              f"ci_weight majority (w={w})", '{"src":"ci_sr_facet"}', 1))
        next_id += 1
        ins += 1
    conn.commit()
    print(f"deleted old: {deleted}, inserted: {ins}")
    cur.execute("SELECT count(*) FROM guide_entity_feature_candidates WHERE entity_type='GUIDE' AND method='guide_hazard_weighted_majority'")
    print(f"GUIDE feature rows now: {cur.fetchone()[0]}")
    conn.close()
    print("DONE")


if __name__ == "__main__":
    main()
