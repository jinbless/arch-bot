#!/usr/bin/env python3
"""「즉시 조치」 v5화 검증 — 지게차 hazards → raw CI 매칭 → guide+섹션 인용."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ.setdefault("SEMANTIC_ATTACH", "on")
from app.db.database import SessionLocal  # noqa: E402
from app.services.hazard_to_ci_service import match_hazards_to_ci  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
photos = json.loads((REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "claude_vision_8photo_input.json").read_text(encoding="utf-8"))["photos"]
fk = next(p for p in photos if "지게차" in p["photo"])
hazards = fk["result"]["hazards"]

print("hazards:", [h["name"] for h in hazards])
with SessionLocal() as db:
    rows = match_hazards_to_ci(db, hazards)
print(f"\n{len(rows)} CI grounded (즉시 조치 — guide+섹션 인용):")
for r in rows:
    print(f"  [{r['hazard_name']}] {r['evidence_summary']}")
    print(f"      → {(r['text'] or '')[:64]}")
