#!/usr/bin/env python3
"""8 real-test-photo 자동 분석 — Phase B/A.4/C 효과 시각 검증.

LLM_RERANK_MODE 환경변수에 따라 backend analyze_image 호출.
이전 시연 결과 (analysis_results/) 또는 baseline_v1과 비교 가능.

사용:
  python scripts/test_real_photos.py                       # off (baseline)
  LLM_RERANK_MODE=active python scripts/test_real_photos.py  # Phase B+A.4 활성
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "real-test-photo").is_dir():
            return ancestor
    raise RuntimeError("real-test-photo not found")


REPO = _find_repo_root()
PHOTO_DIR = REPO / "real-test-photo"
RESULTS_DIR = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"


async def analyze_one(path: Path) -> dict:
    from app.db.database import SessionLocal
    from app.services.analysis_service import analysis_service

    with path.open("rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    db = SessionLocal()
    start = time.time()
    try:
        result = await analysis_service.analyze_image(
            db=db,
            image_base64=b64,
            filename=path.name,
        )
        elapsed = time.time() - start
        return {
            "filename": path.name,
            "elapsed_s": round(elapsed, 1),
            "overall_risk_level": getattr(result.overall_risk_level, "value", str(result.overall_risk_level)),
            "summary": result.summary[:200],
            "procedures": [
                {
                    "guide_code": p.guide_code,
                    "title": p.title[:60],
                    "evidence": (p.evidence_summary or "")[:80],
                }
                for p in result.standard_procedures
            ],
            "actions_count": len(result.immediate_actions),
            "excluded_candidates": [
                {
                    "guide_code": e.guide_code,
                    "title": (e.title or "")[:50],
                    "source": e.source,
                    "reason": e.reason[:80],
                }
                for e in result.excluded_candidates
            ],
        }
    except Exception as exc:
        import traceback
        return {
            "filename": path.name,
            "error": str(exc),
            "traceback": traceback.format_exc(limit=3),
        }
    finally:
        db.close()


async def main():
    mode = os.environ.get("LLM_RERANK_MODE", "off")
    photos = sorted(PHOTO_DIR.glob("*.png")) + sorted(PHOTO_DIR.glob("*.jpg"))
    photos = [p for p in photos if p.name != "desktop.ini"]
    print(f"Mode: LLM_RERANK_MODE={mode}")
    print(f"Photos: {len(photos)}")

    results = []
    for idx, path in enumerate(photos):
        short = path.name.split("(")[0]
        print(f"\n[{idx + 1}/{len(photos)}] {short}", flush=True)
        result = await analyze_one(path)
        results.append(result)
        if "error" in result:
            print(f"  ERROR: {result['error'][:100]}")
            continue
        print(f"  elapsed: {result['elapsed_s']}s")
        print(f"  risk: {result['overall_risk_level']}")
        print(f"  procedures ({len(result['procedures'])}):")
        for p in result["procedures"][:5]:
            print(f"    - {p['guide_code']}: {p['title']}")
        print(f"  immediate_actions: {result['actions_count']}")
        if result["excluded_candidates"]:
            print(f"  excluded ({len(result['excluded_candidates'])}):")
            for e in result["excluded_candidates"][:3]:
                print(f"    × {e['guide_code']} ({e['source']}): {e['title']} — {e['reason']}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{mode}" if mode != "off" else "_baseline"
    out_path = RESULTS_DIR / f"real_photo_results{suffix}.json"
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
