#!/usr/bin/env python3
"""OWA→CWA — 사진 장면을 조문 관찰 시그니처에 매칭(닫힌세계 retrieve) + 사람 라벨시트 생성.

각 실제 사진(claude_vision_8photo_input.json)의 장면 서술을 임베딩해 조문 시그니처 인덱스
(article_sig_emb.npz)와 코사인 매칭. 편/장/절/관 계층 boost 옵션. 배포 semantic(hybrid_search
'sr'→조)과 나란히 비교.

산출:
  match_compare.md       사진별 시그니처-매칭 topK vs 배포 semantic topK (정성 비교)
  label_sheet.csv        사람 라벨링용(Excel, UTF-8-BOM). LABEL 열에 y/n/m 기입 → 첫 실제 gold.
  label_sheet_meta.json  사진 목록/소스 카운트

검증 원칙: 라벨 없는 현 단계는 candidate 생성 + recall 확보가 목적. 최종 판정은 사람.
LLM rerank는 (과보수 전력) 여기서 미적용 — 후보 union을 넓게 남겨 사람이 판정.

사용: .venv/bin/python scripts/match_photos_to_articles.py [--knn-boost] [--sig-topk 15] [--depl-topk 10]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
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
from build_article_signatures import _ensure_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
VISION = ART / "claude_vision_8photo_input.json"
SIG_NPZ = ART / "article_sig_emb.npz"
SIG_META = ART / "article_sig_emb_meta.json"
OUT_MD = ART / "match_compare.md"
OUT_CSV = ART / "label_sheet.csv"
OUT_JSON = ART / "label_sheet_meta.json"
EMBED_MODEL = "text-embedding-3-large"


def scene_text(res: dict) -> str:
    obs = " ".join(o.get("text", "") for o in res.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in res.get("visual_cues") or [])
    haz = "; ".join(h.get("name", "") for h in res.get("hazards") or [])
    return f"{obs} 시각단서: {cues} 위험: {haz}".strip()


def group_key(section: str) -> str:
    """절(+관)까지를 그룹키로 — 같은 절/관 = 복합위험 조합 후보."""
    if not section:
        return ""
    m = re.search(r"(절\d+[^>]*)(?:>\s*(관\d+[^>]*))?", section)
    if not m:
        # 절이 없으면 장까지
        mc = re.search(r"(장\d+[^>]*)", section)
        return mc.group(1).strip() if mc else section.strip()
    return (m.group(1) + (" " + m.group(2) if m.group(2) else "")).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sig-topk", type=int, default=15)
    ap.add_argument("--depl-topk", type=int, default=10)
    ap.add_argument("--knn-boost", action="store_true", help="같은 절/관 sibling 소폭 가산")
    args = ap.parse_args()

    vis = json.load(open(VISION, encoding="utf-8"))
    photos = vis["photos"]
    E = np.load(SIG_NPZ)["E"]
    meta = json.loads(SIG_META.read_text(encoding="utf-8"))
    codes = meta["codes"]
    sec = meta["section"]
    ttl = meta["title"]
    code2row = {c: i for i, c in enumerate(codes)}
    grp = [group_key(s) for s in sec]

    _ensure_key()
    from openai import OpenAI
    client = OpenAI()

    db = SessionLocal()
    full = {r[0]: r[1] for r in db.execute(text(
        "select article_code, full_text from articles where law_type='RULE' and not deleted")).fetchall()}
    sr2art = {r[0]: r[1] for r in db.execute(text(
        "select sr_id, article_code from sr_article_mapping where law_type='RULE'")).fetchall()}
    sigrec = {json.loads(l)["article_code"]: json.loads(l)
              for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    db.close()

    try:
        from app.services.hybrid_search import hybrid_search
        have_hybrid = True
    except Exception as e:  # noqa: BLE001
        print(f"[warn] hybrid_search 불가 ({e}) — 배포 비교 생략", file=sys.stderr)
        have_hybrid = False

    def embed(t):
        r = client.embeddings.create(model=EMBED_MODEL, input=[t])
        v = np.array(r.data[0].embedding, dtype=np.float32)
        return v / (np.linalg.norm(v) + 1e-9)

    md = ["# 사진 8장 — 시그니처 매칭 vs 배포 semantic", ""]
    csv_rows = []
    photo_meta = []

    for p in photos:
        name = p.get("photo", "?")
        short = name.split("(")[0]
        res = p.get("result") or {}
        st = scene_text(res)
        q = embed(st)
        sims = E @ q  # 코사인(둘 다 L2정규화)
        order = np.argsort(-sims)

        # 시그니처 매칭 top-K
        sig_top = [(codes[i], float(sims[i])) for i in order[:args.sig_topk]]

        # 계층 boost(옵션): top-5 그룹의 sibling을 소폭 가산해 재정렬
        if args.knn_boost:
            top_grps = {grp[i] for i in order[:5] if grp[i]}
            boosted = sims.copy()
            for i in range(len(codes)):
                if grp[i] in top_grps:
                    boosted[i] += 0.03
            order_b = np.argsort(-boosted)
            sig_top = [(codes[i], float(boosted[i])) for i in order_b[:args.sig_topk]]

        # 배포 semantic
        depl = []
        if have_hybrid:
            try:
                rows = hybrid_search("sr", st, n_results=30)
                seen = set()
                for r in rows:
                    a = sr2art.get(r["id"])
                    if a and a not in seen:
                        seen.add(a); depl.append(a)
                    if len(depl) >= args.depl_topk:
                        break
            except Exception as e:  # noqa: BLE001
                print(f"[warn] hybrid '{short}': {e}", file=sys.stderr)

        sig_codes = [c for c, _ in sig_top]
        sig_score = {c: s for c, s in sig_top}

        # 비교 리포트
        md.append(f"## {short}  (industry: {p.get('industry','')})")
        md.append(f"- 장면: {st[:180]}")
        md.append(f"- **시그니처 top8:** " + " · ".join(
            f"{c}({ttl[code2row[c]][:12]},{sig_score[c]:.2f})" for c in sig_codes[:8]))
        md.append(f"- **배포 semantic top8:** " + " · ".join(
            f"{c}({ttl[code2row.get(c,0)][:12] if c in code2row else (sigrec.get(c,{}).get('title',''))[:12]})"
            for c in depl[:8]))
        md.append("")

        # 라벨시트 candidate union (recall 우선: sig ∪ depl)
        union, src = [], {}
        for c in sig_codes:
            if c not in src:
                union.append(c); src[c] = []
            src[c].append(f"SIG{sig_codes.index(c)+1}")
        for c in depl:
            if c not in src:
                union.append(c); src[c] = []
            src[c].append(f"DEPL{depl.index(c)+1}")

        for c in union:
            rec = sigrec.get(c, {})
            csv_rows.append({
                "photo": short,
                "article_code": c,
                "title": rec.get("title", "") or "",
                "section": (rec.get("section", "") or "")[:80],
                "observable": rec.get("observable", "?"),
                "sources": "/".join(src[c]),
                "sig_sim": f"{sig_score.get(c, 0):.3f}" if c in sig_score else "",
                "violation_scene": rec.get("violation_scene", "") or "",
                "full_excerpt": (full.get(c, "") or "")[:280].replace("\n", " "),
                "LABEL": "",
            })
        photo_meta.append({"photo": short, "industry": p.get("industry", ""),
                           "n_candidates": len(union),
                           "n_sig": len(sig_codes), "n_depl": len(depl)})

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    cols = ["photo", "article_code", "title", "section", "observable", "sources",
            "sig_sim", "violation_scene", "full_excerpt", "LABEL"]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(csv_rows)
    OUT_JSON.write_text(json.dumps({"photos": photo_meta, "n_rows": len(csv_rows)},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"compare → {OUT_MD.name}")
    print(f"label sheet({len(csv_rows)}행) → {OUT_CSV.name}  (Excel에서 LABEL 열에 y/n/m 기입)")
    for pm in photo_meta:
        print(f"  {pm['photo']}: cand {pm['n_candidates']} (sig {pm['n_sig']} / depl {pm['n_depl']})")


if __name__ == "__main__":
    main()
