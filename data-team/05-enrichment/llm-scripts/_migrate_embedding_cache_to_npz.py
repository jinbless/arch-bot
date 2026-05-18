"""T1.B (1회성) — embedding cache JSON → npz 변환.

대상:
- alias_embedding_cache.json (51MB) → .npz + .meta.json
- catalog_label_embedding_cache.json (45MB) → .npz + .meta.json

JSON 구조 (현재):
  {
    "<sha256_key>": {
      "axis": "...", "code": "...",
      "aliases": {"text1": [1536 floats], "text2": [...]}
    }
  }

npz + meta 구조:
  .npz: 각 key가 (N, 1536) float32 array
  .meta.json: {key: {axis, code, aliases: [ordered alias texts]}}

기대 효과: 51MB → ~5-10MB (compressed npz).
"""
import json
import sys
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[3]
RUNTIME = REPO / "data-team/05-enrichment/runtime-artifacts"

TARGETS = [
    ("alias_embedding_cache.json", "alias_embedding_cache.npz", "alias_embedding_cache.meta.json"),
    ("catalog_label_embedding_cache.json", "catalog_label_embedding_cache.npz", "catalog_label_embedding_cache.meta.json"),
]


def migrate(json_name: str, npz_name: str, meta_name: str) -> None:
    json_path = RUNTIME / json_name
    npz_path = RUNTIME / npz_name
    meta_path = RUNTIME / meta_name

    if not json_path.is_file():
        print(f"  SKIP — {json_name} not found")
        return

    src_size = json_path.stat().st_size
    print(f"\n[{json_name}] {src_size / 1024 / 1024:.1f}MB → loading...")
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # catalog_label_embedding_cache.json schema differs slightly:
    # { "<cache_key>": { "axes": { "axis_name": { "label_text": {"code": ..., "emb": [...]}, ... }}}}
    is_label_cache = json_name.startswith("catalog_label")

    arrays = {}
    meta = {}

    if is_label_cache:
        # Walk catalog label cache structure
        for cache_key, root in data.items():
            axes = root.get("axes", {}) or {}
            for axis_name, label_map in axes.items():
                if not isinstance(label_map, dict) or not label_map:
                    continue
                sub_key = f"{cache_key}__{axis_name}"
                labels = sorted(label_map.keys())
                embeddings = []
                meta_labels = []
                for label in labels:
                    info = label_map[label]
                    emb = info.get("emb")
                    if not emb:
                        continue
                    embeddings.append(emb)
                    meta_labels.append({"label": label, "code": info.get("code", "")})
                if embeddings:
                    arr = np.array(embeddings, dtype=np.float32)
                    arrays[sub_key] = arr
                    meta[sub_key] = {
                        "cache_key": cache_key, "axis": axis_name,
                        "labels": meta_labels,  # ordered list aligned with array rows
                    }
        print(f"  parsed {len(arrays)} (cache_key, axis) groups (total embeddings: {sum(a.shape[0] for a in arrays.values())})")
    else:
        # auto_register_aliases.py cache schema
        for cache_key, entry in data.items():
            aliases_dict = (entry or {}).get("aliases", {}) or {}
            if not aliases_dict:
                continue
            alias_texts = sorted(aliases_dict.keys())
            embeddings = [aliases_dict[t] for t in alias_texts if aliases_dict[t]]
            if not embeddings:
                continue
            arr = np.array(embeddings, dtype=np.float32)
            arrays[cache_key] = arr
            meta[cache_key] = {
                "axis": entry.get("axis", ""),
                "code": entry.get("code", ""),
                "aliases": alias_texts,
            }
        print(f"  parsed {len(arrays)} (axis, code) entries (total embeddings: {sum(a.shape[0] for a in arrays.values())})")

    if not arrays:
        print(f"  WARN — no embeddings found, skipping write")
        return

    # Atomic write — np.savez_compressed auto-appends .npz, work around
    tmp_npz_stem = npz_path.with_name(npz_path.stem + "_tmp")  # e.g., alias_embedding_cache_tmp
    tmp_meta = meta_path.with_suffix(".json.tmp")
    np.savez_compressed(tmp_npz_stem, **arrays)  # writes tmp_npz_stem.npz
    actual_tmp_npz = tmp_npz_stem.with_suffix(".npz")  # actual file written
    tmp_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    actual_tmp_npz.replace(npz_path)
    tmp_meta.replace(meta_path)

    npz_size = npz_path.stat().st_size
    meta_size = meta_path.stat().st_size
    reduction = (1 - (npz_size + meta_size) / src_size) * 100
    print(f"  ✅ wrote {npz_name} ({npz_size/1024/1024:.1f}MB) + {meta_name} ({meta_size/1024:.0f}KB)")
    print(f"     Reduction: {reduction:.1f}% (from {src_size/1024/1024:.1f}MB)")


def main() -> int:
    print("=" * 60)
    print("T1.B — embedding cache JSON → npz migration")
    print("=" * 60)
    for json_name, npz_name, meta_name in TARGETS:
        migrate(json_name, npz_name, meta_name)
    print()
    print("Next steps:")
    print("  1. Verify scripts work with .npz (auto_register_aliases.py --gate1)")
    print("  2. git rm *.json (old caches, regenerable from npz)")
    print("  3. .gitignore *.json (prevent re-commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
