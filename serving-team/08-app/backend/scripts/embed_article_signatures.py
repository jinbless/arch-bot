#!/usr/bin/env python3
"""OWA→CWA — 관찰 시그니처를 임베딩(닫힌세계 인덱스 물질화).

article_signatures.jsonl(build_article_signatures collect 산출)에서 관찰가능(yes/partial)
조문만 골라, violation_scene(위반 사진 묘사)을 주축으로 context/visual_cues/required_measures를
합친 '관찰 언어' 텍스트를 임베딩. 사진 장면 서술과 같은 공간 → 코사인 매칭.

산출: article_sig_emb.npz(E[N,d] L2정규화) + article_sig_emb_meta.json(codes/observable/section/title).

사용: .venv/bin/python scripts/embed_article_signatures.py [--include-partial/--no-partial]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from build_article_signatures import _ensure_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
SIGS = ART / "article_signatures.jsonl"
OUT_NPZ = ART / "article_sig_emb.npz"
OUT_META = ART / "article_sig_emb_meta.json"
EMBED_MODEL = "text-embedding-3-large"


def sig_text(rec: dict) -> str:
    parts = [rec.get("violation_scene", "")]
    if rec.get("context"):
        parts.append(rec["context"])
    cues = rec.get("visual_cues") or []
    if cues:
        parts.append("시각징후: " + "; ".join(cues))
    rm = rec.get("required_measures") or []
    if rm:
        parts.append("요구조치: " + ", ".join(rm))
    eq = rec.get("equipment") or []
    if eq:
        parts.append("설비: " + ", ".join(eq))
    return "\n".join(p for p in parts if p).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-partial", action="store_true", help="observable=yes만 포함(기본은 yes+partial)")
    args = ap.parse_args()

    recs = [json.loads(l) for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()]
    keep = {"yes"} if args.no_partial else {"yes", "partial"}
    obs = [r for r in recs if r.get("observable") in keep and sig_text(r)]
    print(f"전체 {len(recs)} → 관찰가능({'/'.join(sorted(keep))}) {len(obs)} 임베딩")

    _ensure_key()
    from openai import OpenAI
    client = OpenAI()
    texts = [sig_text(r) for r in obs]
    embs = []
    B = 128
    for i in range(0, len(texts), B):
        chunk = texts[i:i + B]
        resp = client.embeddings.create(model=EMBED_MODEL, input=chunk)
        for d in resp.data:
            v = np.array(d.embedding, dtype=np.float32)
            embs.append(v / (np.linalg.norm(v) + 1e-9))
        print(f"  embedded {min(i + B, len(texts))}/{len(texts)}")
    E = np.vstack(embs).astype(np.float32)
    np.savez_compressed(OUT_NPZ, E=E)
    meta = {
        "model": EMBED_MODEL,
        "codes": [r["article_code"] for r in obs],
        "observable": [r["observable"] for r in obs],
        "section": [r.get("section", "") for r in obs],
        "title": [r.get("title", "") for r in obs],
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"saved E{E.shape} → {OUT_NPZ.name} + {OUT_META.name}")


if __name__ == "__main__":
    main()
