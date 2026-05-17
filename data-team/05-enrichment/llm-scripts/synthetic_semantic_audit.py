#!/usr/bin/env python3
"""Phase 3A — Synthetic KO enum codes의 의미적 audit.

각 KO code를 5+1 categorical decision으로 분류:
- (E) EXISTING_EQUIV: 기존 catalog code의 직접 동등어
- (NEW) NEW_CODE_NEEDED: 신규 catalog code 후보
- (SUB) SUB_CLASS_OF: 기존 code의 sub-class
- (RELOC) WRONG_AXIS: axis 잘못 분류 → 정확한 axis
- (DROP) NOT_A_CODE: enum 부적합 (vague/noise)
- (HUMAN) DISAGREEMENT: voices 합의 < 2/3 → 사람 검토 queue

Ensemble (3 voices for vote majority):
1. GPT-4o (temperature=0)
2. Claude Sonnet 4.6 (temperature=0)
3. GPT-4o self-consistency (temperature=0.7, majority of N=3)

References injected to prompts (where applicable):
- KOSHA 22대 사고유형 분류 (accident_types axis)
- 현재 catalog codes (모든 axis)
- KSIC 11차 (industry context)

ENV:
  OPENAI_API_KEY (필수)
  ANTHROPIC_API_KEY (필수)
  OPENAI_MODEL (default: gpt-4o)
  CLAUDE_MODEL (default: claude-sonnet-4-5-20250929)

사용:
  python synthetic_semantic_audit.py --dry-run          # sample N=5만, 비용 확인
  python synthetic_semantic_audit.py --apply            # 전체 1857 codes
  python synthetic_semantic_audit.py --apply --max 30   # top 30만 (저비용 테스트)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("repo root not found")


ROOT = find_root()
SYNTH_DIR = ROOT / "data-team/05-enrichment/eval-data"
KOSHA_REF = ROOT / "data-team/05-enrichment/runtime-artifacts/kosha_reference_parsed.json"
CATALOG = ROOT / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
ALIASES = ROOT / "serving-team/08-app/backend/app/data/risk_feature_aliases.json"
F2_PROPOSALS = ROOT / "data-team/05-enrichment/runtime-artifacts/f2_light_catalog_proposals.json"
OUT_AUDIT = ROOT / "data-team/05-enrichment/runtime-artifacts/synthetic_audit_v1.json"
OUT_HUMAN = ROOT / "data-team/05-enrichment/runtime-artifacts/synthetic_audit_human_queue.json"

AXIS_KEY_MAP = {
    "accident_types": "accident_type",
    "hazardous_agents": "hazardous_agent",
    "work_contexts": "work_context",
    "ppe_states": "ppe_state",
    "environmental": "environmental",
}

CATEGORY_ENUM = ["EXISTING_EQUIV", "NEW_CODE_NEEDED", "SUB_CLASS_OF", "WRONG_AXIS", "NOT_A_CODE"]


SYSTEM_PROMPT = """\
당신은 KOSHA 산업안전 ontology curator입니다.
주어진 한국어 enum 코드 (synthetic data에서 추출)를 5개 카테고리로 분류합니다.

카테고리:
1. EXISTING_EQUIV — 기존 catalog code의 직접 동등어
   예: "감전" → ELECTRIC_SHOCK (이미 catalog에 있음)
2. NEW_CODE_NEEDED — 신규 catalog code 후보 (도메인 의미 있고 기존 미포함)
   예: "가구 전도" → FURNITURE_TIPOVER (신규 추가 가치)
3. SUB_CLASS_OF — 기존 code의 sub-class (구체화)
   예: "고소 추락" → FALL의 sub (FALL_FROM_HEIGHT)
4. WRONG_AXIS — 다른 axis가 맞음
   예: hazardous_agent에 "감전 사고" → 사실 accident_type
5. NOT_A_CODE — enum 부적합 (vague, noise, 일반 단어)
   예: "없음", "기타", "일반"

판정 시 우선순위:
- KOSHA 사고유형 22대 분류와 정합성 (accident_types axis 시)
- 기존 catalog code 중복 회피 (EXISTING_EQUIV 우선)
- 의미적 명확성 (모호하면 NOT_A_CODE)
- 도메인 가치 (산업안전 맥락에서 의미 있는가)

