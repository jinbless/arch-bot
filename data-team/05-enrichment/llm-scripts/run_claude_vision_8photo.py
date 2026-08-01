#!/usr/bin/env python3
"""Claude-as-Vision 8-photo end-to-end eval — 실제 Vision(gpt-4.1) 호출 우회.

Claude가 real-test-photo/ 8장을 직접 보고 작성한 관찰(claude_vision_8photo_input.json)을
analysis_pipeline.run()에 result로 주입 → 정상 4패널 산출(hazards/standard_procedures/
penalty_paths/situation_matches). eval_hazard_direct_8photo.py(실제 Vision 호출판)의 우회 버전.

목적: Claude-Vision 추출 + 시스템 매칭 품질을, 저장된 gpt-4.1 결과(hazard_direct_8photo_eval.json) 및
장면 truth와 3자 비교 → 기대이하 원인 localize.

실행 (WSL backend venv):
  cd /mnt/c/project/arch-bot/serving-team/08-app/backend
  DATABASE_URL='postgresql://kosha:1229@localhost:5432/kosha' \
    PYTHONIOENCODING=utf-8 ./.venv/bin/python \
    ../../../data-team/05-enrichment/llm-scripts/run_claude_vision_8photo.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


def find_repo() -> Path:
    for anc in Path(__file__).resolve().parents:
        if (anc / "real-test-photo").is_dir() or (anc / "shared" / "reference").is_dir():
            return anc
    raise RuntimeError("repo root not found")


REPO = find_repo()
BACKEND = REPO / "serving-team" / "08-app" / "backend"
INPUT = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "claude_vision_8photo_input.json"
OUTPUT = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "claude_vision_8photo_eval.json"
CATALOG = BACKEND / "app" / "data" / "risk_feature_catalog.json"
sys.path.insert(0, str(BACKEND))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_valid_codes() -> dict[str, set[str]]:
    """axis -> 유효 코드 집합 (canonical keys ∪ sub). 제안 코드 검증용."""
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for axis, block in data.get("axes", {}).items():
        codes: set[str] = set()
        for code, meta in (block.get("codes") or {}).items():
            codes.add(code)
            for sub in (meta.get("sub") or []):
                codes.add(sub)
        out[axis] = codes
    return out


def check_candidates(result: dict, valid: dict[str, set[str]]) -> dict:
    """제안 risk_feature_candidates 중 카탈로그 유효/탈락 분리."""
    kept, dropped = [], []
    for c in result.get("risk_feature_candidates", []):
        axis, text = c.get("axis"), c.get("text")
        tag = f"{axis}.{text}"
        if axis in valid and text in valid[axis]:
            kept.append(tag)
        else:
            dropped.append(tag)
    return {"kept": kept, "dropped": dropped}


async def run_one(db, photo: str, industry: str, result: dict) -> dict:
    from app.services.analysis_pipeline import analysis_pipeline, AnalysisRunInput

    resp = await analysis_pipeline.run(
        db=db,
        run_input=AnalysisRunInput(
            result=result,
            analysis_type="image",
            input_preview=photo,
            declared_industry_text=industry,
        ),
    )
    d = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)

    def pick(items, *keys):
        rows = []
        for it in (items or []):
            it = it if isinstance(it, dict) else (it.model_dump() if hasattr(it, "model_dump") else {})
            rows.append({k: it.get(k) for k in keys})
        return rows

    return {
        "photo": photo,
        "industry": industry,
        "finding_status": d.get("finding_status"),
        "penalty_exposure_status": d.get("penalty_exposure_status"),
        "overall_risk_level": str(d.get("overall_risk_level")),
        "risk_features": pick(d.get("risk_features"), "axis", "code", "label"),
        "hazards": pick(d.get("hazards"), "name", "risk_level", "mapped_codes"),
        "standard_procedures": pick(d.get("standard_procedures"), "guide_code", "title", "confidence"),
        "penalty_paths": pick(d.get("penalty_paths"), "path_type", "notice_level"),
        "situation_matches": pick(d.get("situation_matches"), "pattern_id", "status", "applies_sr_ids"),
        "hazard_guide_relations": pick(d.get("hazard_guide_relations"), "hazard_name", "guides"),
        "summary": (d.get("summary") or "")[:160],
    }


async def main() -> int:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    photos = payload["photos"]
    valid = load_valid_codes()
    print(f"[Claude-Vision 8photo] photos={len(photos)}  catalog axes={ {a: len(v) for a, v in valid.items()} }")
    print()

    from app.db.database import SessionLocal

    results = []
    for i, p in enumerate(photos, 1):
        photo, industry, result = p["photo"], p.get("industry", ""), p["result"]
        cand = check_candidates(result, valid)
        db = SessionLocal()
        try:
            r = await run_one(db, photo, industry, result)
        except Exception as e:  # noqa: BLE001
            r = {"photo": photo, "error": repr(e)[:400]}
            print(f"  [{i}/{len(photos)}] {photo[:34]:34s} ERROR: {e}")
            db.close()
            r["candidates"] = cand
            results.append(r)
            continue
        db.close()
        r["candidates"] = cand
        sp = r["standard_procedures"]
        pp = r["penalty_paths"]
        sm = r["situation_matches"]
        print(f"  [{i}/{len(photos)}] {photo.split('(')[0][:22]:22s} "
              f"rf={len(r['risk_features']):2d}(kept {len(cand['kept'])}/drop {len(cand['dropped'])})  "
              f"haz={len(r['hazards']):2d}  guide={len(sp):2d}  pen={len(pp)}  she={len(sm):2d}  "
              f"status={r['finding_status']}")
        if cand["dropped"]:
            print(f"        dropped codes: {', '.join(cand['dropped'])}")
        # top 3 guide titles
        for g in sp[:3]:
            print(f"          guide {g.get('guide_code')}: {(g.get('title') or '')[:40]}  conf={g.get('confidence')}")
        results.append(r)

    OUTPUT.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  output: {OUTPUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
