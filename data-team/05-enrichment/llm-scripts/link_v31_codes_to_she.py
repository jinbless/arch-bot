#!/usr/bin/env python3
"""F.2 Day 5 — Catalog v3.1 origin codes를 SHE pattern에 연계 (기술 부채 해소).

문제: v3.1 patch가 94 신규 main codes를 catalog에 추가했지만 SHE patterns에 미연계.
       → production traffic이 이 codes 매핑 후 downstream linkage 없어 false_negative.

해결: 각 v3.1 code에 대해 Sonnet 4.6이 현실적 SHE pattern을 생성 → PG INSERT.
- 입력: catalog v3.3의 _source="f1_recovery_sonnet_4_6" codes (= v3.1 origin)
- 처리: Sonnet 4.6로 8-axis SHE + visual_triggers 제안
- 적용: confidence >= 0.85 시 PG INSERT (status='approved_auto')
- audit: v31_codes_she_link_audit.jsonl

기존 패턴 재사용:
- bootstrap_she_from_synthetic.py의 PG INSERT SQL (upsert_pg)
- enrich_she_with_sonnet.py의 Sonnet async pattern

ENV: ANTHROPIC_API_KEY, DATABASE_URL

사용:
  python link_v31_codes_to_she.py --dry-run                # count + cost preview
  python link_v31_codes_to_she.py --apply --max-codes 5    # small sample (~$0.10)
  python link_v31_codes_to_she.py --apply                  # full (~$2, ~3분)
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
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
AUDIT_PATH = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "v31_codes_she_link_audit.jsonl"

SONNET_MODEL = "claude-sonnet-4-6"
SONNET_MAX_TOKENS = 600
SONNET_CONCURRENCY = 4
DEFAULT_MIN_CONFIDENCE = 0.80  # Day 5는 SHE 신규 생성이라 Day 3-4(0.85)보다 약간 완화

# SHE-only axes (not in catalog v3.3 axes)
DEFAULT_AGENT_STATES = ["OTHER", "LIVE_VOLTAGE", "FLAMMABLE_EXPOSED", "MOVING_PART", "SHARP_EDGE"]
DEFAULT_WORK_ACTIVITIES = ["OTHER", "WELDING", "CLEANING", "LIFTING", "MAINTENANCE", "INSPECTION", "ASSEMBLY"]
DEFAULT_TEMPORAL = ["DURING_WORK", "BEFORE_WORK", "AFTER_WORK", "EMERGENCY"]


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def get_axis_vocabularies(catalog: dict) -> dict[str, list[str]]:
    out = {}
    for axis_name in ("accident_type", "hazardous_agent", "work_context", "ppe_state", "environmental"):
        axis = catalog.get("axes", {}).get(axis_name, {})
        out[axis_name] = sorted((axis.get("codes") or {}).keys())
    return out


def filter_v31_origin_codes(catalog: dict) -> list[dict]:
    """Return [{axis, code, label, confidence}] for v3.1 origin codes."""
    out = []
    for axis_name, axis_def in catalog.get("axes", {}).items():
        for code, code_def in (axis_def.get("codes") or {}).items():
            if isinstance(code_def, dict) and code_def.get("_source") == "f1_recovery_sonnet_4_6":
                out.append({
                    "axis": axis_name,
                    "code": code,
                    "label": code_def.get("label", code),
                    "_confidence": code_def.get("_confidence"),
                })
    return out


SONNET_SYSTEM = """\
당신은 KOSHA 산업안전 SHE pattern designer입니다.
주어진 catalog code에 대해, 그것을 포함하는 현실적 SHE pattern 1개를 생성합니다.

SHE pattern = 8 axis 조합 + visual_triggers (한국어 시각 단서).

원칙:
1. **주어진 code는 반드시 해당 axis에 포함** (target_axis = target_code 강제)
2. 다른 7 axis는 catalog vocabulary 내에서 의미적으로 일치하는 코드 선택
3. SHE-only axes (work_activity, agent_state, temporal_stage)는 일반 enum 사용
4. visual_triggers: 한국어 단서 3-5개 (Vision LLM이 사진에서 식별할 수 있는 것)
5. broadness_score: 0.5 (구체) ~ 0.8 (일반)
6. confidence < 0.85 시 'OTHER' fallback 또는 부분 채택 가능
"""


def make_user_prompt(code_info: dict, vocabs: dict[str, list[str]]) -> str:
    axis = code_info["axis"]
    code = code_info["code"]
    label = code_info["label"]

    def fmt_vocab(name: str) -> str:
        vocab = vocabs.get(name, [])
        return f"  {name} ({len(vocab)}): {', '.join(vocab[:60])}{'...' if len(vocab) > 60 else ''}"

    return f"""\