응답은 JSON. canonical_label_en은 UPPER_SNAKE_CASE.
NEW_CODE_NEEDED 또는 SUB_CLASS_OF인 경우 반드시 canonical_label_en 제안.
SUB_CLASS_OF인 경우 parent_code (기존 catalog code) 명시.
WRONG_AXIS인 경우 correct_axis 명시.
kosha_22_match는 KOSHA 22대 중 매칭되는 KO 이름 (없으면 빈 문자열).
"""


def user_prompt(item: dict, kosha_22: list[dict], current_catalog_axis_codes: list[str], axis_label_en: str) -> str:
    kosha_block = ""
    if axis_label_en == "accident_type":
        kosha_lines = []
        for ent in kosha_22:
            kosha_lines.append(f"  - {ent['ko']} ({ent['en_suggested']}): {ent['description_ko']}")
        kosha_block = "\nKOSHA 공식 사고유형 22대 분류 (ground truth):\n" + "\n".join(kosha_lines) + "\n"

    catalog_block = f"\n현재 {axis_label_en} catalog codes ({len(current_catalog_axis_codes)}개):\n  " + ", ".join(current_catalog_axis_codes[:60])
    if len(current_catalog_axis_codes) > 60:
        catalog_block += f"\n  ... +{len(current_catalog_axis_codes)-60}개 더"

    return f"""평가할 KO enum 코드:
  axis: {axis_label_en}
  코드: "{item['ko_code']}"
  synthetic 출현 빈도: {item['freq']}
{kosha_block}{catalog_block}

위 코드를 5개 카테고리로 분류하세요.
"""


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORY_ENUM},
        "confidence": {"type": "number"},
        "canonical_label_en": {"type": "string"},
        "parent_code": {"type": "string"},
        "correct_axis": {"type": "string"},
        "kosha_22_match": {"type": "string"},
        "reasoning": {"type": "string"},
    },
    "required": ["category", "confidence", "canonical_label_en", "parent_code", "correct_axis", "kosha_22_match", "reasoning"],
    "additionalProperties": False,
}


def load_synthetic_ko_codes() -> dict[str, Counter[str]]:
    by_axis: dict[str, Counter[str]] = defaultdict(Counter)
    for fp in sorted(SYNTH_DIR.glob("synthetic_observations_v*.jsonl")):
        for line in fp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            exp = r.get("expected_features", {})
            for axis_synth, codes in exp.items():
                if isinstance(codes, list):
                    for c in codes:
                        if isinstance(c, str) and any(ord(ch) > 127 for ch in c):
                            by_axis[axis_synth][c] += 1
    return by_axis


def load_catalog_codes_by_axis() -> dict[str, list[str]]:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {axis: sorted(d.get("codes", {}).keys()) for axis, d in cat.get("axes", {}).items()}


async def call_openai(client, model, system, user, temperature=0.0):
    try:
        r = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "audit_decision", "strict": True, "schema": RESPONSE_SCHEMA}},
            temperature=temperature,
            max_completion_tokens=600,
        )
        return json.loads(r.choices[0].message.content or "{}")
    except Exception as exc:
        return {"error": str(exc), "category": "NOT_A_CODE", "confidence": 0.0}


async def call_anthropic(client, model, system, user):
    """Claude doesn't have JSON schema strict mode but tool_use achieves equivalent."""
    try:
        r = await client.messages.create(
            model=model,
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{
                "name": "audit_decision",
                "description": "Submit the audit classification decision.",
                "input_schema": RESPONSE_SCHEMA,
            }],
            tool_choice={"type": "tool", "name": "audit_decision"},
        )
        for block in r.content:
            if hasattr(block, "input"):
                return dict(block.input)
        return {"error": "no tool_use in response", "category": "NOT_A_CODE", "confidence": 0.0}
    except Exception as exc:
        return {"error": str(exc), "category": "NOT_A_CODE", "confidence": 0.0}


