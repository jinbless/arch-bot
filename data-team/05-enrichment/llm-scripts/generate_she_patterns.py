#!/usr/bin/env python3
"""Phase 3C — Direct LLM SHE pattern generation for catalog v4 uncovered codes.

For each catalog code with no existing SHE pattern, ask LLM to propose 2 patterns
(realistic combinations of 8 features + visual_triggers + source_sr_ids).

Output: data-team/05-enrichment/runtime-artifacts/she_pattern_proposals.json
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("root")


ROOT = find_root()
CATALOG_PATH = ROOT / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
OUT_PATH = ROOT / "data-team/05-enrichment/runtime-artifacts/she_pattern_proposals.json"

SHE_AXES = ["work_activity", "work_context", "hazardous_agent", "accident_type",
            "agent_state", "ppe_state", "environmental", "temporal_stage"]


SYSTEM_PROMPT = """\
당신은 KOSHA 산업안전 SHE pattern designer입니다.
주어진 catalog code에 대해, 실제 산업 상황을 표현하는 SHE pattern 1-2개를 제안.

SHE pattern = 8 axis 조합:
1. work_activity (예: WELDING, CLEANING, LIFTING, OTHER)
2. work_context (예: SCAFFOLD, CONFINED_SPACE, KITCHEN_COOKING)
3. hazardous_agent (예: CHEMICAL, ELECTRICITY, HEAT_COLD)
4. accident_type (예: FALL, CRUSH, BURN)
5. agent_state (예: LIVE_VOLTAGE, FLAMMABLE_EXPOSED, OTHER)
6. ppe_state (예: HELMET_MISSING, HARNESS_UNTIED, GLOVE_WORN)
7. environmental (예: WET_SURFACE, HIGH_ELEVATION, EXTREME_TEMPERATURE)
8. temporal_stage (예: DURING_WORK)

원칙:
- 한 pattern = 한 시나리오 (구체적·실현 가능)
- visual_triggers: 한국어 단서 3-5개 (Vision LLM이 사진에서 볼 만한 것)
- source_sr_ids: 제공된 list에서만 1-3개
- broadness_score: 0.5 (구체) ~ 0.9 (광범위)
- 제공 list에 없는 값 금지

