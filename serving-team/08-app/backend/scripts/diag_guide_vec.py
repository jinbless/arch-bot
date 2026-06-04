#!/usr/bin/env python3
"""ohs_guide 벡터에 실제로 임베딩된 텍스트 확인 (guide당 1벡터, 통째 아님)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from app.services.hybrid_search import get_index  # noqa: E402

col = get_index("ohs_guide").collection
print("ohs_guide 벡터 개수:", col.count())
for gid in ["B-M-11-2025", "B-M-36-2026"]:
    r = col.get(ids=[gid], include=["documents"])
    docs = r.get("documents") or []
    if docs:
        d = docs[0] or ""
        print(f"\n=== [{gid}] 임베딩 텍스트 (총 {len(d)}자) ===")
        print(d[:550])
