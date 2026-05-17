#!/usr/bin/env python3
"""Phase F.1 helper — Recover catalog-mismatched codes via 3-stage hybrid pipeline.

light proposals(`f1_light_proposals.json`)의 944 catalog-mismatched 코드를
다음 3단계로 valid catalog enum에 매핑한다:

  Stage 1 (Rule, 0 cost): catalog label/sub label/기존 alias 정확 일치
  Stage 2 (Embedding, ~$0.02): text-embedding-3-small cosine ≥ 0.7
  Stage 3 (Sonnet 4.6, ~$3-5): residual hard cases — Korean industrial reasoning

산출:
  - f1_light_proposals_recovered.json (auto_register_aliases.py drop-in 입력)
  - runtime-artifacts/catalog_mismatch_audit.jsonl (method + confidence per code)
  - runtime-artifacts/new_subcode_candidates.jsonl (F.2 forward — catalog 신규 등재 후보)

ENV:
  OPENAI_API_KEY      (Stage 2 embedding, 필수 unless --skip-embedding)
  ANTHROPIC_API_KEY   (Stage 3 Sonnet, 필수 unless --skip-sonnet)

사용:
  python recover_catalog_mismatch.py                         # full 3-stage
  python recover_catalog_mismatch.py --skip-sonnet           # Rule + Embedding only
  python recover_catalog_mismatch.py --skip-embedding --skip-sonnet  # Rule only (dry mode)
  python recover_catalog_mismatch.py --max-residual 50       # cap Sonnet calls
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths + Constants
# ---------------------------------------------------------------------------


def find_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = find_root()
RUNTIME = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
LIGHT_PATH = RUNTIME / "f1_light_proposals.json"
RECOVERED_PATH = RUNTIME / "f1_light_proposals_recovered.json"
AUDIT_PATH = RUNTIME / "catalog_mismatch_audit.jsonl"
NEW_SUBCODE_PATH = RUNTIME / "new_subcode_candidates.jsonl"
EMBEDDING_CACHE_PATH = RUNTIME / "alias_embedding_cache.json"
RECOVERY_EMBED_CACHE = RUNTIME / "catalog_label_embedding_cache.json"
CATALOG_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
ALIAS_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_aliases.json"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_CUTOFF = 0.7
EMBED_BATCH = 100

SONNET_MODEL = "claude-sonnet-4-6"
SONNET_MAX_TOKENS = 500
SONNET_CONCURRENCY = 4
SONNET_CONFIDENCE_MIN = 0.6  # Sonnet 자체 confidence threshold


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_light() -> dict[str, Any]:
    return json.loads(LIGHT_PATH.read_text(encoding="utf-8"))


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def load_existing_aliases() -> dict[str, dict[str, list[str]]]:
    """Return {axis: {code: [aliases]}} from main aliases file."""
    data = json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    out: dict[str, dict[str, list[str]]] = {}
    for axis, code_map in data.get("tier1", {}).items():
        if not isinstance(code_map, dict):
            continue
        out[axis] = {
            code: [a for a in aliases if isinstance(a, str)]
            for code, aliases in code_map.items()
            if isinstance(aliases, list)
        }
    return out


def build_valid_codes(catalog: dict) -> dict[str, set[str]]:
    """{axis: set(main_codes + sub_codes)}."""
    out: dict[str, set[str]] = defaultdict(set)
    for axis, axis_def in catalog.get("axes", {}).items():
        for code, code_def in (axis_def.get("codes") or {}).items():
            out[axis].add(code)
            if isinstance(code_def, dict):
                for sub in (code_def.get("sub") or []) or []:
                    if isinstance(sub, str):
                        out[axis].add(sub)
    return out


def collect_mismatched(
    light: dict, valid_codes: dict[str, set[str]]
) -> list[dict[str, Any]]:
    """Return [{axis, code, entries[]}] for each (axis, code) not in catalog."""
    out: list[dict] = []
    for axis, code_map in light.get("proposals", {}).items():
        valid_for_axis = valid_codes.get(axis, set())
        for code, entries in code_map.items():
            if code in valid_for_axis:
                continue
            out.append({"axis": axis, "code": code, "entries": entries})
    return out


# ---------------------------------------------------------------------------
# Stage 1: Rule-based (catalog label + existing alias exact match)
# ---------------------------------------------------------------------------


def build_label_to_code(catalog: dict) -> dict[str, dict[str, str]]:
    """{axis: {label_korean: code}}. Main code labels only (sub has no label)."""
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for axis, axis_def in catalog.get("axes", {}).items():
        for code, code_def in (axis_def.get("codes") or {}).items():
            if isinstance(code_def, dict):
                label = code_def.get("label")
                if isinstance(label, str) and label.strip():
                    out[axis][label.strip()] = code
    return out


def build_alias_to_code(existing: dict[str, dict[str, list[str]]]) -> dict[str, dict[str, str]]:
    """{axis: {alias_text: code}}."""
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for axis, code_map in existing.items():
        for code, aliases in code_map.items():
            for a in aliases:
                a = a.strip()
                if a:
                    out[axis][a] = code
    return out


def stage1_rule(
    mismatched: list[dict],
    catalog: dict,
    existing: dict,
) -> tuple[dict[tuple[str, str], dict], list[dict]]:
    """Match by label or existing alias. Returns (recovered, residual).

    recovered: {(axis, code): {recovered_axis, recovered_code, method, confidence, reason}}
    """
    label_map = build_label_to_code(catalog)
    alias_map = build_alias_to_code(existing)

    recovered: dict[tuple[str, str], dict] = {}
    residual: list[dict] = []
    for item in mismatched:
        axis = item["axis"]
        code = item["code"]

        # 1a. Catalog label exact match (same axis)
        if code in label_map.get(axis, {}):
            recovered[(axis, code)] = {
                "recovered_axis": axis,
                "recovered_code": label_map[axis][code],
                "method": "rule_label",
                "confidence": 1.0,
                "reason": f"한국어 표현이 catalog axes.{axis}.codes.{label_map[axis][code]}.label과 정확 일치",
            }
            continue

        # 1b. Catalog label match in OTHER axis (axis-flip)
        flipped = None
        for other_axis, lm in label_map.items():
            if other_axis == axis:
                continue
            if code in lm:
                flipped = (other_axis, lm[code])
                break
        if flipped:
            recovered[(axis, code)] = {
                "recovered_axis": flipped[0],
                "recovered_code": flipped[1],
                "method": "rule_label_flip",
                "confidence": 0.95,
                "reason": f"label 매칭 (axis {axis} → {flipped[0]}, code {flipped[1]})",
            }
            continue

        # 1c. Existing alias exact match (same axis)
        if code in alias_map.get(axis, {}):
            recovered[(axis, code)] = {
                "recovered_axis": axis,
                "recovered_code": alias_map[axis][code],
                "method": "rule_alias",
                "confidence": 1.0,
                "reason": f"한국어 표현이 risk_feature_aliases.json[{axis}.{alias_map[axis][code]}]에 이미 등재된 alias",
            }
            continue

        # 1d. Existing alias match in OTHER axis
        flipped_alias = None
        for other_axis, am in alias_map.items():
            if other_axis == axis:
                continue
            if code in am:
                flipped_alias = (other_axis, am[code])
                break
        if flipped_alias:
            recovered[(axis, code)] = {
                "recovered_axis": flipped_alias[0],
                "recovered_code": flipped_alias[1],
                "method": "rule_alias_flip",
                "confidence": 0.9,
                "reason": f"alias 매칭 (axis {axis} → {flipped_alias[0]}, code {flipped_alias[1]})",
            }
            continue

        residual.append(item)

    return recovered, residual


# ---------------------------------------------------------------------------
# Stage 2: Embedding similarity
# ---------------------------------------------------------------------------


def _label_cache_key(catalog: dict) -> str:
    """Single hash of full label set — invalidates on catalog change."""
    payload = json.dumps(
        {
            axis: {c: cd.get("label", "") for c, cd in (ad.get("codes") or {}).items()}
            for axis, ad in catalog.get("axes", {}).items()
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_label_cache() -> dict:
    if not RECOVERY_EMBED_CACHE.is_file():
        return {}
    try:
        return json.loads(RECOVERY_EMBED_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_label_cache(cache: dict) -> None:
    RECOVERY_EMBED_CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = RECOVERY_EMBED_CACHE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RECOVERY_EMBED_CACHE)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


async def embed_batch(client, texts: list[str]) -> list[list[float]]:
    r = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in r.data]


async def stage2_embedding(
    openai_client,
    residual: list[dict],
    catalog: dict,
    existing: dict,
    cutoff: float = EMBEDDING_CUTOFF,
) -> tuple[dict[tuple[str, str], dict], list[dict]]:
    """Embed residual Korean codes; compare to catalog label + existing aliases per axis."""
    if not residual:
        return {}, []

    # Build per-axis text → embedding map (catalog label + existing aliases)
    cache_key = _label_cache_key(catalog)
    cache = load_label_cache()
    cache_root = cache.get(cache_key)
    if cache_root is None:
        cache_root = cache[cache_key] = {"axes": {}}

    # Collect label/alias texts needing embedding
    work: list[tuple[str, str, str]] = []  # (axis, code, text)
    axis_texts: dict[str, dict[str, str]] = defaultdict(dict)  # axis → {text: code}
    for axis, axis_def in catalog.get("axes", {}).items():
        for code, code_def in (axis_def.get("codes") or {}).items():
            if isinstance(code_def, dict):
                label = (code_def.get("label") or "").strip()
                if label:
                    axis_texts[axis][label] = code
        for code, aliases in existing.get(axis, {}).items():
            for a in aliases:
                a = a.strip()
                if a:
                    axis_texts[axis][a] = code
        cached_axis = cache_root["axes"].setdefault(axis, {})
        for text in axis_texts[axis]:
            if text not in cached_axis:
                work.append((axis, axis_texts[axis][text], text))
    # Batch embed
    if work:
        for i in range(0, len(work), EMBED_BATCH):
            batch = work[i : i + EMBED_BATCH]
            texts = [t for (_, _, t) in batch]
            embs = await embed_batch(openai_client, texts)
            for (axis, code, text), emb in zip(batch, embs):
                cache_root["axes"][axis][text] = {"code": code, "emb": emb}
        save_label_cache(cache)

    # Embed residual Korean codes
    residual_texts = [item["code"] for item in residual]
    residual_embs: list[list[float]] = []
    for i in range(0, len(residual_texts), EMBED_BATCH):
        embs = await embed_batch(openai_client, residual_texts[i : i + EMBED_BATCH])
        residual_embs.extend(embs)

    recovered: dict[tuple[str, str], dict] = {}
    still_residual: list[dict] = []
    for item, emb in zip(residual, residual_embs):
        axis = item["axis"]
        code_orig = item["code"]
        best_sim = 0.0
        best: tuple[str, str] | None = None  # (axis, code)
        # Search same axis first (preferred)
        for text, info in cache_root["axes"].get(axis, {}).items():
            sim = cosine(emb, info["emb"])
            if sim > best_sim:
                best_sim = sim
                best = (axis, info["code"])
        # Also check other axes (axis-flip)
        best_flip_sim = 0.0
        best_flip: tuple[str, str] | None = None
        for other_axis, label_map in cache_root["axes"].items():
            if other_axis == axis:
                continue
            for text, info in label_map.items():
                sim = cosine(emb, info["emb"])
                if sim > best_flip_sim:
                    best_flip_sim = sim
                    best_flip = (other_axis, info["code"])
        # Prefer same-axis unless flip significantly higher
        if best and best_sim >= cutoff and best_sim >= best_flip_sim - 0.05:
            recovered[(axis, code_orig)] = {
                "recovered_axis": best[0],
                "recovered_code": best[1],
                "method": "embedding_same_axis",
                "confidence": round(best_sim, 4),
                "reason": f"cosine {best_sim:.3f} (same axis preferred over flip {best_flip_sim:.3f})",
            }
        elif best_flip and best_flip_sim >= cutoff:
            recovered[(axis, code_orig)] = {
                "recovered_axis": best_flip[0],
                "recovered_code": best_flip[1],
                "method": "embedding_axis_flip",
                "confidence": round(best_flip_sim, 4),
                "reason": f"cosine {best_flip_sim:.3f} (axis {axis} → {best_flip[0]})",
            }
        else:
            item["_top_sim"] = round(max(best_sim, best_flip_sim), 4)
            item["_top_match"] = best_flip if best_flip_sim > best_sim else best
            still_residual.append(item)

    return recovered, still_residual


# ---------------------------------------------------------------------------
# Stage 3: Sonnet 4.6 (claude-sonnet-4-6)
# ---------------------------------------------------------------------------


SONNET_SYSTEM = """\
당신은 KOSHA 산업안전 위험 카탈로그 매핑 전문가입니다.
주어진 한국어 위험 표현이 catalog의 어느 axis/code에 속하는지 판정하세요.

