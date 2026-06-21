#!/usr/bin/env python3
"""De-risk #1 — 합성→실제 전이 테스트. 8장 실제 사진 Vision 출력으로 gold-reuse vs 배포 semantic 비교.

KB·gold는 합성, 질의는 실제 Vision 서술(claude_vision_8photo_input.json) → 실제 분포에서
gold-reuse가 무너지는지 확인. 라벨 없음 → 타당성(파일명/hazard) 정성 판단. 산출 real_photo_transfer.md.

사용: .venv/bin/python scripts/real_photo_transfer.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("SEMANTIC_ATTACH", "1")
HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402
from judge_sr_article_mapping import _ensure_openai_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
VISION = ART / "claude_vision_8photo_input.json"
GOLD_AUTO = ART / "gold_auto.jsonl"
PROTO = ART / "semantic_proto_emb.npz"
PROTO_IDS = ART / "semantic_proto_emb_ids.json"
KB_JSON = ART / "semantic_kb.json"
OUT = ART / "real_photo_transfer.md"
EMBED_MODEL = "text-embedding-3-large"


def scene_text(res: dict) -> str:
    obs = " ".join(o.get("text", "") for o in res.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in res.get("visual_cues") or [])
    return f"{obs} 시각단서: {cues}"


def main():
    vis = json.load(open(VISION, encoding="utf-8"))
    photos = vis["photos"] if isinstance(vis, dict) and "photos" in vis else (vis if isinstance(vis, list) else list(vis.values()))
    auto = {json.loads(l)["case_id"]: json.loads(l) for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
    pid = json.loads(PROTO_IDS.read_text(encoding="utf-8"))
    kb_cases = pid["cases"]
    z = np.load(PROTO)
    S = z["S"]
    art_meta = json.loads(KB_JSON.read_text(encoding="utf-8"))["art_meta"]

    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()
    from app.services.hybrid_search import hybrid_search

    db = SessionLocal()
    sr2art = {r[0]: r[1] for r in db.execute(text("select sr_id, article_code from sr_article_mapping where law_type='RULE'")).fetchall()}

    def title(code):
        return (art_meta.get(code) or {}).get("title", "")

    def embed(t):
        r = client.embeddings.create(model=EMBED_MODEL, input=[t])
        v = np.array(r.data[0].embedding, dtype=np.float32)
        return v / (np.linalg.norm(v) + 1e-9)

    md = ["# 실제 사진 8장 — gold-reuse vs 배포 semantic (합성→실제 전이)", ""]
    for p in photos:
        name = p.get("photo", "?")
        res = p.get("result") or {}
        st = scene_text(res)
        hz = (res.get("hazards") or [{}])[0].get("name", "")
        q = embed(st)
        sims = S @ q
        order = np.argsort(-sims)
        # gold-reuse
        score, used = {}, 0
        for j in order:
            jc = kb_cases[j]
            if not auto.get(jc, {}).get("core"):
                continue
            for code in auto[jc]["core"]:
                score[code] = score.get(code, 0.0) + float(sims[j])
            used += 1
            if used >= 10:
                break
        gr = sorted(score, key=lambda c: -score[c])[:5]
        top_nbr_sim = float(sims[order[0]])
        # 배포 semantic
        rows = hybrid_search("sr", st, n_results=15)
        seen, depl = set(), []
        for r in rows:
            a = sr2art.get(r["id"])
            if a and a not in seen:
                seen.add(a); depl.append(a)
            if len(depl) >= 5:
                break

        md.append(f"## {name}")
        md.append(f"- Vision hazard: **{hz}** | 최근접 합성이웃 sim={top_nbr_sim:.2f}")
        md.append(f"- 장면: {st[:160]}")
        md.append("- **gold-reuse top5:** " + " · ".join(f"{c}({title(c)[:14]})" for c in gr))
        md.append("- **배포 semantic top5:** " + " · ".join(f"{c}({title(c)[:14]})" for c in depl))
        md.append("")
    db.close()
    OUT.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
