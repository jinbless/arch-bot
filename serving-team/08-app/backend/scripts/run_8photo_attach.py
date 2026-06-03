#!/usr/bin/env python3
"""라이브 8장 — 실사진 GPT/Claude-Vision hazards[]를 v5 semantic attach에 통과 (off vs on+rerank).

claude_vision_8photo_input.json의 photo별 result.hazards[]를 normalize_hazards_array →
match_hazards_to_guides로 부착, hazard_guide_relations(hazard별 guide)를 off/on 비교.

실행: ./.venv/bin/python scripts/run_8photo_attach.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.database import SessionLocal  # noqa: E402
from app.services.hazard_normalizer import normalize_hazards_array  # noqa: E402
from app.services.hazard_to_guide_service import match_hazards_to_guides  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
INPUT = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "claude_vision_8photo_input.json"
photos = json.loads(INPUT.read_text(encoding="utf-8"))["photos"]


def run(env: dict) -> list:
    for k, v in env.items():
        os.environ[k] = v
    out = []
    with SessionLocal() as db:
        for p in photos:
            hazards = p["result"].get("hazards") or []
            canonical = normalize_hazards_array(hazards)
            rels, _ = match_hazards_to_guides(db, hazards, canonical, industry_contexts=[])
            out.append(rels)
    return out


OFF = run({"SEMANTIC_ATTACH": "off", "SEMANTIC_ATTACH_RERANK": "off", "HYBRID_ATTACH_CACHE": "off"})
ON = run({"SEMANTIC_ATTACH": "on", "SEMANTIC_ATTACH_RERANK": "on", "HYBRID_ATTACH_CACHE": "off"})


def fmt(guides):
    return " / ".join(f"{g['guide_code']}:{(g.get('title') or '')[:24]}" for g in guides) or "(없음)"


for p, off_rels, on_rels in zip(photos, OFF, ON):
    print(f"\n■ {p['photo'].split('(')[0][:26]}  [{p.get('industry','')}]")
    by_off = {r["hazard_name"]: r for r in off_rels}
    for nrel in on_rels:
        name = nrel["hazard_name"]
        orel = by_off.get(name, {})
        print(f"  ▶ {name}")
        print(f"     off : {fmt(orel.get('guides') or [])}")
        print(f"     on  : {fmt(nrel.get('guides') or [])}")
