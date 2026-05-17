#!/usr/bin/env python3
"""Phase A.1 — 1,038 Guide 자동 multi-label 도메인 분류 (gpt-5.4-mini).

각 Guide JSON의 title + sections[0..2].text를 LLM에 보내고 industry domains을
multi-label로 분류한다. 2,360 synthetic_observations에서 추출한 distinct
industry_context (78개)를 closed vocabulary로 제공해서 일관성/비용 모두 ↑.

3-way self-consistency: 같은 Guide를 3회 호출 → 2/3 일치 라벨만 채택.

비용: ~$5 (gpt-5.4-mini, 1,038 × 3 호출, structured output)

사용:
  python data-team/05-enrichment/llm-scripts/build_guide_llm_domains.py
  python data-team/05-enrichment/llm-scripts/build_guide_llm_domains.py --limit 20
  python data-team/05-enrichment/llm-scripts/build_guide_llm_domains.py --n-shot 3 --extra-allowed

ENV:
  OPENAI_API_KEY (required)
  LLM_RERANK_MODEL (default: gpt-5.4-mini)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
GUIDES_DIR = REPO_ROOT / "data-team" / "01-parsing" / "kosha-guides" / "parsed"
EVAL_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "eval-data"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "guide_llm_domains.json"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")
MAX_GUIDE_TEXT_CHARS = 2000


SYSTEM_PROMPT = """\
당신은 KOSHA 산업안전 Guide의 산업 도메인 분류자입니다.
각 Guide가 어떤 산업/현장에 적용되는지 multi-label로 분류합니다.

원칙:
- closed vocabulary (제공된 후보 산업 목록) 안에서 우선 선택
- 후보에 없는 경우만 free-form 라벨 추가 (영문/한글 자유)
- multi-label: 1~5개 적절히 (지나치게 많이 채우지 말 것)
- 일반적/공통 Guide는 ["general"] 단일 라벨
- 명확히 단일 산업이면 그 산업만 선택

분류하지 마세요:
- 위험 종류 (FALL, BURN 등) — 이건 work_context이지 industry 아님
- 처벌 여부
- Guide의 품질
"""

USER_TEMPLATE = """\
[Guide 제목]
{title}

[Guide 본문 발췌 (~{n_chars}자)]
{body}

[후보 산업 목록 (closed vocabulary, 우선 선택)]
{vocabulary}