def aggregate_voices(voices: list[dict]) -> dict:
    """3 voices → consensus."""
    valid = [v for v in voices if not v.get("error")]
    if not valid:
        return {"status": "ERROR", "category": "NOT_A_CODE", "consensus_score": 0.0, "confidence": 0.0}
    # Vote majority on category
    cats = [v.get("category", "NOT_A_CODE") for v in valid]
    cat_counts = Counter(cats)
    top_cat, top_n = cat_counts.most_common(1)[0]
    consensus_score = top_n / len(valid)
    # Average confidence from voices that picked top_cat
    matching = [v for v in valid if v.get("category") == top_cat]
    avg_conf = sum(float(v.get("confidence", 0.0)) for v in matching) / max(len(matching), 1)
    # For category-specific fields, pick from highest-confidence matching voice
    if matching:
        best = max(matching, key=lambda v: float(v.get("confidence", 0.0)))
        result = {
            "status": "AUTO_ACCEPT" if consensus_score >= 0.99 else ("ACCEPT" if consensus_score >= 0.5 else "HUMAN"),
            "category": top_cat,
            "consensus_score": consensus_score,
            "confidence": avg_conf,
            "canonical_label_en": best.get("canonical_label_en", ""),
            "parent_code": best.get("parent_code", ""),
            "correct_axis": best.get("correct_axis", ""),
            "kosha_22_match": best.get("kosha_22_match", ""),
            "reasoning": best.get("reasoning", "")[:300],
        }
    else:
        result = {"status": "HUMAN", "category": top_cat, "consensus_score": consensus_score, "confidence": 0.0}
    return result


async def audit_one_code(item: dict, openai_client, anthropic_client, openai_model: str, claude_model: str,
                          openai_sc_model: str, kosha_22: list[dict], catalog_axis_codes: list[str]) -> dict:
    axis_label = AXIS_KEY_MAP.get(item["axis_synth"], item["axis_synth"])
    sys_p = SYSTEM_PROMPT
    user_p = user_prompt(item, kosha_22, catalog_axis_codes, axis_label)

    # Voice 1: Primary OpenAI (gpt-4.1) temp=0
    v1 = await call_openai(openai_client, openai_model, sys_p, user_p, temperature=0.0)
    v1["model"] = f"{openai_model}@t=0"
    # Voice 2: Claude
    v2 = await call_anthropic(anthropic_client, claude_model, sys_p, user_p)
    v2["model"] = claude_model
    # Voice 3: Self-consistency on cheaper model (gpt-5.4-mini) — N=3 majority
    sc = await asyncio.gather(*[call_openai(openai_client, openai_sc_model, sys_p, user_p, temperature=0.7) for _ in range(3)])
    sc_cats = Counter(v.get("category", "NOT_A_CODE") for v in sc if not v.get("error"))
    if sc_cats:
        sc_top_cat, _ = sc_cats.most_common(1)[0]
        sc_matching = [v for v in sc if v.get("category") == sc_top_cat]
        if sc_matching:
            v3 = max(sc_matching, key=lambda v: float(v.get("confidence", 0.0)))
        else:
            v3 = sc[0]
    else:
        v3 = {"error": "all SC errored", "category": "NOT_A_CODE", "confidence": 0.0}
    v3["model"] = f"{openai_sc_model}@t=0.7,N=3-majority"

    voices = [v1, v2, v3]
    consensus = aggregate_voices(voices)
    return {
        "axis_synth": item["axis_synth"],
        "axis": axis_label,
        "ko_code": item["ko_code"],
        "freq": item["freq"],
        "voices": [{"model": v.get("model"), **{k: v[k] for k in v if k != "model"}} for v in voices],
        "consensus": consensus,
    }


