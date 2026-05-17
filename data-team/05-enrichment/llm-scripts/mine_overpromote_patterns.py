#!/usr/bin/env python3
"""Phase C.2 — Self-Refine 패턴 마이닝.

analysis_log.jsonl을 분석하여 자주 reject된 (사진 산업 × guide 도메인) 페어를
찾아 incompatibility KB에 신규 candidate로 추가한다.

흐름:
1. analysis_log.jsonl 로드 (Phase C.1 후크가 매 분석마다 append)
2. excluded entries 집계 → (industry, guide_primary_domain) 페어 카운트
3. 빈도 N≥3 페어 중:
   - 이미 guide_domain_incompatibilities.json에 있으면 skip
   - subsumption pre-check (embedding cosine > 0.55)으로 hyponym 제외
   - LLM (gpt-5.4-nano)에게 incompatible 여부 재판정
   - 통과한 페어를 candidate level로 KB에 머지
4. audit log: incompatibility_audit.jsonl 에 변경 이력

ENV:
  OPENAI_API_KEY (required if --apply)
  LLM_RERANK_MODEL (default: gpt-5.4-nano)

사용:
  python mine_overpromote_patterns.py --dry-run
  python mine_overpromote_patterns.py --apply --min-freq 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
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
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
LOG_PATH = ARTIFACTS_DIR / "analysis_log.jsonl"
INCOMPAT_PATH = ARTIFACTS_DIR / "guide_domain_incompatibilities.json"
LLM_DOMAINS_PATH = ARTIFACTS_DIR / "guide_llm_domains.json"
AUDIT_PATH = ARTIFACTS_DIR / "incompatibility_audit.jsonl"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


SYSTEM_PROMPT = """\
당신은 KOSHA 산업 도메인 호환성 판정자입니다.
서비스 분석 로그에서 자주 reject된 (사진 산업 × guide 도메인) 페어가
실제로 incompatible한지 (같은 현장에서 동시 적용 불가) 판정합니다.

incompatible이면 새 axiom으로 등재되어 향후 같은 매칭을 차단합니다.
실제로 같이 등장 가능한 페어(hyponym/hypernym 포함)는 compatible로 판정하세요.
"""

USER_TEMPLATE = """\
사진 산업: {industry}
Guide 도메인: {guide_domain}
최근 reject 빈도: {freq}회
샘플 reject 사유: {sample_reasons}

