"""의미 retrieval 기반 산업안전보건규칙 '조' 추천 서비스.

근거(2026-06-21 검증): facet 매칭은 article 변별 불가(P@1 1.9%). 장면 텍스트를 임베딩해
gold 장면 kNN으로 후보 조를 모으고(⒞, P@1 57%), LLM이 조문 전문 대조로 선별(rerank, P@1 76%).

KB 아티팩트(semantic_kb.npz/json, build_semantic_article_index.py 산출)만으로 동작 — PG 불요.
파이프라인 입력은 Vision LLM의 장면 서술(photo_description + visual_cues).

recommend_articles(scene_text) → [{article_code, title, retrieval_score, applies, rank}]
"""
from __future__ import annotations

import functools
import json
import os
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parents[2]
REPO = Path(__file__).resolve().parents[5]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
KB_NPZ = ART / "semantic_kb.npz"
KB_JSON = ART / "semantic_kb.json"
EMBED_MODEL = os.environ.get("SEMANTIC_EMBED_MODEL", "text-embedding-3-large")
RERANK_MODEL = os.environ.get("SEMANTIC_RERANK_MODEL", "gpt-5.4")

_RERANK_SYS = (
    "너는 대한민국 산업안전보건 전문가다. 작업장 '장면 서술'과 '후보 조(전문)' 목록을 받는다. "
    "각 후보 조가 그 장면에서 관찰된 위험의 위반으로 성립하는지 조문 근거로 판정하라. "
    "applies: yes(직접 명백)/maybe(정황 필요)/no(무관). 모든 후보를 빠짐없이 판정."
)
_RERANK_SCHEMA = {"name": "v", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"verdicts": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"article_code": {"type": "string"}, "applies": {"type": "string", "enum": ["yes", "maybe", "no"]}},
        "required": ["article_code", "applies"]}}}, "required": ["verdicts"]}}
_APPLY_RANK = {"yes": 0, "maybe": 1, "no": 2}


@functools.lru_cache(maxsize=1)
def _kb():
    z = np.load(KB_NPZ)
    meta = json.loads(KB_JSON.read_text(encoding="utf-8"))
    return {
        "scene_emb": z["scene_emb"], "case_ids": meta["case_ids"], "gold": meta["gold"],
        "art_meta": meta["art_meta"], "model": meta.get("model", EMBED_MODEL),
    }


def _ensure_openai_key() -> None:
    if os.environ.get("OPENAI_API_KEY"):
        return
    for envf in (BACKEND / ".env", BACKEND.parent / ".env"):
        if envf.exists():
            for line in envf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        os.environ["OPENAI_API_KEY"] = v
                        return


@functools.lru_cache(maxsize=1)
def _client():
    _ensure_openai_key()
    from openai import OpenAI
    return OpenAI()


def _embed(text: str) -> np.ndarray:
    r = _client().embeddings.create(model=EMBED_MODEL, input=[text])
    v = np.array(r.data[0].embedding, dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def _candidates(scene_text: str, top_k: int, knn: int, exclude_case_id=None):
    kb = _kb()
    q = _embed(scene_text)
    sims = kb["scene_emb"] @ q
    order = np.argsort(-sims)
    score: dict[str, float] = {}
    used = 0
    for j in order:
        if exclude_case_id is not None and kb["case_ids"][j] == exclude_case_id:
            continue
        w = float(sims[j])
        for code in kb["gold"][j]:
            score[code] = score.get(code, 0.0) + w
        used += 1
        if used >= knn:
            break
    return sorted(score, key=lambda c: -score[c])[:top_k], score


def _rerank(scene_text: str, cands: list[str]) -> dict[str, str]:
    kb = _kb()
    lines = [f"[장면]\n{scene_text}", "", "[후보 조 (전문)]"]
    for c in cands:
        m = kb["art_meta"].get(c, {})
        lines.append(f"- {c} {m.get('title','')}\n  {(m.get('full') or '')[:350]}")
    user = "\n".join(lines) + "\n\n위 후보를 모두 판정하라."
    resp = _client().chat.completions.create(model=RERANK_MODEL, messages=[
        {"role": "system", "content": _RERANK_SYS}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": _RERANK_SCHEMA})
    return {v["article_code"]: v["applies"] for v in json.loads(resp.choices[0].message.content)["verdicts"]}


def recommend_articles(scene_text: str, top_k: int = 8, knn: int = 10,
                       rerank: bool = True, exclude_case_id=None) -> list[dict]:
    """장면 서술 → 산업안전보건규칙 조 추천(검색→rerank). applies='yes'가 상위."""
    kb = _kb()
    cands, score = _candidates(scene_text, top_k, knn, exclude_case_id)
    if not cands:
        return []
    verdicts = _rerank(scene_text, cands) if rerank else {}
    out = []
    for c in cands:
        out.append({
            "article_code": c, "title": kb["art_meta"].get(c, {}).get("title", ""),
            "retrieval_score": round(score[c], 4),
            "applies": verdicts.get(c, "yes" if not rerank else "?"),
        })
    out.sort(key=lambda r: (_APPLY_RANK.get(r["applies"], 3), -r["retrieval_score"]))
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out
