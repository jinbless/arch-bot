#!/usr/bin/env python3
"""Hazard-Direct Pivot Phase 2 Day 1 — generate_hazard_name_seed.py.

목적: GPT가 자연어로 출력한 hazard.name (예: '끼임/협착', '추락') → catalog
v3.3 529 codes 매핑 seed를 Sonnet 4.6 자동 생성. 사용자 vetted 후
auto_register_aliases.py Gate 1-2 → risk_feature_aliases.json 등재.

입력:
  1. .compare_moellab/*.json — moellab 8 photo 응답 (hazards[].name 분포)
  2. serving-team/08-app/backend/app/data/risk_feature_catalog.json (529 codes)

출력:
  data-team/05-enrichment/runtime-artifacts/hazard_name_seed.json
  {
    "generated_at": "2026-05-19T...",
    "source_photos": 8,
    "unique_names": 14,
    "total_occurrences": 37,
    "mappings": [
      {"name": "끼임/협착", "frequency": 4, "axis": "accident_type",
       "code": "ENTANGLE", "confidence": 0.95, "reasoning": "...",
       "vetted": false}
    ],
    "unmappable": [
      {"name": "...", "frequency": 1, "reasoning": "no matching catalog code"}
    ]
  }

ENV:
  ANTHROPIC_API_KEY  (--apply 시 필수)

사용:
  python generate_hazard_name_seed.py --dry-run                 # 분포만 출력
  python generate_hazard_name_seed.py --apply                   # Sonnet 호출 (~$0.20)
  python generate_hazard_name_seed.py --apply --min-conf 0.85   # stricter (default 0.80)

다음 단계 (사용자 vetted 후):
  1. hazard_name_seed.json 수동 검토 + vetted=true 설정
  2. auto_register_aliases.py가 vetted entries를 Gate 1-2로 검증 + 등재
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
COMPARE_DIR = REPO_ROOT / ".compare_moellab"
CATALOG_PATH = (
    REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
)
SEED_OUT = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "hazard_name_seed.json"
AUDIT_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "hazard_name_seed_audit.jsonl"
)

SONNET_MODEL = "claude-sonnet-4-6"
SONNET_MAX_TOKENS = 500
SONNET_CONCURRENCY = 4
DEFAULT_MIN_CONFIDENCE = 0.80


# ---------------- catalog + moellab loaders ---------------- #


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def get_axis_codes(catalog: dict) -> dict[str, list[str]]:
    """axis name → sorted list of codes."""
    out: dict[str, list[str]] = {}
    for axis_name, axis_info in (catalog.get("axes") or {}).items():
        if isinstance(axis_info, dict):
            codes = (axis_info.get("codes") or {})
            out[axis_name] = sorted(codes.keys() if isinstance(codes, dict) else codes)
    return out


def collect_hazard_names(compare_dir: Path) -> tuple[Counter, dict[str, list[str]]]:
    """moellab 응답 8개에서 hazards[].name 빈도 + 사진별 hazard list 수집."""
    counter: Counter = Counter()
    per_photo: dict[str, list[str]] = {}
    for fp in sorted(compare_dir.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  skip {fp.name}: {e}", file=sys.stderr)
            continue
        names = [h.get("name", "").strip() for h in (data.get("hazards") or []) if h.get("name")]
        per_photo[fp.stem] = names
        counter.update(names)
    return counter, per_photo


# ---------------- Sonnet prompt + tool ---------------- #


SONNET_SYSTEM = """\
당신은 KOSHA 산업안전 hazard 자연어 → catalog code 매핑 전문가입니다.
GPT가 자연어로 출력한 hazard.name (예: '끼임/협착', '추락', '감전')을
주어진 catalog vocabulary 내에서 가장 적합한 axis + code로 매핑합니다.

