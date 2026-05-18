#!/usr/bin/env python3
"""F.2 Day 3-4 — Enrich SHE catalog OTHER fields with Sonnet 4.6.

PG she_catalog 1,616 SHE 중 ppe_state='OTHER' 또는 environmental='OTHER' 인 행
(약 1,328건)에 대해 Sonnet 4.6이 catalog v3.3 vocabulary 내에서 적합한 코드를 제안.

원칙 (보수적):
1. OTHER가 아닌 필드는 절대 변경하지 않음 (보존)
2. 추출 코드는 반드시 catalog v3.3 vocabulary에 존재 (자동 검증)
3. confidence >= 0.85 (--min-conf로 조정)
4. Sonnet이 자신 없으면 'OTHER' 그대로 반환 가능 (보수성 OK)

ENV:
  ANTHROPIC_API_KEY 필수
  DATABASE_URL (PG)

사용:
  python enrich_she_with_sonnet.py --dry-run                # count + cost estimate
  python enrich_she_with_sonnet.py --apply --max-residual 20  # small sample (~$0.10)
  python enrich_she_with_sonnet.py --apply                  # full (~$6, ~7분)
  python enrich_she_with_sonnet.py --apply --min-conf 0.90  # stricter
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


def find_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = find_root()
sys.path.insert(0, str(REPO_ROOT / "serving-team" / "08-app" / "backend"))

CATALOG_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
AUDIT_PATH = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "she_enrichment_audit.jsonl"

SONNET_MODEL = "claude-sonnet-4-6"
SONNET_MAX_TOKENS = 400
SONNET_CONCURRENCY = 4
DEFAULT_MIN_CONFIDENCE = 0.85


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def get_axis_vocabulary(catalog: dict) -> tuple[set[str], set[str]]:
    axes = catalog.get("axes", {})
    ppe = set((axes.get("ppe_state") or {}).get("codes", {}).keys())
    env = set((axes.get("environmental") or {}).get("codes", {}).keys())
    return ppe, env


SONNET_SYSTEM = """\
당신은 KOSHA 산업안전 SHE pattern enrichment 전문가입니다.
주어진 SHE pattern의 'OTHER'로 표시된 ppe_state / environmental 필드에 대해
catalog vocabulary 내에서 가장 적합한 코드를 제안합니다.

원칙:
1. 자신 없으면 'OTHER' 그대로 유지 (보수성 우선)
2. 추출 코드는 반드시 vocabulary 내에 있어야 함
3. SHE의 work_context + accident_type + hazardous_agent 조합과 의미적으로 일치해야 채택
4. ppe_state와 environmental은 독립적 — 한쪽만 채워도 됨
5. 같은 SHE에 여러 PPE 또는 환경 요소가 있어도 가장 핵심적인 1개만 선택 (catalog single-value)
"""


def make_user_prompt(she: dict, vocab_ppe: set[str], vocab_env: set[str]) -> str:
    features = she.get("features", {})
    return f"""\
SHE pattern: {she['she_id']} - {she['name']}
work_context:    {features.get('work_context', '?')}
accident_type:   {features.get('accident_type', '?')}
hazardous_agent: {features.get('hazardous_agent', 'OTHER')}
agent_state:     {features.get('agent_state', 'OTHER')}
work_activity:   {features.get('work_activity', 'OTHER')}
temporal_stage:  {features.get('temporal_stage', 'OTHER')}
현재 ppe_state:      {features.get('ppe_state', 'OTHER')}
현재 environmental: {features.get('environmental', 'OTHER')}

catalog ppe_state vocabulary ({len(vocab_ppe)} codes):
{', '.join(sorted(vocab_ppe))}

catalog environmental vocabulary ({len(vocab_env)} codes):
{', '.join(sorted(vocab_env))}

