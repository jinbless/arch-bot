#!/usr/bin/env python3
"""De-risk 후속 — 하이브리드 검증. 8장 실제 사진에서 (gold-reuse ∪ 배포 semantic) → LLM rerank.

발견: 실제 사진에선 gold-reuse(흔한·복합 위험)와 배포 semantic(특정 조문)이 상보적.
가설: 두 소스 합집합을 rerank로 선별하면 각 단독보다 낫다(= 통합안 직접 증명).
출력 real_photo_hybrid.md. 라벨 없음 → 정성 판단(조문 타당성).

사용: .venv/bin/python scripts/real_photo_hybrid.py
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
OUT = ART / "real_photo_hybrid.md"
EMBED_MODEL = "text-embedding-3-large"
RERANK_MODEL = "gpt-5.4"

RR_SYS = ("너는 대한민국 산업안전보건 전문가다. 작업장 장면과 후보 산업안전보건규칙 조(전문)를 보고 "
          "각 조가 그 장면 위험의 위반으로 성립하는지 판정. applies: yes(직접 명백)/maybe(정황)/no(무관). 모두 판정.")
RR_SCHEMA = {"name": "v", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"verdicts": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"article_code": {"type": "string"}, "applies": {"type": "string", "enum": ["yes", "maybe", "no"]}},
        "required": ["article_code", "applies"]}}}, "required": ["verdicts"]}}


def scene_text(res):
    obs = " ".join(o.get("text", "") for o in res.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in res.get("visual_cues") or [])
    return f"{obs} 시각단서: {cues}"


def main():
    vis = json.load(open(VISION, encoding="utf-8"))
    photos = vis["photos"]
    auto = {json.loads(l)["case_id"]: json.loads(l) for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
    pid = json.loads(PROTO_IDS.read_text(encoding="utf-8"))
    kb_cases = pid["cases"]
    S = np.load(PROTO)["S"]
    art_meta = json.loads(KB_JSON.read_text(encoding="utf-8"))["art_meta"]

    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()
    from app.services.hybrid_search import hybrid_search
    db = SessionLocal()
    sr2art = {r[0]: r[1] for r in db.execute(text("select sr_id, article_code from sr_article_mapping where law_type='RULE'")).fetchall()}

    def ttl(c):
        return (art_meta.get(c) or {}).get("title", "")

    def embed(t):
        v = np.array(client.embeddings.create(model=EMBED_MODEL, input=[t]).data[0].embedding, dtype=np.float32)
        return v / (np.linalg.norm(v) + 1e-9)

    def rerank(st, cands):
        lines = [f"[장면]\n{st}", "", "[후보 조 (전문)]"]
        for c in cands:
            m = art_meta.get(c) or {}
            lines.append(f"- {c} {m.get('title','')}\n  {(m.get('full') or '')[:300]}")
        resp = client.chat.completions.create(model=RERANK_MODEL, messages=[
            {"role": "system", "content": RR_SYS}, {"role": "user", "content": "\n".join(lines) + "\n\n모두 판정."}],
            response_format={"type": "json_schema", "json_schema": RR_SCHEMA})
        return {v["article_code"]: v["applies"] for v in json.loads(resp.choices[0].message.content)["verdicts"]}

    md = ["# 실제 사진 8장 — 하이브리드(gold-reuse ∪ 배포 → rerank)", ""]
    for p in photos:
        name = p.get("photo", "?")
        res = p.get("result") or {}
        st = scene_text(res)
        hz = (res.get("hazards") or [{}])[0].get("name", "")
        q = embed(st)
        sims = S @ q
        order = np.argsort(-sims)
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
        gr = [c for c in sorted(score, key=lambda c: -score[c])][:8]
        rows = hybrid_search("sr", st, n_results=20)
        depl, seen = [], set()
        for r in rows:
            a = sr2art.get(r["id"])
            if a and a not in seen:
                seen.add(a); depl.append(a)
            if len(depl) >= 8:
                break
        union, us = [], set()
        for c in gr + depl:
            if c not in us:
                us.add(c); union.append(c)
        vd = rerank(st, union)
        yes = [c for c in union if vd.get(c) == "yes"]
        # 출처 표기
        def src(c):
            return ("G" if c in gr else "") + ("D" if c in depl else "")
        md.append(f"## {name.split('(')[0]}  (hazard: {hz})")
        md.append(f"- gold-reuse top3: {' · '.join(c for c in gr[:3])}")
        md.append(f"- 배포 top3: {' · '.join(c for c in depl[:3])}")
        md.append(f"- **하이브리드 rerank YES:** " + (" · ".join(f"{c}[{src(c)}]({ttl(c)[:16]})" for c in yes) or "(없음)"))
        md.append("")
    db.close()
    OUT.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