target_axis: {axis}
target_code: {code}
target_label: {label!r}

이 code를 {axis} axis에 포함하는 현실적 SHE pattern 1개를 생성하세요.

Catalog vocabulary (선택 가능):
{fmt_vocab('accident_type')}
{fmt_vocab('hazardous_agent')}
{fmt_vocab('work_context')}
{fmt_vocab('ppe_state')}
{fmt_vocab('environmental')}

SHE-only axes (대표 enum):
  work_activity: {DEFAULT_WORK_ACTIVITIES}
  agent_state: {DEFAULT_AGENT_STATES}
  temporal_stage: {DEFAULT_TEMPORAL}

조건: features의 {axis} 필드는 반드시 '{code}'여야 함.
"""


SONNET_TOOL = {
    "name": "generate_she",
    "description": "Generate one realistic SHE pattern that includes the given catalog code.",
    "input_schema": {
        "type": "object",
        "properties": {
            "work_activity": {"type": "string"},
            "work_context": {"type": "string"},
            "hazardous_agent": {"type": "string"},
            "accident_type": {"type": "string"},
            "agent_state": {"type": "string"},
            "ppe_state": {"type": "string"},
            "environmental": {"type": "string"},
            "temporal_stage": {"type": "string"},
            "visual_triggers": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 5,
            },
            "broadness_score": {"type": "number", "minimum": 0.3, "maximum": 0.9},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "rationale": {"type": "string"},
        },
        "required": [
            "work_activity", "work_context", "hazardous_agent", "accident_type",
            "agent_state", "ppe_state", "environmental", "temporal_stage",
            "visual_triggers", "broadness_score", "confidence", "rationale",
        ],
    },
}


async def propose_she(client, code_info: dict, vocabs: dict) -> dict:
    prompt = make_user_prompt(code_info, vocabs)
    try:
        msg = await client.messages.create(
            model=SONNET_MODEL,
            max_tokens=SONNET_MAX_TOKENS,
            temperature=0,
            system=SONNET_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            tools=[SONNET_TOOL],
            tool_choice={"type": "tool", "name": "generate_she"},
        )
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "generate_she":
                return dict(block.input)
        return {"error": "no tool_use block"}
    except Exception as exc:
        return {"error": str(exc)}


def make_she_id(features: dict, code: str) -> str:
    work_ctx = (features.get("work_context") or "OTHER")
    work_ctx_clean = re.sub(r"[^A-Z0-9]", "", work_ctx.upper())[:14]
    payload = json.dumps(features, sort_keys=True, ensure_ascii=False) + "|f2-day5|" + code
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]
    return f"SHE-{work_ctx_clean}-{h}"


def validate_and_sanitize(features: dict, target_axis: str, target_code: str, valid_all: dict[str, set[str]]) -> tuple[bool, str, dict, list[str]]:
    """Strict: target_axis = target_code. Relaxed: invalid other axes → 'OTHER' fallback.

    Returns (ok, reason, sanitized_features, sanitization_notes).
    Only target_axis violation is fatal.
    """
    if features.get(target_axis) != target_code:
        return False, f"target axis '{target_axis}' is {features.get(target_axis)!r} not {target_code!r}", features, []

    notes = []
    sanitized = dict(features)
    for axis in ("accident_type", "hazardous_agent", "work_context", "ppe_state", "environmental"):
        if axis == target_axis:
            continue  # already validated above
        v = sanitized.get(axis, "OTHER")
        if v == "OTHER":
            continue
        if v not in valid_all[axis]:
            notes.append(f"{axis}={v!r} not in vocab → OTHER")
            sanitized[axis] = "OTHER"
    return True, "ok", sanitized, notes


DEFAULT_STATUS = "pending_review"  # Day 5 회고: approved_auto는 matcher 손상 (she_accuracy -39.5%p)
                                    # pending_review는 matcher 제외 (status filter), 수동 승격 후 활성화


def build_she_row(code_info: dict, verdict: dict, status: str = DEFAULT_STATUS) -> dict:
    features = {
        "work_activity": verdict.get("work_activity", "OTHER"),
        "work_context": verdict.get("work_context", "OTHER"),
        "hazardous_agent": verdict.get("hazardous_agent", "OTHER"),
        "accident_type": verdict.get("accident_type", "OTHER"),
        "agent_state": verdict.get("agent_state", "OTHER"),
        "ppe_state": verdict.get("ppe_state", "OTHER"),
        "environmental": verdict.get("environmental", "OTHER"),
        "temporal_stage": verdict.get("temporal_stage", "DURING_WORK"),
    }
    # Force target axis = target code
    features[code_info["axis"]] = code_info["code"]
    she_id = make_she_id(features, code_info["code"])
    name = f"{features['work_context']} {features['accident_type']} pattern (F.2 v3.1 link {code_info['code']})"
    return {
        "she_id": she_id,
        "name": name,
        "name_pattern": f"{features['work_context']} {features['accident_type']}",
        "features": features,
        "industry_hints": [],
        "visual_triggers": list(verdict.get("visual_triggers") or [])[:5],
        "rationale": (verdict.get("rationale") or "")[:500],
        "status": status,  # Default: pending_review (matcher 제외, 수동 승격 필요)
        "broadness_score": float(verdict.get("broadness_score", 0.6)),
        "source_model": SONNET_MODEL,
        "source_prompt_hash": hashlib.sha256(("f2_day5_v31_link_" + code_info["code"]).encode()).hexdigest()[:16],
        "source_sr_ids": [],
        "notes": f"F.2 Day 5 link_v31_codes — target {code_info['axis']}={code_info['code']}",
    }


def upsert_she(db, rows: list[dict]) -> int:
    from sqlalchemy import text

    n = 0
    for row in rows:
        db.execute(
            text("""
                INSERT INTO she_catalog (
                    she_id, name, name_pattern, features, industry_hints, visual_triggers, rationale,
                    status, broadness_score, source_model, source_prompt_hash,
                    source_sr_ids, notes
                )
                VALUES (
                    :she_id, :name, :name_pattern,
                    CAST(:features AS jsonb), CAST(:industry_hints AS jsonb),
                    CAST(:visual_triggers AS jsonb), :rationale,
                    :status, :broadness_score, :source_model, :source_prompt_hash,
                    CAST(:source_sr_ids AS jsonb), :notes
                )
                ON CONFLICT (she_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    features = EXCLUDED.features,
                    visual_triggers = EXCLUDED.visual_triggers,
                    rationale = EXCLUDED.rationale,
                    status = EXCLUDED.status,
                    broadness_score = EXCLUDED.broadness_score,
                    notes = EXCLUDED.notes
            """),
            {
                **row,
                "features": json.dumps(row["features"], ensure_ascii=False),
                "industry_hints": json.dumps(row["industry_hints"], ensure_ascii=False),
                "visual_triggers": json.dumps(row["visual_triggers"], ensure_ascii=False),
                "source_sr_ids": json.dumps(row["source_sr_ids"], ensure_ascii=False),
            },
        )
        n += 1
    db.commit()
    return n


def append_audit(events: list[dict]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps({"ts": ts, **ev}, ensure_ascii=False) + "\n")


async def main_async(args: argparse.Namespace) -> int:
    from app.db.database import SessionLocal

    catalog = load_catalog()
    print(f"Catalog v{catalog.get('version')}")

    vocabs = get_axis_vocabularies(catalog)
    valid_all = {k: set(v) for k, v in vocabs.items()}
    print(f"  vocab sizes: {dict((k, len(v)) for k, v in vocabs.items())}")

    v31_codes = filter_v31_origin_codes(catalog)
    print(f"  v3.1 origin codes (_source='f1_recovery_sonnet_4_6'): {len(v31_codes)}")
    by_axis: Counter = Counter()
    for c in v31_codes:
        by_axis[c["axis"]] += 1
    for ax, n in by_axis.most_common():
        print(f"    {ax:20s}: {n}")

    if args.max_codes and len(v31_codes) > args.max_codes:
        v31_codes = v31_codes[:args.max_codes]
        print(f"  capped to {args.max_codes}")

    # Cost estimate: ~5K input + 0.3K output per call
    est_cost = len(v31_codes) * 0.02
    print(f"\n  Estimated Sonnet 4.6 cost: ~${est_cost:.2f}")
    print(f"  Estimated time (conc {SONNET_CONCURRENCY}): ~{len(v31_codes)//(SONNET_CONCURRENCY*30)+1}분")

    if args.dry_run:
        print("\n[dry-run] no LLM calls.")
        print("  Sample first 5 codes that would be processed:")
        for c in v31_codes[:5]:
            print(f"    {c['axis']:18s}  {c['code']:35s}  {c['label']!r}")
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY required", file=sys.stderr)
        return 2

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=api_key)
    sem = asyncio.Semaphore(SONNET_CONCURRENCY)

    async def _work(c):
        async with sem:
            return c, await propose_she(client, c, vocabs)

    print(f"\n[Sonnet 4.6] generating SHE patterns for {len(v31_codes)} codes...")
    results = await asyncio.gather(*[_work(c) for c in v31_codes])

    rows: list[dict] = []
    audit_events: list[dict] = []
    accepted = 0
    low_conf = 0
    invalid = 0
    errors = 0

    for code_info, verdict in results:
        if verdict.get("error"):
            errors += 1
            audit_events.append({
                "action": "error", "axis": code_info["axis"], "code": code_info["code"],
                "error": verdict["error"],
            })
            continue

        conf = float(verdict.get("confidence", 0))
        features = {
            "work_activity": verdict.get("work_activity", "OTHER"),
            "work_context": verdict.get("work_context", "OTHER"),
            "hazardous_agent": verdict.get("hazardous_agent", "OTHER"),
            "accident_type": verdict.get("accident_type", "OTHER"),
            "agent_state": verdict.get("agent_state", "OTHER"),
            "ppe_state": verdict.get("ppe_state", "OTHER"),
            "environmental": verdict.get("environmental", "OTHER"),
            "temporal_stage": verdict.get("temporal_stage", "DURING_WORK"),
        }
        features[code_info["axis"]] = code_info["code"]

        ok, reason, sanitized, sanitization_notes = validate_and_sanitize(
            features, code_info["axis"], code_info["code"], valid_all
        )
        if not ok:
            invalid += 1
            audit_events.append({
                "action": "rejected_invalid", "axis": code_info["axis"], "code": code_info["code"],
                "reason": reason, "verdict": verdict,
            })
            continue

        if conf < args.min_conf:
            low_conf += 1
            audit_events.append({
                "action": "rejected_low_conf", "axis": code_info["axis"], "code": code_info["code"],
                "confidence": conf, "verdict": verdict,
            })
            continue

        # Use sanitized features (invalid other-axis codes → OTHER fallback)
        verdict_for_row = {**verdict, **sanitized}
        row = build_she_row(code_info, verdict_for_row)
        rows.append(row)
        accepted += 1
        audit_events.append({
            "action": "accepted", "axis": code_info["axis"], "code": code_info["code"],
            "she_id": row["she_id"], "confidence": conf,
            "features": row["features"], "visual_triggers": row["visual_triggers"],
            "sanitization_notes": sanitization_notes,
        })

    print()
    print(f"Results:")
    print(f"  processed         : {len(results)}")
    print(f"  accepted          : {accepted}")
    print(f"  low_conf reject   : {low_conf}")
    print(f"  invalid reject    : {invalid}")
    print(f"  errors            : {errors}")

    # Sample accepted
    print()
    print(f"  Sample accepted (top 5):")
    for r in rows[:5]:
        ft = r["features"]
        vt = ", ".join(r["visual_triggers"][:3])
        print(f"    {r['she_id']}")
        print(f"      target: {ft.get('work_context')}/{ft.get('accident_type')}")
        print(f"      visual: {vt}")

    if not rows:
        print("\nNo SHE rows to insert.")
        append_audit(audit_events)
        return 0

    db = SessionLocal()
    try:
        print(f"\n[PG INSERT] inserting {len(rows)} SHE rows...")
        n = upsert_she(db, rows)
        print(f"  inserted: {n}")
        append_audit(audit_events)
        print(f"  audit appended: {AUDIT_PATH.relative_to(REPO_ROOT)}")
    finally:
        db.close()

    print()
    print("⚠️  Gate 3 regression 필수:")
    print("    make f1-regression")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--max-codes", type=int, default=0, help="cap to N codes (test)")
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
