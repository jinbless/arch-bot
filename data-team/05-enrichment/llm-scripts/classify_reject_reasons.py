#!/usr/bin/env python3
"""F.3.0 — Reject Reason Classifier.

analysis_log.jsonl의 excluded[].reason 텍스트를 5개 카테고리로 자동 분류해
Phase F.3 (Autonomous Axiom Learning Loop) 본격 진행 정당성을 데이터로 결정한다.

카테고리:
- domain_mismatch  : 산업/도메인 mismatch이고 KB에 해당 axiom이 이미 존재 (기존 reasoning이 작동)
- axiom_missing    : 산업/도메인 mismatch인데 KB에 axiom 없음 (새 axiom 후보 — F.3의 진짜 신호)
- normalizer_gap   : Normalizer 매핑 누락이 reason 텍스트에 드러난 케이스
- data_quality    : catalog 미정의, freq<5 등 데이터 자체 문제
- ambiguous       : 위 어느 것에도 안 맞음 (LLM 2nd pass 후보)

1차 분류: regex + keyword + existing incompatibilities 조회 (LLM 0회)
2차 분류 (--llm-fallback): ambiguous bucket을 gpt-5.4-nano batched로 분류

ENV:
  OPENAI_API_KEY      (--llm-fallback 시 필요)
  LLM_RERANK_MODEL    (default: gpt-5.4-nano)

사용:
  python classify_reject_reasons.py                # 1차만, LLM 0회
  python classify_reject_reasons.py --llm-fallback # 2차 포함 (ambiguous >20%일 때만)
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
LOG_PATH = ARTIFACTS_DIR / "analysis_log.jsonl"
INCOMPAT_PATH = ARTIFACTS_DIR / "guide_domain_incompatibilities.json"
LLM_DOMAINS_PATH = ARTIFACTS_DIR / "guide_llm_domains.json"
KO_TO_EN_MAP_PATH = ARTIFACTS_DIR / "industry_ko_to_en_map.json"
OUTPUT_PATH = ARTIFACTS_DIR / "reject_reason_classified.jsonl"
DISTRIBUTION_PATH = ARTIFACTS_DIR / "reject_reason_distribution.json"
SAMPLE_PATH = ARTIFACTS_DIR / "reject_reason_sample_100.jsonl"
LLM_CACHE_PATH = ARTIFACTS_DIR / "reject_reason_llm_cache.json"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


# Regex priority: normalizer_gap > data_quality > axiom_hint > domain_mismatch > ambiguous
NORMALIZER_GAP_PATTERNS = [
    r"매핑\s*불가", r"unmapped", r"정의되지\s*않", r"catalog에\s*없",
    r"식별\s*불가", r"normalizer\s*(fail|miss)", r"unknown\s+(code|term)",
]
DATA_QUALITY_PATTERNS = [
    r"freq\s*[<≤]\s*\d", r"빈약", r"불충분", r"모호한\s*후보",
    r"catalog\s*미정의", r"target.*없", r"중복\s*제거",
]
AXIOM_HINT_PATTERNS = [
    r"공리\s*부재", r"axiom\s*없", r"rule\s*없", r"제약\s*없",
    r"axiom\s*missing", r"부족한\s*공리",
]
# 한국어 동사 활용형 (다르다 → 다른/다르/달라/다릅/다름/달랐)을 cover하기 위해
# 어근/축약형까지 포함. 또 LLM rerank reject reason의 표준 형식 ("사진은 X, 후보 Guide는 Y")
# 자체도 강한 신호로 사용.
_DOMAIN_MISMATCH_VERBS = (
    r"(다른|다르|다릅|다름|달라|달랐|달랐던|달리|"  # "다르다" 활용
    r"차이|별개|구분되|구별되|다양|"  # 차이/구분
    r"맞지\s*않|안\s*맞|불일치|일치하지|"  # 일치 부정
    r"적합하지\s*않|부적합|적용\s*불가|적용\s*안|"  # 적합/적용 부정
    r"매칭되지|매칭\s*불가|대응되지|대응되지\s*않|대응\s*안|대응\s*없|"  # 매칭/대응
    r"무관|관련[성이]?\s*없|연관[성이]?\s*없|해당하지\s*않|해당\s*안|"  # 무관/해당
    r"mismatch|differ|different|unrelated|irrelevant)"
)
_DOMAIN_MISMATCH_NOUNS = (
    r"(맥락|도메인|산업|분야|영역|업종|작업|수단|목적|성격|"
    r"대상|공정|업무|용도|범주|항목|상황|기능|category|domain|context|industry|field)"
)
DOMAIN_MISMATCH_PATTERNS = [
    # noun + verb 인접 (10~30자 내)
    _DOMAIN_MISMATCH_NOUNS + r"[은는이가과와의]?\s*.{0,30}?" + _DOMAIN_MISMATCH_VERBS,
    # verb + noun (예: "다른 분야", "다른 도메인")
    r"다른\s*" + _DOMAIN_MISMATCH_NOUNS,
    # standalone strong verb-form anywhere
    r"적합하지\s*않", r"부적합", r"매칭되지", r"매칭\s*불가",
    r"대응되지", r"무관", r"불일치",
    # 표준 reject reason form 자체
    r"후보\s*[Gg]uide.{0,80}?(다른|다르|다릅|달라|차이|맞지\s*않|관련\s*없|무관|아니|초점)",
    r"사진[은과의]\s*.{0,200}?(다른|다르|다릅|달라|차이|맞지\s*않|관련\s*없|무관)",
]

_NORMALIZER_RE = re.compile("|".join(NORMALIZER_GAP_PATTERNS), re.IGNORECASE)
_DATA_QUALITY_RE = re.compile("|".join(DATA_QUALITY_PATTERNS), re.IGNORECASE)
_AXIOM_HINT_RE = re.compile("|".join(AXIOM_HINT_PATTERNS), re.IGNORECASE)
_DOMAIN_MISMATCH_RE = re.compile("|".join(DOMAIN_MISMATCH_PATTERNS), re.IGNORECASE)
# "후보 Guide" + "사진" 둘 다 등장하는 표준 reject reason 형식 자체도 강 신호
_STANDARD_REJECT_FORM_RE = re.compile(
    r"(후보\s*[Gg]uide|후보의\s*도메인|후보의\s*Guide).+사진|"
    r"사진.+(후보\s*[Gg]uide|후보의\s*도메인)",
    re.IGNORECASE | re.DOTALL,
)


def load_log() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        print(f"ERROR: log not found at {LOG_PATH}", file=sys.stderr)
        return []
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_guide_domains() -> dict[str, str]:
    if not LLM_DOMAINS_PATH.exists():
        return {}
    payload = json.loads(LLM_DOMAINS_PATH.read_text(encoding="utf-8"))
    return {
        code: (info or {}).get("primary_domain", "")
        for code, info in (payload.get("classifications") or {}).items()
    }


def load_ko_to_en_industry_map() -> dict[str, str]:
    """KO industry name → EN UPPER_SNAKE_CASE enum (84 entries)."""
    if not KO_TO_EN_MAP_PATH.exists():
        return {}
    payload = json.loads(KO_TO_EN_MAP_PATH.read_text(encoding="utf-8"))
    return dict(payload.get("mappings") or {})


def translate_industry(name: str, ko_to_en: dict[str, str]) -> str:
    """Best-effort KO→EN translation. EN inputs and unknown KO pass through unchanged."""
    if not name:
        return name
    if name in ko_to_en:
        return ko_to_en[name]
    # already EN UPPER_SNAKE?
    if name.replace("_", "").isascii() and name.isupper():
        return name
    return name


def load_existing_incompat(ko_to_en: dict[str, str]) -> set[tuple[str, str]]:
    """Returns EN-normalized pair set (both directions)."""
    if not INCOMPAT_PATH.exists():
        return set()
    payload = json.loads(INCOMPAT_PATH.read_text(encoding="utf-8"))
    existing: set[tuple[str, str]] = set()
    for entry in payload.get("incompatibilities") or []:
        if not entry.get("incompatible"):
            continue
        a = translate_industry(str(entry.get("domain_a") or "").strip(), ko_to_en)
        b = translate_industry(str(entry.get("domain_b") or "").strip(), ko_to_en)
        if a and b:
            existing.add((a, b))
            existing.add((b, a))
    return existing


def classify_regex(reason: str) -> tuple[str, float]:
    """Stage 1: regex/keyword only. Returns (category, confidence)."""
    if not reason or not reason.strip():
        return ("data_quality", 0.6)
    if _NORMALIZER_RE.search(reason):
        return ("normalizer_gap", 0.9)
    if _DATA_QUALITY_RE.search(reason):
        return ("data_quality", 0.85)
    if _AXIOM_HINT_RE.search(reason):
        return ("axiom_missing", 0.95)
    if _DOMAIN_MISMATCH_RE.search(reason):
        return ("domain_mismatch", 0.75)  # tentative — pair check upgrades to axiom_missing
    # 표준 reject form ("사진은 X, 후보 Guide는 Y") + LLM reason 충분히 길면 묵시적 mismatch
    if _STANDARD_REJECT_FORM_RE.search(reason) and len(reason) >= 50:
        return ("domain_mismatch", 0.6)  # weaker confidence, pair check 활용 가능
    return ("ambiguous", 0.0)


def upgrade_with_pair_check(
    category: str,
    confidence: float,
    industry: str,
    guide_code: str,
    guide_to_domain: dict[str, str],
    existing_incompat: set[tuple[str, str]],
    ko_to_en: dict[str, str],
) -> tuple[str, float, bool, str, str]:
    """domain_mismatch + 해당 pair가 KB에 미등재 → axiom_missing으로 upgrade.

    Returns (final_category, confidence, pair_known_flag, ind_norm, dom_norm)
    """
    ind_norm = translate_industry(industry, ko_to_en)
    dom_norm = translate_industry(guide_to_domain.get(guide_code, ""), ko_to_en)
    if category != "domain_mismatch":
        return (category, confidence, False, ind_norm, dom_norm)
    if not dom_norm or not ind_norm or dom_norm == ind_norm:
        return (category, confidence, False, ind_norm, dom_norm)
    pair_known = (ind_norm, dom_norm) in existing_incompat
    if pair_known:
        return ("domain_mismatch", min(1.0, confidence + 0.1), True, ind_norm, dom_norm)
    return ("axiom_missing", 0.8, False, ind_norm, dom_norm)


LLM_SYSTEM_PROMPT = """\
당신은 KOSHA 산업안전 추천 시스템의 reject 사유 분류자입니다.
LLM이 후보 가이드를 reject한 reason 문장을 5개 카테고리 중 하나로 분류합니다.

