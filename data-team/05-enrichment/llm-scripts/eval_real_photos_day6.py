#!/usr/bin/env python3
"""Phase F.1 Day 6 — 8 real-test-photo eval (candidate ON/OFF 비교).

Vision LLM이 8 photos에서 추출한 free-form text 중 Normalizer가 매핑하지 못한
`normalizer_unknown_codes`를 candidate aliases 활성/비활성 상태에서 비교한다.

측정 방식: A hook (commit ebe1011)가 `analysis_log.jsonl`에 쓰는 entry를
photo별로 byte offset 추적해 추출.

각 photo:
- ON  (candidate file 존재): cascade step 4.5 활성, 6 candidate aliases 사용
- OFF (candidate file aside): step 4.5 no-op, baseline state

목표 (plan acceptance):
- ≥6/8 (75%) photos에서 normalizer_miss 감소
- 8/8 모두 errored=0 (Vision LLM 호출 정상)

비용: ~$0.40-0.80 (16 Vision LLM 호출)
시간: ~8분

ENV 필수:
  OPENAI_API_KEY     — Vision LLM 호출
  DATABASE_URL       — analysis_log 쓰기
  LLM_RERANK_MODE=shadow  — A hook 발동 조건
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
    raise RuntimeError("real-test-photo not found in this worktree")


WORKTREE = find_repo()
PHOTO_DIR = WORKTREE / "real-test-photo"
BACKEND = WORKTREE / "serving-team" / "08-app" / "backend"
CANDIDATE_FILE = BACKEND / "app" / "data" / "risk_feature_aliases_candidates.json"
ANALYSIS_LOG = WORKTREE / "data-team" / "05-enrichment" / "runtime-artifacts" / "analysis_log.jsonl"
RESULTS_PATH = (
    WORKTREE / "data-team" / "05-enrichment" / "runtime-artifacts" / "day6_real_photo_eval.json"
)

sys.path.insert(0, str(BACKEND))


def _log_size() -> int:
    return ANALYSIS_LOG.stat().st_size if ANALYSIS_LOG.is_file() else 0


def _read_new_entries(before_size: int) -> list[dict]:
    """Read new analysis_log entries since byte offset."""
    if not ANALYSIS_LOG.is_file():
        return []
    out = []
    with ANALYSIS_LOG.open("rb") as f:
        f.seek(before_size)
        for line in f:
            try:
                out.append(json.loads(line.decode("utf-8").strip()))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    return out


async def analyze_one(path: Path) -> dict:
    """Call backend analyze_image, return result + log delta."""
    from app.db.database import SessionLocal
    from app.services.analysis_service import analysis_service

    with path.open("rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    before = _log_size()
    db = SessionLocal()
    t0 = time.time()
    try:
        await analysis_service.analyze_image(
            db=db,
            image_base64=b64,
            filename=path.name,
        )
    finally:
        db.close()
    elapsed = time.time() - t0

    new = _read_new_entries(before)
    if not new:
        return {
            "photo": path.name,
            "elapsed_s": round(elapsed, 2),
            "log_fired": False,
            "note": "A hook did not fire (LLM_RERANK_MODE off or early-return)",
        }
    entry = new[-1]  # latest entry from this call
    return {
        "photo": path.name,
        "elapsed_s": round(elapsed, 2),
        "log_fired": True,
        "normalizer_unknown_codes": list(entry.get("normalizer_unknown_codes") or []),
        "she_match_count": entry.get("she_match_count", 0),
        "raw_vision_features_count": len(entry.get("raw_vision_features") or []),
        "visual_obs_count": entry.get("visual_obs_count", 0),
        "candidate_count": entry.get("candidate_count", 0),
        "scene_hash": entry.get("scene_hash", ""),
    }


async def run_pass(label: str, photos: list[Path]) -> list[dict]:
    """Run analysis on all photos with current candidate state. Invalidate cache first."""
    from app.services import hazard_normalizer as hn
    hn._CANDIDATE_ALIASES = None
    hn._ALIASES = None
    hn._TAXONOMY = None

    print(f"\n[{label}] analyzing {len(photos)} photos...")
    out = []
    for i, p in enumerate(photos, 1):
        try:
            r = await analyze_one(p)
            out.append({**r, "errored": False})
            if r.get("log_fired"):
                print(
                    f"  [{i}/{len(photos)}] {p.name[:42]:42s}  "
                    f"unk={len(r['normalizer_unknown_codes']):2d}  "
                    f"she={r['she_match_count']:2d}  "
                    f"feat={r['raw_vision_features_count']:2d}  "
                    f"{r['elapsed_s']:5.1f}s"
                )
            else:
                print(f"  [{i}/{len(photos)}] {p.name[:42]:42s}  HOOK_NOT_FIRED  {r['elapsed_s']:5.1f}s")
        except Exception as exc:
            print(f"  [{i}/{len(photos)}] {p.name[:42]:42s}  ERROR: {str(exc)[:60]}")
            out.append({"photo": p.name, "errored": True, "error": str(exc)})
    return out


async def main_async() -> int:
    if os.environ.get("LLM_RERANK_MODE") not in ("shadow", "active"):
        print("WARN: LLM_RERANK_MODE not in (shadow, active) — A hook may not fire", file=sys.stderr)
        print("  Setting LLM_RERANK_MODE=shadow for this run", file=sys.stderr)
        os.environ["LLM_RERANK_MODE"] = "shadow"

    photos = sorted(
        p for p in PHOTO_DIR.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg"} and not p.name.startswith(".")
    )
    if not photos:
        print(f"ERROR: no photos in {PHOTO_DIR}", file=sys.stderr)
        return 2
    print(f"Found {len(photos)} photos in {PHOTO_DIR.name}/")

    on_results = None
    if CANDIDATE_FILE.is_file():
        on_results = await run_pass("ON (with 6 candidate aliases)", photos)
        aside = CANDIDATE_FILE.with_suffix(".json.day6_aside")
        try:
            CANDIDATE_FILE.rename(aside)
            print(f"\nMoved candidate file aside: {aside.name}")
            off_results = await run_pass("OFF (candidate file aside)", photos)
        finally:
            if aside.is_file():
                aside.rename(CANDIDATE_FILE)
                print(f"Restored candidate file.")
    else:
        print(f"WARN: {CANDIDATE_FILE.name} 미존재 — OFF만 측정")
        off_results = await run_pass("OFF (no candidate file)", photos)

    print()
    print("=" * 80)
    print("Day 6 SUMMARY — normalizer_unknown_codes (lower = better)")
    print("=" * 80)
    if on_results is None:
        for r in off_results:
            unks = r.get("normalizer_unknown_codes", [])
            print(f"  {r['photo'][:45]:45s}  unknowns={len(unks):2d}")
        return 0

    print(f"  {'photo':45s}  {'ON':>4s}  {'OFF':>4s}  {'diff':>5s}  status")
    improved = 0
    equal = 0
    worse = 0
    err = 0
    for on, off in zip(on_results, off_results):
        if on.get("errored") or off.get("errored"):
            print(f"  {on.get('photo','?')[:45]:45s}  ERROR")
            err += 1
            continue
        if not (on.get("log_fired") and off.get("log_fired")):
            print(f"  {on.get('photo','?')[:45]:45s}  HOOK_NOT_FIRED")
            err += 1
            continue
        on_n = len(on["normalizer_unknown_codes"])
        off_n = len(off["normalizer_unknown_codes"])
        diff = off_n - on_n  # positive = ON 더 좋음 (unknowns 감소)
        if diff > 0:
            improved += 1
            tag = f"✓ -{diff}"
        elif diff == 0:
            equal += 1
            tag = "="
        else:
            worse += 1
            tag = f"✗ +{-diff}"
        print(f"  {on['photo'][:45]:45s}  {on_n:>4d}  {off_n:>4d}  {diff:>+5d}  {tag}")
    print()
    n_total = len(on_results)
    print(f"  Improved : {improved}/{n_total}  (plan target: ≥6/8 = 75%)")
    print(f"  Equal    : {equal}")
    print(f"  Worse    : {worse}")
    print(f"  Errors   : {err}")
    if improved >= 6:
        print(f"  ✅ PLAN ACCEPTANCE 충족")
    elif improved >= 4:
        print(f"  ⚠️  부분 충족 (6 aliases가 사진 내용과 부분만 일치)")
    else:
        print(f"  ⚠️  PLAN ACCEPTANCE 미달 (6 aliases가 사진 어휘와 거의 매치 안 함)")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "photo_count": n_total,
        "candidate_file_active": True,
        "summary": {"improved": improved, "equal": equal, "worse": worse, "errors": err},
        "on": on_results,
        "off": off_results,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved: {RESULTS_PATH.relative_to(WORKTREE)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
