"""Phase B.1 — Guide domain embedding pre-filter.

Runtime에서 candidate guide의 도메인 적합성을 cosine similarity로 빠르게
판정한다. LLM rerank의 회색영역만 LLM에 전달하여 비용 70%+ 절감.

흐름:
  scene_text → embed_scene → scene_emb (cached by hash)
  candidate guide_code → lookup pre-built embedding (오프라인 빌드)
  cosine(scene_emb, guide_emb):
    < drop_threshold  (0.25): 즉시 drop
    < gray_threshold  (0.45): LLM gate로 전달 (gray)
    >= gray_threshold: 기존 scoring 통과

미빌드 상태에서는 graceful degrade (모든 candidate 통과).

Env:
  LLM_RERANK_MODE=off|shadow|active   (off: filter 자체를 호출하지 않는 것이 좋음)
  GUIDE_EMBEDDING_PATH                (default: data-team/05-enrichment/runtime-artifacts/guide_domain_embeddings.npz)
  OPENAI_EMBEDDING_MODEL              (default: text-embedding-3-small)
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


logger = logging.getLogger(__name__)


from app.embedding_config import EMBEDDING_MODEL as DEFAULT_EMBEDDING_MODEL  # WS-DRIFT-5 SSOT
DROP_THRESHOLD = 0.25
GRAY_THRESHOLD = 0.45


def _default_npz_path() -> Path:
    override = os.environ.get("GUIDE_EMBEDDING_PATH")
    if override:
        return Path(override)
    backend_app = Path(__file__).resolve().parents[1]
    for ancestor in backend_app.parents:
        candidate = (
            ancestor / "data-team" / "05-enrichment" / "runtime-artifacts"
            / "guide_domain_embeddings.npz"
        )
        if candidate.exists():
            return candidate
    return (
        Path(__file__).resolve().parents[1] / "data" / "guide_domain_embeddings.npz"
    )


@dataclass
class FilterResult:
    keep: list[str]
    gray: list[str]
    drop: list[str]
    similarities: dict[str, float]

    @property
    def reduction_ratio(self) -> float:
        total = len(self.keep) + len(self.gray) + len(self.drop)
        if not total:
            return 0.0
        return len(self.drop) / total


class GuideEmbeddingFilter:
    """Cosine pre-filter for candidate guide codes.

    Singleton-ish: 첫 호출 시 npz를 load (lazy). Thread-safe.
    """

    _instance: Optional["GuideEmbeddingFilter"] = None
    _instance_lock = threading.Lock()

    def __init__(self, npz_path: Optional[Path] = None) -> None:
        self.npz_path = npz_path or _default_npz_path()
        self._loaded = False
        self._load_lock = threading.Lock()
        self.guide_codes: list[str] = []
        self.code_to_idx: dict[str, int] = {}
        self.embeddings = None  # numpy ndarray, shape (N, dim)
        self.dim: int = 0
        self.metadata: dict = {}
        self._scene_cache: dict[str, "np.ndarray"] = {}  # type: ignore[name-defined]
        self._client = None

    @classmethod
    def instance(cls) -> "GuideEmbeddingFilter":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def is_available(self) -> bool:
        if not self._loaded:
            self._try_load()
        return self.embeddings is not None and len(self.guide_codes) > 0

    def _try_load(self) -> None:
        with self._load_lock:
            if self._loaded:
                return
            self._loaded = True
            if not self.npz_path.exists():
                logger.warning(
                    "GuideEmbeddingFilter: npz not found at %s — degrading to passthrough",
                    self.npz_path,
                )
                return
            try:
                import numpy as np

                data = np.load(self.npz_path, allow_pickle=True)
                self.guide_codes = [str(c) for c in data["guide_codes"]]
                self.embeddings = data["embeddings"]
                self.code_to_idx = {code: i for i, code in enumerate(self.guide_codes)}
                self.dim = (
                    int(self.embeddings.shape[1])
                    if self.embeddings.ndim == 2
                    else 0
                )
                import json as _json

                meta_raw = data.get("metadata") if hasattr(data, "get") else None
                if meta_raw is None and "metadata" in data.files:
                    meta_raw = data["metadata"]
                if meta_raw is not None:
                    try:
                        meta_text = (
                            meta_raw.item() if hasattr(meta_raw, "item") else str(meta_raw)
                        )
                        self.metadata = _json.loads(meta_text)
                    except Exception:
                        self.metadata = {}
                logger.info(
                    "GuideEmbeddingFilter loaded: %d guides, dim=%d, path=%s",
                    len(self.guide_codes),
                    self.dim,
                    self.npz_path,
                )
            except Exception as exc:
                logger.exception(
                    "GuideEmbeddingFilter: failed to load %s: %s",
                    self.npz_path,
                    exc,
                )
                self.embeddings = None
                self.guide_codes = []
                self.code_to_idx = {}

    def _get_client(self):
        if self._client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.warning(
                    "GuideEmbeddingFilter: OPENAI_API_KEY missing — scene embedding will fail"
                )
                return None
            try:
                from app.embedding_config import build_embedding_client

                self._client = build_embedding_client(api_key)  # 타임아웃·재시도 (행 방지)
            except Exception as exc:
                logger.exception("Failed to init OpenAI client for embeddings: %s", exc)
                return None
        return self._client

    def embed_scene(self, scene_text: str) -> Optional["np.ndarray"]:  # type: ignore[name-defined]
        """Embed scene text. Cached by sha256(text)."""
        if not scene_text:
            return None
        # WS-DRIFT-5: 캐시 키에 모델명 포함 — 모델 교체 후 옛 임베딩이 hit로 재사용되어
        # 질의·인덱스 공간이 어긋나는 silent staleness 차단.
        key = hashlib.sha256(
            (DEFAULT_EMBEDDING_MODEL + "\x00" + scene_text).encode("utf-8")
        ).hexdigest()
        cached = self._scene_cache.get(key)
        if cached is not None:
            return cached

        client = self._get_client()
        if client is None:
            return None

        try:
            import numpy as np

            response = client.embeddings.create(
                model=DEFAULT_EMBEDDING_MODEL,
                input=[scene_text],
            )
            vec = np.array(response.data[0].embedding, dtype=np.float32)
            self._scene_cache[key] = vec
            return vec
        except Exception as exc:
            logger.exception("Failed to embed scene: %s", exc)
            return None

    def filter_candidates(
        self,
        scene_text: str,
        candidate_codes: Iterable[str],
        *,
        drop_threshold: float = DROP_THRESHOLD,
        gray_threshold: float = GRAY_THRESHOLD,
    ) -> FilterResult:
        candidates = [c for c in candidate_codes if c]
        if not self.is_available():
            return FilterResult(keep=candidates, gray=[], drop=[], similarities={})
        scene_emb = self.embed_scene(scene_text)
        if scene_emb is None:
            return FilterResult(keep=candidates, gray=[], drop=[], similarities={})

        import numpy as np

        scene_norm = float(np.linalg.norm(scene_emb))
        if scene_norm == 0.0:
            return FilterResult(keep=candidates, gray=[], drop=[], similarities={})
        scene_unit = scene_emb / scene_norm

        keep: list[str] = []
        gray: list[str] = []
        drop: list[str] = []
        similarities: dict[str, float] = {}

        for code in candidates:
            idx = self.code_to_idx.get(code)
            if idx is None:
                keep.append(code)
                continue
            guide_emb = self.embeddings[idx]
            guide_norm = float(np.linalg.norm(guide_emb))
            if guide_norm == 0.0:
                keep.append(code)
                continue
            sim = float(np.dot(scene_unit, guide_emb / guide_norm))
            similarities[code] = round(sim, 4)
            if sim < drop_threshold:
                drop.append(code)
            elif sim < gray_threshold:
                gray.append(code)
            else:
                keep.append(code)

        return FilterResult(keep=keep, gray=gray, drop=drop, similarities=similarities)


def build_scene_text(
    visual_observations: Iterable[str],
    visual_cues: Iterable[str],
    canonical_features: Iterable[str] = (),
    industry_contexts: Iterable[str] = (),
) -> str:
    """Scene 텍스트 빌더 — embedding 입력으로 사용."""
    parts: list[str] = []
    industries = [i for i in industry_contexts if i]
    if industries:
        parts.append("산업: " + ", ".join(industries))
    cues = [c for c in visual_cues if c]
    if cues:
        parts.append("시각 단서: " + ", ".join(cues))
    obs = [o for o in visual_observations if o]
    if obs:
        parts.append("관찰: " + " ".join(obs))
    features = [f for f in canonical_features if f]
    if features:
        parts.append("위험 특징: " + ", ".join(features))
    return ". ".join(parts)
