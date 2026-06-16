#!/usr/bin/env python3
"""HITL: mapping_review_verdicts(합의) → gold-truth-v2.jsonl (WS-EVAL-2 사람-라벨 golden set).

candidate 판정(approve/reject)을 사진별로 합의(consensus)해 expected_sr_ids/expected_guide_codes를
산출하고, SCENE 행의 누락(recall) 추가와 scene-correctness를 합친다. synthetic 스키마 상위호환 →
replay_synthetic_observations.py::evaluate_case()가 그대로 소비.

합의 규칙(고정밀 기본): target는 approve>reject 다수결일 때만 채택. split/reject/uncertain은 제외(로그).
recall(missing_*)은 SCENE 행에 기재된 id를 합집합으로 추가(reviewer 1명 이상 기재 시; --recall-min로 상향).

사용:
  PYTHONIOENCODING=utf-8 python scripts/build_gold_truth_v2.py [--out .../gold-truth-v2.jsonl] [--manifest .../review_corpus_manifest.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.db.models import OhsAnalysisRecord  # noqa: E402

DEFAULT_OUT = PROJECT_ROOT / "serving-team" / "08-app" / "data" / "eval" / "gold-truth-v2.jsonl"
DEFAULT_MANIFEST = BACKEND_DIR / "scripts" / "review_corpus_manifest.json"


def _git_rev() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(PROJECT_ROOT)).decode().strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _consensus(verdicts: dict[str, str]) -> str:
    """reviewer→verdict → 'keep'|'drop'|'split'. approve>reject=keep, reject>approve=drop, else split."""
    a = sum(1 for v in verdicts.values() if v == "approve")
    r = sum(1 for v in verdicts.values() if v == "reject")
    if a > r:
        return "keep"
    if r > a:
        return "drop"
    return "split"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="사진 메타(case_type/industry/work_context) 조인용(선택)")
    ap.add_argument("--recall-min", type=int, default=1, help="recall 추가 채택 최소 reviewer 수")
    args = ap.parse_args()

    manifest = {}
    mp = Path(args.manifest)
    if mp.exists():
        try:
            for e in json.loads(mp.read_text(encoding="utf-8")).get("photos", []):
                if e.get("analysis_id"):
                    manifest[e["analysis_id"]] = e
        except Exception:  # noqa: BLE001
            pass

    db = SessionLocal()
    rows = db.execute(text(
        "SELECT analysis_id, mapping_kind, target_id, row_kind, reviewer, verdict, notes "
        "FROM mapping_review_verdicts")).fetchall()
    # analysis_id → {SR:{target:{reviewer:verdict}}, GUIDE:{...}, SCENE:[notes...]}
    agg: dict[str, dict] = defaultdict(lambda: {"SR": defaultdict(dict), "GUIDE": defaultdict(dict), "SCENE": []})
    for aid, kind, target, row_kind, reviewer, verdict, notes in rows:
        if row_kind == "scene":
            agg[aid]["SCENE"].append(notes)
        elif kind in ("SR", "GUIDE"):
            agg[aid][kind][target][reviewer] = verdict

    out_lines = []
    stats = {"photos": 0, "sr_kept": 0, "sr_dropped": 0, "sr_split": 0, "guide_kept": 0, "guide_dropped": 0, "guide_split": 0, "recall_sr": 0, "recall_guide": 0}
    for aid, d in agg.items():
        rec = db.get(OhsAnalysisRecord, aid)
        rj = (rec.result_json if rec else {}) or {}
        meta = manifest.get(aid, {})

        def resolve(kind):
            kept, dropped, split = [], [], []
            for target, vs in d[kind].items():
                c = _consensus(vs)
                (kept if c == "keep" else dropped if c == "drop" else split).append(target)
            return kept, dropped, split

        sr_keep, sr_drop, sr_split = resolve("SR")
        g_keep, g_drop, g_split = resolve("GUIDE")

        # recall 추가(SCENE notes JSON에서) — reviewer ≥ recall-min명이 같은 id 기재 시 채택
        rc_sr, rc_g = defaultdict(int), defaultdict(int)
        scene_label = None
        for notes in d["SCENE"]:
            try:
                pl = json.loads(notes) if notes else {}
            except Exception:  # noqa: BLE001
                pl = {}
            for sid in str(pl.get("missing_sr_ids") or "").replace(" ", "").split(","):
                if sid:
                    rc_sr[sid] += 1
            for gc in str(pl.get("missing_guide_codes") or "").replace(" ", "").split(","):
                if gc:
                    rc_g[gc] += 1
            if pl.get("scene_label_correct"):
                scene_label = pl["scene_label_correct"]
        recall_sr = [s for s, n in rc_sr.items() if n >= args.recall_min]
        recall_g = [g for g, n in rc_g.items() if n >= args.recall_min]

        expected_sr = sorted(set(sr_keep) | set(recall_sr))
        expected_guide = sorted(set(g_keep) | set(recall_g))

        # expected_features ← risk_features (canonical 3축)
        feats = defaultdict(list)
        for rf in rj.get("risk_features") or []:
            ax, code = rf.get("axis"), rf.get("code")
            if ax and code:
                feats[ax + "s"].append(code)

        out_lines.append({
            "case_id": f"GOLD-{aid[:8]}",
            "analysis_id": aid,
            "source_photo": (rec.input_preview if rec else "") or meta.get("photo", ""),
            "catalog_git_rev": meta.get("catalog_git_rev", ""),
            "case_type": meta.get("case_type", "positive"),
            "industry_context": meta.get("industry_context", ""),
            "work_context": (feats.get("work_contexts") or [""])[0],
            "scene_label_correct": scene_label,
            "expected_features": dict(feats),
            "expected_pipeline_behavior": {
                "should_match_she": bool(rj.get("situation_matches")),
                "should_recommend_sr": bool(expected_sr),
                "penalty_exposure": (rj.get("penalty_exposure_status") or "no_penalty"),
            },
            "expected_sr_ids": expected_sr,
            "expected_guide_codes": expected_guide,
            "review_meta": {
                "reviewers": sorted({rv for k in ("SR", "GUIDE") for vs in d[k].values() for rv in vs}),
                "sr_kept": len(sr_keep), "sr_dropped": sr_drop, "sr_split": sr_split,
                "guide_kept": len(g_keep), "guide_dropped": g_drop, "guide_split": g_split,
                "recall_sr_added": recall_sr, "recall_guide_added": recall_g,
            },
        })
        stats["photos"] += 1
        stats["sr_kept"] += len(sr_keep); stats["sr_dropped"] += len(sr_drop); stats["sr_split"] += len(sr_split)
        stats["guide_kept"] += len(g_keep); stats["guide_dropped"] += len(g_drop); stats["guide_split"] += len(g_split)
        stats["recall_sr"] += len(recall_sr); stats["recall_guide"] += len(recall_g)
    db.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    print(f"gold-truth-v2: {stats['photos']} photo → {out.relative_to(PROJECT_ROOT)}")
    print(f"  SR keep={stats['sr_kept']} drop={stats['sr_dropped']} split={stats['sr_split']} recall+={stats['recall_sr']}")
    print(f"  GUIDE keep={stats['guide_kept']} drop={stats['guide_dropped']} split={stats['guide_split']} recall+={stats['recall_guide']}")
    print(f"  (git rev hint: {_git_rev()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
