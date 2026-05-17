#!/usr/bin/env python3
"""F.3.2 — Missing Disjoint Axiom Miner.

F.3.0 (reject_reason_classified.jsonl)에서 axiom_missing으로 분류된
(industry_en × guide_primary_domain_en) pair를 추출하고, freq ≥ min-freq만
LLM verify → 통과한 것을 candidate level로 guide_domain_incompatibilities.json에 머지.

기존 mine_overpromote_patterns.py와의 차이:
- input: analysis_log 직접 mining 대신 F.3.0 분류 결과 사용 (정제된 신호)
- KB가 이미 EN-normalized (C 단계 후) — translate step 불요
- 4-Gate 중 Gate 2 (LLM verify) 본 스크립트, Gate 4 (asymmetric trust)는 'level':'candidate'로 머지하고
  vetted promotion은 기존 promote_incompatibilities.py가 50회 사용 후 자동
- Gate 1 (embedding pre-filter)과 Gate 3 (regression hard-stop)은 후속 sub-phase

ENV:
  OPENAI_API_KEY      (--apply 시 필요)
  LLM_RERANK_MODEL    (default: gpt-5.4-nano)

사용:
  python mine_missing_axioms.py --dry-run                  # 후보만 출력
  python mine_missing_axioms.py --apply --min-freq 5       # LLM verify + KB 머지
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


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("Cannot locate repo root")


ROOT = find_root()
ARTIFACTS = ROOT / "data-team/05-enrichment/runtime-artifacts"
CLASSIFIED_PATH = ARTIFACTS / "reject_reason_classified.jsonl"
INCOMPAT_PATH = ARTIFACTS / "guide_domain_incompatibilities.json"
AUDIT_PATH = ARTIFACTS / "incompatibility_audit.jsonl"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


SYSTEM_PROMPT = """\
당신은 KOSHA 산업 도메인 호환성 판정자입니다.
서비스 분석 로그에서 자주 reject된 (사진 산업 × Guide 도메인) 페어가
실제로 incompatible한지 (같은 사진/현장에서 동시 적용 불가) 판정합니다.

incompatible이면 새 disjoint axiom으로 등재되어 향후 같은 매칭을 차단합니다.
실제로 같이 등장 가능한 페어(hyponym/hypernym/현장 병행 포함)는 compatible로 판정하세요.
산업명은 EN UPPER_SNAKE_CASE enum입니다.
"""

USER_TEMPLATE = """\
사진 산업 (industry_en): {industry}
Guide 도메인 (guide_primary_domain_en): {guide_domain}
F.3.0 reject 빈도: {freq}회
샘플 reject 사유 (한국어 narrative): {sample_reasons}

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


def load_classified() -> list[dict[str, Any]]:
    if not CLASSIFIED_PATH.exists():
        print(f"ERROR: F.3.0 결과 없음: {CLASSIFIED_PATH}", file=sys.stderr)
        return []
    rows = []
    for line in CLASSIFIED_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_existing_pairs() -> set[tuple[str, str]]:
    """KB에 이미 incompatible로 등재된 pair (EN-normalized assumed, C 단계 후)."""
    if not INCOMPAT_PATH.exists():
        return set()
    payload = json.loads(INCOMPAT_PATH.read_text(encoding="utf-8"))
    existing: set[tuple[str, str]] = set()
    for e in payload.get("incompatibilities") or []:
        if not e.get("incompatible"):
            continue
        a = str(e.get("domain_a") or "").strip()
        b = str(e.get("domain_b") or "").strip()
        if a and b:
            existing.add((a, b))
            existing.add((b, a))
    return existing


def mine_candidates(min_freq: int) -> list[dict[str, Any]]:
    """F.3.0 분류 결과에서 axiom_missing pair freq 집계 + KB 미등재 필터."""
    rows = load_classified()
    print(f"loaded {len(rows)} F.3.0 entries")
    pair_freq: Counter = Counter()
    sample_reasons: dict[tuple[str, str], list[str]] = {}
    for e in rows:
        if e.get("reason_category") != "axiom_missing":
            continue
        ind = (e.get("industry_en") or "").strip()
        dom = (e.get("guide_primary_domain_en") or "").strip()
        if not ind or not dom or ind == dom:
            continue
        key = (ind, dom)
        pair_freq[key] += 1
        if len(sample_reasons.setdefault(key, [])) < 3:
            sample_reasons[key].append(str(e.get("original_reason") or "")[:200])
    print(f"  unique axiom_missing pairs: {len(pair_freq)}")
    existing = load_existing_pairs()
    print(f"  KB existing pairs (incompatible): {len(existing) // 2}")
    candidates = []
    for pair, freq in pair_freq.most_common():
        if freq < min_freq:
            continue
        if pair in existing:
            continue
        candidates.append({
            "industry": pair[0],
            "guide_domain": pair[1],
            "freq": freq,
            "sample_reasons": sample_reasons.get(pair, []),
        })
    print(f"  candidates after freq ≥ {min_freq} + KB dedup: {len(candidates)}")
    return candidates