JSON으로 응답.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "patterns": {
            "type": "array",
            "items": {
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
                    "visual_triggers": {"type": "array", "items": {"type": "string"}},
                    "source_sr_ids": {"type": "array", "items": {"type": "string"}},
                    "broadness_score": {"type": "number"},
                    "rationale": {"type": "string"},
                },
                "required": ["work_activity", "work_context", "hazardous_agent", "accident_type",
                             "agent_state", "ppe_state", "environmental", "temporal_stage",
                             "visual_triggers", "source_sr_ids", "broadness_score", "rationale"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["patterns"],
    "additionalProperties": False,
}


def normalize_en(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]+", "_", s.strip())).strip("_").upper() or "OTHER"


def build_she_id(features: dict, idx: int) -> str:
    wc = features.get("work_context", "OTHER").replace("_", "")[:14]
    raw = "|".join(f"{k}:{features.get(k, 'OTHER')}" for k in sorted(SHE_AXES))
    h = hashlib.md5((raw + f"|p3c-{idx}").encode("utf-8")).hexdigest()[:10]
    return f"SHE-{wc.upper()}-{h}"


def query_pg_uncovered(catalog: dict) -> dict:
    from sqlalchemy import create_engine, text
    db = os.environ.get("DATABASE_URL", "postgresql://kosha:1229@localhost:5432/kosha")
    eng = create_engine(db)
    covered = {}
    with eng.connect() as conn:
        for axis in ("accident_type", "hazardous_agent", "work_context"):
            rows = conn.execute(text(f"SELECT DISTINCT features->>'{axis}' AS v FROM she_catalog WHERE features->>'{axis}' IS NOT NULL"))
            covered[axis] = {r[0] for r in rows if r[0]}
    eng.dispose()
    out = {}
    for axis, info in catalog.get("axes", {}).items():
        if axis not in covered:
            continue
        out[axis] = sorted(set(info.get("codes", {}).keys()) - covered[axis])
    return out


def query_sr_table() -> list:
    from sqlalchemy import create_engine, text
    db = os.environ.get("DATABASE_URL", "postgresql://kosha:1229@localhost:5432/kosha")
    eng = create_engine(db)
    out = []
    with eng.connect() as conn:
        rows = conn.execute(text("""
            SELECT identifier, title, accident_types, hazardous_agents
            FROM safety_requirements
            WHERE accident_types IS NOT NULL OR hazardous_agents IS NOT NULL
        """))
        for r in rows:
            out.append({
                "identifier": r[0],
                "title": (r[1] or "")[:80],
                "accident_types": r[2] or [],
                "hazardous_agents": r[3] or [],
            })
    eng.dispose()
    return out


def select_srs(axis: str, code: str, table: list, limit: int = 25) -> list:
    rel = []
    for sr in table:
        if axis == "accident_type" and code in (sr.get("accident_types") or []):
            rel.append(sr)
        elif axis == "hazardous_agent" and code in (sr.get("hazardous_agents") or []):
            rel.append(sr)
    if not rel:
        rel = table[:limit]
    return rel[:limit]


def user_prompt(axis: str, code: str, label: str, catalog: dict, srs: list) -> str:
    PPE = ["OTHER", "HELMET_MISSING", "HELMET_WORN", "HARNESS_MISSING", "HARNESS_UNTIED",
           "GLOVES_MISSING", "GLOVE_WORN", "MASK_MISSING", "SAFETY_SHOES_MISSING"]
    ENV = ["OTHER", "WET_SURFACE", "HIGH_ELEVATION", "EXTREME_TEMPERATURE", "NARROW_SPACE", "DARK", "DUSTY"]
    AGENT = ["OTHER", "LIVE_VOLTAGE", "FLAMMABLE_EXPOSED", "PRESSURIZED", "MOVING"]
    TEMP = ["BEFORE_WORK", "DURING_WORK", "AFTER_WORK"]
    ACT = ["OTHER", "WELDING", "CLEANING", "LIFTING", "CUTTING", "MIXING", "INSPECTION", "INSTALLATION", "TRANSPORT"]
    by_axis = {ax: sorted(info.get("codes", {}).keys()) for ax, info in catalog.get("axes", {}).items()}
    sr_block = "\n".join(f"  - {s['identifier']}: {s['title']}" for s in srs)
    return f"""[target catalog code]
axis    : {axis}
code    : {code}
label_ko: {label}

[유효 axis 값]
work_activity   : {ACT}
work_context    : (catalog v4 work_context {len(by_axis.get('work_context', []))}개, sample) {by_axis.get('work_context', [])[:30]}
hazardous_agent : {by_axis.get('hazardous_agent', [])[:60]}
accident_type   : {by_axis.get('accident_type', [])[:60]}
agent_state     : {AGENT}
ppe_state       : {PPE}
environmental   : {ENV}
temporal_stage  : {TEMP}

[SR 후보 (source_sr_ids 선택)]
{sr_block}

위 catalog code "{code}" ({label})에 대해 2개의 SHE pattern을 제안하세요.
"""


async def call_llm(client, model, sys_p, user_p):
    try:
        r = await client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}],
            response_format={"type": "json_schema", "json_schema": {
                "name": "she_pattern", "strict": True, "schema": RESPONSE_SCHEMA}},
            temperature=0,
            max_completion_tokens=1200,
        )
        return json.loads(r.choices[0].message.content or "{}")
    except Exception as exc:
        return {"error": str(exc), "patterns": []}


