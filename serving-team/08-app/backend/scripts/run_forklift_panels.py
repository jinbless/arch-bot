#!/usr/bin/env python3
"""지게차 사진을 현재 백엔드 파이프라인(.env 플래그)으로 돌려 3패널 대조.
위험요소별(hazard_guide_relations, v5) vs 표준개선(standard_procedures, legacy) vs 즉시조치(legacy)."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.database import SessionLocal  # noqa: E402
from app.services.analysis_pipeline import analysis_pipeline, AnalysisRunInput  # noqa: E402
from app.services.hazard_to_guide_service import _semantic_attach_enabled, _semantic_rerank_enabled  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
photos = json.loads((REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "claude_vision_8photo_input.json").read_text(encoding="utf-8"))["photos"]
_kw = sys.argv[1] if len(sys.argv) > 1 else "지게차"
fk = next(p for p in photos if _kw in p["photo"])
print(f"[photo] {fk['photo'][:40]}")

print(f"flags: semantic_attach={_semantic_attach_enabled()} rerank={_semantic_rerank_enabled()}")


async def main():
    with SessionLocal() as db:
        resp = await analysis_pipeline.run(db=db, run_input=AnalysisRunInput(
            result=fk["result"], analysis_type="image",
            input_preview=fk["photo"], declared_industry_text=fk.get("industry", "")))
    d = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)

    print("\n=== ① 위험요소별 가이드 (hazard_guide_relations) — v5 경로 ===")
    for r in d.get("hazard_guide_relations") or []:
        gs = " / ".join(f"{g['guide_code']}:{(g.get('title') or '')[:22]}" for g in (r.get("guides") or []))
        print(f"  ▶ {r['hazard_name']}  →  {gs or '(없음)'}")

    print("\n=== ② 표준 개선 절차 (standard_procedures) — legacy 경로 ===")
    for p in (d.get("standard_procedures") or [])[:5]:
        print(f"  · {(p.get('title') or '')[:55]}")

    print("\n=== ③ 즉시 조치 (immediate_actions) ===")
    for a in (d.get("immediate_actions") or [])[:5]:
        print(f"  · {(a.get('title') or '')[:46]}  [{(a.get('description') or '')[:34]}]")

    print("\n=== ④ 벌칙 3경로 (penalty_paths) — 조문 ===")
    for p in d.get("penalty_paths") or []:
        arts = [a.get("article_id") for a in (p.get("article_refs") or [])]
        print(f"  · [{p.get('path_type')}] {p.get('title')}  조문={arts[:6]}")


asyncio.run(main())
