#!/usr/bin/env python3
"""Phase 1 (v5 처방) — 온톨로지 원문에서 파생 임베딩 index 구축 (NS/SR/CI).

근거(plan): 정규화가 문맥을 죽이고 코드만 남겼지만 원문은 보존돼 있음
(norm_statements.text / safety_requirements.title+text / canonical_checklist_items.rep_text).
이 원문을 text-embedding-3-small로 임베딩 → ChromaDB(ohs_ns/ohs_sr/ohs_ci).
온톨로지 IRI(identifier/canonical_ci_id)에 키잉 → 부착 시 검증/전파가 IRI로 이어짐.

GUIDE(ohs_guide)는 title+sub_category+특이 CI 텍스트로 구성 — SR→CI→Guide 체인(희소·skew) 우회.
ARTICLE은 기존 자산(reindex_articles.py) 사용.
BM25는 hybrid_search 서비스가 이 컬렉션에서 lazy 구축(article_service 패턴) — 별도 산출 불요.

실행 (WSL backend venv):
  cd /mnt/c/project/arch-bot/serving-team/08-app/backend
  DATABASE_URL='postgresql://kosha:1229@localhost:5432/kosha' PYTHONIOENCODING=utf-8 \
    ./.venv/bin/python scripts/build_kb_embeddings.py --kind sr,ns          # 빠름(검증)
  ... --kind ci          # 51K (수 분)
  ... (옵션) --limit 100 --dry-run
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import chromadb
import psycopg2
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("build_kb_embeddings")

CHROMA_DIR = Path(__file__).resolve().parent.parent / "data" / "chromadb"
EMBED_MODEL = "text-embedding-3-small"
BATCH = 50

# kind → (collection, SQL, id_field, text_builder, meta_builder)
KINDS = {
    "ns": {
        "collection": "ohs_ns",
        "sql": "SELECT identifier, text FROM norm_statements WHERE text IS NOT NULL AND text <> '' ORDER BY identifier",
        "id": lambda r: r[0],
        "text": lambda r: r[1],
        "meta": lambda r: {"kind": "ns", "identifier": r[0]},
    },
    "sr": {
        "collection": "ohs_sr",
        "sql": "SELECT identifier, COALESCE(title,''), COALESCE(text,'') FROM safety_requirements ORDER BY identifier",
        "id": lambda r: r[0],
        "text": lambda r: (r[1] + "\n" + r[2]).strip(),
        "meta": lambda r: {"kind": "sr", "identifier": r[0], "title": r[1][:300]},
    },
    "ci": {
        "collection": "ohs_ci",
        "sql": "SELECT canonical_ci_id, rep_text FROM canonical_checklist_items WHERE rep_text IS NOT NULL AND rep_text <> '' ORDER BY canonical_ci_id",
        "id": lambda r: r[0],
        "text": lambda r: r[1],
        "meta": lambda r: {"kind": "ci", "identifier": r[0]},
    },
    # GUIDE: title + sub_category + 가이드별 '특이' CI 텍스트(guide_frequency<=3, boilerplate 배제)로
    # 풍부한 주제 신호 구성. SR→CI→Guide 체인(희소·skew)을 우회한 직접 semantic recall용.
    "guide": {
        "collection": "ohs_guide",
        "sql": (
            "SELECT g.guide_code, g.title, COALESCE(g.sub_category,''), "
            "COALESCE((SELECT string_agg(t, ' ') FROM ("
            "  SELECT ci.text AS t FROM checklist_items ci "
            "  WHERE ci.source_guide = g.guide_code AND COALESCE(ci.guide_frequency, 1) <= 3 "
            "  ORDER BY COALESCE(ci.guide_frequency, 1) ASC LIMIT 25"
            ") sub), '') "
            "FROM kosha_guides g ORDER BY g.guide_code"
        ),
        "id": lambda r: r[0],
        "text": lambda r: (r[1] + "\n" + (r[2] or "") + "\n" + (r[3] or ""))[:4000].strip(),
        "meta": lambda r: {"kind": "guide", "identifier": r[0], "title": (r[1] or "")[:300]},
    },
}


def pg_conn():
    dsn = os.environ.get("DATABASE_URL") or "dbname=kosha user=kosha password=1229 host=localhost"
    return psycopg2.connect(dsn)


def build_kind(kind: str, client, oai: OpenAI, limit: int | None, dry: bool) -> int:
    cfg = KINDS[kind]
    conn = pg_conn()
    cur = conn.cursor()
    sql = cfg["sql"] + (f" LIMIT {limit}" if limit else "")
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    logger.info(f"[{kind}] rows={len(rows)} → collection={cfg['collection']}")
    if dry:
        for r in rows[:3]:
            logger.info(f"  id={cfg['id'](r)}  text={cfg['text'](r)[:60]!r}")
        return len(rows)

    # delete+recreate (idempotent)
    try:
        client.delete_collection(cfg["collection"])
    except Exception:
        pass
    col = client.get_or_create_collection(name=cfg["collection"], metadata={"hnsw:space": "cosine"})

    done = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        texts = [cfg["text"](r) for r in batch]
        try:
            resp = oai.embeddings.create(model=EMBED_MODEL, input=texts)
            embs = [d.embedding for d in resp.data]
            col.add(
                ids=[str(cfg["id"](r)) for r in batch],
                embeddings=embs,
                documents=texts,
                metadatas=[cfg["meta"](r) for r in batch],
            )
            done += len(batch)
            if done % 500 == 0 or done == len(rows):
                logger.info(f"  [{kind}] {done}/{len(rows)}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"  [{kind}] batch {i} failed: {e}")
    logger.info(f"[{kind}] done: {col.count()} indexed")
    return col.count()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kind", default="sr,ns,ci", help="comma list: sr,ns,ci,guide")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    kinds = [k.strip() for k in args.kind.split(",") if k.strip() in KINDS]
    if not kinds:
        logger.error("no valid --kind (sr,ns,ci,guide)")
        return 2

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=ChromaSettings(anonymized_telemetry=False))
    oai = None if args.dry_run else OpenAI(api_key=settings.OPENAI_API_KEY)

    logger.info(f"ChromaDB: {CHROMA_DIR}  model={EMBED_MODEL}  kinds={kinds}")
    for k in kinds:
        build_kind(k, client, oai, args.limit, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
