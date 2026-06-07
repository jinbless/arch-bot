#!/usr/bin/env python3
"""OWA→CWA 라이브 검증 하니스 — 업종별 실제상황 텍스트 → 라이브 데모 text 분석 → 매핑 검증.

synthetic_observations_v*.jsonl 의 photo_description(업종별 실제상황)을 라이브 데모의
POST /api/v1/analysis/text 로 보내고, 응답을 ground-truth(expected_*)와 비교해 업종별
매핑 품질을 리포트한다. **라이브 경로는 실제 LLM 추출 + 정규화 + SHE/SR/Guide/Penalty
매핑 전체 체인을 검증**한다(replay는 expected_features 주입으로 LLM 우회).

reuse: replay_synthetic_observations.{load_synthetic_cases, evaluate_case, build_summary,
PENALTY_EXPOSURE_MAP}; app.models.analysis.AnalysisResponse(응답 역직렬화 → evaluate_case 그대로).

실행:
  set -a; . <main>/serving-team/08-app/backend/.env; set +a   # OPENAI_API_KEY (import 체인용)
  <venv> scripts/verify_owa_cwa_live.py --dry-run
  <venv> scripts/verify_owa_cwa_live.py --shard 0/4 --out /mnt/c/.../partial_0.jsonl   (4개 병렬)
  <venv> scripts/verify_owa_cwa_live.py --report p0.jsonl,p1.jsonl,p2.jsonl,p3.jsonl

주: 센티넬 미사용(showcase 기록을 깨끗하게). 라이브 분석은 데모 history(ohs_analysis_records)에
persist된다(의도 — showcase). manifest(case_id↔analysis_id)는 partial jsonl에 캡처.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR / "scripts"))
sys.path.insert(0, str(BACKEND_DIR))

# reuse (import 시 app.services.analysis_pipeline → openai_client 생성 → OPENAI_API_KEY 필요)
from replay_synthetic_observations import (  # noqa: E402
    ARTIFACTS_DIR,
    EVAL_DIR,
    PENALTY_EXPOSURE_MAP,  # noqa: F401  (evaluate_case 내부에서 사용)
    build_summary,
    evaluate_case,
    load_synthetic_cases,
)
from app.models.analysis import AnalysisResponse  # noqa: E402

DEFAULT_BASE = "http://127.0.0.1:8000"
REPORTS_DIR = EVAL_DIR / "reports"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def select_cases(args) -> list[dict]:
    cases = [c for c in load_synthetic_cases() if (c.get("photo_description") or "").strip()]
    if args.industries:
        inds = {s.strip() for s in args.industries.split(",")}
        cases = [c for c in cases if c.get("industry_context") in inds]
    if args.case_types:
        cts = {s.strip() for s in args.case_types.split(",")}
        cases = [c for c in cases if c.get("case_type") in cts]
    if args.shard:
        k, of = (int(x) for x in args.shard.split("/"))
        cases = [c for i, c in enumerate(cases) if i % of == k]
    if args.limit:
        cases = cases[: args.limit]
    return cases


def _coerce_penalty_v10(case: dict, result: dict) -> None:
    """v10은 penalty_exposure가 bool(True/False) → strict 비교 불가. relaxed로 덮어씀."""
    pe = (case.get("expected_pipeline_behavior") or {}).get("penalty_exposure")
    if isinstance(pe, bool):
        actual = result.get("penalty_actual") or "no_penalty"
        result["penalty_correct"] = (actual != "no_penalty") if pe else (actual == "no_penalty")
        result["penalty_relaxed_v10"] = True


def _compact_response(rj: dict) -> dict:
    """judge/검토시트용 경량 응답 요약(full 응답 저장 회피)."""
    def take(lst, *keys, n=3):
        return [{k: it.get(k) for k in keys} for it in (lst or [])[:n]]

    return {
        "overall_risk_level": rj.get("overall_risk_level"),
        "finding_status": rj.get("finding_status"),
        "penalty_exposure_status": rj.get("penalty_exposure_status"),
        "summary": (rj.get("summary") or "")[:300],
        "situation_matches": take(rj.get("situation_matches"), "title", "status", "score"),
        "standard_procedures": take(rj.get("standard_procedures"), "title", "evidence_summary"),
        "immediate_actions": take(rj.get("immediate_actions"), "title"),
        "penalty_paths": take(rj.get("penalty_paths"), "path_type", "notice_level", "penalty_descriptions"),
        "hazards": take(rj.get("hazards"), "name", "risk_level"),
    }


async def _post_one(client, sem, base, case, timeout, retries=3) -> dict:
    cid = case.get("case_id")
    err_base = {
        "case_id": cid,
        "case_type": case.get("case_type"),
        "industry_context": case.get("industry_context"),
    }
    body = {
        "description": case.get("photo_description") or "",
        "workplace_type": case.get("work_context") or None,
        "industry_sector": case.get("industry_context") or None,
    }
    to = httpx.Timeout(timeout, connect=10.0)
    async with sem:
        last = None
        for attempt in range(retries):
            try:
                t0 = time.monotonic()
                r = await client.post(f"{base}/api/v1/analysis/text", json=body, timeout=to)
                latency = round((time.monotonic() - t0) * 1000)
                if r.status_code == 200:
                    rj = r.json()
                    try:
                        resp = AnalysisResponse.model_validate(rj)
                    except Exception as ve:  # noqa: BLE001
                        return {**err_base, "error": f"deserialize: {ve}", "http_status": 200}
                    ev = evaluate_case(case, resp)
                    _coerce_penalty_v10(case, ev)
                    ev["analysis_id"] = rj.get("analysis_id")
                    ev["http_status"] = 200
                    ev["latency_ms"] = latency
                    ev["response_compact"] = _compact_response(rj)
                    return ev
                if r.status_code in (429, 500, 502, 503, 504):
                    ra = r.headers.get("Retry-After")
                    await asyncio.sleep(float(ra) if ra else (attempt + 1) ** 2)
                    last = f"http {r.status_code}"
                    continue
                return {**err_base, "error": f"http {r.status_code}", "http_status": r.status_code}
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last = str(e)
                await asyncio.sleep((attempt + 1) ** 2)
        return {**err_base, "error": f"retries exhausted: {last}"}


async def run(args) -> int:
    cases = select_cases(args)
    out_path = Path(args.out) if args.out else ARTIFACTS_DIR / f"verify_owa_cwa_partial_{_ts()}.jsonl"
    done: set = set()
    if args.resume and out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line).get("case_id"))
            except Exception:  # noqa: BLE001
                pass
    todo = [c for c in cases if c.get("case_id") not in done]
    print(f"[verify] selected={len(cases)} resume_skip={len(done)} todo={len(todo)} out={out_path}")
    if args.dry_run:
        ind = Counter(c.get("industry_context") for c in cases)
        ct = Counter(c.get("case_type") for c in cases)
        print(f"[dry-run] industries={len(ind)} case_types={dict(ct)} ~gpt-4.1 calls={len(todo)} (+rerank)")
        return 0

    sem = asyncio.Semaphore(args.concurrency)
    limits = httpx.Limits(max_connections=args.concurrency + 4)
    n = 0
    async with httpx.AsyncClient(limits=limits) as client:
        with out_path.open("a", encoding="utf-8") as fh:
            tasks = [asyncio.create_task(_post_one(client, sem, args.base_url, c, args.timeout)) for c in todo]
            for fut in asyncio.as_completed(tasks):
                rec = await fut
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                n += 1
                if n % 50 == 0 or n == len(todo):
                    print(f"  [{n}/{len(todo)}] {rec.get('case_id')} {rec.get('http_status', rec.get('error'))}")
    print(f"[verify] done {n} → {out_path}")
    return 0


def _by_industry(per_case: list[dict]) -> dict:
    groups = defaultdict(list)
    for r in per_case:
        groups[r.get("industry_context")].append(r)
    rows = {}
    for ind, rs in groups.items():
        valid = [r for r in rs if "error" not in r]
        nn = len(valid)
        if not nn:
            rows[ind] = {"n": 0, "errored": len(rs)}
            continue
        pos = [r for r in valid if r.get("case_type") == "positive"]
        rows[ind] = {
            "n": nn,
            "she_accuracy": round(sum(1 for r in valid if r.get("she_correct")) / nn, 4),
            "sr_accuracy": round(sum(1 for r in valid if r.get("sr_correct")) / nn, 4),
            "penalty_accuracy": round(sum(1 for r in valid if r.get("penalty_correct")) / nn, 4),
            "overall_accuracy": round(
                sum(1 for r in valid if r.get("she_correct") and r.get("sr_correct") and r.get("penalty_correct")) / nn, 4
            ),
            "false_negative": sum(1 for r in valid if r.get("false_negative")),
            "false_positive": sum(1 for r in valid if r.get("false_positive")),
            "guide_present_rate_pos": round(sum(1 for r in pos if r.get("procedures_count", 0) > 0) / len(pos), 4) if pos else None,
            "n_pos": len(pos),
            "errored": len(rs) - nn,
        }
    return dict(sorted(rows.items(), key=lambda kv: kv[1].get("overall_accuracy", 1.0)))


def _failure_modes(per_case: list[dict]) -> Counter:
    fm: Counter = Counter()
    for r in per_case:
        if "error" in r:
            fm["errored"] += 1
            continue
        ct = r.get("case_type")
        if ct == "negative" and r.get("false_positive"):
            fm["negative_false_positive"] += 1
        elif ct == "positive" and r.get("false_negative"):
            fm["positive_false_negative"] += 1
        elif ct == "positive" and r.get("she_expected") and not r.get("she_matched"):
            fm["positive_no_she"] += 1
        elif not r.get("she_correct"):
            fm["she_mismatch"] += 1
        elif not r.get("sr_correct"):
            fm["sr_mismatch"] += 1
        elif not r.get("penalty_correct"):
            fm["penalty_mismatch"] += 1
        else:
            fm["ok"] += 1
    return fm


def build_report(args) -> int:
    per_case: list[dict] = []
    for p in args.report.split(","):
        for line in Path(p.strip()).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                per_case.append(json.loads(line))
    summary = build_summary(per_case)
    by_ind = _by_industry(per_case)
    fmodes = _failure_modes(per_case)
    worst = [{"industry": k, **v} for k, v in by_ind.items() if v.get("n", 0) >= 5][:15]

    ts = _ts()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "meta": {"generated_at": ts, "base_url": args.base_url, "total": len(per_case)},
        "summary": summary,
        "failure_modes": dict(fmodes.most_common()),
        "worst_industries": worst,
        "by_industry": by_ind,
    }
    jp = REPORTS_DIR / f"verify_owa_cwa_report_{ts}.json"
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        f"# OWA→CWA 라이브 검증 리포트 {ts}",
        "",
        f"- total={len(per_case)} valid={summary['valid']} errored={summary['errored']}",
        f"- she={summary['she_accuracy']} sr={summary['sr_accuracy']} penalty={summary['penalty_accuracy']} overall={summary['overall_accuracy']}",
        f"- fp_rate={summary['false_positive_rate']} fn_rate={summary['false_negative_rate']} avg_proc={summary['avg_procedures']}",
        "",
        "## 실패모드",
        "",
    ]
    md += [f"- {k}: {v}" for k, v in fmodes.most_common()]
    md += [
        "",
        "## 업종별 (overall 오름차순, n≥5)",
        "",
        "| 업종 | n | she | sr | penalty | overall | FN | FP | guide(pos) |",
        "|---|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for ind, v in by_ind.items():
        if v.get("n", 0) < 5:
            continue
        md.append(
            f"| {ind} | {v['n']} | {v['she_accuracy']} | {v['sr_accuracy']} | {v['penalty_accuracy']} "
            f"| {v['overall_accuracy']} | {v['false_negative']} | {v['false_positive']} | {v.get('guide_present_rate_pos')} |"
        )
    mp = REPORTS_DIR / f"verify_owa_cwa_report_{ts}.md"
    mp.write_text("\n".join(md), encoding="utf-8")
    print(f"[report] {jp}")
    print(f"[report] {mp}")
    print("\n".join(md[:13]))
    return 0


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--shard", help="k/of (modulo shard)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--industries", help="comma-sep industry_context filter")
    ap.add_argument("--case-types", help="comma-sep case_type filter")
    ap.add_argument("--out", help="partial jsonl path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", help="comma-sep partial jsonl paths → build aggregate report")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    if args.report:
        return build_report(args)
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
