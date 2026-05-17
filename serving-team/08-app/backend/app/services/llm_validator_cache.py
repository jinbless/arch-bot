"""Phase B.2 — LLM validator persistent cache.

(scene_hash, guide_code) → {verdict, reason, confidence, ts}

scene_hash는 visual_observations + visual_cues + industry로 만든 sha256.
캐시 히트 시 LLM 호출 0회. 같은 사진 재분석 시 0 비용.

저장: data-team/05-enrichment/runtime-artifacts/llm_validator_cache.json
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


logger = logging.getLogger(__name__)


def _default_cache_path() -> Path:
    override = os.environ.get("LLM_VALIDATOR_CACHE_PATH")
    if override:
        return Path(override)
    backend_app = Path(__file__).resolve().parents[1]
    for ancestor in backend_app.parents:
        candidate = (
            ancestor / "data-team" / "05-enrichment" / "runtime-artifacts"
            / "llm_validator_cache.json"
        )
        if candidate.parent.exists():
            return candidate
    return (
        Path(__file__).resolve().parents[1] / "data" / "llm_validator_cache.json"
    )


@dataclass
class ValidatorVerdict:
    verdict: str  # "accept" | "reject"
    reason: str
    confidence: float
    ts: str

    @property
    def is_reject(self) -> bool:
        return self.verdict == "reject"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "confidence": self.confidence,
            "ts": self.ts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ValidatorVerdict":
        return cls(
            verdict=str(data.get("verdict", "accept")),
            reason=str(data.get("reason", "")),
            confidence=float(data.get("confidence", 0.0)),
            ts=str(data.get("ts", "")),
        )


def make_scene_hash(
    visual_observations: Iterable[str],
    visual_cues: Iterable[str],
    industry_context: str = "",
) -> str:
    payload = json.dumps(
        {
            "obs": sorted(o.strip() for o in visual_observations if o),
            "cues": sorted(c.strip() for c in visual_cues if c),
            "industry": industry_context.strip(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


class LlmValidatorCache:
    _instance: Optional["LlmValidatorCache"] = None
    _instance_lock = threading.Lock()

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or _default_cache_path()
        self._lock = threading.Lock()
        self._cache: dict[str, dict[str, ValidatorVerdict]] = {}
        self._dirty = False
        self._loaded = False

    @classmethod
    def instance(cls) -> "LlmValidatorCache":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            self._loaded = True
            if not self.path.exists():
                return
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                for scene_hash, by_guide in (payload.get("verdicts") or {}).items():
                    self._cache[scene_hash] = {
                        g: ValidatorVerdict.from_dict(v) for g, v in by_guide.items()
                    }
                logger.info(
                    "LlmValidatorCache loaded: %d scenes from %s",
                    len(self._cache),
                    self.path,
                )
            except Exception as exc:
                logger.exception("Failed to load validator cache: %s", exc)

    def get(self, scene_hash: str, guide_code: str) -> Optional[ValidatorVerdict]:
        self._ensure_loaded()
        return self._cache.get(scene_hash, {}).get(guide_code)

    def put(self, scene_hash: str, guide_code: str, verdict: ValidatorVerdict) -> None:
        self._ensure_loaded()
        with self._lock:
            self._cache.setdefault(scene_hash, {})[guide_code] = verdict
            self._dirty = True

    def flush(self) -> None:
        self._ensure_loaded()
        with self._lock:
            if not self._dirty:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "scene_count": len(self._cache),
                "verdicts": {
                    h: {g: v.to_dict() for g, v in by_g.items()}
                    for h, by_g in self._cache.items()
                },
            }
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.path)
            self._dirty = False
