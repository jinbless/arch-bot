#!/usr/bin/env python3
"""Phase B.1 — Guide domain embeddings 빌드.

각 Guide의 domain profile (title + domain_family + required_context_terms)을
OpenAI text-embedding-3-small로 임베딩하여 npz로 저장한다.

런타임의 guide_embedding_filter.py가 이 npz를 로드해서 candidate guide의
도메인 적합성을 cosine으로 판정한다.

사용:
  python data-team/05-enrichment/llm-scripts/build_guide_domain_embeddings.py
  python data-team/05-enrichment/llm-scripts/build_guide_domain_embeddings.py --limit 50
  python data-team/05-enrichment/llm-scripts/build_guide_domain_embeddings.py --output custom.npz

ENV:
  OPENAI_API_KEY (required)
  OPENAI_EMBEDDING_MODEL (default: text-embedding-3-small)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
PROFILES_PATH = (
    REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data"
    / "guide_domain_profiles.json"
)
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "guide_domain_embeddings.npz"
DEFAULT_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
BATCH_SIZE = 100


def build_profile_text(profile: dict) -> str:
    """Profile → embedding 입력 텍스트.

    포함:
    - title
    - domain_family
    - required_context_terms
    - feature_codes
    - work_processes 일부
    """
    parts: list[str] = []
    title = profile.get("title") or ""
    if title:
        parts.append(f"제목: {title}")

    domain_family = profile.get("domain_family") or ""
    if domain_family:
        parts.append(f"도메인: {domain_family}")

    terms = profile.get("required_context_terms") or []
    if terms:
        parts.append("핵심 용어: " + ", ".join(str(t) for t in terms[:30]))

    feature_codes = profile.get("feature_codes") or []
    if feature_codes:
        parts.append("위험 특징: " + ", ".join(str(c) for c in feature_codes[:20]))

    negative_terms = profile.get("negative_context_terms") or []
    if negative_terms:
        parts.append("배제 도메인: " + ", ".join(str(t) for t in negative_terms[:10]))

    return ". ".join(parts) if parts else profile.get("guide_code", "")


def load_profiles(limit: int | None = None) -> dict[str, dict]:
    payload = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = payload.get("profiles") or {}
    if limit:
        items = list(profiles.items())[:limit]
        return dict(items)
    return profiles


def embed_batch(client, texts: list[str], model: str) -> list[list[float]]:
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="처음 N개만 (디버깅용)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 텍스트만 출력")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not args.dry_run and not api_key:
        print("ERROR: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        print("  export OPENAI_API_KEY=sk-...", file=sys.stderr)
        return 2

    try:
        import numpy as np
    except ImportError:
        print("ERROR: numpy 미설치. pip install numpy", file=sys.stderr)
        return 2

    profiles = load_profiles(limit=args.limit)
    if not profiles:
        print(f"No profiles found in {PROFILES_PATH}", file=sys.stderr)
        return 1

    guide_codes = sorted(profiles.keys())
    texts = [build_profile_text(profiles[code]) for code in guide_codes]
    print(f"Loaded {len(profiles)} profiles. Model: {args.model}. Batch: {args.batch_size}")

    if args.dry_run:
        print("\n--- Sample profile texts (first 3) ---")
        for code, text in zip(guide_codes[:3], texts[:3]):
            print(f"\n[{code}]\n{text[:500]}")
        return 0

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    embeddings: list[list[float]] = []
    start = time.time()

    for i in range(0, len(texts), args.batch_size):
        batch_texts = texts[i : i + args.batch_size]
        try:
            batch_emb = embed_batch(client, batch_texts, args.model)
        except Exception as exc:
            print(f"ERROR at batch {i}: {exc}", file=sys.stderr)
            return 1
        embeddings.extend(batch_emb)
        elapsed = time.time() - start
        rate = (i + len(batch_texts)) / elapsed if elapsed else 0
        print(
            f"  [{i + len(batch_texts):4d}/{len(texts)}] "
            f"{rate:.1f} items/s  elapsed={elapsed:.1f}s"
        )

    arr = np.array(embeddings, dtype=np.float32)
    codes_arr = np.array(guide_codes, dtype=object)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "count": len(guide_codes),
        "dim": arr.shape[1] if arr.size else 0,
        "source_profiles": str(PROFILES_PATH.relative_to(REPO_ROOT)),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        guide_codes=codes_arr,
        embeddings=arr,
        metadata=json.dumps(metadata, ensure_ascii=False),
    )
    print(f"\nSaved: {args.output}")
    print(f"  shape: {arr.shape}, dtype: {arr.dtype}")
    print(f"  metadata: {json.dumps(metadata, ensure_ascii=False, indent=2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
