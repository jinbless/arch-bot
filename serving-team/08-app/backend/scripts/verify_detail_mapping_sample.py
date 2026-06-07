#!/usr/bin/env python3
"""OWA→CWA 상세매핑 검토시트 (Track B, no LLM) — expected vs actual 나란히 CSV.

verify_owa_cwa_live.py 의 partial jsonl(응답 요약 포함)과 코퍼스(expected_*)를 case_id로
join해, 각 케이스의 실제상황 텍스트 + 기대(정답) vs 실제 산출(SHE/절차/조치/벌칙)을 한 줄로
나란히 놓는다. '문제 점수'(불일치/FN/FP 가중) 내림차순 정렬 → 상위가 가장 의심스러운 매핑.

사용:
  <venv> scripts/verify_detail_mapping_sample.py --partial <p1.jsonl,p2.jsonl> [--top 200]
출력: data-team/05-enrichment/eval-data/reports/verify_detail_review_<ts>.csv (+ .md 상위 N)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR / "scripts"))
from replay_synthetic_observations import EVAL_DIR, load_synthetic_cases  # noqa: E402

REPORTS_DIR = EVAL_DIR / "reports"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _problem_score(rec: dict) -> int:
    if "error" in rec:
        return 100
    s = 0
    ct = rec.get("case_type")
    if ct == "positive" and rec.get("false_negative"):
        s += 50
    if ct == "negative" and rec.get("false_positive"):
        s += 40
    if ct == "positive" and rec.get("she_expected") and not rec.get("she_matched"):
        s += 30
    if not rec.get("she_correct"):
        s += 10
    if not rec.get("sr_correct"):
        s += 8
    if not rec.get("penalty_correct"):
        s += 8
    return s


def _first(lst, key, default=""):
    if lst:
        return (lst[0] or {}).get(key, default) or default
    return default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--partial", required=True, help="comma-sep partial jsonl")
    ap.add_argument("--top", type=int, default=200, help="md에 실을 상위 문제 케이스 수")
    args = ap.parse_args()

    corpus = {c.get("case_id"): c for c in load_synthetic_cases()}
    recs: list[dict] = []
    for p in args.partial.split(","):
        for line in Path(p.strip()).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                recs.append(json.loads(line))

    rows = []
    for r in recs:
        cid = r.get("case_id")
        case = corpus.get(cid, {})
        rc = r.get("response_compact") or {}
        rows.append({
            "problem_score": _problem_score(r),
            "case_id": cid,
            "industry": r.get("industry_context"),
            "case_type": r.get("case_type"),
            "situation(실제상황)": (case.get("photo_description") or "")[:200],
            "expected_risk(정답)": (case.get("expected_primary_risk") or "")[:160],
            "expected_corrective(정답)": (case.get("expected_corrective_direction") or "")[:160],
            "actual_risk_level": rc.get("overall_risk_level"),
            "actual_finding_status": rc.get("finding_status"),
            "actual_top_she": _first(rc.get("situation_matches"), "title"),
            "actual_top_procedure": _first(rc.get("standard_procedures"), "title"),
            "actual_top_action": _first(rc.get("immediate_actions"), "title"),
            "actual_penalty_status": rc.get("penalty_exposure_status"),
            "she_correct": r.get("she_correct"),
            "sr_correct": r.get("sr_correct"),
            "penalty_correct": r.get("penalty_correct"),
            "false_negative": r.get("false_negative"),
            "false_positive": r.get("false_positive"),
            "error": r.get("error", ""),
        })
    rows.sort(key=lambda x: x["problem_score"], reverse=True)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = _ts()
    cp = REPORTS_DIR / f"verify_detail_review_{ts}.csv"
    with cp.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)

    md = [f"# 상세매핑 검토 — 상위 {args.top} 문제 케이스 {ts}", ""]
    for x in rows[: args.top]:
        if x["problem_score"] <= 0:
            break
        md += [
            f"### [{x['problem_score']}] {x['case_id']} · {x['industry']} · {x['case_type']}"
            f" (she={x['she_correct']} sr={x['sr_correct']} penalty={x['penalty_correct']}"
            f" FN={x['false_negative']} FP={x['false_positive']})",
            f"- 실제상황: {x['situation(실제상황)']}",
            f"- 기대위험: {x['expected_risk(정답)']}",
            f"- 실제 SHE: {x['actual_top_she']} | finding={x['actual_finding_status']} | 벌칙={x['actual_penalty_status']}",
            f"- 실제 절차top: {x['actual_top_procedure']}",
            "",
        ]
    mp = REPORTS_DIR / f"verify_detail_review_{ts}.md"
    mp.write_text("\n".join(md), encoding="utf-8")
    n_prob = sum(1 for x in rows if x["problem_score"] > 0)
    print(f"[detail] {cp}\n[detail] {mp}\n[detail] rows={len(rows)} problem>0={n_prob}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