카테고리:
- domain_mismatch : 산업/도메인이 다르다는 명확한 mismatch (예: 건설 사진에 식품 가이드)
- axiom_missing   : mismatch인데 해당 axiom 부재가 reason에 명시 또는 강하게 시사
- normalizer_gap  : 용어 식별/매핑 실패가 reason에 드러남
- data_quality    : freq 부족, catalog 미정의 등 데이터 문제
- ambiguous       : 위 어디에도 명확히 안 맞음
"""

LLM_RESPONSE_SCHEMA = {
    "name": "reason_categories",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "idx": {"type": "integer"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "domain_mismatch",
                                "axiom_missing",
                                "normalizer_gap",
                                "data_quality",
                                "ambiguous",
                            ],
                        },
                        "confidence": {"type": "number"},
                    },
                    "required": ["idx", "category", "confidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    },
}


def reason_hash(reason: str) -> str:
    return hashlib.sha256(reason.encode("utf-8")).hexdigest()[:16]


def load_llm_cache() -> dict[str, dict[str, Any]]:
    if not LLM_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(LLM_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_llm_cache(cache: dict[str, dict[str, Any]]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    LLM_CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def classify_batch_llm(
    client, model: str, batch: list[tuple[int, str]]
) -> list[tuple[int, str, float]]:
    """Classify a batch of (idx, reason) → [(idx, category, confidence)]."""
    user_payload = "\n".join(
        f"[{i}] {reason[:300]}" for i, reason in batch
    )
    try:
        r = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "developer", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            response_format={"type": "json_schema", "json_schema": LLM_RESPONSE_SCHEMA},
            max_completion_tokens=1024,
        )
        parsed = json.loads(r.choices[0].message.content or "{}")
        out = []
        for item in parsed.get("results", []):
            out.append((int(item["idx"]), str(item["category"]), float(item["confidence"])))
        return out
    except Exception as exc:
        print(f"  LLM batch error: {exc}", file=sys.stderr)
        return [(i, "ambiguous", 0.0) for i, _ in batch]


async def llm_pass(
    ambiguous_entries: list[dict[str, Any]],
    model: str,
    batch_size: int,
    concurrency: int,
) -> None:
    """Mutate ambiguous_entries in place with LLM categorization (cached)."""
    cache = load_llm_cache()
    work: list[tuple[int, str]] = []  # (entry_idx, reason)
    cache_hits = 0
    for i, e in enumerate(ambiguous_entries):
        h = reason_hash(e["original_reason"])
        cached = cache.get(h)
        if cached:
            e["reason_category"] = cached["category"]
            e["confidence"] = cached["confidence"]
            e["classifier_pass"] = 2
            e["pass2_cache_hit"] = True
            cache_hits += 1
        else:
            work.append((i, e["original_reason"]))
    print(f"  LLM cache: {cache_hits} hits, {len(work)} to call")

    if not work:
        return

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  ERROR: OPENAI_API_KEY missing for --llm-fallback", file=sys.stderr)
        return

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(concurrency)
    batches = [work[i : i + batch_size] for i in range(0, len(work), batch_size)]
    print(f"  Calling {model} on {len(batches)} batches of up to {batch_size}")

    async def _run(b):
        async with semaphore:
            return await classify_batch_llm(client, model, b)

    results_per_batch = await asyncio.gather(*[_run(b) for b in batches])

    # Map idx in work back to ambiguous_entries idx
    work_idx_to_entry_idx = {pos: w[0] for pos, w in enumerate(work)}
    # Each batch contains a contiguous slice of work; reconstruct
    flat_results: dict[int, tuple[str, float]] = {}
    pos = 0
    for batch, results in zip(batches, results_per_batch):
        for batch_local_idx, (_, _) in enumerate(batch):
            # Find result with matching idx (LLM returns idx as we sent it)
            pass
        for result_idx, cat, conf in results:
            flat_results[result_idx] = (cat, conf)
        pos += len(batch)

    for orig_idx, reason in work:
        cat, conf = flat_results.get(orig_idx, ("ambiguous", 0.0))
        entry = ambiguous_entries[orig_idx]
        entry["reason_category"] = cat
        entry["confidence"] = conf
        entry["classifier_pass"] = 2
        cache[reason_hash(reason)] = {"category": cat, "confidence": conf}

    save_llm_cache(cache)


def classify_all(
    rows: list[dict[str, Any]],
    guide_to_domain: dict[str, str],
    existing_incompat: set[tuple[str, str]],
    ko_to_en: dict[str, str],
) -> list[dict[str, Any]]:
    """Stage 1: regex + pair check."""
    out: list[dict[str, Any]] = []
    for row_idx, row in enumerate(rows):
        industry = str(row.get("industry") or "").strip()
        mode = str(row.get("mode") or "")
        scene_hash = str(row.get("scene_hash") or "")
        ts = str(row.get("ts") or "")
        for excl in row.get("excluded") or []:
            reason = str(excl.get("reason") or "")
            guide_code = str(excl.get("guide_code") or "")
            source = str(excl.get("source") or "")
            similarity = excl.get("similarity")
            cat0, conf0 = classify_regex(reason)
            cat1, conf1, pair_known, ind_norm, dom_norm = upgrade_with_pair_check(
                cat0, conf0, industry, guide_code, guide_to_domain, existing_incompat, ko_to_en
            )
            out.append(
                {
                    "row_idx": row_idx,
                    "ts": ts,
                    "mode": mode,
                    "scene_hash": scene_hash,
                    "industry": industry,
                    "industry_en": ind_norm,
                    "guide_code": guide_code,
                    "guide_primary_domain": guide_to_domain.get(guide_code, ""),
                    "guide_primary_domain_en": dom_norm,
                    "source": source,
                    "similarity": similarity,
                    "original_reason": reason[:300],
                    "reason_category": cat1,
                    "confidence": round(conf1, 3),
                    "classifier_pass": 1,
                    "pair_known_in_kb": pair_known,
                }
            )
    return out


def write_outputs(entries: list[dict[str, Any]], sample_size: int) -> dict[str, Any]:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    # 1. classified.jsonl (full)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    # 2. distribution.json
    counter = Counter(e["reason_category"] for e in entries)
    total = sum(counter.values())
    distribution = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_excluded_entries": total,
        "by_category": {cat: counter[cat] for cat in sorted(counter)},
        "by_category_pct": {
            cat: round(100 * counter[cat] / max(total, 1), 2) for cat in sorted(counter)
        },
        "pass1_count": sum(1 for e in entries if e.get("classifier_pass") == 1),
        "pass2_count": sum(1 for e in entries if e.get("classifier_pass") == 2),
        "axiom_missing_pct": round(100 * counter["axiom_missing"] / max(total, 1), 2),
        "f3_recommendation": (
            "PROCEED_F3" if 100 * counter["axiom_missing"] / max(total, 1) >= 5 else "DEFER_F3_PRIORITIZE_F1"
        ),
    }
    DISTRIBUTION_PATH.write_text(
        json.dumps(distribution, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # 3. sample (random 100 for manual review)
    rng = random.Random(20260517)
    sample = rng.sample(entries, min(sample_size, len(entries)))
    with SAMPLE_PATH.open("w", encoding="utf-8") as f:
        for e in sample:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return distribution


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--llm-fallback", action="store_true",
                   help="ambiguous bucket을 LLM으로 2차 분류 (gpt-5.4-nano)")
    p.add_argument("--llm-threshold", type=float, default=0.20,
                   help="ambiguous 비율이 이 값 이상이면 LLM 2nd pass 실행 (default: 0.20)")
    p.add_argument("--model", type=str, default=DEFAULT_MODEL)
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--sample-size", type=int, default=100)
    return p.parse_args()


async def main_async() -> int:
    args = parse_args()
    rows = load_log()
    print(f"Loaded {len(rows)} analysis_log rows from {LOG_PATH.name}")
    guide_to_domain = load_guide_domains()
    print(f"Loaded {len(guide_to_domain)} guide → primary_domain mappings")
    ko_to_en = load_ko_to_en_industry_map()
    print(f"Loaded {len(ko_to_en)} industry KO→EN mappings")
    existing_incompat = load_existing_incompat(ko_to_en)
    print(f"Loaded {len(existing_incompat) // 2} incompatibility pairs (EN-normalized) from KB")

    entries = classify_all(rows, guide_to_domain, existing_incompat, ko_to_en)
    if not entries:
        print("No excluded entries found.", file=sys.stderr)
        return 1
    print(f"\nStage 1 (regex + pair-check): classified {len(entries)} excluded entries")

    counter = Counter(e["reason_category"] for e in entries)
    total = sum(counter.values())
    ambig_pct = 100 * counter["ambiguous"] / max(total, 1)
    print(f"  ambiguous: {counter['ambiguous']} ({ambig_pct:.1f}%)")

    if args.llm_fallback and ambig_pct >= 100 * args.llm_threshold:
        print(f"\nStage 2 (LLM): ambiguous ≥ {100 * args.llm_threshold:.0f}% threshold, running...")
        ambiguous_entries = [e for e in entries if e["reason_category"] == "ambiguous"]
        await llm_pass(ambiguous_entries, args.model, args.batch_size, args.concurrency)
    elif args.llm_fallback:
        print(f"\nStage 2 skipped: ambiguous {ambig_pct:.1f}% < threshold {100 * args.llm_threshold:.0f}%")

    distribution = write_outputs(entries, args.sample_size)
    print(f"\n=== Final distribution ===")
    for cat, n in sorted(distribution["by_category"].items(), key=lambda x: -x[1]):
        pct = distribution["by_category_pct"][cat]
        print(f"  {cat:18s}  {n:5d}  ({pct:5.2f}%)")
    print(f"\naxiom_missing: {distribution['axiom_missing_pct']:.2f}%")
    print(f"F.3 recommendation: {distribution['f3_recommendation']}")
    print(f"\nOutputs:")
    print(f"  {OUTPUT_PATH}")
    print(f"  {DISTRIBUTION_PATH}")
    print(f"  {SAMPLE_PATH} (random 100 for manual review)")
    return 0


def main() -> None:
    sys.exit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