def build_row(axis: str, code: str, label: str, p: dict, sr_universe: set, ph: str, idx: int) -> dict:
    feat = {k: normalize_en(p.get(k, "OTHER")) or "OTHER" for k in SHE_AXES}
    feat[axis] = code  # anchor primary
    sr_ids = [s for s in (p.get("source_sr_ids") or []) if isinstance(s, str) and s.strip() in sr_universe]
    return {
        "she_id": build_she_id(feat, idx),
        "name": f"{feat.get('work_context','OTHER')} {feat.get('accident_type','OTHER')} pattern ({code})",
        "name_pattern": f"phase3c_{axis}_{code}",
        "features": feat,
        "rationale": (p.get("rationale") or "")[:500],
        "source_model": "phase3c/direct-llm-gpt-4.1",
        "source_prompt_hash": ph,
        "source_sr_ids": sr_ids,
        "visual_triggers": [v for v in (p.get("visual_triggers") or [])[:8] if isinstance(v, str)],
        "broadness_score": min(0.95, max(0.4, float(p.get("broadness_score", 0.7)))),
        "status": "draft",
        "_phase3c_meta": {"anchor_axis": axis, "anchor_code": code, "anchor_label_ko": label},
    }


async def main_async(args):
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    print("[1/4] uncovered codes from PG...")
    uncovered = query_pg_uncovered(catalog)
    for ax, codes in uncovered.items():
        print(f"  {ax:20s} {len(codes)} uncovered")
    print("\n[2/4] SR table from PG...")
    srs = query_sr_table()
    sr_universe = {s["identifier"] for s in srs}
    print(f"  {len(srs)} SRs loaded")

    items = []
    for ax, codes in uncovered.items():
        cat_codes = catalog["axes"][ax]["codes"]
        for c in codes:
            items.append({"axis": ax, "code": c, "label_ko": cat_codes.get(c, {}).get("label", c)})
    items.sort(key=lambda x: (x["axis"], x["code"]))

    if args.max and len(items) > args.max:
        items = items[: args.max]
        print(f"  limited to {args.max}")

    if args.dry_run:
        print(f"\n[3/4] DRY — {len(items)} codes, est ${len(items)*0.005:.2f}")
        for it in items[:5]:
            print(f"  - {it['axis']:18s} {it['code']:30s} {it['label_ko']}")
        return 0

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("ERROR: OPENAI_API_KEY", file=sys.stderr); return 2
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1")
    sem = asyncio.Semaphore(args.concurrency)
    ph = hashlib.md5(SYSTEM_PROMPT.encode()).hexdigest()
    print(f"\n[3/4] LLM ({model}, c={args.concurrency}) — {len(items)} codes...")

    async def _work(it):
        async with sem:
            user_p = user_prompt(it["axis"], it["code"], it["label_ko"], catalog, select_srs(it["axis"], it["code"], srs))
            return {**it, "llm": await call_llm(client, model, SYSTEM_PROMPT, user_p)}

    completed = 0
    results = []
    for f in asyncio.as_completed([_work(it) for it in items]):
        r = await f
        results.append(r)
        completed += 1
        if completed % 20 == 0:
            print(f"  [{completed}/{len(items)}]")

    print(f"\n[4/4] Build SHE rows...")
    rows = []
    errs = 0
    for r in results:
        if r["llm"].get("error"):
            errs += 1; continue
        for i, p in enumerate((r["llm"].get("patterns") or [])[:2]):
            rows.append(build_row(r["axis"], r["code"], r["label_ko"], p, sr_universe, ph, i))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "source_codes": len(items),
        "patterns_generated": len(rows),
        "llm_errors": errs,
        "patterns": rows,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved: {OUT_PATH.relative_to(ROOT)}")
    print(f"  source codes : {len(items)}")
    print(f"  patterns out : {len(rows)} (target ~{len(items)*2})")
    print(f"  llm errors   : {errs}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=10)
    args = p.parse_args()
    if not args.apply:
        args.dry_run = True
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