async def main_async(args):
    print("[1/5] Loading inputs...")
    ko_by_axis = load_synthetic_ko_codes()
    cat_codes_by_axis = load_catalog_codes_by_axis()
    kosha_ref = json.loads(KOSHA_REF.read_text(encoding="utf-8")) if KOSHA_REF.exists() else {}
    kosha_22 = kosha_ref.get("accident_types_22", [])
    print(f"  synthetic axes with KO codes:")
    for axis, c in ko_by_axis.items():
        print(f"    {axis:20s} {len(c):4d} unique KO")
    print(f"  catalog axes: {list(cat_codes_by_axis.keys())}")
    print(f"  KOSHA 22 categories loaded: {len(kosha_22)}")

    # Flatten + sort by freq desc
    items = []
    for axis_synth, c in ko_by_axis.items():
        for ko, freq in c.items():
            items.append({"axis_synth": axis_synth, "ko_code": ko, "freq": freq})
    items.sort(key=lambda x: -x["freq"])
    total = len(items)
    print(f"\n[2/5] Total KO codes to audit: {total}")

    if args.max and total > args.max:
        items = items[: args.max]
        print(f"  limited to top {args.max} by frequency")

    if args.dry_run:
        sample = items[:5]
        print(f"\n[3/5] DRY RUN — would audit {len(items)} codes. Sample (top 5):")
        for it in sample:
            print(f"  [{it['freq']:4d}] {it['axis_synth']:18s} {it['ko_code']}")
        # cost estimate
        n_calls_per_code = 5  # 1 GPT t=0 + 3 GPT t=0.7 + 1 Claude
        est_gpt_calls = len(items) * 4
        est_claude_calls = len(items) * 1
        est_cost = est_gpt_calls * 0.005 + est_claude_calls * 0.015
        print(f"\n  estimated: {est_gpt_calls} GPT-4o + {est_claude_calls} Claude calls")
        print(f"  estimated cost: ~${est_cost:.2f}")
        print(f"\n  Re-run with --apply to execute.")
        return 0

    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not openai_key or not anthropic_key:
        print("ERROR: OPENAI_API_KEY 와 ANTHROPIC_API_KEY 모두 필요", file=sys.stderr)
        return 2

    try:
        from openai import AsyncOpenAI
        from anthropic import AsyncAnthropic
    except ImportError as e:
        print(f"ERROR: SDK missing: {e}", file=sys.stderr)
        return 2

    openai_client = AsyncOpenAI(api_key=openai_key)
    anthropic_client = AsyncAnthropic(api_key=anthropic_key)
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4.1")
    claude_model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    openai_sc_model = os.environ.get("OPENAI_SC_MODEL", "gpt-5.4-mini")

    print(f"\n[3/5] Hybrid ensemble (Voice1={openai_model}@t=0, Voice2={claude_model}@t=0, Voice3={openai_sc_model}@t=0.7,N=3-majority, concurrency={args.concurrency})...")
    sem = asyncio.Semaphore(args.concurrency)

    async def _work(item):
        async with sem:
            axis = AXIS_KEY_MAP.get(item["axis_synth"], item["axis_synth"])
            catalog_codes = cat_codes_by_axis.get(axis, [])
            return await audit_one_code(item, openai_client, anthropic_client, openai_model, claude_model, openai_sc_model, kosha_22, catalog_codes)

    results = []
    completed = 0
    BATCH_REPORT_EVERY = 50
    tasks = [_work(it) for it in items]
    for fut in asyncio.as_completed(tasks):
        r = await fut
        results.append(r)
        completed += 1
        if completed % BATCH_REPORT_EVERY == 0:
            print(f"  [{completed}/{len(items)}] processed...")

    print(f"\n[4/5] Aggregating + categorizing...")
    by_status = Counter(r["consensus"]["status"] for r in results)
    by_category = Counter(r["consensus"]["category"] for r in results)
    by_axis = Counter(r["axis"] for r in results)
    print(f"  by status: {dict(by_status)}")
    print(f"  by category: {dict(by_category)}")
    print(f"  by axis: {dict(by_axis)}")

    audit_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "openai_model": openai_model,
            "claude_model": claude_model,
            "ensemble": "GPT@t=0 + Claude@t=0 + GPT@t=0.7,N=3-majority",
            "consensus_threshold": "≥ 2/3 voices agree on category → ACCEPT; 3/3 → AUTO_ACCEPT; else → HUMAN",
        },
        "stats": {
            "total_audited": len(results),
            "by_status": dict(by_status),
            "by_category": dict(by_category),
            "by_axis": dict(by_axis),
        },
        "results": results,
    }

    human_items = [r for r in results if r["consensus"]["status"] == "HUMAN"]
    human_data = {
        "generated_at": audit_data["generated_at"],
        "count": len(human_items),
        "items": human_items,
    }

    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.write_text(json.dumps(audit_data, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_HUMAN.write_text(json.dumps(human_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[5/5] Saved:")
    print(f"  {OUT_AUDIT.relative_to(ROOT)} ({len(results)} entries)")
    print(f"  {OUT_HUMAN.relative_to(ROOT)} ({len(human_items)} HUMAN queue)")
    return 0


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=8)
    args = p.parse_args()
    if not args.apply:
        args.dry_run = True
    return args


def main():
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
