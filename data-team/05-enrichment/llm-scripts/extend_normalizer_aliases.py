#!/usr/bin/env python3
"""Phase B+ Pre-step — Catalog 동기화 + alias 자동 확장.

Step A (즉시 효과, LLM 불필요):
1. risk_feature_catalog.json의 한글 label → risk_feature_aliases.json tier1에 자동 머지
2. work_context의 신규 영문 코드 (synthetic v10에서 사용 중) catalog에 자동 추가
3. 알려진 변형 (예: ELECTRICITY_WORK → ELECTRICAL_WORK) 매핑

Step B (LLM 사용, optional):
4. 가장 빈도 높은 한글 missing (top N)에 대해 gpt-5.4-nano가 catalog 코드 매핑

사용:
  python extend_normalizer_aliases.py --apply        # Step A만
  python extend_normalizer_aliases.py --apply --llm  # Step A + B

ENV:
  OPENAI_API_KEY (required if --llm)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
CATALOG_PATH = REPO_ROOT / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
ALIASES_PATH = REPO_ROOT / "serving-team/08-app/backend/app/data/risk_feature_aliases.json"
EVAL_DIR = REPO_ROOT / "data-team/05-enrichment/eval-data"

AXIS_MAP = {
    "accident_types": "accident_type",
    "hazardous_agents": "hazardous_agent",
    "work_contexts": "work_context",
}

KNOWN_WORK_CONTEXT_REMAP = {
    "ELECTRICITY_WORK": "ELECTRICAL_WORK",
    "PRESSURIZED_WORK": "PRESSURE_VESSEL",
}


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def load_aliases() -> dict[str, Any]:
    if not ALIASES_PATH.exists():
        return {"version": "1.0", "tier1": {}}
    return json.loads(ALIASES_PATH.read_text(encoding="utf-8"))


def synthetic_freq() -> dict[str, Counter[str]]:
    out: dict[str, Counter[str]] = {
        "accident_type": Counter(),
        "hazardous_agent": Counter(),
        "work_context": Counter(),
    }
    for f in sorted(EVAL_DIR.glob("synthetic_observations_v*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            ef = row.get("expected_features") or {}
            for field, axis in AXIS_MAP.items():
                for v in (ef.get(field) or []):
                    if v:
                        out[axis][str(v).strip()] += 1
    return out


def catalog_codes(catalog: dict, axis: str) -> set[str]:
    codes = set()
    axis_data = catalog["axes"][axis]["codes"]
    for code, info in axis_data.items():
        codes.add(code)
        for sub in info.get("sub", []):
            codes.add(sub)
    return codes


def catalog_labels(catalog: dict, axis: str) -> dict[str, list[str]]:
    """code → [labels] (kor + en)"""
    out: dict[str, list[str]] = {}
    axis_data = catalog["axes"][axis]["codes"]
    for code, info in axis_data.items():
        labels = []
        label = info.get("label") or ""
        if label and label != code.lower():
            labels.append(label)
        out[code] = labels
    return out


def step_a_merge_catalog_labels(catalog: dict, aliases: dict) -> dict[str, int]:
    """Catalog의 label들을 aliases tier1에 자동 머지."""
    aliases.setdefault("tier1", {})
    added: dict[str, int] = {}
    for axis in ("accident_type", "hazardous_agent", "work_context"):
        aliases["tier1"].setdefault(axis, {})
        labels = catalog_labels(catalog, axis)
        cnt = 0
        for code, lbls in labels.items():
            existing = set(aliases["tier1"][axis].get(code, []))
            for label in lbls:
                if label and label not in existing:
                    aliases["tier1"][axis].setdefault(code, []).append(label)
                    existing.add(label)
                    cnt += 1
        added[axis] = cnt
    return added


def step_a_remap_known(aliases: dict) -> int:
    """알려진 변형(ELECTRICITY_WORK 등)을 catalog 코드의 alias로 추가."""
    aliases.setdefault("tier1", {})
    aliases["tier1"].setdefault("work_context", {})
    cnt = 0
    for variant, code in KNOWN_WORK_CONTEXT_REMAP.items():
        existing = set(aliases["tier1"]["work_context"].get(code, []))
        if variant not in existing:
            aliases["tier1"]["work_context"].setdefault(code, []).append(variant)
            cnt += 1
    return cnt


def step_a_add_missing_work_contexts(
    catalog: dict, syn_freq: Counter[str]
) -> list[str]:
    """synthetic에서 자주 나오는 영문 work_context 코드를 catalog에 자동 추가."""
    existing = catalog_codes(catalog, "work_context")
    added = []
    for code, cnt in syn_freq.most_common():
        if code in existing:
            continue
        if code in KNOWN_WORK_CONTEXT_REMAP:
            continue
        if not code.replace("_", "").isalnum() or not code.isupper():
            continue
        if cnt < 3:  # 너무 드문 코드는 skip
            continue
        catalog["axes"]["work_context"]["codes"][code] = {
            "label": code.replace("_", " ").lower(),
            "source": "synthetic_v10_auto_added",
        }
        existing.add(code)
        added.append(code)
    return added


async def step_b_llm_map(
    missing: list[tuple[str, int]],
    axis: str,
    valid_codes: set[str],
    aliases: dict,
    *,
    model: str,
    top_n: int,
    concurrency: int,
) -> int:
    """LLM이 한글 missing을 catalog 코드로 매핑."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required for --llm", file=sys.stderr)
        return 0

    targets = missing[:top_n]
    if not targets:
        return 0

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(concurrency)

    schema = {
        "name": "alias_map",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "axis의 valid_codes 중 하나, 또는 'UNKNOWN'",
                },
                "confidence": {"type": "number"},
            },
            "required": ["code", "confidence"],
            "additionalProperties": False,
        },
    }

    sys_prompt = (
        f"당신은 KOSHA 위험요소 분류자입니다. 주어진 표현을 "
        f"{axis} axis의 다음 valid codes 중 하나로 매핑하세요.\n"
        f"valid codes: {sorted(valid_codes)}\n"
        f"매핑 불가능하면 'UNKNOWN' 반환. 동의어/하위개념이면 가장 가까운 코드."
    )

    async def _map(term: str) -> tuple[str, str, float]:
        async with semaphore:
            try:
                r = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "developer", "content": sys_prompt},
                        {"role": "user", "content": f"표현: {term}"},
                    ],
                    response_format={"type": "json_schema", "json_schema": schema},
                    max_completion_tokens=64,
                )
                content = json.loads(r.choices[0].message.content or "{}")
                return term, str(content.get("code", "UNKNOWN")), float(content.get("confidence", 0))
            except Exception as exc:
                return term, "UNKNOWN", 0.0

    print(f"  LLM mapping {len(targets)} {axis} terms (model={model})...")
    results = await asyncio.gather(*(_map(t) for t, _ in targets))
    aliases["tier1"].setdefault(axis, {})
    added = 0
    for term, code, conf in results:
        if code == "UNKNOWN" or code not in valid_codes or conf < 0.6:
            continue
        existing = set(aliases["tier1"][axis].get(code, []))
        if term not in existing:
            aliases["tier1"][axis].setdefault(code, []).append(term)
            added += 1
    print(f"  → {added} new {axis} aliases accepted (conf >= 0.6)")
    return added


