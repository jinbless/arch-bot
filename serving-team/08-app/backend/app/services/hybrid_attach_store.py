"""Phase 4 (v5 처방) — hybrid_attach 학습 store (derived cache).

검증된 semantic attach 결과를 누적해 "동일 장면 결정적·LLM 미호출"을 실현(continual / LLM 점진 폐지).
거버넌스 (사용자 승인 design-a):
- **파생 캐시 = 자동**: 누적은 batch(offline 쓰기), support_count≥k + 검증 통과 시 promoted.
  서빙은 promoted 캐시를 **읽기 전용**으로 소비(→ recall/rerank LLM 미호출). regenerable·가역.
- **SSOT = 수동**: canonical_vocab alias / SHE TTL / TBox 편입은 본 store가 *후보 report*만 생성,
  사람 승인 + reasoner/SHACL/manifest 게이트(별도). 본 모듈은 SSOT를 직접 건드리지 않음.

학습 단위 두 종(둘 다 discrete key → 결정적 재사용):
- **alias**: name_norm → canonical codes  (semantic 매칭 entity facet back-fill, normalize 보강)
- **link** : code_sig(정렬 코드) → 검증 guide/SR  (SHE-like, attach 보강)

저장: backend/data/hybrid_attach/learned.json (파생물, gitignore 권장). 서빙은 1회 load 후 in-memory.
플래그(기본 off): HYBRID_ATTACH_CACHE(서빙 읽기), HYBRID_ATTACH_LEARN(런타임 쓰기, batch는 직접 record_*).
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "hybrid_attach" / "learned.json"
PROMOTE_K = int(os.environ.get("HYBRID_ATTACH_PROMOTE_K", "2"))

_LOCK = threading.Lock()
_CACHE: Optional[dict] = None  # 서빙 읽기용 load-once in-memory


def cache_enabled() -> bool:
    """서빙 읽기 경로 활성 (promoted 캐시 소비). env(HYBRID_ATTACH_CACHE) 우선, 없으면 config.OHS_ENABLE_ATTACH_CACHE."""
    env = os.environ.get("HYBRID_ATTACH_CACHE")
    if env is not None and env.strip() != "":
        return env.strip().lower() in ("1", "true", "on", "yes")
    try:
        from app.config import settings
        return bool(settings.OHS_ENABLE_ATTACH_CACHE)
    except Exception:  # noqa: BLE001
        return False


def learn_enabled() -> bool:
    """런타임 쓰기 활성 (batch 누적은 record_* 직접 호출이라 무관)."""
    return os.environ.get("HYBRID_ATTACH_LEARN", "").strip().lower() in ("1", "true", "on", "yes")


def name_sig(name: str) -> str:
    """hazard name → 정규화 키 (소문자·공백압축). alias 결정적 lookup용."""
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def code_sig(codes: list[str]) -> str:
    """canonical 코드 리스트 → 정렬·dedup '|' 서명. link 결정적 lookup용 (순서 무관)."""
    return "|".join(sorted({c for c in (codes or []) if c}))


def _empty() -> dict:
    return {"aliases": {}, "links": {}, "meta": {"promote_k": PROMOTE_K}}


def load(force: bool = False) -> dict:
    """store 로드 (서빙 읽기용 캐시; force=True면 재로딩)."""
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    try:
        _CACHE = json.loads(STORE_PATH.read_text(encoding="utf-8")) if STORE_PATH.exists() else _empty()
    except Exception as e:  # noqa: BLE001
        logger.warning("[HybridAttachStore] load 실패 → empty: %s", e)
        _CACHE = _empty()
    return _CACHE


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 누적 (batch/offline 쓰기) ────────────────────────────────────
def record_alias(data: dict, name: str, codes: list[str], confidence: float = 1.0) -> None:
    sig = name_sig(name)
    if not sig or not codes:
        return
    a = data["aliases"].setdefault(sig, {"codes": {}, "support": 0, "status": "candidate"})
    for c in codes:
        a["codes"][c] = a["codes"].get(c, 0) + 1  # 코드별 득표(여러 관찰서 다른 코드 가능)
    a["support"] += 1
    a["confidence"] = round(max(a.get("confidence", 0.0), float(confidence)), 3)


def record_link(data: dict, codes: list[str], guides: list[dict], srs: list[str], confidence: float = 1.0) -> None:
    sig = code_sig(codes)
    if not sig:
        return
    l = data["links"].setdefault(sig, {"guides": {}, "srs": {}, "support": 0, "status": "candidate"})
    for g in guides or []:
        gc = g.get("guide_code") if isinstance(g, dict) else g
        if gc:
            l["guides"][gc] = l["guides"].get(gc, 0) + 1
    for s in srs or []:
        l["srs"][s] = l["srs"].get(s, 0) + 1
    l["support"] += 1
    l["confidence"] = round(max(l.get("confidence", 0.0), float(confidence)), 3)


def promote(data: dict, k: int = PROMOTE_K) -> dict:
    """support_count≥k 후보를 promoted로 승격 (자동, 임계치 게이트).

    (온톨로지 검증은 누적 시점에서 이미 통과한 링크만 기록한다는 전제 — record 호출측 책임.)
    """
    stats = {"alias_promoted": 0, "link_promoted": 0}
    for a in data["aliases"].values():
        a["status"] = "promoted" if a["support"] >= k else "candidate"
        stats["alias_promoted"] += a["status"] == "promoted"
    for l in data["links"].values():
        l["status"] = "promoted" if l["support"] >= k else "candidate"
        stats["link_promoted"] += l["status"] == "promoted"
    data["meta"]["promote_k"] = k
    return stats


def save_store(data: dict) -> None:
    with _LOCK:
        _save(data)
    load(force=True)  # in-memory 갱신


# ── 서빙 읽기 (promoted만, 결정적) ───────────────────────────────
def get_promoted_alias(name: str) -> Optional[list[str]]:
    """promoted alias의 다수결 코드 반환 (없으면 None). cache_enabled() 확인은 호출측."""
    a = load()["aliases"].get(name_sig(name))
    if not a or a.get("status") != "promoted":
        return None
    return [c for c, _ in sorted(a["codes"].items(), key=lambda kv: kv[1], reverse=True)]


def get_promoted_link(codes: list[str]) -> Optional[dict]:
    """promoted link의 guide/sr (support 내림차순) 반환. 없으면 None."""
    l = load()["links"].get(code_sig(codes))
    if not l or l.get("status") != "promoted":
        return None
    return {
        "guide_codes": [g for g, _ in sorted(l["guides"].items(), key=lambda kv: kv[1], reverse=True)],
        "sr_ids": [s for s, _ in sorted(l["srs"].items(), key=lambda kv: kv[1], reverse=True)],
        "support": l["support"],
    }


def stats() -> dict:
    d = load()
    return {
        "aliases": len(d["aliases"]),
        "aliases_promoted": sum(1 for a in d["aliases"].values() if a.get("status") == "promoted"),
        "links": len(d["links"]),
        "links_promoted": sum(1 for l in d["links"].values() if l.get("status") == "promoted"),
        "promote_k": d.get("meta", {}).get("promote_k"),
    }
