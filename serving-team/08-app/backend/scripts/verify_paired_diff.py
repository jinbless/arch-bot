#!/usr/bin/env python3
"""live-vs-replay paired diff — positive SHE-miss를 L1(LLM 추출/정규화) vs L2(SHE 패턴 부재)로 격리.

라이브(verify_owa_cwa_live partial)는 실제 LLM 추출+정규화+매핑 전체 체인.
replay(replay_synthetic_observations --output, expected_features 주입)는 정규화+SHE 매칭 ceiling.
positive & should_match_she 인 케이스에서:
  live SHE 매칭     → live_ok
  live X, replay O  → L1_extraction (정답 features면 SHE 매칭됨 → 라이브 LLM이 코드 추출 실패)
  live X, replay X  → L2_she_missing (정답 features로도 SHE 미매칭 → SHE 패턴 자체 부재)
업종 + work_context별로 집계 → L2 gap = 추가할 SHE 패턴, L1 gap = alias/추출 보강 대상.

사용: <venv> scripts/verify_paired_diff.py --live <partial.jsonl> --replay <replay.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR / "scripts"))
from replay_synthetic_observations import EVAL_DIR, load_synthetic_cases  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", required=True, help="verify_owa_cwa_live partial jsonl(들), comma-sep")
    ap.add_argument("--replay", required=True, help="replay_synthetic_observations --output json")
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    corpus = {c.get("case_id"): c for c in load_synthetic_cases()}

    live = {}
    for p in args.live.split(","):
        for line in Path(p.strip()).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                r = json.loads(line)
                live[r.get("case_id")] = r

    replay = {}
    rj = json.loads(Path(args.replay).read_text(encoding="utf-8"))
    for r in rj.get("cases", []):
        replay[r.get("case_id")] = r

    klass = Counter()
    by_ind = defaultdict(Counter)
    l2_gaps = Counter()   # (industry, work_context) → count  (추가할 SHE 패턴)
    l1_gaps = Counter()   # (industry, work_context) → count  (추출/alias 보강)
    l2_examples = defaultdict(list)
    l1_examples = defaultdict(list)

    for cid, case in corpus.items():
        if case.get("case_type") != "positive":
            continue
        if not (case.get("expected_pipeline_behavior") or {}).get("should_match_she"):
            continue
        lr = live.get(cid)
        rr = replay.get(cid)
        if not lr or not rr or "error" in lr or "error" in rr:
            klass["skip(no data)"] += 1
            continue
        ind = case.get("industry_context")
        wc = case.get("work_context")
        live_she = bool(lr.get("she_matched"))
        replay_she = bool(rr.get("she_matched"))
        if live_she:
            klass["live_ok"] += 1
            by_ind[ind]["live_ok"] += 1
        elif replay_she:
            klass["L1_extraction"] += 1
            by_ind[ind]["L1_extraction"] += 1
            l1_gaps[(ind, wc)] += 1
            if len(l1_examples[(ind, wc)]) < 2:
                l1_examples[(ind, wc)].append((cid, (case.get("photo_description") or "")[:90]))
        else:
            klass["L2_she_missing"] += 1
            by_ind[ind]["L2_she_missing"] += 1
            l2_gaps[(ind, wc)] += 1
            if len(l2_examples[(ind, wc)]) < 2:
                l2_examples[(ind, wc)].append((cid, (case.get("photo_description") or "")[:90]))

    print("=== positive&should_match_she 격리 ===")
    for k, v in klass.most_common():
        print(f"  {k}: {v}")
    tot = klass["live_ok"] + klass["L1_extraction"] + klass["L2_she_missing"]
    if tot:
        print(f"  live SHE recall = {klass['live_ok']/tot:.3f}  (L2-ceiling = {(klass['live_ok']+klass['L1_extraction'])/tot:.3f})")

    print(f"\n=== L2 gap (SHE 패턴 부재) — 상위 {args.top} (industry, work_context) ===")
    for (ind, wc), n in l2_gaps.most_common(args.top):
        ex = l2_examples[(ind, wc)]
        print(f"  [{n}] {ind} / {wc}")
        for cid, d in ex:
            print(f"        {cid}: {d}")

    print(f"\n=== L1 gap (LLM 추출/정규화 누락) — 상위 {args.top} ===")
    for (ind, wc), n in l1_gaps.most_common(args.top):
        ex = l1_examples[(ind, wc)]
        print(f"  [{n}] {ind} / {wc}")
        for cid, d in ex:
            print(f"        {cid}: {d}")

    print(f"\n=== 업종별 (L2_she_missing 내림차순) ===")
    rows = sorted(by_ind.items(), key=lambda kv: kv[1].get("L2_she_missing", 0), reverse=True)
    for ind, c in rows[: args.top]:
        print(f"  {ind}: ok={c.get('live_ok',0)} L1={c.get('L1_extraction',0)} L2={c.get('L2_she_missing',0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