원칙:
1. catalog의 main code (UPPER_SNAKE_CASE) 또는 sub code를 우선 선택.
2. 적절한 catalog code가 없으면 is_new_subcode_candidate=true로 표시하고,
   new_subcode_suggestion에 영문 enum 형태(UPPER_SNAKE_CASE)로 제안.
3. light이 부여한 axis가 잘못된 경우 correct_axis에 정정.
4. confidence는 매핑 강도 0.0~1.0.
"""


def _stage3_user_prompt(item: dict, axis_catalog_summary: dict[str, str]) -> str:
    axis = item["axis"]
    code = item["code"]
    top_sim = item.get("_top_sim", 0.0)
    top_match = item.get("_top_match")
    sim_note = ""
    if top_match:
        sim_note = f"\nStage 2 embedding 최고 매칭: axis={top_match[0]}, code={top_match[1]}, cosine={top_sim:.3f} (cutoff 0.7 미만으로 reject)"
    sample_aliases = [e.get("alias", "") for e in (item.get("entries") or [])[:5]]
    return f"""\
한국어 위험 표현: "{code}"
원래 부여된 axis: {axis}
이 표현 아래 묶인 light alias 후보 (참고): {sample_aliases}
{sim_note}

각 axis의 catalog 요약 (code: label):
{axis_catalog_summary.get('accident_type', '')}
{axis_catalog_summary.get('hazardous_agent', '')}
{axis_catalog_summary.get('work_context', '')}

