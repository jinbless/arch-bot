#!/usr/bin/env python3
"""Hazard-Direct Pivot Phase 5 Day 1 — 8 real-test-photo 효과성 검증.

본 Sprint 산출의 최종 검증:
1. ⭐ hazards[] 응답 필드 항상 채워짐 (AC-1)
2. hazards → catalog code 매핑 정확도 (AC-2)
3. hazard_guide_relations 채워짐 (AC-5)
4. 기존 standard_procedures 병행 유지 (호환성)
5. moellab 8 photo 응답과 hazards.name 분포 비교

실행 (worktree backend venv):
  cd serving-team/08-app/backend
  PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe ../../../data-team/05-enrichment/llm-scripts/eval_hazard_direct_8photo.py

ENV:
  OPENAI_API_KEY    (Vision LLM 호출)
  DATABASE_URL      (PG)
  HAZARD_DIRECT_MODE=parallel  (default; off/parallel/primary 모두 가능)

cost: ~$0.40-0.60 (8 Vision LLM 호출, gpt-4.1, image detail=high)
시간: ~5-8분
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def find_repo() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "real-test-photo").is_dir():
            return ancestor
    raise RuntimeError("real-test-photo not found")


WORKTREE = find_repo()
PHOTO_DIR = WORKTREE / "real-test-photo"
BACKEND = WORKTREE / "serving-team" / "08-app" / "backend"
COMPARE_DIR = WORKTREE / ".compare_moellab"
RESULTS_PATH = WORKTREE / "data-team" / "05-enrichment" / "runtime-artifacts" / "hazard_direct_8photo_eval.json"

sys.path.insert(0, str(BACKEND))


def _photo_to_moellab_key(photo_name: str) -> str:
    """photo filename → moellab json filename mapping.

    real-test-photo: "고소대작업(httpswww.youtube...).png"
    moellab json:    "고소대작업.json"
    """
    # 괄호 앞 부분만
    base = photo_name.split("(")[0].strip()
    return base


def _load_moellab_hazards() -> dict[str, list[str]]:
    """각 사진의 moellab hazards[].name 분포."""
    out: dict[str, list[str]] = {}
    for fp in sorted(COMPARE_DIR.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            names = [h.get("name", "").strip() for h in (data.get("hazards") or []) if h.get("name")]
            out[fp.stem] = names
        except Exception:
            continue
    return out


async def analyze_one(path: Path) -> dict:
    """8 photo 1장 호출 + hazard-direct 산출 수집."""
    from app.db.database import SessionLocal
    from app.services.analysis_service import analysis_service

    with path.open("rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    db = SessionLocal()
    t0 = time.time()
    try:
        resp = await analysis_service.analyze_image(
            db=db,
            image_base64=b64,
            filename=path.name,
        )
    finally:
        db.close()
    elapsed = time.time() - t0

    # Pydantic v2 → dict
    return {
        "photo": path.name,
        "elapsed_s": round(elapsed, 2),
        "hazards": [h.model_dump() for h in resp.hazards],
        "hazard_guide_relations": [r.model_dump() for r in resp.hazard_guide_relations],
        "standard_procedures_count": len(resp.standard_procedures),
        "standard_procedures": [
            {"procedure_id": p.procedure_id, "title": p.title}
            for p in resp.standard_procedures
        ],
        "penalty_paths_count": len(resp.penalty_paths),
        "overall_risk_level": str(resp.overall_risk_level),
        "summary": resp.summary[:200],
    }


async def main_async() -> int:
    photos = sorted(PHOTO_DIR.glob("*"))
    photos = [p for p in photos if p.is_file()]
    if not photos:
        print(f"ERROR: no photos in {PHOTO_DIR}", file=sys.stderr)
        return 2
    print(f"[Hazard-Direct 8 photo eval] HAZARD_DIRECT_MODE={os.environ.get('HAZARD_DIRECT_MODE', 'parallel')}")
    print(f"  photos: {len(photos)}, est cost ~$0.40-0.60")
    print()

    moellab = _load_moellab_hazards()
    results: list[dict] = []
    for i, p in enumerate(photos, 1):
        try:
            r = await analyze_one(p)
        except Exception as e:  # noqa: BLE001
            r = {"photo": p.name, "error": str(e)[:300]}
            print(f"  [{i}/{len(photos)}] {p.name[:40]:40s}  ERROR: {e}")
            results.append(r)
            continue

        hz_count = len(r["hazards"])
        rel_count = len(r["hazard_guide_relations"])
        sp_count = r["standard_procedures_count"]
        pp_count = r["penalty_paths_count"]

        # mapping rate per photo
        mapped = sum(1 for h in r["hazards"] if h.get("mapped_codes"))
        rate = mapped / hz_count if hz_count else 0.0
        r["mapping_rate"] = rate

        # moellab cross-compare
        moellab_key = _photo_to_moellab_key(p.name)
        moellab_names = moellab.get(moellab_key, [])
        dev_names = [h["name"] for h in r["hazards"]]
        r["moellab_key"] = moellab_key
        r["moellab_hazards"] = moellab_names
        r["dev_hazards"] = dev_names

        # overlap (case-insensitive substring or exact)
        overlap = set()
        for dn in dev_names:
            for mn in moellab_names:
                if dn == mn or dn in mn or mn in dn:
                    overlap.add((dn, mn))
                    break
        r["overlap_count"] = len(overlap)
        r["overlap_examples"] = [f"{a}↔{b}" for a, b in list(overlap)[:5]]

        print(
            f"  [{i}/{len(photos)}] {p.name[:40]:40s}  "
            f"hz={hz_count:2d}({mapped}m={rate:.0%})  "
            f"rel={rel_count:2d}  sp={sp_count:2d}  pp={pp_count:2d}  "
            f"vs_moellab={len(overlap)}/{len(moellab_names)}  "
            f"{r['elapsed_s']:5.1f}s"
        )
        results.append(r)

    # aggregate stats
    total_hz = sum(len(r.get("hazards") or []) for r in results)
    total_mapped = sum(int((r.get("mapping_rate") or 0) * len(r.get("hazards") or [])) for r in results)
    avg_rate = total_mapped / total_hz if total_hz else 0.0
    total_rel = sum(len(r.get("hazard_guide_relations") or []) for r in results)
    total_sp = sum(r.get("standard_procedures_count", 0) for r in results)
    total_pp = sum(r.get("penalty_paths_count", 0) for r in results)
    ok_photos = sum(1 for r in results if not r.get("error"))
    overlap_per_photo = [(r.get("overlap_count", 0), len(r.get("moellab_hazards") or [])) for r in results if not r.get("error")]

    print()
    print("=" * 64)
    print("AGGREGATE")
    print("=" * 64)
    print(f"  photos analyzed   : {ok_photos}/{len(photos)}")
    print(f"  total hazards     : {total_hz}")
    print(f"  total mapped      : {total_mapped} ({avg_rate:.1%})")
    print(f"  total relations   : {total_rel}")
    print(f"  total procedures  : {total_sp}")
    print(f"  total penalty_p   : {total_pp}")
    print(f"  moellab overlap   : {sum(o for o, _ in overlap_per_photo)}/{sum(m for _, m in overlap_per_photo)}")

    out = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "hazard_direct_mode": os.environ.get("HAZARD_DIRECT_MODE", "parallel"),
        "photos_evaluated": ok_photos,
        "total_hazards": total_hz,
        "total_mapped": total_mapped,
        "avg_mapping_rate": avg_rate,
        "total_relations": total_rel,
        "total_procedures": total_sp,
        "total_penalty_paths": total_pp,
        "moellab_total_overlap": sum(o for o, _ in overlap_per_photo),
        "moellab_total_count": sum(m for _, m in overlap_per_photo),
        "results": results,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print(f"  output: {RESULTS_PATH.relative_to(WORKTREE)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
