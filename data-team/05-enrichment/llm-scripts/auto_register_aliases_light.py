#!/usr/bin/env python3
"""F.1-light — 1회성 alias 등재 제안 생성기.

흐름:
1. synthetic_observations_v*.jsonl 로드 (2,360건 ABox 정답 코퍼스)
2. 각 record의 expected_features 코드별로 "현재 alias로 visual_cues에서 검출 가능한가?" 검사
3. 검출 불가 = gap. (axis, code)별로 cue 모아 LLM에 batch 질의
4. LLM 응답을 confidence로 필터링 → proposals JSON 출력
5. 사람이 검토 후 risk_feature_aliases.json에 머지

정식 F.1의 4-Gate 중 Gate 2 (LLM 분류)만 수행. 다음 검증은 사람 + regression test로 보완.

ENV:
  OPENAI_API_KEY     (--apply 시 필수)
  LLM_RERANK_MODEL   (default: gpt-5.4-nano)

사용:
  python auto_register_aliases_light.py                  # dry-run (gap 통계만)
  python auto_register_aliases_light.py --apply          # 실제 LLM 호출
  python auto_register_aliases_light.py --apply --max-gaps 20  # 비싼 LLM 절약 위해 top 20만
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
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
SYNTHETIC_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "eval-data"
ALIAS_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_aliases.json"
CATALOG_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
OUT_PATH = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "f1_light_proposals.json"


# synthetic JSON uses PLURAL axis keys (accident_types) but catalog/aliases use SINGULAR (accident_type).
AXIS_KEY_MAP = {
    "accident_types": "accident_type",
    "hazardous_agents": "hazardous_agent",
    "work_contexts": "work_context",
    "ppe_states": "ppe_state",
    "environmental": "environmental",
}


SYSTEM_PROMPT = """\
당신은 KOSHA 산업안전 한국어 표현 분류자입니다.
주어진 관찰 사실 문장에서, 특정 안전 코드를 직접 가리키는 한국어 표현 중
기존 alias 사전에 없는 것을 추출합니다.

원칙:
1. 직접 동의어 또는 그 변형만 제안하세요.
   - 예: 코드 FALL(추락)의 alias로 "곤두박이", "꼬꾸라짐"은 OK.
   - 예: "안전난간 없음", "고소작업"은 FALL의 정황/원인이므로 alias 아님.
2. 명사/명사구 형태로 정규화 (조사·문장부호 제거).
3. 확신이 낮으면 빈 list 반환. 억지로 만들지 마세요.
4. 기존 alias에 이미 있는 표현은 제외.
"""

USER_TEMPLATE = """\
코드: {code} ({code_label}) — axis: {axis_label}
기존 alias ({existing_count}개): {existing_sample}

관찰 사실 (synthetic corpus에서 발췌, frequency={freq}회):
{cues_formatted}

