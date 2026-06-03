#!/usr/bin/env python3
"""CI → Guide → section/page provenance 점검."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import psycopg2  # noqa: E402

c = psycopg2.connect(os.environ["DATABASE_URL"])
cur = c.cursor()
cur.execute("SELECT source_guide, left(source_section, 70) FROM checklist_items WHERE source_section IS NOT NULL AND source_section <> '' LIMIT 6")
print("=== checklist_items.source_section 샘플 ===")
for g, s in cur.fetchall():
    print(f"  {g}: {s}")
cur.execute("SELECT count(*), count(*) FILTER (WHERE source_section ~ '[0-9]') FROM checklist_items")
tot, withnum = cur.fetchone()
print(f"\nsource_section: 전체 {tot}, 숫자 포함(페이지 후보) {withnum}")
cur.execute("SELECT canonical_ci_id, member_count, guide_degree FROM canonical_checklist_items ORDER BY guide_degree LIMIT 2")
print("canonical CI 예(고유):", cur.fetchall())
# canonical_ci -> member 매핑 테이블 존재?
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%canonical%' OR table_name LIKE '%ci_member%'")
print("관련 테이블:", [r[0] for r in cur.fetchall()])
c.close()
