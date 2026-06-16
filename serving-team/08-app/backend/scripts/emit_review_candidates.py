#!/usr/bin/env python3
"""HITL Phase 0: 큐레이션 실사진 코퍼스 → 실 파이프라인(analyze_image, Vision 포함) → ohs_analysis_records.

review_corpus_manifest.json(photos[].photo 경로 + industry_context/case_type/work_context 사전라벨)을 읽어
각 사진을 analysis_service.analyze_image로 분석·영속(analysis_id 조인 보장)하고, 매니페스트에 analysis_id +
catalog_git_rev를 기록한다. 이후 export_mapping_review_xlsx.py가 이 레코드들로 검토 행을 만든다.

**OPENAI_API_KEY 필요**(실 Vision 호출). 사진 경로는 repo 루트 기준 상대 또는 절대.

사용:
  PYTHONIOENCODING=utf-8 OPENAI_API_KEY=sk-... python scripts/emit_review_candidates.py [--manifest ...] [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_MANIFEST = BACKEND_DIR / "scripts" / "review_corpus_manifest.json"


def _git_rev() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(PROJECT_ROOT)).decode().strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _resolve(photo: str) -> Path:
    p = Path(photo)
    return p if p.is_absolute() else (PROJECT_ROOT / photo)


async def _analyze(entry: dict, git_rev: str) -> dict:
    from app.db.database import SessionLocal
    from app.services.analysis_service import analysis_service

    path = _resolve(entry["photo"])
    if not path.exists():
        return {**entry, "error": f"file not found: {path}"}
    b64 = base64.b64encode(path.read_bytes()).decode()
    db = SessionLocal()
    try:
        resp = await analysis_service.analyze_image(
            db=db, image_base64=b64, filename=path.name,
            workplace_type=entry.get("industry_context") or None,
        )
        aid = getattr(resp, "analysis_id", None)
        return {**entry, "analysis_id": aid, "catalog_git_rev": git_rev}
    except Exception as e:  # noqa: BLE001
        return {**entry, "error": repr(e)[:200]}
    finally:
        db.close()


async def main_async(args) -> int:
    mp = Path(args.manifest)
    if not mp.exists():
        print(f"[error] 매니페스트 없음: {mp}\n  → review_corpus_manifest.json에 photos[]를 채워주세요(photo 경로 + 사전라벨).")
        return 1
    data = json.loads(mp.read_text(encoding="utf-8"))
    photos = data.get("photos", [])
    if args.limit:
        photos = photos[: args.limit]
    git_rev = _git_rev()
    print(f"코퍼스 {len(photos)}장 분석 (git {git_rev}) — Vision 실호출")
    if args.dry_run:
        for e in photos[:5]:
            print(f"  [dry] {e.get('photo')} | industry={e.get('industry_context')} case={e.get('case_type')}")
        return 0

    done = []
    for i, entry in enumerate(photos, 1):
        res = await _analyze(entry, git_rev)
        done.append(res)
        tag = res.get("analysis_id", res.get("error"))
        print(f"  [{i}/{len(photos)}] {Path(res.get('photo','')).name[:30]:30s} → {tag}")
    data["photos"] = done + photos[len(done):]
    mp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for d in done if d.get("analysis_id"))
    print(f"DONE — {ok}/{len(done)} 분석·영속, 매니페스트 갱신(analysis_id 기록) → {mp.relative_to(PROJECT_ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
