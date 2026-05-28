#!/usr/bin/env python3
"""P1 — CI 변별력(guide_frequency) 계산 + backfill.

Guide 추천 정확도 개선 plan P1:
- 동일 텍스트 CI가 몇 개 distinct source_guide에 중복 등장하는지 = guide_frequency.
- boilerplate CI(시험법 공통문구 등, 최대 130 Guide 중복)일수록 높음.
- Guide 랭킹에서 ci_weight = 1/log2(1+guide_frequency)로 변별력 가중 down.

ALTER TABLE은 models.py 정의와 동기 (idempotent IF NOT EXISTS).

사용:
  PYTHONIOENCODING=utf-8 python compute_ci_guide_frequency.py          # dry-run (분포만)
  PYTHONIOENCODING=utf-8 python compute_ci_guide_frequency.py --apply  # ALTER + backfill
"""
from __future__ import annotations

import argparse
import math
import sys

import psycopg2

PG = "dbname=kosha user=kosha password=1229 host=localhost"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="ALTER + UPDATE 실행")
    args = ap.parse_args()

    conn = psycopg2.connect(PG)
    cur = conn.cursor()

    # 분포 미리보기
    cur.execute("""
        SELECT count(*) total,
               sum(case when gf > 1 then 1 else 0 end) dup,
               max(gf)
        FROM (SELECT count(distinct source_guide) gf FROM checklist_items GROUP BY text) t
    """)
    total_groups, dup_groups, max_gf = cur.fetchone()
    print(f"text 그룹: {total_groups}, 중복(gf>1): {dup_groups}, max guide_frequency: {max_gf}")

    if not args.apply:
        # ci_weight 예시
        for gf in [1, 2, 5, 10, 50, 130]:
            w = 1.0 / math.log2(1 + gf)
            print(f"  guide_frequency={gf:>3} → ci_weight={w:.3f}")
        print("\n--apply 로 ALTER + backfill 실행")
        return

    print("ALTER TABLE checklist_items ADD COLUMN IF NOT EXISTS guide_frequency ...")
    cur.execute("""
        ALTER TABLE checklist_items
        ADD COLUMN IF NOT EXISTS guide_frequency integer NOT NULL DEFAULT 1
    """)

    print("backfill UPDATE (text별 distinct source_guide count)...")
    cur.execute("""
        UPDATE checklist_items c
        SET guide_frequency = sub.gf
        FROM (
            SELECT text, count(distinct source_guide) AS gf
            FROM checklist_items GROUP BY text
        ) sub
        WHERE c.text = sub.text AND c.guide_frequency <> sub.gf
    """)
    updated = cur.rowcount
    conn.commit()
    print(f"  updated {updated} rows")

    # 검증
    cur.execute("SELECT count(*) FROM checklist_items WHERE guide_frequency > 1")
    print(f"  guide_frequency > 1 CI: {cur.fetchone()[0]}")
    cur.execute("SELECT guide_frequency, count(*) FROM checklist_items GROUP BY guide_frequency ORDER BY guide_frequency DESC LIMIT 5")
    print("  상위 guide_frequency 분포:")
    for gf, cnt in cur.fetchall():
        print(f"    gf={gf}: {cnt} CIs")
    conn.close()
    print("DONE")


if __name__ == "__main__":
    main()
