#!/usr/bin/env python3
"""Phase F.1 — Normalizer alias auto-registration (정식 4-Gate).

Layer 4 Module 4.1. F.1-light (auto_register_aliases_light.py)이 생성한
synthetic 기반 proposals + (향후) analysis_log.jsonl[normalizer_unknown_codes]
mining 결과를 입력으로 4-Gate 검증을 거친 alias를 candidate file에 등재한다.

4-Gate:
  Gate 1 (embedding similarity): text-embedding-3-small cosine ≥ 0.7 vs 기존 alias
                                  (Day 3) — light=verify mode, log=discover mode
  Gate 2 (LLM verify):           light이 이미 confidence 부여 — threshold ≥ 0.8 필터
                                  (재호출 불필요, 비용 절약)
  Gate 3 (regression):           별도 호출 (`scripts/replay_synthetic_observations.py`
                                  + `scripts/regression_gate.py`, Day 5 통합)
  Gate 4 (asymmetric trust):     candidate file에 level=candidate로 작성,
                                  50회 사용 후 promote_aliases.py로 vetted 승격 (Day 7)

입력 우선순위:
  1. f1_light_proposals.json (synthetic 기반 LLM 제안 1,235개)
  2. analysis_log.jsonl[normalizer_unknown_codes] (production miss, A hook 후 누적)

산출:
  - risk_feature_aliases_candidates.json    (Normalizer cascade step 4.5에서 startup load)
  - runtime-artifacts/alias_candidate_meta.jsonl (sidecar: uses, last_used_at, source)
  - runtime-artifacts/alias_audit.jsonl     (Gate 1/2/3 결과 + accept/reject 사유)
  - runtime-artifacts/alias_embedding_cache.json (Gate 1 캐시, per-code sha256 키)

ENV:
  OPENAI_API_KEY     (Gate 1 embedding 호출용, --gate1 또는 --apply 시 필수)

사용:
  python auto_register_aliases.py                              # dry-run (stats 표시)
  python auto_register_aliases.py --min-freq 3                 # log min_freq 조정
  python auto_register_aliases.py --gate1                      # Gate 1만 실행 + cache 빌드
  python auto_register_aliases.py --apply                      # 4-Gate 실행 + write (Day 5+)
  python auto_register_aliases.py --apply --min-confidence 0.7 # threshold 조정
  python auto_register_aliases.py --skip-light                 # light proposals 무시
  python auto_register_aliases.py --skip-log                   # analysis_log 무시

상태: Day 1+2+3 — scaffold + 후보 추출/dedup + Gate 1 embedding. Gate 3/4는 Day 5에서.
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
LIGHT_PROPOSALS_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "f1_light_proposals.json"
)
ANALYSIS_LOG_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "analysis_log.jsonl"
)
ALIAS_MAIN_PATH = (
    REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_aliases.json"
)
ALIAS_CANDIDATES_PATH = (
    REPO_ROOT
    / "serving-team"
    / "08-app"
    / "backend"
    / "app"
    / "data"
    / "risk_feature_aliases_candidates.json"
)
CATALOG_PATH = (
    REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
)
META_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "alias_candidate_meta.jsonl"
)
AUDIT_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "alias_audit.jsonl"
)
EMBEDDING_CACHE_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "alias_embedding_cache.json"
)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_CUTOFF = 0.7  # Gate 1 threshold (R5: Korean pair에서 0.65~0.75 재조정 검토)
EMBED_BATCH = 100  # OpenAI embeddings batch size


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_light_proposals() -> dict[str, Any]:
    if not LIGHT_PROPOSALS_PATH.is_file():
        return {"stats": {}, "proposals": {}}
    return json.loads(LIGHT_PROPOSALS_PATH.read_text(encoding="utf-8"))


def load_analysis_log_unknowns() -> list[dict[str, Any]]:
    """Parse `normalizer_unknown_codes` from analysis_log.jsonl. Format: `"TEXT (axis)"`."""
    out: list[dict[str, Any]] = []
    if not ANALYSIS_LOG_PATH.is_file():
        return out
    with ANALYSIS_LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            unknowns = entry.get("normalizer_unknown_codes") or []
            if not unknowns:
                continue
            ts = entry.get("ts", "")
            scene_hash = entry.get("scene_hash", "")
            for raw in unknowns:
                parsed = parse_unknown(raw)
                if parsed is None:
                    continue
                text, axis = parsed
                out.append({"raw": raw, "text": text, "failed_axis": axis, "ts": ts, "scene_hash": scene_hash})
    return out


def parse_unknown(raw: str) -> tuple[str, str] | None:
    """Parse `"TEXT (axis)"` → (text, axis). None on shape mismatch."""
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not raw.endswith(")") or "(" not in raw:
        return None
    text, _, axis_part = raw.rpartition("(")
    text = text.strip()
    axis = axis_part.rstrip(")").strip()
    if not text or not axis:
        return None
    return text, axis


def load_existing_aliases() -> dict[str, dict[str, set[str]]]:
    """Return {axis: {code: set(aliases)}} merging main + candidates files."""
    out: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for path in (ALIAS_MAIN_PATH, ALIAS_CANDIDATES_PATH):
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        tier1 = data.get("tier1", {})
        for axis, code_map in tier1.items():
            if not isinstance(code_map, dict):
                continue
            for code, aliases in code_map.items():
                if isinstance(aliases, list):
                    for a in aliases:
                        if isinstance(a, str) and a.strip():
                            out[axis][code].add(a.strip())
                        elif isinstance(a, dict) and isinstance(a.get("alias"), str):
                            out[axis][code].add(a["alias"].strip())
    return out


def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.is_file():
        return {"axes": {}}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def load_valid_codes(catalog: dict[str, Any]) -> dict[str, set[str]]:
    """Return {axis: set(valid_codes_including_subs)} from catalog.

    Catalog schema (v3.0): axes.{axis}.codes.{CODE}.sub = [SUB_CODE, ...].
    Both main code and sub-codes are valid enum values; both should pass validation.
    """
    out: dict[str, set[str]] = defaultdict(set)
    for axis, axis_def in catalog.get("axes", {}).items():
        codes = axis_def.get("codes") or {}
        for code, code_def in codes.items():
            out[axis].add(code)
            if isinstance(code_def, dict):
                for sub in code_def.get("sub", []) or []:
                    if isinstance(sub, str):
                        out[axis].add(sub)
    return out


# ---------------------------------------------------------------------------
# Day 2: Candidate building + dedup
# ---------------------------------------------------------------------------


def build_light_candidates(
    proposals: dict[str, Any],
    min_confidence: float,
    valid_codes: dict[str, set[str]] | None = None,
) -> tuple[list[dict], int]:
    """Convert light proposals to unified Candidate (filter by confidence + catalog validity).

    light이 synthetic의 한국어 sub-code 등 catalog 미존재 코드를 제안하는 경우 reject.
    Returns (candidates, n_catalog_mismatch).
    """
    out: list[dict] = []
    catalog_dropped = 0
    for axis, code_map in proposals.get("proposals", {}).items():
        valid_for_axis = valid_codes.get(axis, set()) if valid_codes else None
        for code, entries in code_map.items():
            if valid_for_axis is not None and code not in valid_for_axis:
                catalog_dropped += len(entries)
                continue
            for e in entries:
                conf = float(e.get("confidence", 0.0))
                if conf < min_confidence:
                    continue
                text = (e.get("alias") or "").strip()
                if not text:
                    continue
                out.append(
                    {
                        "text": text,
                        "failed_axis": axis,  # for light, axis == proposed_axis
                        "proposed_code": code,
                        "source": "light",
                        "confidence": conf,
                        "freq": int(e.get("frequency_in_synthetic", 0)),
                        "reasoning": (e.get("reasoning") or "")[:200],
                    }
                )
    return out, catalog_dropped


def build_log_candidates(unknowns: list[dict], min_freq: int) -> list[dict]:
    """Aggregate log unknowns by (text, failed_axis); filter by min_freq.

    Log entries have no proposed_code — Gate 1 (Day 3) will assign via similarity.
    """
    freq: Counter = Counter()
    for u in unknowns:
        freq[(u["text"], u["failed_axis"])] += 1
    out: list[dict] = []
    for (text, axis), n in freq.items():
        if n < min_freq:
            continue
        out.append(
            {
                "text": text,
                "failed_axis": axis,
                "proposed_code": None,  # to be set by Gate 1
                "source": "log",
                "confidence": 1.0,  # log has no LLM-assigned confidence
                "freq": n,
            }
        )
    return out


def dedupe_candidates(
    candidates: list[dict], existing: dict[str, dict[str, set[str]]]
) -> tuple[list[dict], int]:
    """Filter out candidates whose text already exists in main/candidate aliases.

    Light: check against existing aliases of proposed_code (within same axis).
    Log: check against ALL aliases in failed_axis (defensive — text might match a
         different code than expected).
    Returns (filtered, dropped_count).
    """
    filtered: list[dict] = []
    dropped = 0
    for c in candidates:
        text = c["text"]
        axis = c["failed_axis"]
        if c["source"] == "light" and c.get("proposed_code"):
            if text in existing.get(axis, {}).get(c["proposed_code"], set()):
                dropped += 1
                continue
        else:  # log or light-without-code
            axis_pool: set[str] = set()
            for s in existing.get(axis, {}).values():
                axis_pool.update(s)
            if text in axis_pool:
                dropped += 1
                continue
        filtered.append(c)
    return filtered, dropped


# ---------------------------------------------------------------------------
# Day 3: Gate 1 (embedding similarity)
# ---------------------------------------------------------------------------


def _code_cache_key(axis: str, code: str, aliases: set[str] | list[str]) -> str:
    """Stable hash of (axis, code, sorted aliases) for per-code cache invalidation."""
    payload = "|".join([axis, code] + sorted(aliases))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_embedding_cache() -> dict[str, dict]:
    if not EMBEDDING_CACHE_PATH.is_file():
        return {}
    try:
        return json.loads(EMBEDDING_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_embedding_cache(cache: dict[str, dict]) -> None:
    EMBEDDING_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = EMBEDDING_CACHE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    tmp.replace(EMBEDDING_CACHE_PATH)  # atomic (R6)


def cosine_similarity(a: list[float], b: list[float]) -> float:
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
    """Embed batch via text-embedding-3-small. Returns list of vectors aligned to texts."""
    r = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in r.data]


async def _populate_existing_embeddings(
    client, existing: dict[str, dict[str, set[str]]], cache: dict[str, dict]
) -> dict[str, dict]:
    """For each (axis, code) ensure cache holds per-alias embeddings under current key.

    Cache schema: {key: {"axis": str, "code": str, "aliases": {alias_str: vector}}}
    Per-code sha256 key invalidates when alias set changes (R1).
    """
    work: list[tuple[str, str, str]] = []  # (key, axis, code, alias) - flatten
    work_keys: list[tuple[str, str, str]] = []
    for axis, code_map in existing.items():
        for code, aliases in code_map.items():
            if not aliases:
                continue
            key = _code_cache_key(axis, code, aliases)
            entry = cache.get(key)
            if entry is None:
                cache[key] = {"axis": axis, "code": code, "aliases": {}}
                entry = cache[key]
            for a in aliases:
                if a not in entry["aliases"]:
                    work.append((key, axis, code, a))
    if not work:
        return cache
    # Batch
    for i in range(0, len(work), EMBED_BATCH):
        batch = work[i : i + EMBED_BATCH]
        texts = [a for (_, _, _, a) in batch]
        embs = await embed_batch(client, texts)
        for (key, axis, code, alias), emb in zip(batch, embs):
            cache[key]["aliases"][alias] = emb
    save_embedding_cache(cache)
    return cache


async def gate1_embedding(
    client,
    candidates: list[dict],
    existing: dict[str, dict[str, set[str]]],
    cache: dict[str, dict],
    cutoff: float = EMBEDDING_CUTOFF,
) -> list[dict]:
    """Add gate1_similarity + proposed_enum + gate1_pass to each candidate.

    Light (verify mode):  similarity vs existing aliases of proposed_code only.
                          Pass = max_sim >= cutoff. Low sim = LLM hallucination signal.
    Log (discover mode):  similarity vs all aliases in failed_axis.
                          Best-fit code = proposed_enum. Pass = max_sim >= cutoff.
    """
    if not candidates:
        return []
    # Ensure existing aliases are embedded
    await _populate_existing_embeddings(client, existing, cache)
    # Embed candidate texts
    cand_texts = [c["text"] for c in candidates]
    cand_embs: list[list[float]] = []
    for i in range(0, len(cand_texts), EMBED_BATCH):
        batch_texts = cand_texts[i : i + EMBED_BATCH]
        embs = await embed_batch(client, batch_texts)
        cand_embs.extend(embs)

    out: list[dict] = []
    for c, emb in zip(candidates, cand_embs):
        axis = c["failed_axis"]
        if c["source"] == "light" and c.get("proposed_code"):
            target_code = c["proposed_code"]
            aliases = existing.get(axis, {}).get(target_code, set())
            key = _code_cache_key(axis, target_code, aliases)
            existing_embs = cache.get(key, {}).get("aliases", {})
            max_sim = 0.0
            for _, exi_emb in existing_embs.items():
                sim = cosine_similarity(emb, exi_emb)
                if sim > max_sim:
                    max_sim = sim
            out.append(
                {
                    **c,
                    "gate1_similarity": round(max_sim, 4),
                    "proposed_enum": target_code,
                    "gate1_pass": max_sim >= cutoff,
                }
            )
        else:  # log: discover best-fit code in axis
            best_sim = 0.0
            best_code: str | None = None
            for code, aliases in existing.get(axis, {}).items():
                if not aliases:
                    continue
                key = _code_cache_key(axis, code, aliases)
                existing_embs = cache.get(key, {}).get("aliases", {})
                for _, exi_emb in existing_embs.items():
                    sim = cosine_similarity(emb, exi_emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_code = code
            out.append(
                {
                    **c,
                    "gate1_similarity": round(best_sim, 4),
                    "proposed_enum": best_code,
                    "gate1_pass": best_sim >= cutoff,
                }
            )
    return out


# ---------------------------------------------------------------------------
# Reporting (dry-run + Gate 1 summary)
# ---------------------------------------------------------------------------


def _confidence_dist(cands: list[dict]) -> Counter:
    """Bucket confidence values."""
    c = Counter()
    for x in cands:
        v = float(x.get("confidence", 0.0))
        if v >= 0.9:
            c[">=0.9"] += 1
        elif v >= 0.8:
            c["0.8-0.9"] += 1
        elif v >= 0.7:
            c["0.7-0.8"] += 1
        elif v >= 0.6:
            c["0.6-0.7"] += 1
        else:
            c["<0.6"] += 1
    return c


def print_dry_run(
    light_total: int,
    light_cands: list[dict],
    catalog_dropped: int,
    log_total: int,
    log_cands: list[dict],
    dropped: int,
    final_cands: list[dict],
    existing: dict,
    min_confidence: float,
    min_freq: int,
    skip_light: bool,
    skip_log: bool,
) -> None:
    print("=" * 70)
    print("F.1 auto_register_aliases — DRY RUN")
    print("=" * 70)
    print(f"min_confidence (Gate 2, light): {min_confidence}    min_freq (log): {min_freq}")
    print()

    print("[Existing aliases — main + candidates merged]")
    total_codes = 0
    total_aliases = 0
    for axis, code_map in existing.items():
        n_codes = len(code_map)
        n_aliases = sum(len(s) for s in code_map.values())
        total_codes += n_codes
        total_aliases += n_aliases
        print(f"  {axis:25s}  codes={n_codes:4d}  aliases={n_aliases:5d}")
    print(f"  {'TOTAL':25s}  codes={total_codes:4d}  aliases={total_aliases:5d}")
    print()

    print("[Source 1: f1_light_proposals.json]")
    if skip_light:
        print("  SKIPPED (--skip-light)")
    else:
        print(f"  total proposals          : {light_total}")
        print(f"  catalog mismatch dropped : {catalog_dropped}  (code not in catalog v3.0)")
        print(f"  after confidence filter  : {len(light_cands)}")
        cd = _confidence_dist(light_cands)
        for bucket in [">=0.9", "0.8-0.9", "0.7-0.8", "0.6-0.7", "<0.6"]:
            n = cd.get(bucket, 0)
            if n:
                print(f"    {bucket:10s}: {n:5d}")
    print()

    print("[Source 2: analysis_log.jsonl[normalizer_unknown_codes]]")
    if skip_log:
        print("  SKIPPED (--skip-log)")
    else:
        print(f"  total unknown entries    : {log_total}")
        print(f"  after min_freq filter    : {len(log_cands)}")
        if log_cands:
            top = sorted(log_cands, key=lambda x: -x["freq"])[:10]
            print(f"  top 10 by freq:")
            for r in top:
                print(f"    freq={r['freq']:4d}  axis={r['failed_axis']:20s}  text={r['text']!r}")
        elif log_total == 0:
            print("  (no unknowns logged — A hook may not have produced traffic yet)")
    print()

    print("[Combined + dedup]")
    print(f"  combined (light + log)   : {len(light_cands) + len(log_cands)}")
    print(f"  dropped as existing      : {dropped}")
    print(f"  final candidate pool     : {len(final_cands)}")
    by_source: Counter = Counter()
    by_axis: Counter = Counter()
    for c in final_cands:
        by_source[c["source"]] += 1
        by_axis[c["failed_axis"]] += 1
    if by_source:
        print(f"  by source:")
        for s, n in by_source.most_common():
            print(f"    {s:10s}: {n}")
        print(f"  by axis:")
        for a, n in by_axis.most_common():
            print(f"    {a:25s}: {n}")
    print()

    print("[Next: --gate1 (Day 3) or --apply (Day 5+)]")
    print("=" * 70)


def print_gate1_summary(gated: list[dict], cutoff: float) -> None:
    print()
    print("=" * 70)
    print(f"Gate 1 (embedding similarity, text-embedding-3-small, cutoff={cutoff})")
    print("=" * 70)
    if not gated:
        print("  (no candidates to gate)")
        return
    n_total = len(gated)
    n_pass = sum(1 for g in gated if g["gate1_pass"])
    print(f"  total candidates         : {n_total}")
    print(f"  Gate 1 pass              : {n_pass} ({n_pass/n_total*100:.1f}%)")
    print(f"  Gate 1 reject            : {n_total - n_pass} ({(n_total-n_pass)/n_total*100:.1f}%)")

    # Distribution
    sim_buckets: Counter = Counter()
    for g in gated:
        s = g["gate1_similarity"]
        if s >= 0.9:
            sim_buckets[">=0.9"] += 1
        elif s >= 0.8:
            sim_buckets["0.8-0.9"] += 1
        elif s >= 0.7:
            sim_buckets["0.7-0.8"] += 1
        elif s >= 0.6:
            sim_buckets["0.6-0.7"] += 1
        elif s >= 0.5:
            sim_buckets["0.5-0.6"] += 1
        else:
            sim_buckets["<0.5"] += 1
    print(f"  similarity distribution:")
    for b in [">=0.9", "0.8-0.9", "0.7-0.8", "0.6-0.7", "0.5-0.6", "<0.5"]:
        n = sim_buckets.get(b, 0)
        if n:
            print(f"    {b:10s}: {n:5d}")

    # Sample passes/rejects
    passes = [g for g in gated if g["gate1_pass"]]
    rejects = [g for g in gated if not g["gate1_pass"]]
    passes.sort(key=lambda x: -x["gate1_similarity"])
    rejects.sort(key=lambda x: -x["gate1_similarity"])

    print()
    print(f"  Top 10 PASS (highest similarity):")
    for g in passes[:10]:
        src = g["source"][:5]
        print(
            f"    sim={g['gate1_similarity']:.3f}  axis={g['failed_axis']:18s}  "
            f"code={(g['proposed_enum'] or '?'):20s}  text={g['text']!r}  ({src})"
        )

    print()
    print(f"  Top 10 REJECT (just below cutoff):")
    for g in rejects[:10]:
        src = g["source"][:5]
        print(
            f"    sim={g['gate1_similarity']:.3f}  axis={g['failed_axis']:18s}  "
            f"code={(g['proposed_enum'] or '?'):20s}  text={g['text']!r}  ({src})"
        )

    print("=" * 70)


# ---------------------------------------------------------------------------
# Apply (Day 5+)
# ---------------------------------------------------------------------------


def apply_pipeline(args: argparse.Namespace) -> int:
    print("--apply is not yet implemented (Day 5 work).", file=sys.stderr)
    print("Currently available: --gate1 (Day 3) to validate embedding similarity.", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--apply", action="store_true", help="run 4-Gate pipeline + write candidates (Day 5+)")
    parser.add_argument("--dry-run", action="store_true", help="print stats only (default)")
    parser.add_argument(
        "--gate1",
        action="store_true",
        help="run Gate 1 embedding similarity check on dedup candidate pool (Day 3)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        help="Gate 2 threshold for light proposals (default 0.8; F.3.2 used 0.7)",
    )
    parser.add_argument(
        "--min-freq",
        type=int,
        default=3,
        help="min frequency for log candidates (default 3)",
    )
    parser.add_argument(
        "--cutoff",
        type=float,
        default=EMBEDDING_CUTOFF,
        help=f"Gate 1 similarity cutoff (default {EMBEDDING_CUTOFF}, R5 may tune to 0.65-0.75)",
    )
    parser.add_argument("--skip-light", action="store_true", help="ignore f1_light_proposals.json")
    parser.add_argument("--skip-log", action="store_true", help="ignore analysis_log.jsonl unknowns")
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=0,
        help="cap candidate pool to top N (by freq) for cheap iteration (0=no cap)",
    )
    args = parser.parse_args()
    if not args.apply and not args.gate1:
        args.dry_run = True
    return args


async def main_async(args: argparse.Namespace) -> int:
    # Load all
    light = load_light_proposals() if not args.skip_light else {"stats": {}, "proposals": {}}
    unknowns = load_analysis_log_unknowns() if not args.skip_log else []
    existing = load_existing_aliases()
    catalog = load_catalog()
    valid_codes = load_valid_codes(catalog)

    # Day 2: Build candidates (with catalog validation for light)
    light_total = sum(
        len(v) for ax in light.get("proposals", {}).values() for v in ax.values()
    )
    if not args.skip_light:
        light_cands, catalog_dropped = build_light_candidates(
            light, args.min_confidence, valid_codes
        )
    else:
        light_cands, catalog_dropped = [], 0
    log_cands = build_log_candidates(unknowns, args.min_freq) if not args.skip_log else []
    log_total = len(unknowns)

    combined = light_cands + log_cands
    final_cands, dropped = dedupe_candidates(combined, existing)

    if args.max_candidates and len(final_cands) > args.max_candidates:
        final_cands.sort(key=lambda x: (-x["freq"], -float(x.get("confidence", 0))))
        final_cands = final_cands[: args.max_candidates]

    # Dry-run stats (always print)
    print_dry_run(
        light_total,
        light_cands,
        catalog_dropped,
        log_total,
        log_cands,
        dropped,
        final_cands,
        existing,
        args.min_confidence,
        args.min_freq,
        args.skip_light,
        args.skip_log,
    )

    if args.dry_run:
        return 0

    # Day 3: Gate 1 (--gate1) or full apply (--apply)
    if not final_cands:
        print("\nNo candidates to gate. Done.")
        return 0

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\nERROR: OPENAI_API_KEY env var required for --gate1/--apply", file=sys.stderr)
        return 2

    try:
        from openai import AsyncOpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
        return 2

    client = AsyncOpenAI(api_key=api_key)

    if args.gate1 or args.apply:
        print(
            f"\n[Gate 1] embedding {len(final_cands)} candidates "
            f"+ ensuring existing alias embeddings cached..."
        )
        cache = load_embedding_cache()
        cache_size_before = sum(len(v.get("aliases", {})) for v in cache.values())
        gated = await gate1_embedding(client, final_cands, existing, cache, cutoff=args.cutoff)
        cache_size_after = sum(len(v.get("aliases", {})) for v in cache.values())
        print(
            f"  embedding cache: {cache_size_before} → {cache_size_after} entries "
            f"({cache_size_after - cache_size_before} newly embedded)"
        )
        print_gate1_summary(gated, args.cutoff)

    if args.apply:
        return apply_pipeline(args)

    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