위 관찰사실에서, {code}({code_label})를 직접 가리키는 한국어 표현 중 기존 alias에 없는 것을 list로 제안하세요.
없으면 빈 list 반환.
"""

RESPONSE_SCHEMA = {
    "name": "alias_proposal",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "proposed_aliases": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"},
        },
        "required": ["proposed_aliases", "confidence", "reasoning"],
        "additionalProperties": False,
    },
}


def load_synthetic() -> list[dict]:
    rows: list[dict] = []
    for p in sorted(SYNTHETIC_DIR.glob("synthetic_observations_v*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def load_aliases() -> dict:
    return json.loads(ALIAS_PATH.read_text(encoding="utf-8"))


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def find_gaps(rows: list[dict], aliases: dict, catalog: dict) -> tuple[list[dict], dict[str, int]]:
    """Mine record-level (axis, code) gaps. Skip axes that don't exist in production catalog
    (e.g., synthetic has ppe_state/environmental which catalog v3.0 doesn't define yet).
    """
    gaps: list[dict] = []
    skipped_axis_counter: dict[str, int] = {}
    tier1 = aliases.get("tier1", {})
    cat_axes = catalog.get("axes", {})
    for row in rows:
        cid = row.get("case_id", "?")
        cues = [c for c in (row.get("visual_cues") or []) if isinstance(c, str)]
        if not cues:
            continue
        cues_text = " ".join(cues)
        expected = row.get("expected_features") or {}
        for synth_key, codes in expected.items():
            axis = AXIS_KEY_MAP.get(synth_key)
            if not axis or not codes:
                continue
            if axis not in cat_axes:
                skipped_axis_counter[axis] = skipped_axis_counter.get(axis, 0) + len(codes)
                continue
            axis_alias = tier1.get(axis, {})
            axis_codes = cat_axes.get(axis, {}).get("codes", {})
            for code in codes:
                code_label = axis_codes.get(code, {}).get("label", code)
                existing = axis_alias.get(code, [])
                hit = (
                    any(a and a in cues_text for a in existing)
                    or code in cues_text
                    or (code_label and code_label in cues_text)
                )
                if not hit:
                    gaps.append({
                        "case_id": cid,
                        "axis": axis,
                        "code": code,
                        "code_label": code_label,
                        "cues": cues,
                        "existing_aliases_count": len(existing),
                    })
    return gaps, skipped_axis_counter


def aggregate_gaps(gaps: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for g in gaps:
        groups[(g["axis"], g["code"])].append(g)
    out = []
    for (axis, code), group in groups.items():
        seen: set[str] = set()
        rep_cues: list[str] = []
        for g in group:
            for c in g["cues"]:
                if c in seen:
                    continue
                seen.add(c)
                rep_cues.append(c)
                if len(rep_cues) >= 8:
                    break
            if len(rep_cues) >= 8:
                break
        out.append({
            "axis": axis,
            "code": code,
            "code_label": group[0]["code_label"],
            "cues": rep_cues,
            "frequency": len(group),
            "existing_aliases_count": group[0]["existing_aliases_count"],
        })
    return out


async def llm_propose(client, model: str, gap: dict, axis_label: str, existing_aliases: list[str]) -> dict:
    user_prompt = USER_TEMPLATE.format(
        code=gap["code"],
        code_label=gap["code_label"],
        axis_label=axis_label,
        existing_count=len(existing_aliases),
        existing_sample=", ".join(existing_aliases[:10]) or "(없음)",
        freq=gap["frequency"],
        cues_formatted="\n".join(f"  - {c}" for c in gap["cues"]),
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
        return {"error": str(exc), "proposed_aliases": [], "confidence": 0.0, "reasoning": ""}


async def main_async(args: argparse.Namespace) -> int:
    print(f"[1/5] Loading data from {SYNTHETIC_DIR.relative_to(REPO_ROOT)}/")
    rows = load_synthetic()
    aliases = load_aliases()
    catalog = load_catalog()
    print(f"  synthetic records      : {len(rows)}")
    print(f"  catalog axes           : {list(catalog.get('axes', {}).keys())}")
    print(f"  alias tier1 axes       : {list(aliases.get('tier1', {}).keys())}")

    print("\n[2/5] Mining gaps...")
    gaps, skipped = find_gaps(rows, aliases, catalog)
    if skipped:
        print(f"  skipped non-catalog axes (synthetic has, catalog doesn't):")
        for ax, n in sorted(skipped.items(), key=lambda x: -x[1]):
            print(f"    - {ax:20s} {n:5d} code references skipped")
    grouped = aggregate_gaps(gaps)
    grouped.sort(key=lambda x: -x["frequency"])
    print(f"  raw record-level gaps  : {len(gaps)}")
    print(f"  unique (axis, code)    : {len(grouped)}")
    print(f"  top 10 by frequency:")
    for g in grouped[:10]:
        print(f"    freq={g['frequency']:4d}  {g['axis']:20s} {g['code']:25s} ({g['code_label']:15s}) existing_aliases={g['existing_aliases_count']}")

    if args.max_gaps and len(grouped) > args.max_gaps:
        grouped = grouped[: args.max_gaps]
        print(f"  limited to top {args.max_gaps} for this run")

    if args.dry_run:
        print(f"\n[3/5] DRY RUN — would send {len(grouped)} prompts to {args.model}")
        est_cost = len(grouped) * 0.0015
        print(f"  Estimated cost: ~${est_cost:.2f} with gpt-5.4-nano (small prompts)")
        print(f"\nNext step: re-run with --apply (and OPENAI_API_KEY in env)")
        return 0

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY env var required for --apply", file=sys.stderr)
        return 2

    print(f"\n[3/5] LLM batch call ({len(grouped)} gaps, model={args.model}, concurrency={args.concurrency})...")
    try:
        from openai import AsyncOpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
        return 2

    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(args.concurrency)
    cat_axes = catalog.get("axes", {})
    tier1 = aliases.get("tier1", {})

    async def _work(gap):
        async with semaphore:
            axis_label = cat_axes.get(gap["axis"], {}).get("label", gap["axis"])
            existing = tier1.get(gap["axis"], {}).get(gap["code"], [])
            verdict = await llm_propose(client, args.model, gap, axis_label, existing)
            return {**gap, "llm": verdict}

    results = await asyncio.gather(*[_work(g) for g in grouped])

    print("\n[4/5] Aggregating proposals (confidence >= 0.6)...")
    proposals: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    rejected = 0
    errors = 0
    accepted_unique = 0
    for r in results:
        llm = r["llm"] or {}
        if llm.get("error"):
            errors += 1
            continue
        if float(llm.get("confidence", 0.0)) < 0.6:
            rejected += 1
            continue
        existing = set(tier1.get(r["axis"], {}).get(r["code"], []))
        added_for_this_pair = 0
        for raw in llm.get("proposed_aliases") or []:
            alias = (raw or "").strip()
            if not alias or alias in existing:
                continue
            proposals[r["axis"]][r["code"]].append({
                "alias": alias,
                "confidence": round(float(llm.get("confidence", 0.0)), 3),
                "reasoning": (llm.get("reasoning") or "")[:200],
                "frequency_in_synthetic": r["frequency"],
            })
            existing.add(alias)
            added_for_this_pair += 1
        accepted_unique += added_for_this_pair

    # dedupe per (axis, code) — keep highest confidence per alias text
    for axis, code_map in proposals.items():
        for code, entries in list(code_map.items()):
            best: dict[str, dict] = {}
            for e in entries:
                k = e["alias"]
                if k not in best or best[k]["confidence"] < e["confidence"]:
                    best[k] = e
            code_map[code] = sorted(best.values(), key=lambda x: -x["confidence"])

    total_proposed = sum(len(v) for axis_codes in proposals.values() for v in axis_codes.values())

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "stats": {
            "synthetic_records": len(rows),
            "raw_record_level_gaps": len(gaps),
            "unique_axis_code_gaps": len(grouped),
            "llm_calls": len(results),
            "llm_errors": errors,
            "low_confidence_rejected": rejected,
            "total_proposed_aliases": total_proposed,
        },
        "proposals": {axis: dict(code_map) for axis, code_map in proposals.items()},
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[5/5] Saved {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  proposals          : {total_proposed}")
    print(f"  llm errors         : {errors}")
    print(f"  low-conf rejected  : {rejected}")
    print(f"  unique axis-code   : {len(grouped)}")
    print(f"\nNext: 사람이 {OUT_PATH.name} 검토 → risk_feature_aliases.json에 머지")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--apply", action="store_true", help="실제 LLM 호출 + JSON 저장")
    parser.add_argument("--dry-run", action="store_true", help="gap 통계만 출력 (default)")
    parser.add_argument("--max-gaps", type=int, default=0, help="top N (frequency) gap만 처리 (0=전체)")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--model", type=str, default=os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano"))
    args = parser.parse_args()
    if not args.apply:
        args.dry_run = True
    return args


def main() -> None:
    args = parse_args()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
