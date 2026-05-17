#!/usr/bin/env python3
"""Phase A.2 — Domain pair incompatibility LLM mining (gpt-5.4-mini).

A.1에서 분류한 domain × domain pair에 대해 incompatible 여부를 판정한다.

흐름:
1. guide_llm_domains.json 로드 → distinct domain 추출
2. Subsumption pre-check: 두 domain embedding cosine > 0.55 → 자동 제외
   (hyponym/hypernym 의심, 예: scaffolding vs fall_protection)
3. 2,360 ground truth 사전검증: synthetic_observations에서 같은 사진의
   industry_context와 work_context로 매칭된 적 있는 페어 → 자동 제외
4. LLM (gpt-5.4-mini)이 남은 페어 incompatible 판정
5. 출력: guide_domain_incompatibilities.json (level: candidate)

비용: ~$5-15 (gpt-5.4-mini, ~2-5k 페어, structured output)

사용:
  python data-team/05-enrichment/llm-scripts/mine_domain_incompatibilities.py
  python data-team/05-enrichment/llm-scripts/mine_domain_incompatibilities.py --dry-run

ENV:
  OPENAI_API_KEY (required)
  OPENAI_EMBEDDING_MODEL (default: text-embedding-3-small)
  LLM_RERANK_MODEL (default: gpt-5.4-mini)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
EVAL_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "eval-data"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
LLM_DOMAINS_PATH = ARTIFACTS_DIR / "guide_llm_domains.json"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "guide_domain_incompatibilities.json"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")
EMBED_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
SUBSUMPTION_THRESHOLD = 0.55


SYSTEM_PROMPT = """\
당신은 KOSHA 산업 도메인 호환성 판정자입니다.
두 산업 도메인이 같은 사진/현장에서 동시에 적용될 수 있는지(compatible)
또는 명백히 다른 현장에서만 적용되는지(incompatible) 판정합니다.

원칙:
- incompatible 예: (식당, 사장교) — 식당과 교량은 다른 물리적 현장
- incompatible 예: (지게차 운전, 가공목재 적재) — 같은 물류 영역이지만 작업/장비/위험 다름
- compatible 예: (비계 작업, 추락방호) — 같은 고소작업의 다른 측면
- compatible 예: (건설, 콘크리트 타설) — subsumption (구체화)
- compatible 예: (general, 화학공장) — general은 모든 산업 포함

판정 기준:
- 동일 물리적 현장에서 동시에 발생 가능? → compatible
- 한 산업의 specialization? → compatible
- 완전히 다른 산업 segment? → incompatible
"""

USER_TEMPLATE = """\
도메인 A: {domain_a}
도메인 B: {domain_b}

[A에 매핑된 Guide 샘플 (최대 3개)]
{a_guides}

[B에 매핑된 Guide 샘플 (최대 3개)]
{b_guides}

