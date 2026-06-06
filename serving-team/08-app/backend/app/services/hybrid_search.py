"""Phase 2 (v5 처방) — BM25 ⊕ 벡터 hybrid recall (RRF) over 온톨로지-파생 임베딩.

온톨로지 원문 임베딩(`ohs_ns`/`ohs_sr`/`ohs_ci`, scripts/build_kb_embeddings.py 산출)에서
GPT 위험요소 rich text를 질의로 후보 SR/CI/NS를 검색. **후보 생성(recall)만** 담당.
id = 온톨로지 IRI(identifier/canonical_ci_id).

⚠️ 이 recall 출력은 기본적으로 닫힌세계(disjoint/도메인) 검증을 거치지 않는다. 부착 경로
(hazard_to_guide_service)의 실제 검증은 현재 ① PG SSOT 존재확인 ② industry soft 정렬
③ (기본 on) soft LLM rerank 뿐이며, hard disjoint/domain reject은 미구현(계획: WS-GATE-2
절대 cosine floor + WS-GATE-3 shadow_reasoner hard-reject). 즉 "온톨로지(Phase 3)가 부착을
검증·보증"하지 않는다 — over-claim 금지.

순수 mechanism(게이팅 없음). 활성화 결정은 부착 경로(hazard_to_guide_service)에서 플래그로.
BM25는 컬렉션 문서로 lazy 구축(article_service 패턴), 벡터는 ChromaDB cosine.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:  # pragma: no cover
    HAS_BM25 = False

from app.config import settings
from app.utils.text_utils import tokenize_korean

logger = logging.getLogger(__name__)

CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "chromadb"
from app.embedding_config import EMBEDDING_MODEL as EMBED_MODEL  # WS-DRIFT-5 SSOT
RRF_K = 60  # Reciprocal Rank Fusion 상수 (관행값)


class HybridIndex:
    """단일 ChromaDB 컬렉션에 대한 BM25⊕벡터 hybrid 검색기 (lazy)."""

    _client: Optional[chromadb.ClientAPI] = None

    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self._collection = None
        self._bm25 = None
        self._bm25_ids: list[str] = []
        self._bm25_docs: list[str] = []
        self._oai = OpenAI(api_key=settings.OPENAI_API_KEY)

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            cls._client = chromadb.PersistentClient(
                path=str(CHROMA_DIR), settings=ChromaSettings(anonymized_telemetry=False)
            )
        return cls._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self._get_client().get_or_create_collection(
                name=self.collection_name, metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0

    # ── BM25 (lazy, 컬렉션 문서에서 구축) ──────────────────────────
    def _ensure_bm25(self):
        if not HAS_BM25 or self._bm25 is not None:
            return
        try:
            data = self.collection.get(include=["documents"])
            ids = data.get("ids") or []
            docs = data.get("documents") or []
            if not ids:
                return
            self._bm25 = BM25Okapi([tokenize_korean(d or "") for d in docs])
            self._bm25_ids = ids
            self._bm25_docs = docs
            logger.info("BM25 built for %s: %d docs", self.collection_name, len(ids))
        except Exception as e:  # noqa: BLE001
            logger.warning("BM25 build failed (%s): %s", self.collection_name, e)

    def _vector_rank(self, query: str, n: int) -> list[dict]:
        if self.count() == 0:
            return []
        try:
            emb = self._oai.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding
        except Exception as e:  # noqa: BLE001
            logger.warning("embed failed: %s", e)
            return []
        res = self.collection.query(
            query_embeddings=[emb], n_results=n, include=["metadatas", "distances", "documents"]
        )
        ids = (res.get("ids") or [[]])[0]
        out = []
        for i, _id in enumerate(ids):
            out.append({
                "id": _id,
                "doc": res["documents"][0][i],
                "meta": res["metadatas"][0][i],
                "vscore": round(1 - res["distances"][0][i], 4),
            })
        return out

    def _bm25_rank(self, query: str, n: int) -> list[dict]:
        self._ensure_bm25()
        if self._bm25 is None:
            return []
        toks = tokenize_korean(query)
        if not toks:
            return []
        scores = self._bm25.get_scores(toks)
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        out = []
        for i in order[:n]:
            if scores[i] <= 0:
                break
            out.append({"id": self._bm25_ids[i], "doc": self._bm25_docs[i], "bscore": round(float(scores[i]), 4)})
        return out

    def search(self, query: str, n_results: int = 10, pool: int = 30) -> list[dict]:
        """벡터·BM25 각 top-pool → RRF 융합 → top-n_results.

        반환: [{id, doc, meta, rrf, vscore?, bscore?}], rrf 내림차순. id=온톨로지 IRI.
        """
        if not query or not query.strip():
            return []
        v = self._vector_rank(query, pool)
        b = self._bm25_rank(query, pool)
        fused: dict[str, dict] = {}
        for rank, it in enumerate(v):
            f = fused.setdefault(it["id"], {"id": it["id"], "doc": it["doc"], "meta": it.get("meta", {}), "rrf": 0.0})
            f["rrf"] += 1.0 / (RRF_K + rank + 1)
            f["vscore"] = it.get("vscore")
        for rank, it in enumerate(b):
            f = fused.setdefault(it["id"], {"id": it["id"], "doc": it["doc"], "meta": {}, "rrf": 0.0})
            f["rrf"] += 1.0 / (RRF_K + rank + 1)
            f["bscore"] = it.get("bscore")
        ranked = sorted(fused.values(), key=lambda x: x["rrf"], reverse=True)
        for r in ranked:
            r["rrf"] = round(r["rrf"], 6)
        return ranked[:n_results]


# 컬렉션별 캐시 (프로세스 단위)
_INDEXES: dict[str, HybridIndex] = {}

# 온톨로지 엔티티 종류 → ChromaDB 컬렉션
# guide_section: guide를 (source_section) passage로 청킹(ohs_guide_section, 12,680) — 1벡터/guide
#   평균 희석 해소(ablation +0.44, 22:10). 섹션 회수 → guide 집계는 hazard_to_guide_service가 담당.
COLLECTIONS = {
    "sr": "ohs_sr",
    "ns": "ohs_ns",
    "ci": "ohs_ci",
    "guide": "ohs_guide",
    "ci_raw": "ohs_ci_raw",
    "guide_section": "ohs_guide_section",
}


def get_index(collection_name: str) -> HybridIndex:
    if collection_name not in _INDEXES:
        _INDEXES[collection_name] = HybridIndex(collection_name)
    return _INDEXES[collection_name]


def hybrid_search(kind: str, query: str, n_results: int = 10, pool: int = 30) -> list[dict]:
    """kind in COLLECTIONS → 해당 컬렉션 hybrid 검색. 컬렉션 없으면 [].

    WS-EVAL-4: `pool`(BM25·vector 채널별 RRF 회수 깊이)을 .search로 **forward**.
    이전에는 이 wrapper가 pool을 전달하지 않아 .search 기본 30으로 고정됐고, n_results만
    넓혀도 각 채널은 여전히 top-30만 RRF에 기여했다(대형 컬렉션 ohs_ci_raw 54.6K에서
    0.05% 깊이 = 침묵 recall FN). 큰 컬렉션 호출처는 더 깊은 pool을 전달할 수 있다.
    기본값 30은 종전 거동과 동일(무회귀).
    """
    col = COLLECTIONS.get(kind)
    if not col:
        return []
    return get_index(col).search(query, n_results=n_results, pool=pool)