이 SHE pattern에 가장 적합한 ppe_state와 environmental code는?
(OTHER로 자신 없으면 그대로 유지하세요)
"""


def make_sonnet_tool(vocab_ppe: set[str], vocab_env: set[str]) -> dict:
    """Tool schema with enum constraints (vocabulary + 'OTHER')."""
    return {
        "name": "enrich_she",
        "description": "Propose ppe_state and environmental codes for a SHE pattern, from catalog vocabulary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ppe_state": {
                    "type": "string",
                    "enum": sorted(vocab_ppe | {"OTHER"}),
                    "description": "ppe_state code from catalog (or 'OTHER' if uncertain)",
                },
                "environmental": {
                    "type": "string",
                    "enum": sorted(vocab_env | {"OTHER"}),
                    "description": "environmental code from catalog (or 'OTHER' if uncertain)",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "정확도 confidence (0.85 이상만 적용됨)",
                },
                "reason": {"type": "string", "description": "1-2 문장 한국어"},
            },
            "required": ["ppe_state", "environmental", "confidence", "reason"],
        },
    }


async def enrich_one(client, she: dict, vocab_ppe: set[str], vocab_env: set[str], tool: dict) -> dict:
    prompt = make_user_prompt(she, vocab_ppe, vocab_env)
    try:
        msg = await client.messages.create(
            model=SONNET_MODEL,
            max_tokens=SONNET_MAX_TOKENS,
            temperature=0,
            system=SONNET_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            tools=[tool],
            tool_choice={"type": "tool", "name": "enrich_she"},
        )
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "enrich_she":
                return dict(block.input)
        return {"error": "no tool_use block"}
    except Exception as exc:
        return {"error": str(exc)}


def fetch_she_with_others(db) -> list[dict]:
    from sqlalchemy import text as sql_text

    rows = db.execute(sql_text("""
        SELECT she_id, name, features
        FROM she_catalog
        WHERE status IN ('approved_auto','approved_manual')
          AND superseded_by IS NULL
          AND (features->>'ppe_state' = 'OTHER' OR features->>'environmental' = 'OTHER')
        ORDER BY she_id
    """)).fetchall()
    out = []
    for row in rows:
        she_id, name, features = row
        if isinstance(features, str):
            features = json.loads(features)
        out.append({"she_id": she_id, "name": name, "features": features})
    return out


def apply_updates(db, updates: list[tuple[str, dict, dict]]) -> int:
    """Apply per-row UPDATE: jsonb_set for ppe_state / environmental.

    updates = [(she_id, new_features, original_features), ...]
    Returns updated count.
    """
    from sqlalchemy import text as sql_text

    n = 0
    for she_id, new_feat, _orig in updates:
        new_ppe = new_feat.get("ppe_state")
        new_env = new_feat.get("environmental")
        # Use CAST(... AS TEXT) — sqlalchemy bind format conflicts with PG ::text shorthand.
        # to_jsonb wraps a TEXT into JSON string scalar (e.g., "GLOVES_MISSING").
        db.execute(
            sql_text("""
                UPDATE she_catalog
                SET features = jsonb_set(
                    jsonb_set(features, '{ppe_state}', to_jsonb(CAST(:ppe AS TEXT))),
                    '{environmental}',
                    to_jsonb(CAST(:env AS TEXT))
                )
                WHERE she_id = :sid
            """),
            {"sid": she_id, "ppe": new_ppe, "env": new_env},
        )
        n += 1
    db.commit()
    return n


def append_audit(updates: list[tuple[str, dict, dict]], rejections: list[dict]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for she_id, new_feat, orig in updates:
            f.write(json.dumps({
                "ts": ts, "action": "applied", "she_id": she_id,
                "ppe_state_before": orig.get("ppe_state"), "ppe_state_after": new_feat.get("ppe_state"),
                "environmental_before": orig.get("environmental"), "environmental_after": new_feat.get("environmental"),
            }, ensure_ascii=False) + "\n")
        for r in rejections:
            f.write(json.dumps({"ts": ts, "action": "rejected", **r}, ensure_ascii=False) + "\n")


async def main_async(args: argparse.Namespace) -> int:
    from app.db.database import SessionLocal

    catalog = load_catalog()
    vocab_ppe, vocab_env = get_axis_vocabulary(catalog)
    print(f"Catalog v{catalog.get('version')} vocabulary:")
    print(f"  ppe_state    : {len(vocab_ppe)} codes")
    print(f"  environmental: {len(vocab_env)} codes")
    print()

    db = SessionLocal()
    try:
        sheets = fetch_she_with_others(db)
        print(f"SHE rows with OTHER in ppe_state or environmental: {len(sheets)}")

        # Cost estimate: per-call ~750 input + 150 output tokens
        # Sonnet 4.6: $3/1M input, $15/1M output → per-call ~$0.005
        est_cost = len(sheets) * 0.005
        print(f"Estimated Sonnet 4.6 cost: ~${est_cost:.2f}")
        print(f"Estimated time (concurrency {SONNET_CONCURRENCY}): ~{len(sheets) // (SONNET_CONCURRENCY * 60)}-{len(sheets) // (SONNET_CONCURRENCY * 30)}분")
        print()

        if args.max_residual and len(sheets) > args.max_residual:
            sheets = sheets[:args.max_residual]
            print(f"Capped to {args.max_residual} for this run.")
            print()

        if args.dry_run:
            print("[dry-run] No LLM calls. Preview first 3 SHEs that would be processed:")
            for s in sheets[:3]:
                ppe = s["features"].get("ppe_state")
                env = s["features"].get("environmental")
                print(f"  {s['she_id']:35s}  ppe={ppe!r:25s} env={env!r}")
            return 0

        # Apply
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY required", file=sys.stderr)
            return 2
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            print("ERROR: anthropic not installed", file=sys.stderr)
            return 2

        client = AsyncAnthropic(api_key=api_key)
        tool = make_sonnet_tool(vocab_ppe, vocab_env)
        sem = asyncio.Semaphore(SONNET_CONCURRENCY)

        async def _work(she):
            async with sem:
                return she, await enrich_one(client, she, vocab_ppe, vocab_env, tool)

        print(f"\n[Sonnet 4.6] processing {len(sheets)} SHE rows...")
        results = await asyncio.gather(*[_work(s) for s in sheets])

        # Filter + build updates
        updates: list[tuple[str, dict, dict]] = []
        rejections: list[dict] = []
        action_counter: Counter = Counter()
        errors = 0

        for she, verdict in results:
            orig = she["features"]
            if verdict.get("error"):
                errors += 1
                rejections.append({"she_id": she["she_id"], "reason": "sonnet_error", "error": verdict["error"]})
                continue
            conf = float(verdict.get("confidence", 0))
            new_ppe = verdict.get("ppe_state", "OTHER")
            new_env = verdict.get("environmental", "OTHER")

            if conf < args.min_conf:
                rejections.append({
                    "she_id": she["she_id"], "reason": "low_confidence",
                    "confidence": conf, "proposed_ppe": new_ppe, "proposed_env": new_env,
                })
                action_counter["low_conf"] += 1
                continue

            new_features = dict(orig)
            ppe_changed = (orig.get("ppe_state") == "OTHER" and new_ppe != "OTHER" and new_ppe in vocab_ppe)
            env_changed = (orig.get("environmental") == "OTHER" and new_env != "OTHER" and new_env in vocab_env)

            if ppe_changed:
                new_features["ppe_state"] = new_ppe
            if env_changed:
                new_features["environmental"] = new_env

            if not (ppe_changed or env_changed):
                # Sonnet didn't propose change (or proposed OTHER) — no-op
                action_counter["kept_other"] += 1
                rejections.append({
                    "she_id": she["she_id"], "reason": "no_change",
                    "confidence": conf, "proposed_ppe": new_ppe, "proposed_env": new_env,
                    "reason_text": verdict.get("reason", "")[:200],
                })
                continue

            updates.append((she["she_id"], new_features, orig))
            if ppe_changed and env_changed:
                action_counter["both_changed"] += 1
            elif ppe_changed:
                action_counter["ppe_changed"] += 1
            else:
                action_counter["env_changed"] += 1

        print()
        print(f"Results:")
        print(f"  processed       : {len(results)}")
        print(f"  applied updates : {len(updates)}")
        print(f"  rejected (low conf or no-change): {len(rejections)}")
        print(f"  errors          : {errors}")
        print(f"  action breakdown:")
        for k, v in action_counter.most_common():
            print(f"    {k:20s}: {v}")

        # Sample updates
        print()
        print(f"  Sample updates (top 5):")
        for she_id, new_feat, orig in updates[:5]:
            ppe_diff = f"{orig.get('ppe_state')} → {new_feat.get('ppe_state')}" if orig.get('ppe_state') != new_feat.get('ppe_state') else "(same)"
            env_diff = f"{orig.get('environmental')} → {new_feat.get('environmental')}" if orig.get('environmental') != new_feat.get('environmental') else "(same)"
            print(f"    {she_id:35s}  ppe: {ppe_diff:50s}  env: {env_diff}")

        if not updates:
            print("\nNo updates to apply.")
            append_audit([], rejections)
            return 0

        # Apply to DB
        print(f"\n[PG UPDATE] applying {len(updates)} changes to she_catalog...")
        n = apply_updates(db, updates)
        print(f"  updated {n} rows")
        append_audit(updates, rejections)
        print(f"  audit appended: {AUDIT_PATH.relative_to(REPO_ROOT)}")

        print()
        print("⚠️  Gate 3 regression 필수:")
        print("    make f1-regression")
        return 0
    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="count + cost preview only")
    p.add_argument("--apply", action="store_true", help="run Sonnet + apply PG UPDATE")
    p.add_argument("--max-residual", type=int, default=0, help="cap to N rows (test / cost control)")
    p.add_argument("--min-conf", type=float, default=DEFAULT_MIN_CONFIDENCE)
    args = p.parse_args()
    if not (args.dry_run or args.apply):
        args.dry_run = True
    return args


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
