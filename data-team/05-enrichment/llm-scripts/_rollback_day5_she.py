"""Day 5 emergency rollback — DELETE 77+5 SHE patterns inserted by link_v31_codes_to_she.py."""
import os, sys, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "serving-team/08-app/backend"))

from sqlalchemy import text
from app.db.database import SessionLocal

AUDIT = REPO / "data-team/05-enrichment/runtime-artifacts/v31_codes_she_link_audit.jsonl"

# Get all she_ids that were accepted in Day 5 (look for 'accepted' action with she_id)
she_ids = set()
with AUDIT.open(encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("action") == "accepted" and r.get("she_id"):
            she_ids.add(r["she_id"])

print(f"Day 5 accepted she_ids in audit: {len(she_ids)}")
print(f"  sample first 5: {list(she_ids)[:5]}")

db = SessionLocal()
try:
    deleted = 0
    for sid in she_ids:
        # delete from she_catalog (cascade should handle she_sr_mapping)
        result = db.execute(text("DELETE FROM she_catalog WHERE she_id = :sid"), {"sid": sid})
        deleted += result.rowcount
    db.commit()
    print(f"DELETE FROM she_catalog: {deleted} rows removed")
finally:
    db.close()
