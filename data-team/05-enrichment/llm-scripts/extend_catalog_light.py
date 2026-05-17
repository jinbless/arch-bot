#!/usr/bin/env python3
"""F.2-light — 1회성 catalog 확장 후보 정제기.

목적: F.1-light에서 발견된 catalog-missing 코드 944건 (synthetic이 사용하지만
production catalog에 없는 코드)을 LLM 큐레이터로 분류 → 사람 검토 후
risk_feature_catalog.json에 ACCEPT한 것만 등재.

판정 카테고리:
- ACCEPT: 정식 영문 enum 스타일 + 명확한 도메인 의미 + 기존과 중복 아님
- REJECT: 한국어가 enum으로 사용된 데이터 품질 이슈 / 기존의 sub / 모호
- RELOCATE: 다른 axis가 더 적합

정식 F.2의 Module 4.2 (TBox class learning) 중 4-Gate Gate 2만 수행.
다음 검증은 사람 + regression test로 보완.

ENV:
  OPENAI_API_KEY     (--apply 시 필수)
  LLM_RERANK_MODEL   (default: gpt-5.4-nano)

사용:
  python extend_catalog_light.py                  # dry-run (분포만)
  python extend_catalog_light.py --apply          # 실제 LLM 호출
  python extend_catalog_light.py --apply --max 30 # top 30만 (저비용 테스트)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
PROPOSALS_IN = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "f1_light_proposals.json"
CATALOG_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
OUT_PATH = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "f2_light_catalog_proposals.json"

ENUM_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")  # UPPER_SNAKE_CASE


SYSTEM_PROMPT = """\
당신은 KOSHA 산업안전 catalog 큐레이터입니다.
synthetic data에서 발견되었으나 production catalog에 없는 코드를 평가합니다.

판정 기준:
1. ACCEPT (catalog 추가 권장):
   - 정식 영문 enum 스타일 (UPPER_SNAKE_CASE)
   - 명확한 도메인 의미 (한국 산업안전 맥락 적합)
   - 기존 catalog 코드와 중복 아님
   - 너무 구체적이지도 너무 일반적이지도 않음

2. REJECT:
   - 한국어가 enum으로 사용 (synthetic data 품질 이슈; 예: "베임", "절단")
   - 기존 catalog 코드의 명백한 sub-class (이미 표현 가능)
   - axis 자체가 모호 (어디 분류해야 할지 불분명)
   - 너무 marginal한 use case

3. RELOCATE (다른 axis로):
   - 이 axis가 아니라 다른 axis (accident_type / hazardous_agent / work_context)가 맞음

원칙: catalog는 안정적이어야 하므로 ACCEPT는 보수적으로. 의심스러우면 REJECT.
"""

USER_TEMPLATE = """\
[제안된 코드]
axis        : {axis}
code        : {code}
참조된 빈도 : {ref_count} (synthetic record 수)
LLM이 제안한 alias 후보들: {aliases_sample}
LLM reasoning 샘플: {reasoning_sample}

[현재 catalog 정의 코드 — {axis} axis]
{existing_codes}

[다른 axis들의 코드 (RELOCATE 참고용)]
{other_axes_summary}

