#!/usr/bin/env python3
"""Step 0 — 합성 관찰셋 → 파이프라인 → 케이스별 SR(focused/broad) + 산업안전보건규칙 조 dump.

judge_sr_article_mapping.py(Step 2)의 입력. `replay_synthetic_observations.py`의 빌딩블록
(load_synthetic_cases·build_fake_result·analysis_pipeline·SessionLocal)을 그대로 재사용해 **동일
경로**로 SR을 산출하고, `_mapping_review_common._sr_articles`로 SR→조(1:1, 산업안전보건규칙)를 붙인다.
서빙/DB 무영향(persist=False). OpenAI 키 불요(facet/SHE 매칭은 PG 기반).

- focused = situation_matches[].applies_sr_ids 합집합 (SHE-귀속, 정밀 후보)
- broad   = reasoning_trace.safety_requirements (광범위 합집합)

사용: python scripts/dump_synthetic_sr_articles.py [--limit N] [--out PATH] [--resume]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import replay_synthetic_observations as R  # 빌딩블록 + path/임포트 셋업 재사용
from _mapping_review_common import _sr_articles

DEFAULT_OUT = R.ARTIFACTS_DIR / "synthetic_sr_article_dump.jsonl"


def extract_sr_sets(resp) -> tuple[list[str], list[str]]:
    """response → (focused, broad). 둘 다 등장순 dedup."""
    focused: list[str] = []
    seen: set[str] = set()
    for m in getattr(resp, "situation_matches", None) or []:
        for sid in getattr(m, "applies_sr_ids", None) or []:
            if sid and sid not in seen:
                seen.add(sid)
                focused.append(sid)
    rt = getattr(resp, "reasoning_trace", None)
    broad = list(getattr(rt, "safety_requirements", None) or []) if rt else []
    return focused, broad


def dump_record(db, case: dict, resp) -> dict:
    focused, broad = extract_sr_sets(resp)
    arts = _sr_articles(db, list(set(focused) | set(broad)))

    def enrich(ids: list[str]) -> list[dict]:
        out = []
        for s in ids:
            a = arts.get(s) or {}
            out.append({
                "sr_id": s,
                "article_code": a.get("article_code", ""),
                "article_title": a.get("title", ""),
            })
        return out

    return {
        "case_id": case.get("case_id"),
        "case_type": case.get("case_type"),
        "industry_context": case.get("industry_context"),
        "work_context": case.get("work_context"),
        "photo_description": case.get("photo_description", ""),
        "visual_cues": case.get("visual_cues") or [],
        "uncertain_cues": case.get("uncertain_cues") or [],
        "expected_features": case.get("expected_features") or {},
        "expected_primary_risk": case.get("expected_primary_risk", ""),
        "expected_corrective_direction": case.get("expected_corrective_direction", ""),
        "focused": enrich(focused),
        "broad": enrich(broad),
        "focused_count": len(focused),
        "broad_count": len(broad),
    }


async def _run_case(db, case: dict):
    fake = R.build_fake_result(case)
    return await R.analysis_pipeline.run(
        db=db,
        run_input=R.AnalysisRunInput(
            result=fake,
            analysis_type="text",
            input_preview=f"dump:{case.get('case_id', '?')}",
            full_description=case.get("photo_description", ""),
            declared_industry_text=case.get("industry_context"),
            persist=False,  # 합성 분석을 운영/데모 DB에 쓰지 않음
        ),
    )


async def main_async(args: argparse.Namespace) -> int:
    cases = R.load_synthetic_cases(limit=args.limit, start_idx=args.start_idx, end_idx=args.end_idx)
    if args.cases_from:
        want: set[str] = set()
        for line in Path(args.cases_from).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("case_id") and not rec.get("error"):
                    want.add(rec["case_id"])
            except Exception:  # noqa: BLE001
                pass
        cases = [c for c in cases if c.get("case_id") in want]
        print(f"[cases-from] {Path(args.cases_from).name} 의 {len(want)} case_id로 필터 → {len(cases)}건")
    if not cases:
        print(f"No cases loaded from {R.EVAL_DIR}", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    done: set[str] = set()
    if args.resume and out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["case_id"])
            except Exception:  # noqa: BLE001 — 절전으로 잘린 마지막 줄 등
                pass
        print(f"[resume] {len(done)}건 이미 dump됨 → 나머지만 실행")

    print(f"Loaded {len(cases)} cases — dump → {out}")
    db = R.SessionLocal()
    n, errs = 0, 0
    try:
        with out.open("a" if args.resume else "w", encoding="utf-8") as f:
            for i, case in enumerate(cases):
                if case.get("case_id") in done:
                    continue
                if i % 50 == 0:
                    print(f"  [{i:4d}/{len(cases)}] {case.get('case_id', '?')}", flush=True)
                try:
                    resp = await _run_case(db, case)
                    rec = dump_record(db, case, resp)
                except Exception as exc:  # noqa: BLE001
                    rec = {"case_id": case.get("case_id"), "error": repr(exc)[:200]}
                    errs += 1
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                n += 1
    finally:
        db.close()
    print(f"DONE — {n} records ({errs} errored) → {out}")
    return 0


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None, help="처음 N개 case만")
    ap.add_argument("--start-idx", type=int, default=0)
    ap.add_argument("--end-idx", type=int, default=None)
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    ap.add_argument("--resume", action="store_true", help="기존 out에 이어서(완료 case_id skip)")
    ap.add_argument("--cases-from", default=None,
                    help="이 jsonl(예: gold_articles.jsonl)에 등장하는 case_id만 처리(샘플 정합용)")
    return ap.parse_args()


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
