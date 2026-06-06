"""T2.A — F.3.1 reasoner shadow channel (runtime side).

F.3.2가 mining한 incompatibility axiom을 런타임에 빠르게 shadow-evaluate한다.
실제 reject 안 함 — analysis_log.jsonl의 `reasoner_rejects` field로 logging만.

Phase G.1 (2026-05-18 저녁): axiom 데이터 source 우선순위 변경.
  1. PG `guide_domain_incompatibilities` table (primary, ontology-backed)
  2. JSON `guide_domain_incompatibilities.json` (fallback, PG unavailable 시)

전체 axiom 인덱스 + industry_ko→en map + guide_code→primary_domain은
프로세스 lifetime 동안 1회만 load (lazy module-level cache).
PG ↔ JSON 결과 일치 보장: import_domain_incompatibilities_to_pg.py가
idempotent UPSERT로 PG state ≈ JSON state 유지.

빠른 dict lookup 위주 (~50μs/photo). pyshacl 동등성은 offline script
`pyshacl_shadow_validator.py --pyshacl` 에서 검증.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Module-level cache (lazy init, thread-safe)
_LOCK = threading.Lock()
_LOADED = False
_AXIOMS_INDEX: dict[tuple[str, str], dict] = {}
_INDUSTRY_MAP: dict[str, str] = {}
_GUIDE_DOMAINS: dict[str, str] = {}


def _find_artifacts_dir() -> Path | None:
    """Locate data-team/05-enrichment/runtime-artifacts from backend tree."""
    backend_app = Path(__file__).resolve().parents[1]
    for ancestor in backend_app.parents:
        d = ancestor / "data-team" / "05-enrichment" / "runtime-artifacts"
        if d.exists():
            return d
    return None


def _load_axioms_from_pg() -> dict[tuple[str, str], dict] | None:
    """Phase G.1: PG primary source. Returns None if PG unavailable (fallback to JSON)."""
    try:
        from app.db.database import SessionLocal
        from app.db.models import PgGuideDomainIncompatibility
        from sqlalchemy import select
    except Exception as exc:
        logger.warning("shadow_reasoner: PG ORM import fail (fallback to JSON): %s", exc)
        return None
    try:
        with SessionLocal() as session:
            stmt = select(
                PgGuideDomainIncompatibility.domain_a,
                PgGuideDomainIncompatibility.domain_b,
                PgGuideDomainIncompatibility.confidence,
                PgGuideDomainIncompatibility.level,
            )
            rows = session.execute(stmt).fetchall()
    except Exception as exc:
        logger.warning("shadow_reasoner: PG query fail (fallback to JSON): %s", exc)
        return None
    if not rows:
        # Empty table = PG up but no data; fall back to JSON for safety
        logger.warning("shadow_reasoner: PG table empty, fallback to JSON")
        return None
    index: dict[tuple[str, str], dict] = {}
    for r in rows:
        a, b, conf, level = r
        if not a or not b:
            continue
        meta = {
            "confidence": float(conf) if conf is not None else 0.0,
            "level": level or "candidate",
        }
        index[(a, b)] = meta
        index[(b, a)] = meta  # symmetric
    logger.info("shadow_reasoner: loaded %d axiom pairs from PG", len(index) // 2)
    return index


def _load_axioms_from_json(artifacts_dir: Path) -> dict[tuple[str, str], dict]:
    """Fallback when PG unavailable. Original JSON dict lookup path."""
    path = artifacts_dir / "guide_domain_incompatibilities.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("shadow_reasoner: load axioms JSON fail: %s", exc)
        return {}
    raw = data.get("incompatibilities", [])
    index: dict[tuple[str, str], dict] = {}
    for entry in raw:
        if not entry.get("incompatible"):
            continue
        a = entry.get("domain_a")
        b = entry.get("domain_b")
        if not a or not b:
            continue
        meta = {
            "confidence": float(entry.get("confidence", 0) or 0),
            "level": entry.get("level", "candidate"),
        }
        # Symmetric (both orderings)
        index[(a, b)] = meta
        index[(b, a)] = meta
    return index


def _load_axioms(artifacts_dir: Path) -> dict[tuple[str, str], dict]:
    """Phase G.1: PG primary, JSON fallback. Logs source used."""
    pg_index = _load_axioms_from_pg()
    if pg_index is not None:
        return pg_index
    logger.info("shadow_reasoner: using JSON fallback for axioms")
    return _load_axioms_from_json(artifacts_dir)


def _load_industry_map(artifacts_dir: Path) -> dict[str, str]:
    path = artifacts_dir / "industry_ko_to_en_map.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("shadow_reasoner: load industry_map fail: %s", exc)
        return {}
    return data.get("mappings", {}) or {}


def _load_guide_domains(artifacts_dir: Path) -> dict[str, str]:
    path = artifacts_dir / "guide_llm_domains.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("shadow_reasoner: load guide_domains fail: %s", exc)
        return {}
    classifications = data.get("classifications", {}) or {}
    out: dict[str, str] = {}
    for code, info in classifications.items():
        pd = info.get("primary_domain") if isinstance(info, dict) else None
        if pd:
            out[code] = pd
    return out


def _ensure_loaded() -> None:
    global _LOADED, _AXIOMS_INDEX, _INDUSTRY_MAP, _GUIDE_DOMAINS
    if _LOADED:
        return
    with _LOCK:
        if _LOADED:
            return
        artifacts_dir = _find_artifacts_dir()
        if artifacts_dir is None:
            logger.warning("shadow_reasoner: artifacts dir not found — disabled")
            _LOADED = True  # mark loaded to avoid retry storm; index stays empty
            return
        _AXIOMS_INDEX = _load_axioms(artifacts_dir)
        _INDUSTRY_MAP = _load_industry_map(artifacts_dir)
        _GUIDE_DOMAINS = _load_guide_domains(artifacts_dir)
        _LOADED = True
        logger.info(
            "shadow_reasoner loaded: axioms=%d, industries=%d, guide_domains=%d",
            len(_AXIOMS_INDEX), len(_INDUSTRY_MAP), len(_GUIDE_DOMAINS),
        )


def reset_cache() -> None:
    """Test/dev helper: reset module-level caches."""
    global _LOADED, _AXIOMS_INDEX, _INDUSTRY_MAP, _GUIDE_DOMAINS
    with _LOCK:
        _LOADED = False
        _AXIOMS_INDEX = {}
        _INDUSTRY_MAP = {}
        _GUIDE_DOMAINS = {}


def shadow_validate(
    industry_ko: str,
    candidate_guide_codes: list[str],
) -> list[dict[str, Any]]:
    """Shadow-validate: would F.3.2 axioms reject any candidate guide?

    Pure read-only. Returns empty list on any error or unmapped input
    (best-effort — never raises).

    Returns list of {guide_code, guide_domain, axiom_pair: [a,b],
    confidence, level}.
    """
    try:
        _ensure_loaded()
        if not _AXIOMS_INDEX or not industry_ko or not candidate_guide_codes:
            return []
        industry_en = _INDUSTRY_MAP.get(industry_ko)
        if not industry_en:
            return []
        rejects: list[dict[str, Any]] = []
        for gc in candidate_guide_codes:
            if not gc:
                continue
            gd = _GUIDE_DOMAINS.get(gc)
            if not gd:
                continue
            meta = _AXIOMS_INDEX.get((industry_en, gd))
            if meta is None:
                continue
            rejects.append({
                "guide_code": gc,
                "guide_domain": gd,
                "axiom_pair": [industry_en, gd],
                "confidence": meta["confidence"],
                "level": meta["level"],
            })
        return rejects
    except Exception as exc:
        logger.warning("shadow_reasoner.shadow_validate failed: %s", exc)
        return []


# ═══ WS-GATE-3 — log-only → opt-in hard reject (domain-incompat 게이트) ═══
#
# 기존 shadow_validate는 analysis_log.jsonl write-only(F.3.2 mining 입력)이고, 기본 off인
# LLM_RERANK_MODE(shadow/active) 경로에서만 호출돼 기본 served 경로에 전혀 안 걸린다.
# domain_reject_codes는 기본 served 경로(analysis_pipeline semantic attach 직전)에서 호출돼
# **level=='vetted' AND confidence>=임계** 인 high-confidence 도메인 모순만 hard-drop 대상으로 반환한다.
# confidence-thresholded opt-in이라 FN을 방지(약/candidate incompat은 무시). **기본 off(무회귀)**.


def _domain_reject_enabled() -> bool:
    """WS-GATE-3 — 도메인-부적합 hard reject 활성 여부. env(OHS_ENABLE_DOMAIN_REJECT) 우선.

    **기본 off** → reject ∅ → semantic attach 무변경(byte-identical 무회귀).
    """
    env = os.environ.get("OHS_ENABLE_DOMAIN_REJECT")
    if env is not None and env.strip() != "":
        return env.strip().lower() in ("1", "true", "on", "yes")
    try:
        from app.config import settings
        return bool(getattr(settings, "OHS_ENABLE_DOMAIN_REJECT", False))
    except Exception:  # noqa: BLE001
        return False


def _domain_reject_conf() -> float:
    """WS-GATE-3 — hard reject confidence 임계. env(OHS_DOMAIN_REJECT_CONF) 우선.

    **기본 0.9(매우 높게 = FN 보수)**. vetted라도 임계 미만 confidence면 drop 안 함.
    """
    env = os.environ.get("OHS_DOMAIN_REJECT_CONF")
    if env is not None and env.strip() != "":
        try:
            return float(env.strip())
        except ValueError:
            return 0.9
    try:
        from app.config import settings
        return float(getattr(settings, "OHS_DOMAIN_REJECT_CONF", 0.9) or 0.9)
    except Exception:  # noqa: BLE001
        return 0.9


def domain_reject_codes(
    industry_ko: str,
    candidate_guide_codes: list[str],
) -> set[str]:
    """WS-GATE-3 — opt-in hard reject 대상 guide_code 집합.

    shadow_validate(industry_ko, codes) 결과 중 **level=='vetted' AND
    confidence >= _domain_reject_conf()** 인 guide_code만 반환(hard-drop 대상).
    **기본 off → 빈 집합(무회귀)**. Pure read-only, never raises.

    FN 보수: candidate-level incompat 또는 저confidence vetted는 무시 → 부착 유지.
    facet(CI-corroborated) guide는 호출측에서 semantic 후보에만 적용하므로 영향 없음.
    """
    try:
        if not _domain_reject_enabled():
            return set()
        if not industry_ko or not candidate_guide_codes:
            return set()
        conf_floor = _domain_reject_conf()
        rejects = shadow_validate(industry_ko, candidate_guide_codes)
        out: set[str] = set()
        for r in rejects:
            try:
                if (
                    r.get("level") == "vetted"
                    and float(r.get("confidence") or 0.0) >= conf_floor
                ):
                    gc = r.get("guide_code")
                    if gc:
                        out.add(gc)
            except Exception:  # noqa: BLE001
                continue
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("shadow_reasoner.domain_reject_codes failed: %s", exc)
        return set()