async def verify_pair(client, model: str, c: dict[str, Any]) -> dict[str, Any]:
    user_prompt = USER_TEMPLATE.format(
        industry=c["industry"],
        guide_domain=c["guide_domain"],
        freq=c["freq"],
        sample_reasons="; ".join(c["sample_reasons"]) or "(없음)",
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


def merge_candidates(new_entries: list[dict[str, Any]]) -> int:
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
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


async def main_async(args: argparse.Namespace) -> int:
    candidates = mine_candidates(args.min_freq)
    if not candidates:
        print("\nNo candidates after filtering.")
        return 0
    print("\nTop 20 candidates (freq desc):")
    for c in candidates[:20]:
        print(f"  freq={c['freq']:4d}  {c['industry']:30s} × {c['guide_domain']}")

    if args.dry_run:
        print("\nDRY mode — no LLM verify, no KB merge. Re-run with --apply.")
        return 0

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Try load from backend .env
        env_path = ROOT / "serving-team/08-app/backend/.env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    os.environ["OPENAI_API_KEY"] = api_key
                    break
    if not api_key:
        print("ERROR: OPENAI_API_KEY missing", file=sys.stderr)
        return 2

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(args.concurrency)

    async def _run(c):
        async with semaphore:
            verdict = await verify_pair(client, args.model, c)
            return c, verdict

    print(f"\nVerifying {len(candidates)} candidates with {args.model} (concurrency={args.concurrency})...")
    results = await asyncio.gather(*[_run(c) for c in candidates])

    new_entries: list[dict[str, Any]] = []
    audit_events: list[dict[str, Any]] = []
    ts = datetime.now(timezone.utc).isoformat()
    accepted = 0
    for c, verdict in results:
        is_incompat = bool(verdict.get("incompatible"))
        conf = float(verdict.get("confidence") or 0.0)
        ok = is_incompat and conf >= 0.7
        if ok:
            new_entries.append({
                "domain_a": c["industry"],
                "domain_b": c["guide_domain"],
                "incompatible": True,
                "confidence": conf,
                "reason": str(verdict.get("reason") or ""),
                "level": "candidate",
                "source": "f32_axiom_miner",
                "freq_when_added": c["freq"],
                "added_at": ts,
            })
            accepted += 1
        audit_events.append({
            "ts": ts,
            "action": "verify",
            "script": "mine_missing_axioms.py",
            "industry": c["industry"],
            "guide_domain": c["guide_domain"],
            "freq": c["freq"],
            "verdict": verdict,
            "accepted": ok,
        })

    if not args.dry_apply:
        added = merge_candidates(new_entries)
        append_audit(audit_events)
        print(f"\nVerified {len(results)} candidates")
        print(f"  accepted (incompat=True AND conf≥0.7): {accepted}")
        print(f"  merged to KB as 'level=candidate': {added}")
        print(f"  audit appended to {AUDIT_PATH.name}")
    else:
        print(f"\nDRY-APPLY: would accept {accepted} / {len(results)} (KB not modified)")
        for entry in new_entries[:15]:
            print(f"  conf={entry['confidence']:.2f}  freq={entry['freq_when_added']}  {entry['domain_a']} × {entry['domain_b']}")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--min-freq", type=int, default=5)
    p.add_argument("--apply", action="store_true", help="LLM verify + KB merge")
    p.add_argument("--dry-run", action="store_true", help="후보만 출력 (default)")
    p.add_argument("--dry-apply", action="store_true",
                   help="LLM verify는 하지만 KB merge는 안 함 (test)")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--model", type=str, default=DEFAULT_MODEL)
    args = p.parse_args()
    if not args.apply and not args.dry_apply:
        args.dry_run = True
    return args


def main() -> None:
    args = parse_args()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
