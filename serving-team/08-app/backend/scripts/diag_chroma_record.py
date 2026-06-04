#!/usr/bin/env python3
"""ChromaDB record 1건 구조 확인 — id + document(원문) + metadata + embedding(벡터) 동일 record?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from app.services.hybrid_search import get_index  # noqa: E402

col = get_index("ohs_ci_raw").collection
r = col.get(limit=1, include=["documents", "metadatas", "embeddings"])
print("=== ohs_ci_raw record 1건 ===")
print("id        :", r["ids"][0])
print("document  :", (r["documents"][0] or "")[:110])
print("metadata  :", r["metadatas"][0])
emb = r["embeddings"][0]
print(f"embedding : dim={len(emb)}  앞5={[round(float(x), 4) for x in emb[:5]]}")