위 Guide가 적용되는 산업 도메인을 multi-label로 분류하세요.
"""

RESPONSE_SCHEMA = {
    "name": "guide_domain_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-5개의 산업 도메인 라벨. closed vocabulary 우선.",
            },
            "primary_domain": {
                "type": "string",
                "description": "domains 중 가장 핵심적인 1개",
            },
            "rationale": {
                "type": "string",
                "description": "한국어 1문장 사유",
            },
        },
        "required": ["domains", "primary_domain", "rationale"],
        "additionalProperties": False,
    },
}


def build_closed_vocabulary() -> list[str]:
    industries: set[str] = set()
    for f in sorted(EVAL_DIR.glob("synthetic_observations_v*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            ind = row.get("industry_context")
            if ind:
                industries.add(str(ind).strip())
    industries.add("general")
    return sorted(industries)


def build_guide_text(guide_data: dict) -> tuple[str, str]:
    metadata = guide_data.get("metadata") or {}
    title = str(metadata.get("title") or metadata.get("guideCode") or "")
    sections = guide_data.get("sections") or []
    body_parts: list[str] = []
    for section in sections[:3]:
        text = section.get("text") or ""
        if text:
            body_parts.append(text.strip())
        if sum(len(p) for p in body_parts) >= MAX_GUIDE_TEXT_CHARS:
            break
    body = " ".join(body_parts)[:MAX_GUIDE_TEXT_CHARS] or "(본문 없음)"
    return title, body


def load_guides(limit: int | None = None) -> list[tuple[str, dict]]:
    items: list[tuple[str, dict]] = []
    for f in sorted(GUIDES_DIR.glob("guide-*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        code = data.get("metadata", {}).get("guideCode") or f.stem
        items.append((str(code), data))
        if limit and len(items) >= limit:
            break
    return items


async def classify_one(
    client,
    *,
    model: str,
    title: str,
    body: str,
    vocabulary: list[str],
    n_shot: int,
    semaphore,
) -> dict[str, Any]:
    vocab_text = ", ".join(vocabulary)
    user_prompt = USER_TEMPLATE.format(
        title=title,
        n_chars=len(body),
        body=body,
        vocabulary=vocab_text,
    )

    async def _call():
        async with semaphore:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "developer", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_schema", "json_schema": RESPONSE_SCHEMA},
                max_completion_tokens=512,
            )
            return json.loads(response.choices[0].message.content or "{}")

    results: list[dict[str, Any]] = []
    for _ in range(n_shot):
        try:
            res = await _call()
            results.append(res)
        except Exception as exc:
            results.append({"error": str(exc), "domains": [], "primary_domain": ""})
    return aggregate_self_consistency(results)


def aggregate_self_consistency(samples: list[dict[str, Any]]) -> dict[str, Any]:
    domain_votes: Counter[str] = Counter()
    primary_votes: Counter[str] = Counter()
    n_valid = 0
    for sample in samples:
        if "error" in sample:
            continue
        n_valid += 1
        for d in sample.get("domains") or []:
            if d:
                domain_votes[str(d).strip()] += 1
        primary = sample.get("primary_domain")
        if primary:
            primary_votes[str(primary).strip()] += 1
    threshold = max(2, (len(samples) // 2) + 1)
    consensus_domains = [d for d, c in domain_votes.most_common() if c >= threshold]
    if not consensus_domains and n_valid > 0:
        consensus_domains = [domain_votes.most_common(1)[0][0]] if domain_votes else []
    primary = primary_votes.most_common(1)[0][0] if primary_votes else (
        consensus_domains[0] if consensus_domains else ""
    )
    rationale = next(
        (s.get("rationale") for s in samples if "error" not in s and s.get("rationale")),
        "",
    )
    return {
        "domains": consensus_domains,
        "primary_domain": primary,
        "rationale": rationale,
        "consistency": round(n_valid / max(1, len(samples)), 4),
        "vote_count": dict(domain_votes),
        "n_samples": len(samples),
    }


async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        return 2

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)

    vocabulary = build_closed_vocabulary()
    print(f"Closed vocabulary: {len(vocabulary)} industries (from synthetic + 'general')")

    guides = load_guides(limit=args.limit)
    if not guides:
        print(f"No guides loaded from {GUIDES_DIR}", file=sys.stderr)
        return 1
    print(f"Loaded {len(guides)} guides. Model: {args.model}. N-shot: {args.n_shot}")
    print(f"Concurrency: {args.concurrency}, total LLM calls: {len(guides) * args.n_shot}")

    semaphore = asyncio.Semaphore(args.concurrency)
    classifications: dict[str, dict] = {}
    start = time.time()

    async def _run_one(idx: int, code: str, data: dict) -> None:
        title, body = build_guide_text(data)
        result = await classify_one(
            client,
            model=args.model,
            title=title,
            body=body,
            vocabulary=vocabulary,
            n_shot=args.n_shot,
            semaphore=semaphore,
        )
        result["title"] = title
        classifications[code] = result
        if (idx + 1) % 20 == 0 or idx == 0:
            elapsed = time.time() - start
            rate = (idx + 1) / elapsed if elapsed else 0
            print(
                f"  [{idx + 1:4d}/{len(guides)}] {code:<15s} "
                f"{result['primary_domain'][:30]:<30s} "
                f"({rate:.1f}/s elapsed={elapsed:.0f}s)"
            )

    tasks = [_run_one(i, code, data) for i, (code, data) in enumerate(guides)]
    await asyncio.gather(*tasks)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "n_shot": args.n_shot,
        "guide_count": len(classifications),
        "closed_vocabulary": vocabulary,
        "classifications": classifications,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {args.output}")
    print(f"Total elapsed: {time.time() - start:.1f}s")

    domain_dist = Counter()
    for c in classifications.values():
        domain_dist[c.get("primary_domain", "unknown")] += 1
    print("\nTop 15 primary domains:")
    for domain, count in domain_dist.most_common(15):
        print(f"  {count:4d}  {domain}")
    unknown = sum(1 for c in classifications.values() if not c.get("domains"))
    print(f"\nGuides with no domain (unknown): {unknown}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="처음 N개만")
    parser.add_argument("--n-shot", type=int, default=3, help="self-consistency 호출 수")
    parser.add_argument("--concurrency", type=int, default=8, help="동시 LLM 호출")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
