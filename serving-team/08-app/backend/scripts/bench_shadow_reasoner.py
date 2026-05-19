#!/usr/bin/env python3
"""Phase G.1 — shadow_reasoner latency bench (PG vs JSON fallback).

목적: PG SELECT 전환이 runtime latency에 미치는 영향 측정.
- Cache warm 후 measure (cold start 1회 + warm 100회)
- p50 / p95 / p99 산출
- 목표: p50 < 10ms (현재 JSON dict lookup ~50μs)

사용:
  PYTHONIOENCODING=utf-8 DATABASE_URL=... python scripts/bench_shadow_reasoner.py
  python scripts/bench_shadow_reasoner.py --iterations 1000
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import shadow_reasoner  # noqa: E402


SAMPLE_INPUTS = [
    ("건설", ["B-M-32-2026", "X-61-2013", "A-G-4-2025"]),
    ("건설", ["B-M-32-2026"]),
    ("건설", ["A-G-4-2025", "A-101-2018", "A-103-2018", "A-104-2018"]),
    ("일반", ["B-M-32-2026"]),
    ("건설", ["X-61-2013"]),
]


def _measure(source_label: str, iterations: int) -> dict:
    """Measure single shadow_validate latency."""
    times_us = []
    for i in range(iterations):
        inp = SAMPLE_INPUTS[i % len(SAMPLE_INPUTS)]
        start = time.perf_counter()
        shadow_reasoner.shadow_validate(inp[0], inp[1])
        elapsed_us = (time.perf_counter() - start) * 1_000_000
        times_us.append(elapsed_us)

    times_us.sort()
    p50 = statistics.median(times_us)
    p95 = times_us[int(len(times_us) * 0.95)]
    p99 = times_us[int(len(times_us) * 0.99)] if len(times_us) >= 100 else times_us[-1]
    return {
        "source": source_label,
        "iterations": iterations,
        "p50_us": round(p50, 1),
        "p95_us": round(p95, 1),
        "p99_us": round(p99, 1),
        "min_us": round(times_us[0], 1),
        "max_us": round(times_us[-1], 1),
        "mean_us": round(statistics.mean(times_us), 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iterations", type=int, default=200)
    ap.add_argument("--warmup", type=int, default=10)
    args = ap.parse_args()

    print(f"=== shadow_reasoner latency bench (iter={args.iterations}, warmup={args.warmup}) ===\n")

    # PG primary (default)
    print(f"--- Path 1: PG primary ---")
    shadow_reasoner.reset_cache()
    for _ in range(args.warmup):
        shadow_reasoner.shadow_validate("건설", ["B-M-32-2026"])
    pg_stats = _measure("PG", args.iterations)
    print(f"  p50: {pg_stats['p50_us']:8.1f}μs   p95: {pg_stats['p95_us']:8.1f}μs   p99: {pg_stats['p99_us']:8.1f}μs")
    print(f"  min: {pg_stats['min_us']:8.1f}μs   max: {pg_stats['max_us']:8.1f}μs   mean: {pg_stats['mean_us']:8.1f}μs")

    # JSON fallback (monkey-patch)
    print(f"\n--- Path 2: JSON fallback ---")
    shadow_reasoner.reset_cache()
    original_pg_loader = shadow_reasoner._load_axioms_from_pg
    try:
        shadow_reasoner._load_axioms_from_pg = lambda: None
        for _ in range(args.warmup):
            shadow_reasoner.shadow_validate("건설", ["B-M-32-2026"])
        json_stats = _measure("JSON", args.iterations)
    finally:
        shadow_reasoner._load_axioms_from_pg = original_pg_loader
    print(f"  p50: {json_stats['p50_us']:8.1f}μs   p95: {json_stats['p95_us']:8.1f}μs   p99: {json_stats['p99_us']:8.1f}μs")
    print(f"  min: {json_stats['min_us']:8.1f}μs   max: {json_stats['max_us']:8.1f}μs   mean: {json_stats['mean_us']:8.1f}μs")

    # Summary
    print(f"\n=== Summary ===")
    p50_ratio = pg_stats["p50_us"] / max(json_stats["p50_us"], 0.01)
    print(f"PG p50 vs JSON p50: {p50_ratio:.1f}x")
    print(f"PG p50 absolute: {pg_stats['p50_us']:.1f}μs")
    target_us = 10_000  # 10ms
    if pg_stats["p50_us"] < target_us:
        print(f"[PASS] PG p50 < target (10ms = 10,000μs)")
        return 0
    else:
        print(f"[FAIL] PG p50 >= target (10ms = 10,000μs)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