원칙:
1. 자연어 hazard.name은 보통 사고형 ('accident_type'으로 매핑이 가장 흔함)
2. 자신 없으면 axis='UNMAPPABLE', code='UNMAPPABLE' 반환 (보수성 우선)
3. 추출 코드는 반드시 catalog vocabulary 내에 있어야 함
4. confidence ≥ 0.85는 명확히 일치, 0.60-0.85는 유사하지만 확정 어려움, <0.60은 UNMAPPABLE 추천
5. axis는 사고형 → accident_type / 위험물질 → hazardous_agent / 작업맥락 → work_context / PPE → ppe_state / 환경 → environmental
"""


def make_user_prompt(name: str, frequency: int, axis_codes: dict[str, list[str]]) -> str:
    parts = [f"자연어 hazard 카테고리: '{name}' (8 photo 중 {frequency}회 등장)\n"]
    parts.append("catalog vocabulary (axis별):\n")
    for axis, codes in axis_codes.items():
        # 너무 길면 잘라서 표시 (Sonnet context 절약)
        codes_str = ", ".join(codes[:80])
        if len(codes) > 80:
            codes_str += f", ... ({len(codes)}개 전체)"
        parts.append(f"\n[{axis}] ({len(codes)} codes):\n{codes_str}\n")
    parts.append(
        "\n이 hazard 자연어를 가장 적합한 (axis, code)로 매핑하세요. "
        "확신 없으면 UNMAPPABLE."
    )
    return "".join(parts)


def make_sonnet_tool(axis_codes: dict[str, list[str]]) -> dict:
    """Tool schema with axis enum + free-string code (post-validation)."""
    return {
        "name": "map_hazard_name",
        "description": "Map a natural-language hazard.name to a catalog (axis, code) pair.",
        "input_schema": {
            "type": "object",
            "properties": {
                "axis": {
                    "type": "string",
                    "enum": [
                        "accident_type",
                        "hazardous_agent",
                        "work_context",
                        "ppe_state",
                        "environmental",
                        "UNMAPPABLE",
                    ],
                },
                "code": {
                    "type": "string",
                    "description": (
                        "catalog code (예: ENTANGLE, FALL_FROM_HEIGHT). "
                        "axis에 해당하는 vocabulary 내에 있어야 함. UNMAPPABLE이면 'UNMAPPABLE'."
                    ),
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "reasoning": {"type": "string", "maxLength": 300},
            },
            "required": ["axis", "code", "confidence", "reasoning"],
        },
    }


# ---------------- Sonnet caller ---------------- #


async def map_one(client, name: str, frequency: int, axis_codes: dict[str, list[str]], tool: dict) -> dict:
    try:
        msg = await client.messages.create(
            model=SONNET_MODEL,
            max_tokens=SONNET_MAX_TOKENS,
            system=SONNET_SYSTEM,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": make_user_prompt(name, frequency, axis_codes)}],
        )
        # Extract tool_use block
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use":
                return dict(block.input)
        return {"error": "no_tool_use_block"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:200]}


# ---------------- validation + audit ---------------- #


def validate_mapping(mapping: dict, axis_codes: dict[str, list[str]]) -> tuple[bool, str]:
    axis = mapping.get("axis")
    code = mapping.get("code")
    if axis == "UNMAPPABLE" or code == "UNMAPPABLE":
        return False, "unmappable"
    if axis not in axis_codes:
        return False, f"unknown axis: {axis}"
    if code not in axis_codes[axis]:
        return False, f"code '{code}' not in axis '{axis}' vocabulary"
    return True, "ok"


def append_audit(records: list[dict]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------- main ---------------- #


async def main_async(args: argparse.Namespace) -> int:
    catalog = load_catalog()
    axis_codes = get_axis_codes(catalog)
    total_codes = sum(len(v) for v in axis_codes.values())
    print(f"[catalog v3.3] {len(axis_codes)} axes / {total_codes} codes")

    counter, per_photo = collect_hazard_names(COMPARE_DIR)
    if not counter:
        print(f"ERROR: no hazard names found in {COMPARE_DIR}", file=sys.stderr)
        return 2

    unique_names = list(counter.keys())
    print(f"[moellab] {len(per_photo)} photos / {len(unique_names)} unique hazard names / {sum(counter.values())} occurrences")
    print("\nTop 20 names by frequency:")
    for name, freq in counter.most_common(20):
        print(f"  {freq:3d}  {name}")

    if args.dry_run:
        print("\n[dry-run] No Sonnet calls. Use --apply to generate seed.")
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY required", file=sys.stderr)
        return 2
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        print("ERROR: anthropic not installed (pip install anthropic)", file=sys.stderr)
        return 2

    # Cost estimate: ~700 input tokens + ~150 output tokens per name × $3/1M in + $15/1M out
    est_cost = len(unique_names) * (700 * 3 / 1_000_000 + 150 * 15 / 1_000_000)
    print(f"\nEstimated Sonnet 4.6 cost: ~${est_cost:.3f} ({len(unique_names)} names)")
    if args.max_names and len(unique_names) > args.max_names:
        unique_names = unique_names[: args.max_names]
        print(f"Capped to {args.max_names} for this run.")

    client = AsyncAnthropic(api_key=api_key)
    tool = make_sonnet_tool(axis_codes)
    sem = asyncio.Semaphore(SONNET_CONCURRENCY)

    async def _work(name: str):
        async with sem:
            return name, await map_one(client, name, counter[name], axis_codes, tool)

    print(f"\n[Sonnet 4.6] mapping {len(unique_names)} hazard names...")
    results = await asyncio.gather(*[_work(n) for n in unique_names])

    mappings: list[dict] = []
    unmappable: list[dict] = []
    audit_rows: list[dict] = []
    accepted = 0
    rejected = 0

    for name, verdict in results:
        if verdict.get("error"):
            rejected += 1
            audit_rows.append({"name": name, "result": "error", "error": verdict["error"]})
            unmappable.append({"name": name, "frequency": counter[name], "reason": "sonnet_error", "error": verdict["error"]})
            continue
        ok, reason = validate_mapping(verdict, axis_codes)
        conf = float(verdict.get("confidence") or 0)
        row = {
            "name": name,
            "frequency": counter[name],
            "axis": verdict.get("axis"),
            "code": verdict.get("code"),
            "confidence": conf,
            "reasoning": (verdict.get("reasoning") or "")[:300],
            "validation": reason,
        }
        audit_rows.append({**row, "result": "accepted" if ok else "rejected"})
        if not ok or conf < args.min_conf:
            rejected += 1
            unmappable.append({**row, "reason": "low_conf" if (ok and conf < args.min_conf) else reason})
            continue
        accepted += 1
        mappings.append({**row, "vetted": False})

    # Sort accepted by frequency desc
    mappings.sort(key=lambda r: -r["frequency"])
    unmappable.sort(key=lambda r: -r["frequency"])

    seed = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": SONNET_MODEL,
        "min_confidence": args.min_conf,
        "source_photos": len(per_photo),
        "unique_names": len(counter),
        "total_occurrences": sum(counter.values()),
        "accepted": accepted,
        "rejected": rejected,
        "mappings": mappings,
        "unmappable": unmappable,
        "per_photo_names": {k: v for k, v in per_photo.items()},
    }
    SEED_OUT.parent.mkdir(parents=True, exist_ok=True)
    SEED_OUT.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding="utf-8")
    append_audit(audit_rows)

    print(f"\nResults:")
    print(f"  unique names processed : {len(unique_names)}")
    print(f"  accepted (≥ {args.min_conf:.2f}) : {accepted}")
    print(f"  rejected / unmappable  : {rejected}")
    print(f"\n  seed written: {SEED_OUT.relative_to(REPO_ROOT)}")
    print(f"  audit  written: {AUDIT_PATH.relative_to(REPO_ROOT)}")
    print(f"\n[next step] 사용자 vetted (mappings[*].vetted=true) → auto_register_aliases.py Gate 1-2")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--dry-run", action="store_true", help="분포만 출력 (Sonnet 호출 안 함)")
    p.add_argument("--apply", action="store_true", help="Sonnet 호출 + seed 저장")
    p.add_argument("--min-conf", type=float, default=DEFAULT_MIN_CONFIDENCE, help=f"minimum confidence (default {DEFAULT_MIN_CONFIDENCE})")
    p.add_argument("--max-names", type=int, default=0, help="cap number of names to map (0 = all)")
    args = p.parse_args(argv)
    if not (args.dry_run or args.apply):
        p.error("--dry-run 또는 --apply 중 하나 필수")
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