이 두 도메인은 같은 사진/현장에서 동시 적용될 수 있는가, 또는 명백히 incompatible한가?
"""

RESPONSE_SCHEMA = {
    "name": "domain_pair_incompatibility",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "incompatible": {
                "type": "boolean",
                "description": "true면 두 도메인이 서로 incompatible (같은 현장에 동시 적용 불가)",
            },
            "confidence": {
                "type": "number",
                "description": "0.0~1.0. incompatible 판정에 대한 확신도",
            },
            "reason": {
                "type": "string",
                "description": "한국어 1-2문장 사유",
            },
        },
        "required": ["incompatible", "confidence", "reason"],
        "additionalProperties": False,
    },
}


def load_synthetic_industry_pairs() -> set[tuple[str, str]]:
    """2,360 ground truth에서 같이 등장한 (industry, work_context) 페어들.

    이런 페어는 incompatible로 자동 채택하지 않음 (실제로 같이 발생).
    """
    pairs: set[tuple[str, str]] = set()
    for f in sorted(EVAL_DIR.glob("synthetic_observations_v*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            ind = str(row.get("industry_context") or "").strip()
            wc = str(row.get("work_context") or "").strip()
            if ind and wc:
                pairs.add((ind, wc))
                pairs.add((wc, ind))
    return pairs


def load_domain_index() -> tuple[list[str], dict[str, list[str]]]:
    if not LLM_DOMAINS_PATH.exists():
        raise FileNotFoundError(
            f"{LLM_DOMAINS_PATH} 없음. 먼저 build_guide_llm_domains.py 실행 필요"
        )
    payload = json.loads(LLM_DOMAINS_PATH.read_text(encoding="utf-8"))
    classifications = payload.get("classifications") or {}
    domain_to_guides: dict[str, list[str]] = defaultdict(list)
    for code, info in classifications.items():
        primary = (info.get("primary_domain") or "").strip()
        if primary:
            domain_to_guides[primary].append(code)
        for d in info.get("domains") or []:
            d = str(d).strip()
            if d and d != primary:
                domain_to_guides[d].append(code)
    domains = sorted(domain_to_guides.keys())
    return domains, dict(domain_to_guides)


async def embed_domains(client, domains: list[str]) -> dict[str, list[float]]:
    if not domains:
        return {}
    response = await client.embeddings.create(model=EMBED_MODEL, input=domains)
    return {d: item.embedding for d, item in zip(domains, response.data)}


def cosine(a: list[float], b: list[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def judge_pair(
    client,
    *,
    model: str,
    domain_a: str,
    domain_b: str,
    a_guides: list[str],
    b_guides: list[str],
    semaphore,
) -> dict[str, Any]:
    user_prompt = USER_TEMPLATE.format(
        domain_a=domain_a,
        domain_b=domain_b,
        a_guides=", ".join(a_guides[:3]) or "(없음)",
        b_guides=", ".join(b_guides[:3]) or "(없음)",
    )
    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "developer", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_schema", "json_schema": RESPONSE_SCHEMA},
                max_completion_tokens=256,
            )
            return json.loads(response.choices[0].message.content or "{}")
        except Exception as exc:
            return {"error": str(exc), "incompatible": False, "confidence": 0.0, "reason": ""}


async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not args.dry_run and not api_key:
        print("ERROR: OPENAI_API_KEY 환경변수 필요", file=sys.stderr)
        return 2

    domains, domain_to_guides = load_domain_index()
    print(f"Loaded {len(domains)} distinct domains from {LLM_DOMAINS_PATH}")

    synthetic_pairs = load_synthetic_industry_pairs()
    print(f"Synthetic ground-truth co-occurrence pairs: {len(synthetic_pairs)}")

    candidate_pairs = [
        (a, b)
        for a, b in combinations(domains, 2)
        if (a, b) not in synthetic_pairs and (b, a) not in synthetic_pairs
    ]
    print(
        f"Pair candidates after ground-truth filter: "
        f"{len(candidate_pairs)} (raw {len(domains) * (len(domains) - 1) // 2})"
    )

    if args.dry_run:
        print("\n--- dry-run: first 10 pair candidates ---")
        for a, b in candidate_pairs[:10]:
            print(f"  {a}  ×  {b}")
        return 0

    if args.limit:
        candidate_pairs = candidate_pairs[: args.limit]

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)

    print(f"\nEmbedding {len(domains)} domains for subsumption pre-check...")
    embeddings = await embed_domains(client, domains)
    excluded_by_subsumption: list[dict] = []
    filtered_pairs: list[tuple[str, str]] = []
    for a, b in candidate_pairs:
        ea, eb = embeddings.get(a), embeddings.get(b)
        if ea and eb:
            sim = cosine(ea, eb)
            if sim >= SUBSUMPTION_THRESHOLD:
                excluded_by_subsumption.append(
                    {"a": a, "b": b, "similarity": round(sim, 4)}
                )
                continue
        filtered_pairs.append((a, b))
    print(
        f"Subsumption-excluded (cosine >= {SUBSUMPTION_THRESHOLD}): "
        f"{len(excluded_by_subsumption)}, remaining: {len(filtered_pairs)}"
    )

    semaphore = asyncio.Semaphore(args.concurrency)
    results: list[dict[str, Any]] = []
    start = time.time()

    async def _run_one(idx: int, a: str, b: str) -> None:
        verdict = await judge_pair(
            client,
            model=args.model,
            domain_a=a,
            domain_b=b,
            a_guides=domain_to_guides.get(a, []),
            b_guides=domain_to_guides.get(b, []),
            semaphore=semaphore,
        )
        results.append(
            {
                "domain_a": a,
                "domain_b": b,
                "incompatible": bool(verdict.get("incompatible", False)),
                "confidence": float(verdict.get("confidence", 0.0)),
                "reason": str(verdict.get("reason", "")),
                "level": "candidate",
                "error": verdict.get("error"),
            }
        )
        if (idx + 1) % 50 == 0:
            elapsed = time.time() - start
            rate = (idx + 1) / elapsed if elapsed else 0
            n_incompat = sum(1 for r in results if r["incompatible"])
            print(
                f"  [{idx + 1:4d}/{len(filtered_pairs)}] "
                f"incompatible={n_incompat} elapsed={elapsed:.0f}s rate={rate:.1f}/s"
            )

    tasks = [_run_one(i, a, b) for i, (a, b) in enumerate(filtered_pairs)]
    await asyncio.gather(*tasks)

    incompatibles = [r for r in results if r["incompatible"] and r.get("confidence", 0) >= 0.5]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "domain_count": len(domains),
        "raw_pair_count": len(domains) * (len(domains) - 1) // 2,
        "after_synthetic_filter": len(candidate_pairs),
        "after_subsumption_filter": len(filtered_pairs),
        "subsumption_excluded": excluded_by_subsumption[:200],
        "incompatible_count": len(incompatibles),
        "incompatibilities": incompatibles,
        "all_verdicts_count": len(results),
    }
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    elapsed = time.time() - start
    print(f"\nSaved: {args.output}")
    print(f"  Total verdicts: {len(results)}")
    print(f"  Incompatibles (confidence ≥ 0.5): {len(incompatibles)}")
    print(f"  Elapsed: {elapsed:.0f}s")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="처음 N개 페어만")
    parser.add_argument("--concurrency", type=int, default=8, help="동시 LLM 호출")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 페어 목록만 출력")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