판정: 이 한국어 표현이 어떤 catalog code에 속하는지, 또는 catalog에 없는 신규 sub-code 후보인지 결정하세요.
"""


SONNET_TOOL = {
    "name": "map_catalog_code",
    "description": "Map a Korean safety expression to a KOSHA catalog enum code, or flag as new subcode candidate.",
    "input_schema": {
        "type": "object",
        "properties": {
            "correct_axis": {
                "type": "string",
                "enum": ["accident_type", "hazardous_agent", "work_context", "ppe_state", "environmental"],
                "description": "Catalog axis the term belongs to.",
            },
            "code": {
                "type": "string",
                "description": "Catalog enum code (UPPER_SNAKE_CASE) if matches. Empty string if is_new_subcode_candidate.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "is_new_subcode_candidate": {
                "type": "boolean",
                "description": "True if no existing catalog code fits well.",
            },
            "new_subcode_suggestion": {
                "type": "string",
                "description": "Suggested new enum (UPPER_SNAKE_CASE) if is_new=true. Empty otherwise.",
            },
            "reason": {
                "type": "string",
                "description": "Korean 1-2 sentence justification.",
            },
        },
        "required": [
            "correct_axis",
            "code",
            "confidence",
            "is_new_subcode_candidate",
            "new_subcode_suggestion",
            "reason",
        ],
    },
}


def _axis_catalog_summary(catalog: dict) -> dict[str, str]:
    """Compact text representation of catalog per axis for prompt context."""
    out: dict[str, str] = {}
    for axis, axis_def in catalog.get("axes", {}).items():
        codes = []
        for code, code_def in (axis_def.get("codes") or {}).items():
            label = ""
            if isinstance(code_def, dict):
                label = code_def.get("label", "")
            codes.append(f"  - {code}: {label}")
        out[axis] = f"[{axis}]\n" + "\n".join(codes)
    return out


async def sonnet_map_one(client, item: dict, axis_summary: dict[str, str]) -> dict[str, Any]:
    prompt = _stage3_user_prompt(item, axis_summary)
    try:
        msg = await client.messages.create(
            model=SONNET_MODEL,
            max_tokens=SONNET_MAX_TOKENS,
            temperature=0,
            system=SONNET_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            tools=[SONNET_TOOL],
            tool_choice={"type": "tool", "name": "map_catalog_code"},
        )
        # Extract tool_use block
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "map_catalog_code":
                return dict(block.input)
        return {"error": "no tool_use block returned"}
    except Exception as exc:
        return {"error": str(exc)}


async def stage3_sonnet(
    anthropic_client,
    residual: list[dict],
    catalog: dict,
    max_residual: int = 0,
) -> tuple[dict[tuple[str, str], dict], list[dict], list[dict]]:
    """Run Sonnet on residual codes. Returns (recovered, new_subcodes, still_residual)."""
    if not residual:
        return {}, [], []
    if max_residual and len(residual) > max_residual:
        residual = residual[:max_residual]
        print(f"  (capped to first {max_residual} residual for Sonnet cost control)")

    axis_summary = _axis_catalog_summary(catalog)
    valid_codes_per_axis = {ax: {c for c, _ in []} for ax in catalog.get("axes", {})}
    for ax, axis_def in catalog.get("axes", {}).items():
        valid_codes_per_axis[ax] = set((axis_def.get("codes") or {}).keys())
        for code, cd in (axis_def.get("codes") or {}).items():
            if isinstance(cd, dict):
                valid_codes_per_axis[ax].update((cd.get("sub") or []) or [])

    sem = asyncio.Semaphore(SONNET_CONCURRENCY)

    async def _work(item):
        async with sem:
            return item, await sonnet_map_one(anthropic_client, item, axis_summary)

    results = await asyncio.gather(*[_work(it) for it in residual])

    recovered: dict[tuple[str, str], dict] = {}
    new_subcodes: list[dict] = []
    still: list[dict] = []
    errors = 0
    for item, verdict in results:
        axis = item["axis"]
        code = item["code"]
        if verdict.get("error"):
            errors += 1
            item["_sonnet_error"] = verdict["error"]
            still.append(item)
            continue
        is_new = bool(verdict.get("is_new_subcode_candidate"))
        confidence = float(verdict.get("confidence", 0.0))
        correct_axis = verdict.get("correct_axis", axis)
        if is_new:
            new_subcodes.append(
                {
                    "from_axis": axis,
                    "from_code": code,
                    "correct_axis": correct_axis,
                    "suggested_code": verdict.get("new_subcode_suggestion", ""),
                    "confidence": round(confidence, 3),
                    "reason": verdict.get("reason", ""),
                    "entry_count": len(item.get("entries") or []),
                }
            )
            item["_sonnet_verdict"] = verdict
            still.append(item)  # not recovered to existing code
            continue
        if confidence < SONNET_CONFIDENCE_MIN:
            item["_sonnet_verdict"] = verdict
            still.append(item)
            continue
        proposed_code = verdict.get("code", "")
        if proposed_code not in valid_codes_per_axis.get(correct_axis, set()):
            item["_sonnet_verdict"] = verdict
            item["_sonnet_invalid_code"] = proposed_code
            still.append(item)
            continue
        recovered[(axis, code)] = {
            "recovered_axis": correct_axis,
            "recovered_code": proposed_code,
            "method": "sonnet" + ("_axis_flip" if correct_axis != axis else ""),
            "confidence": round(confidence, 3),
            "reason": verdict.get("reason", ""),
        }

    if errors:
        print(f"  Sonnet errors: {errors}")
    return recovered, new_subcodes, still


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def merge_recovered_into_light(light: dict, recovered: dict[tuple[str, str], dict]) -> dict:
    """Build new light-shaped dict where mismatched (axis, code) groups are reassigned.

    Entries get _recovered_from + _recovery_method metadata for traceability.
    """
    out_proposals: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    # Original valid entries (untouched)
    for axis, code_map in light.get("proposals", {}).items():
        for code, entries in code_map.items():
            key = (axis, code)
            if key in recovered:
                rec = recovered[key]
                target_axis = rec["recovered_axis"]
                target_code = rec["recovered_code"]
                for e in entries:
                    e2 = dict(e)
                    e2["_recovered_from"] = code
                    e2["_recovered_from_axis"] = axis
                    e2["_recovery_method"] = rec["method"]
                    e2["_recovery_confidence"] = rec["confidence"]
                    out_proposals[target_axis][target_code].append(e2)
            else:
                # passthrough (valid or unrecovered — caller decides whether to include unrecovered)
                for e in entries:
                    out_proposals[axis][code].append(dict(e))
    return {
        "stats": light.get("stats", {}),
        "proposals": {axis: dict(cm) for axis, cm in out_proposals.items()},
    }


def write_recovered(light: dict, recovered: dict, recovery_stats: dict) -> None:
    merged = merge_recovered_into_light(light, recovered)
    merged["recovery_metadata"] = recovery_stats
    RECOVERED_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = RECOVERED_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(RECOVERED_PATH)


def write_audit(recovered: dict[tuple[str, str], dict]) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for (axis, code), rec in recovered.items():
            f.write(
                json.dumps(
                    {
                        "ts": ts,
                        "from_axis": axis,
                        "from_code": code,
                        "to_axis": rec["recovered_axis"],
                        "to_code": rec["recovered_code"],
                        "method": rec["method"],
                        "confidence": rec["confidence"],
                        "reason": rec["reason"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def write_new_subcodes(new_subcodes: list[dict]) -> None:
    if not new_subcodes:
        return
    ts = datetime.now(timezone.utc).isoformat()
    NEW_SUBCODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NEW_SUBCODE_PATH.open("a", encoding="utf-8") as f:
        for n in new_subcodes:
            f.write(json.dumps({"ts": ts, **n}, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CLI + main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--skip-embedding", action="store_true", help="Skip Stage 2 (embedding)")
    p.add_argument("--skip-sonnet", action="store_true", help="Skip Stage 3 (Sonnet 4.6)")
    p.add_argument(
        "--max-residual",
        type=int,
        default=0,
        help="Cap Stage 3 Sonnet calls (0 = no cap)",
    )
    p.add_argument("--cutoff", type=float, default=EMBEDDING_CUTOFF, help="Stage 2 cosine cutoff (default 0.7)")
    p.add_argument("--dry", action="store_true", help="Print plan only, no API calls")
    return p.parse_args()


async def main_async(args: argparse.Namespace) -> int:
    print("=" * 70)
    print("F.1 recover_catalog_mismatch — 3-stage hybrid pipeline")
    print("=" * 70)

    light = load_light()
    catalog = load_catalog()
    existing = load_existing_aliases()
    valid_codes = build_valid_codes(catalog)

    mismatched = collect_mismatched(light, valid_codes)
    total_entries = sum(len(m["entries"]) for m in mismatched)
    print(f"Mismatched (axis, code) pairs: {len(mismatched)}")
    print(f"  total alias entries under them: {total_entries}")
    print()

    if args.dry:
        print("[dry] Would proceed with Stage 1 → 2 → 3.")
        return 0

    # Stage 1
    print("[Stage 1] Rule-based (catalog label + existing alias exact match)...")
    rec1, residual1 = stage1_rule(mismatched, catalog, existing)
    method_counter = Counter(r["method"] for r in rec1.values())
    print(f"  recovered: {len(rec1)} / residual: {len(residual1)}")
    for m, n in method_counter.most_common():
        print(f"    {m:25s}: {n}")
    print()

    # Stage 2
    rec2: dict = {}
    residual2 = residual1
    if not args.skip_embedding and residual1:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY required for Stage 2", file=sys.stderr)
            return 2
        try:
            from openai import AsyncOpenAI
        except ImportError:
            print("ERROR: openai not installed", file=sys.stderr)
            return 2
        openai_client = AsyncOpenAI(api_key=api_key)
        print(f"[Stage 2] Embedding (text-embedding-3-small, cutoff {args.cutoff})...")
        rec2, residual2 = await stage2_embedding(
            openai_client, residual1, catalog, existing, cutoff=args.cutoff
        )
        method_counter2 = Counter(r["method"] for r in rec2.values())
        print(f"  recovered: {len(rec2)} / residual: {len(residual2)}")
        for m, n in method_counter2.most_common():
            print(f"    {m:25s}: {n}")
        print()

    # Stage 3
    rec3: dict = {}
    new_subcodes: list = []
    residual3 = residual2
    if not args.skip_sonnet and residual2:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY required for Stage 3 (Sonnet 4.6)", file=sys.stderr)
            return 2
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            print("ERROR: anthropic not installed", file=sys.stderr)
            return 2
        anthropic_client = AsyncAnthropic(api_key=api_key)
        print(f"[Stage 3] Sonnet 4.6 ({SONNET_MODEL}, conc {SONNET_CONCURRENCY})...")
        rec3, new_subcodes, residual3 = await stage3_sonnet(
            anthropic_client, residual2, catalog, max_residual=args.max_residual
        )
        method_counter3 = Counter(r["method"] for r in rec3.values())
        print(f"  recovered: {len(rec3)} / new_subcode_candidates: {len(new_subcodes)} / residual: {len(residual3)}")
        for m, n in method_counter3.most_common():
            print(f"    {m:25s}: {n}")
        print()

    # Merge + write
    all_rec = {**rec1, **rec2, **rec3}
    recovery_stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mismatched_total": len(mismatched),
        "stage1_rule": len(rec1),
        "stage2_embedding": len(rec2),
        "stage3_sonnet": len(rec3),
        "new_subcode_candidates": len(new_subcodes),
        "unrecovered": len(residual3),
        "recovery_rate": round(len(all_rec) / max(len(mismatched), 1), 4),
    }
    write_recovered(light, all_rec, recovery_stats)
    write_audit(all_rec)
    write_new_subcodes(new_subcodes)

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for k, v in recovery_stats.items():
        print(f"  {k:30s}: {v}")
    print()
    print(f"  output (drop-in for auto_register_aliases.py):")
    print(f"    {RECOVERED_PATH.relative_to(REPO_ROOT)}")
    print(f"  audit:  {AUDIT_PATH.relative_to(REPO_ROOT)}")
    print(f"  new subcodes (F.2 forward): {NEW_SUBCODE_PATH.relative_to(REPO_ROOT)}")
    print("=" * 70)
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