위 정보로 판정하세요.
"""

RESPONSE_SCHEMA = {
    "name": "catalog_decision",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["ACCEPT", "REJECT", "RELOCATE"]},
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"},
            "canonical_label_ko": {"type": "string"},
            "canonical_label_en": {"type": "string"},
            "correct_axis": {"type": "string"},
            "duplicate_of": {"type": "string"},
        },
        "required": [
            "decision", "confidence", "reasoning",
            "canonical_label_ko", "canonical_label_en", "correct_axis", "duplicate_of",
        ],
        "additionalProperties": False,
    },
}


def load_proposals() -> dict:
    return json.loads(PROPOSALS_IN.read_text(encoding="utf-8"))


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def collect_missing(proposals: dict, catalog: dict) -> list[dict]:
    """catalog-missing 코드 추출 (proposals.json 구조 활용)."""
    cat_codes = {axis: set(d.get("codes", {}).keys()) for axis, d in catalog.get("axes", {}).items()}
    missing = []
    for axis, code_map in proposals.get("proposals", {}).items():
        if axis not in cat_codes:
            continue  # 미정의 axis는 별도 처리
        existing = cat_codes[axis]
        for code, ps in code_map.items():
            if code in existing:
                continue
            aliases = [p["alias"] for p in ps]
            avg_conf = sum(p["confidence"] for p in ps) / len(ps) if ps else 0.0
            reasoning_sample = ps[0].get("reasoning", "") if ps else ""
            ref_count = ps[0].get("frequency_in_synthetic", 0) if ps else 0
            missing.append({
                "axis": axis,
                "code": code,
                "ref_count": ref_count,
                "aliases_count": len(aliases),
                "aliases_sample": aliases[:6],
                "avg_alias_confidence": round(avg_conf, 3),
                "reasoning_sample": reasoning_sample[:200],
                "is_enum_style": bool(ENUM_PATTERN.match(code)),
                "has_korean": any(ord(c) > 127 for c in code),
            })
    return missing


async def llm_curate(client, model: str, item: dict, axis_codes: dict[str, set[str]], catalog: dict) -> dict:
    axis = item["axis"]
    existing_list = sorted(axis_codes.get(axis, set()))
    existing_str = ", ".join(existing_list[:80]) + (f" ... +{len(existing_list)-80}개 더" if len(existing_list) > 80 else "")
    other_axes_summary = []
    for other_axis, codes in axis_codes.items():
        if other_axis == axis:
            continue
        codes_list = sorted(codes)
        sample = ", ".join(codes_list[:15]) + (f" ... +{len(codes_list)-15}" if len(codes_list) > 15 else "")
        other_axes_summary.append(f"  {other_axis}: {sample}")

    user_prompt = USER_TEMPLATE.format(
        axis=axis,
        code=item["code"],
        ref_count=item["ref_count"],
        aliases_sample=", ".join(item["aliases_sample"]) or "(없음)",
        reasoning_sample=item["reasoning_sample"] or "(없음)",
        existing_codes=existing_str,
        other_axes_summary="\n".join(other_axes_summary),
    )
    try:
        r = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_schema", "json_schema": RESPONSE_SCHEMA},
            max_completion_tokens=400,
        )
        return json.loads(r.choices[0].message.content or "{}")
    except Exception as exc:
        return {"error": str(exc), "decision": "REJECT", "confidence": 0.0, "reasoning": ""}


async def main_async(args: argparse.Namespace) -> int:
    print("[1/4] Loading inputs...")
    proposals = load_proposals()
    catalog = load_catalog()
    cat_codes = {axis: set(d.get("codes", {}).keys()) for axis, d in catalog.get("axes", {}).items()}
    print(f"  proposals file generated_at: {proposals.get('generated_at', 'unknown')}")
    print(f"  catalog axes / sizes        : {[(a, len(c)) for a, c in cat_codes.items()]}")

    print("\n[2/4] Filtering catalog-missing codes...")
    missing = collect_missing(proposals, catalog)
    by_axis: dict[str, int] = defaultdict(int)
    by_style: dict[str, int] = defaultdict(int)
    for m in missing:
        by_axis[m["axis"]] += 1
        if m["has_korean"]:
            by_style["korean_in_code"] += 1
        elif m["is_enum_style"]:
            by_style["enum_style"] += 1
        else:
            by_style["other"] += 1
    print(f"  total catalog-missing codes: {len(missing)}")
    print(f"  by axis: {dict(by_axis)}")
    print(f"  by style: {dict(by_style)}")

    # sort: enum_style first (likely ACCEPT), then by alias count, then by ref_count
    missing.sort(key=lambda x: (not x["is_enum_style"], -x["aliases_count"], -x["ref_count"]))

    if args.max and len(missing) > args.max:
        print(f"  limited to top {args.max} (sorted by enum-style + alias_count + ref_count)")
        missing = missing[: args.max]

    print(f"\n  top 10:")
    for m in missing[:10]:
        style = "[enum]" if m["is_enum_style"] else ("[KR]" if m["has_korean"] else "[mix]")
        print(f"    {style:6s} {m['axis']:15s} {m['code'][:30]:30s} ref={m['ref_count']:3d} aliases={m['aliases_count']}")

    if args.dry_run:
        est_cost = len(missing) * 0.0015
        print(f"\n[3/4] DRY RUN — would send {len(missing)} prompts to {args.model}")
        print(f"  Estimated cost: ~${est_cost:.2f}")
        return 0

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required for --apply", file=sys.stderr)
        return 2

    print(f"\n[3/4] LLM curator ({len(missing)} codes, model={args.model}, concurrency={args.concurrency})...")
    try:
        from openai import AsyncOpenAI
    except ImportError:
        print("ERROR: openai package not installed", file=sys.stderr)
        return 2

    client = AsyncOpenAI(api_key=api_key)
    sem = asyncio.Semaphore(args.concurrency)

    async def _work(item):
        async with sem:
            return {**item, "verdict": await llm_curate(client, args.model, item, cat_codes, catalog)}

    results = await asyncio.gather(*[_work(m) for m in missing])

    print("\n[4/4] Aggregating decisions...")
    by_decision: dict[str, list[dict]] = defaultdict(list)
    errors = 0
    for r in results:
        v = r["verdict"]
        if v.get("error"):
            errors += 1
            continue
        dec = v.get("decision", "REJECT")
        by_decision[dec].append({
            "axis": r["axis"], "code": r["code"],
            "ref_count": r["ref_count"], "aliases_count": r["aliases_count"],
            "is_enum_style": r["is_enum_style"], "has_korean": r["has_korean"],
            "confidence": round(float(v.get("confidence", 0.0)), 3),
            "reasoning": (v.get("reasoning") or "")[:300],
            "canonical_label_ko": v.get("canonical_label_ko", ""),
            "canonical_label_en": v.get("canonical_label_en", ""),
            "correct_axis": v.get("correct_axis", ""),
            "duplicate_of": v.get("duplicate_of", ""),
            "alias_proposals_from_f1": r["aliases_sample"],
        })

    # sort within each decision by confidence desc
    for dec in by_decision:
        by_decision[dec].sort(key=lambda x: -x["confidence"])

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "source": str(PROPOSALS_IN.relative_to(REPO_ROOT)),
        "stats": {
            "total_missing_codes": len(missing),
            "llm_calls": len(results),
            "llm_errors": errors,
            "ACCEPT": len(by_decision.get("ACCEPT", [])),
            "REJECT": len(by_decision.get("REJECT", [])),
            "RELOCATE": len(by_decision.get("RELOCATE", [])),
            "by_axis_input": dict(by_axis),
        },
        "decisions": {dec: by_decision.get(dec, []) for dec in ["ACCEPT", "RELOCATE", "REJECT"]},
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  ACCEPT   : {len(by_decision.get('ACCEPT', []))}")
    print(f"  RELOCATE : {len(by_decision.get('RELOCATE', []))}")
    print(f"  REJECT   : {len(by_decision.get('REJECT', []))}")
    print(f"  errors   : {errors}")
    print(f"\nNext: 사람이 {OUT_PATH.name} 검토 → ACCEPT 큐레이션 → catalog 머지")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--model", type=str, default=os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano"))
    args = parser.parse_args()
    if not args.apply:
        args.dry_run = True
    return args


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