async def main_async(args: argparse.Namespace) -> int:
    catalog = load_catalog()
    aliases = load_aliases()
    syn = synthetic_freq()

    # Step A.1 — Catalog labels → aliases
    added = step_a_merge_catalog_labels(catalog, aliases)
    print(f"Step A.1 — catalog labels → aliases:")
    for axis, n in added.items():
        print(f"  {axis}: +{n}")

    # Step A.2 — Known remaps
    remapped = step_a_remap_known(aliases)
    print(f"Step A.2 — known variants (ELECTRICITY_WORK etc.): +{remapped}")

    # Step A.3 — Missing work_context codes (영문) catalog에 추가
    added_wc = step_a_add_missing_work_contexts(catalog, syn["work_context"])
    print(f"Step A.3 — new work_context codes added to catalog: {len(added_wc)}")
    if added_wc:
        print(f"  examples: {added_wc[:10]}")

    if args.llm:
        for axis in ("accident_type", "hazardous_agent", "work_context"):
            valid = catalog_codes(catalog, axis)
            existing_aliases = set(
                v for vs in (aliases.get("tier1") or {}).get(axis, {}).values() for v in vs
            )
            missing = []
            for code, cnt in syn[axis].most_common():
                if code in valid or code in existing_aliases:
                    continue
                missing.append((code, cnt))
            if missing:
                print(f"\nStep B — LLM map {axis}: {len(missing)} missing, top {args.top_n}")
                await step_b_llm_map(
                    missing, axis, valid, aliases,
                    model=args.model, top_n=args.top_n, concurrency=args.concurrency,
                )

    if args.apply:
        CATALOG_PATH.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        ALIASES_PATH.write_text(
            json.dumps(aliases, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nWritten: {CATALOG_PATH.name}, {ALIASES_PATH.name}")
    else:
        print("\nDry-run: no files written. Use --apply.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="실제로 파일 저장")
    parser.add_argument("--llm", action="store_true", help="Step B (LLM 매핑) 실행")
    parser.add_argument("--top-n", type=int, default=100, help="LLM 매핑할 빈도 상위 N개")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano"),
    )
    return parser.parse_args()


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
