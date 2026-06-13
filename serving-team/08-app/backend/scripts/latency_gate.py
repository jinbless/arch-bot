#!/usr/bin/env python3
"""파이프라인 레이턴시 회귀 게이트 — PERF-1 (S2). `make latency-gate`.

"서빙 PG ms 경로 무후퇴" 불변 원칙의 기계 강제. replay 하네스의 fake result를
재사용해 analysis_pipeline.run의 Layer 1-3 wall time(Vision LLM 제외 — 영구
외부 의존이라 측정 대상 아님)을 N회 측정하고, p50/p95를 커밋된
perf_baseline.json과 비교한다. p95가 기준 대비 +20% 초과 시 exit 1.

matcher/파이프라인 변경(MATCH-*, VT backfill 등)의 머지 전제조건.

주의:
- 측정은 부하 없는 상태에서(다른 replay/배치와 동시 실행 금지 — CPU 경합 왜곡).
- semantic rerank는 LLM 호출(비결정·외부)이라 게이트에선 off 고정.
- baseline 재캡처(--capture)는 의도적 채택 시만(하드웨어/환경 변경 포함 커밋 사유 필수).

사용:
  python scripts/latency_gate.py              # 검증 (기본, N=100)
  python scripts/latency_gate.py --capture    # perf_baseline.json 재캡처
  python scripts/latency_gate.py --n 50       # 표본 수 조정
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

# 게이트는 결정적이어야 함 (import 전에 env 설정):
# - rerank(LLM) off + semantic attach off → 임베딩 네트워크 호출(변동·30s 타임아웃) 배제.
#   레이턴시 게이트의 목적은 matcher/파이프라인 compute 경로의 회귀 탐지이며, 임베딩
#   지연은 외부 네트워크 지배라 코드로 회귀시킬 수 없다(우리 코드 변경이 영향 주는
#   건 PG·matcher 경로). semantic을 켜면 기준선이 네트워크 노이즈로 무의미해진다.
os.environ.setdefault("SEMANTIC_ATTACH_RERANK", "off")
os.environ.setdefault("SEMANTIC_ATTACH", "off")

from app.db.database import SessionLocal  # noqa: E402
from app.services.analysis_pipeline import AnalysisRunInput, analysis_pipeline  # noqa: E402
from replay_synthetic_observations import build_fake_result, load_synthetic_cases  # noqa: E402


def _find_repo_root() -> Path:
    for a in Path(__file__).resolve().parents:
        if (a / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return a
    raise RuntimeError("repo root not found")


BASELINE = (_find_repo_root() / "data-team" / "05-enrichment" / "runtime-artifacts"
            / "perf_baseline.json")
P95_TOLERANCE = 0.20  # p95 +20% 초과 → exit 1


def percentile(values: list[float], pct: float) -> float:
    s = sorted(values)
    idx = max(0, min(len(s) - 1, round(pct / 100 * (len(s) - 1))))
    return s[idx]


async def measure(n: int) -> list[float]:
    cases = load_synthetic_cases(limit=n)
    if len(cases) < n:
        print(f"WARN: 케이스 {len(cases)}개만 로드됨 (요청 {n})", file=sys.stderr)
    db = SessionLocal()
    timings: list[float] = []
    try:
        # 워밍업 1회(커넥션·캐시 초기화 비용 제외)
        warm = build_fake_result(cases[0])
        await analysis_pipeline.run(db=db, run_input=AnalysisRunInput(
            result=warm, analysis_type="text", input_preview="latency:warmup",
            full_description=cases[0].get("photo_description", ""),
            declared_industry_text=cases[0].get("industry_context"), persist=False))
        for case in cases:
            fake = build_fake_result(case)
            t0 = time.perf_counter()
            await analysis_pipeline.run(db=db, run_input=AnalysisRunInput(
                result=fake, analysis_type="text",
                input_preview=f"latency:{case.get('case_id')}",
                full_description=case.get("photo_description", ""),
                declared_industry_text=case.get("industry_context"), persist=False))
            timings.append(time.perf_counter() - t0)
    finally:
        db.close()
    return timings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=100, help="측정 표본 수 (기본 100)")
    ap.add_argument("--capture", action="store_true",
                    help="perf_baseline.json 재캡처(의도적 채택 시만)")
    args = ap.parse_args()

    timings = asyncio.run(measure(args.n))
    stats = {
        "n": len(timings),
        "p50_ms": round(percentile(timings, 50) * 1000, 1),
        "p95_ms": round(percentile(timings, 95) * 1000, 1),
        "mean_ms": round(statistics.mean(timings) * 1000, 1),
        "max_ms": round(max(timings) * 1000, 1),
    }
    print(f"Layer1-3 latency (N={stats['n']}, rerank off, persist off): "
          f"p50 {stats['p50_ms']}ms · p95 {stats['p95_ms']}ms · "
          f"mean {stats['mean_ms']}ms · max {stats['max_ms']}ms")

    if args.capture:
        BASELINE.write_text(json.dumps(stats, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"Captured: {BASELINE.name}")
        return 0

    if not BASELINE.exists():
        print(f"기준선 부재: {BASELINE} — 먼저 --capture 실행", file=sys.stderr)
        return 2

    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    limit = base["p95_ms"] * (1 + P95_TOLERANCE)
    print(f"baseline p95 {base['p95_ms']}ms → 허용 한도 {limit:.1f}ms (+{P95_TOLERANCE:.0%})")
    if stats["p95_ms"] > limit:
        print(f"latency-gate FAIL — p95 {stats['p95_ms']}ms > 한도 {limit:.1f}ms")
        return 1
    print("latency-gate PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