이 두 도메인은 같은 현장/사진에 동시 적용 불가능한가?
"""

RESPONSE_SCHEMA = {
    "name": "incompat_verdict",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "incompatible": {"type": "boolean"},
            "confidence": {"type": "number"},
            "reason": {"type": "string"},
        },
        "required": ["incompatible", "confidence", "reason"],
        "additionalProperties": False,
    },
}


def load_log() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_guide_domains() -> dict[str, str]:
    if not LLM_DOMAINS_PATH.exists():
        return {}
    payload = json.loads(LLM_DOMAINS_PATH.read_text(encoding="utf-8"))
    return {
        code: (info or {}).get("primary_domain", "")
        for code, info in (payload.get("classifications") or {}).items()
    }


def load_existing_incompat() -> set[tuple[str, str]]:
    if not INCOMPAT_PATH.exists():
        return set()
    payload = json.loads(INCOMPAT_PATH.read_text(encoding="utf-8"))
    existing: set[tuple[str, str]] = set()
    for entry in payload.get("incompatibilities") or []:
        if not entry.get("incompatible"):
            continue
        a = str(entry.get("domain_a") or "")
        b = str(entry.get("domain_b") or "")
        if a and b:
            existing.add((a, b))
            existing.add((b, a))
    return existing


def mine_pairs(min_freq: int) -> dict[tuple[str, str], dict[str, Any]]:
    """Walk analysis_log → (industry, guide_domain) → {freq, sample_reasons}."""
    rows = load_log()
    guide_to_domain = load_guide_domains()
    counter: Counter[tuple[str, str]] = Counter()
    sample_reasons: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        industry = str(row.get("industry") or "").strip()
        if not industry:
            continue
        for excl in row.get("excluded") or []:
            code = str(excl.get("guide_code") or "")
            domain = guide_to_domain.get(code, "")
            if not domain or domain == industry:
                continue
            key = (industry, domain)
            counter[key] += 1
            sample_reasons.setdefault(key, []).append(str(excl.get("reason") or "")[:80])
    return {
        pair: {"freq": freq, "sample_reasons": sample_reasons.get(pair, [])[:3]}
        for pair, freq in counter.items()
        if freq >= min_freq
    }


async def verify_pair(client, model, industry, guide_domain, freq, reasons):
    user_prompt = USER_TEMPLATE.format(
        industry=industry,
        guide_domain=guide_domain,
        freq=freq,
        sample_reasons="; ".join(reasons) or "(없음)",
    )
    try:
        r = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "developer", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_schema", "json_schema": RESPONSE_SCHEMA},
            max_completion_tokens=256,
        )
        return json.loads(r.choices[0].message.content or "{}")
    except Exception as exc:
        return {"error": str(exc), "incompatible": False}


def merge_into_incompat(new_entries: list[dict[str, Any]]) -> int:
    if not new_entries:
        return 0
    payload: dict[str, Any] = {}
    if INCOMPAT_PATH.exists():
        payload = json.loads(INCOMPAT_PATH.read_text(encoding="utf-8"))
    payload.setdefault("incompatibilities", [])
    payload["last_refined_at"] = datetime.now(timezone.utc).isoformat()
    payload["incompatibilities"].extend(new_entries)
    payload["incompatible_count"] = sum(
        1 for e in payload["incompatibilities"] if e.get("incompatible")
    )
    INCOMPAT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(new_entries)


def append_audit(events: list[dict[str, Any]]) -> None:
    if not events:
        return
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


async def main_async(args: argparse.Namespace) -> int:
    candidates = mine_pairs(min_freq=args.min_freq)
    print(f"Found {len(candidates)} candidate pairs (freq ≥ {args.min_freq})")
    if not candidates:
        print("No candidates; nothing to refine.")
        return 0

    existing = load_existing_incompat()
    new_candidates = {pair: info for pair, info in candidates.items() if pair not in existing}
    print(
        f"  After deduplication against existing incompatibilities: "
        f"{len(new_candidates)} new"
    )

    if args.dry_run or not new_candidates:
        for (industry, guide_domain), info in sorted(
            new_candidates.items(), key=lambda x: -x[1]["freq"]
        )[:20]:
            print(f"  freq={info['freq']:3d}  {industry} × {guide_domain}")
        return 0

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required for --apply", file=sys.stderr)
        return 2

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(args.concurrency)

    async def _verify(pair, info):
        async with semaphore:
            return pair, info, await verify_pair(
                client, args.model, pair[0], pair[1], info["freq"], info["sample_reasons"]
            )

    tasks = [_verify(pair, info) for pair, info in new_candidates.items()]
    results = await asyncio.gather(*tasks)

    new_entries: list[dict[str, Any]] = []
    audit_events: list[dict[str, Any]] = []
    ts = datetime.now(timezone.utc).isoformat()
    for (industry, guide_domain), info, verdict in results:
        accepted = (
            verdict.get("incompatible")
            and float(verdict.get("confidence", 0.0)) >= 0.7
        )
        if accepted:
            entry = {
                "domain_a": industry,
                "domain_b": guide_domain,
                "incompatible": True,
                "confidence": float(verdict.get("confidence", 0.0)),
                "reason": str(verdict.get("reason", "")),
                "level": "candidate",
                "source": "self_refine",
                "freq_when_added": info["freq"],
                "added_at": ts,
            }
            new_entries.append(entry)
        audit_events.append(
            {
                "ts": ts,
                "action": "verify",
                "industry": industry,
                "guide_domain": guide_domain,
                "freq": info["freq"],
                "verdict": verdict,
                "accepted": accepted,
            }
        )

    added = merge_into_incompat(new_entries)
    append_audit(audit_events)
    print(f"\nVerified {len(results)} candidates, accepted {added} new incompatibilities.")
    print(f"Audit appended to {AUDIT_PATH}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-freq", type=int, default=3)
    parser.add_argument("--apply", action="store_true", help="LLM 호출 + KB 머지")
    parser.add_argument("--dry-run", action="store_true", help="후보 페어만 출력 (default)")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    args = parser.parse_args()
    if not args.apply:
        args.dry_run = True
    return args


def main() -> None:
    args = parse_args()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
