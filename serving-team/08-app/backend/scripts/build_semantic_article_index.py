#!/usr/bin/env python3
"""의미 서빙 KB 물질화 — gold 장면 + RULE 조문 임베딩 + 조문 메타 → 단일 아티팩트.

서빙(semantic_article_service)이 이 아티팩트만으로 동작(PG·재임베딩 불요). 재실행은 gold 갱신 시.
출력: semantic_kb.npz(scene_emb, art_emb) + semantic_kb.json(case_ids, gold[][], art_codes, art_meta).

gold 소스(--gold): consensus(기본, gold_auto core 비어있지 않음 = 두 LLM 합의, 고정밀 KB)
                   | claude(claude_gold_v2 전체 = 커버리지↑, 신뢰도↓).
임베딩은 semantic_proto_emb.npz 캐시와 일치하면 재사용(무료). 사용: .venv/bin/python scripts/build_semantic_article_index.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402
from judge_sr_article_mapping import _ensure_openai_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DUMP = ART / "synthetic_sr_article_dump.jsonl"
GOLD_AUTO = ART / "gold_auto.jsonl"
CLAUDE = ART / "claude_gold_v2.jsonl"
CACHE = ART / "semantic_proto_emb.npz"
CACHE_IDS = ART / "semantic_proto_emb_ids.json"
KB_NPZ = ART / "semantic_kb.npz"
KB_JSON = ART / "semantic_kb.json"
EMBED_MODEL = "text-embedding-3-large"


def _scene_text(d):
    return f"{d.get('photo_description','')} 시각단서: {'; '.join(d.get('visual_cues') or [])}"


def embed(client, texts, batch=256):
    out = []
    for i in range(0, len(texts), batch):
        r = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + batch])
        out.extend([d.embedding for d in r.data])
        print(f"  embedded {min(i+batch,len(texts))}/{len(texts)}", file=sys.stderr)
    m = np.array(out, dtype=np.float32)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", choices=["consensus", "claude"], default="consensus")
    args = ap.parse_args()

    dump = {json.loads(l)["case_id"]: json.loads(l) for l in DUMP.read_text(encoding="utf-8").splitlines() if l.strip()}
    if args.gold == "consensus":
        auto = {json.loads(l)["case_id"]: json.loads(l) for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
        gold_src = {cid: a["core"] for cid, a in auto.items() if a.get("core")}
    else:
        cl = {json.loads(l)["case_id"]: json.loads(l) for l in CLAUDE.read_text(encoding="utf-8").splitlines() if l.strip()}
        gold_src = {cid: c["gold_codes"] for cid, c in cl.items() if c.get("gold_codes")}
    case_ids = [cid for cid in gold_src if cid in dump]
    gold = [gold_src[cid] for cid in case_ids]
    scenes = [_scene_text(dump[cid]) for cid in case_ids]

    db = SessionLocal()
    try:
        arts = db.execute(text("""
            select article_code, title, full_text from articles
            where law_type='RULE' and coalesce(deleted,false)=false and coalesce(full_text,'')<>''
        """)).fetchall()
    finally:
        db.close()
    art_codes = [a[0] for a in arts]
    art_meta = {a[0]: {"title": a[1], "full": a[2][:1000]} for a in arts}

    # 임베딩: 캐시(consensus 동일 case/art)면 재사용
    cache_ok = (args.gold == "consensus" and CACHE.exists() and CACHE_IDS.exists()
                and json.loads(CACHE_IDS.read_text(encoding="utf-8")) == {"cases": case_ids, "art_codes": art_codes, "model": EMBED_MODEL})
    if cache_ok:
        z = np.load(CACHE)
        S, A = z["S"], z["A"]
        print("embeddings: cache 재사용", file=sys.stderr)
    else:
        _ensure_openai_key()
        from openai import OpenAI
        client = OpenAI()
        print("embedding articles...", file=sys.stderr)
        A = embed(client, [f"{art_meta[c]['title']}. {art_meta[c]['full']}" for c in art_codes])
        print("embedding KB scenes...", file=sys.stderr)
        S = embed(client, scenes)

    np.savez(KB_NPZ, scene_emb=S, art_emb=A)
    KB_JSON.write_text(json.dumps({
        "model": EMBED_MODEL, "gold_source": args.gold,
        "case_ids": case_ids, "gold": gold, "art_codes": art_codes, "art_meta": art_meta,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"KB 물질화: {len(case_ids)} 장면 · {len(art_codes)} 조문 → {KB_NPZ.name}, {KB_JSON.name}")


if __name__ == "__main__":
    main()
