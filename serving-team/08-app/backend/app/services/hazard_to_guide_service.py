"""Hazard-Direct Pivot Phase 3 Day 1-2 — hazard_to_guide_service.

각 GPT hazard.name별로 catalog code 매핑 → SR → Guide 추출 + grouping.
hazard_rule_engine.query_sr_for_facets() + get_guides_from_srs() 재사용
(Phase G.2 domain profile + Phase G.3 penalty 차별점 유지).

핵심 차이점 (vs 기존 SHE-based path):
- SHE matcher 우회 (broadness 회귀 risk 제거)
- hazard별 grouping (frontend UX 친화적, moellab 스타일)
- canonical 3축 → SR → Guide는 동일 (penalty 3-경로 차별점 보존)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from app.services.hazard_rule_engine import (
    get_guides_from_srs,
    get_guides_by_hazard_features,
    query_sr_for_facets,
)
from app.services import hybrid_attach_store as _attach_store

logger = logging.getLogger(__name__)


# ═══ v5 처방 Phase 3 — semantic attach (온톨로지 SSOT·검증·근거 + 파생 임베딩 recall) ═══

def _semantic_attach_enabled() -> bool:
    """SEMANTIC_ATTACH 활성 여부. env(평가 하니스 A/B 1-프로세스용) 우선, 없으면 config.OHS_ENABLE_HYBRID_SEARCH.

    **기본 off** → semantic 후보 ∅ → SR 집합·Guide 부착이 기존 facet 경로와 동일(무회귀).
    """
    env = os.environ.get("SEMANTIC_ATTACH")
    if env is not None and env.strip() != "":
        return env.strip().lower() in ("1", "true", "on", "yes")
    try:
        from app.config import settings
        return bool(settings.OHS_ENABLE_HYBRID_SEARCH)
    except Exception:  # noqa: BLE001
        return False


def _semantic_rerank_enabled() -> bool:
    """bounded LLM rerank 활성. env(SEMANTIC_ATTACH_RERANK) 우선, 없으면 config.OHS_ENABLE_SEMANTIC_RERANK.

    semantic recall은 정확하지만 top-1 절대 적합도에 헤드룸(eval 입증) → 후보 top-K를
    LLM이 재정렬해 정밀도↑. **기본 off**(결정적·무비용). on일 때만 hazard당 1회 호출.
    """
    env = os.environ.get("SEMANTIC_ATTACH_RERANK")
    if env is not None and env.strip() != "":
        return env.strip().lower() in ("1", "true", "on", "yes")
    try:
        from app.config import settings
        return bool(settings.OHS_ENABLE_SEMANTIC_RERANK)
    except Exception:  # noqa: BLE001
        return False


def _rerank_guides_llm(rich_text: str, guides: list[dict], model: str = "gpt-4.1-mini") -> list[dict]:
    """bounded LLM rerank — hazard 원문 ↔ 후보 guide 적합성을 LLM이 0~10 채점 후 재정렬.

    search_enhancer.rerank_results 패턴의 sync 버전(match_hazards_to_guides가 sync). 후보 enum만
    평가(bounded). 실패 시 recall 순서 유지(graceful). 0점(무관)은 제거하되 전부 0이면 recall 유지(coverage).
    """
    if len(guides) <= 1:
        return guides
    try:
        from openai import OpenAI
        from app.config import settings

        listing = "\n".join(f"[{i}] {g.get('guide_code')}: {g.get('title', '')}" for i, g in enumerate(guides))
        prompt = (
            f"[위험 상황]\n{rich_text[:700]}\n\n[후보 KOSHA 가이드]\n{listing}\n\n"
            "각 후보가 이 위험의 '표준 개선 절차' 근거로 얼마나 적합한지 0~10으로 평가하세요. "
            "10=직접 적합, 7~9=관련 위험유형, 4~6=간접, 0~3=무관. "
            "JSON만: {\"scores\": [{\"i\": 번호, \"s\": 점수}, ...]}"
        )
        oai = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = oai.chat.completions.create(
            model=model, temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "한국 산업안전보건(KOSHA) 전문가. 오직 JSON만 출력."},
                {"role": "user", "content": prompt},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        score_map = {int(x["i"]): float(x["s"]) for x in data.get("scores", []) if "i" in x and "s" in x}
    except Exception as e:  # noqa: BLE001
        logger.warning("[SemanticAttach] guide LLM rerank 실패 → recall 순서 유지: %s", e)
        return guides

    reranked: list[dict] = []
    for i, g in enumerate(guides):
        s = score_map.get(i)
        if s is None or s <= 0:
            continue  # LLM 미채점/무관(0) → 제거
        g2 = dict(g)
        g2["relevance_score"] = round(min(0.99, max(0.0, s / 10.0)), 3)
        g2["mapping_type"] = "hybrid_semantic_rerank"
        g2["llm_rerank_score"] = s
        reranked.append(g2)
    reranked.sort(key=lambda x: x["relevance_score"], reverse=True)
    return reranked or guides  # 전부 0이면 recall 유지(coverage 보존)


def _hazard_rich_text(h: dict) -> str:
    """GPT hazard 원문 결합 — name + description + location + preventive_measures.

    normalize는 hazard.name만 코드화(맥락 소실)하지만 부착 recall에는 원문 전체가 필요(v5 처방 핵심).
    match_hazards_to_guides가 raw hazards를 받으므로 normalizer 변경 없이 여기서 직접 결합.
    """
    parts = [
        (h.get("name") or "").strip(),
        (h.get("description") or "").strip(),
        (h.get("location") or "").strip(),
    ]
    for m in h.get("preventive_measures") or []:
        if isinstance(m, str) and m.strip():
            parts.append(m.strip())
    return " ".join(p for p in parts if p)


def _semantic_sr_candidates(
    db: Session,
    rich_text: str,
    n: int,
    industry_contexts: Optional[list[str]] = None,
) -> list[dict]:
    """rich text → hybrid recall(SR) → 온톨로지 검증. 반환 [{identifier, rrf, title, citable, domain_alignment}].

    온톨로지 역할(v5 — recall은 임베딩, precision·근거는 온톨로지):
    - **SSOT 존재 검증(hard reject)**: 인덱스에만 있고 PgSafetyRequirement에 없는 stale id 제거.
    - **근거(citability 주석)**: sr_article_mapping 보유 = 조문/벌칙 인용 가능(부착 정당성).
    - **도메인 정합(soft 주석)**: applicable_industry vs 장면 산업(industry는 hard rule 아님 — 설계 준수).
    - hard disjoint/domain reject은 Phase 4(disjoint 공리 PG 물질화) 이후 추가.
    """
    if not rich_text or not rich_text.strip():
        return []
    try:
        from app.services.hybrid_search import hybrid_search

        rows = hybrid_search("sr", rich_text, n_results=max(n * 2, 10))
    except Exception as e:  # noqa: BLE001
        logger.warning("[SemanticAttach] hybrid_search 실패 → facet fallback: %s", e)
        return []
    if not rows:
        return []

    from app.db.models import PgSafetyRequirement, PgSrArticleMapping
    from app.services.industry_context import score_industry_alignment

    ids = [r["id"] for r in rows]
    sr_objs = {
        s.identifier: s
        for s in db.query(PgSafetyRequirement)
        .filter(PgSafetyRequirement.identifier.in_(ids))
        .all()
    }
    citable_ids = {
        row[0]
        for row in db.query(PgSrArticleMapping.sr_id)
        .filter(PgSrArticleMapping.sr_id.in_(ids))
        .distinct()
    }
    industry_contexts = industry_contexts or []
    out: list[dict] = []
    rejected_missing = 0
    for r in rows:
        sr = sr_objs.get(r["id"])
        if sr is None:
            rejected_missing += 1
            continue  # SSOT 존재 검증 실패 → 거부
        _adj, alignment, _ = score_industry_alignment(sr.applicable_industry or [], industry_contexts)
        out.append({
            "identifier": r["id"],
            "rrf": r.get("rrf"),
            "title": sr.title,
            "citable": r["id"] in citable_ids,
            "domain_alignment": alignment,
        })
        if len(out) >= n:
            break
    if rejected_missing:
        logger.info("[SemanticAttach] SSOT 존재검증으로 %d개 stale SR 거부", rejected_missing)
    return out


def _semantic_guide_candidates(
    db: Session,
    rich_text: str,
    n: int,
    industry_contexts: Optional[list[str]] = None,
) -> list[dict]:
    """rich text → hybrid recall(GUIDE) → 온톨로지 존재 검증. SR→CI→Guide 체인(희소·skew) 우회.

    SR recall이 정확해도(지게차→SR-VEHICLE) SR→CI→Guide 링크가 vehicle SR엔 희소하고
    전기/철도 SR엔 조밀 → 합산 시 전기 guide가 압도(실측). 따라서 guide는 원문에서 직접 recall.

    반환은 guide dict(_merge_guide_paths 호환). relevance_score는 hybrid **순위** 기반
    ordinal(0.92−0.04·rank)+산업 정합 — 튜닝 점수 아님(recall 순위 보존).
    """
    if not rich_text or not rich_text.strip():
        return []
    try:
        from app.services.hybrid_search import hybrid_search

        rows = hybrid_search("guide", rich_text, n_results=max(n * 2, 8))
    except Exception as e:  # noqa: BLE001
        logger.warning("[SemanticAttach] guide hybrid_search 실패 → SR→CI fallback: %s", e)
        return []
    if not rows:
        return []

    from app.db.models import PgKoshaGuide
    from app.services.industry_context import infer_industry_context, score_industry_alignment

    ids = [r["id"] for r in rows]
    gmap = {
        g.guide_code: g
        for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(ids)).all()
    }
    industry_contexts = industry_contexts or []
    out: list[dict] = []
    for rank, r in enumerate(rows):
        g = gmap.get(r["id"])
        if g is None:
            continue  # SSOT 존재 검증
        gi = infer_industry_context(text=" ".join(filter(None, [g.title, g.sub_category])))
        adj, alignment, _ = score_industry_alignment(gi.active_industries, industry_contexts)
        out.append({
            "guide_code": g.guide_code,
            "title": g.title,
            "classification": g.domain,
            "industry_hints": gi.active_industries,
            "industry_alignment": alignment,
            "relevant_sections": [],
            "relevance_score": round(min(0.99, max(0.0, 0.92 - 0.04 * rank + adj)), 3),
            "mapping_type": "hybrid_semantic",
            "ci_hit_count": 0,
        })
    # bounded LLM rerank (flag on) — 후보 enum top-K를 LLM이 재정렬해 절대 정밀도↑.
    if _semantic_rerank_enabled():
        out = _rerank_guides_llm(rich_text, out)
    return out[:n]


def _cached_guides(db: Session, guide_codes: list[str], n: int) -> list[dict]:
    """Phase 4 — promoted 학습 캐시의 guide_code → guide dict (제목 PG 조회). 결정적, LLM 미호출."""
    if not guide_codes:
        return []
    from app.db.models import PgKoshaGuide

    top = guide_codes[:n]
    gmap = {g.guide_code: g for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(top)).all()}
    out: list[dict] = []
    for rank, gc in enumerate(top):
        g = gmap.get(gc)
        if g is None:
            continue  # 캐시에만 있고 PG에 없는 stale → SSOT 존재검증
        out.append({
            "guide_code": gc,
            "title": g.title,
            "classification": g.domain,
            "industry_hints": [],
            "industry_alignment": None,
            "relevant_sections": [],
            "relevance_score": round(max(0.0, 0.95 - 0.05 * rank), 3),
            "mapping_type": "hybrid_cache",
            "ci_hit_count": 0,
        })
    return out


def _merge_guide_paths(direct: list[dict], ci: list[dict], limit: int) -> list[dict]:
    """P2 — Guide 직접 매핑(우선) + CI 경유 union.

    - 직접 매핑(guide_hazard_direct)을 base로. 양쪽에 모두 있으면 직접 점수에 bonus(+0.15)
      가산하고 mapping_type을 'guide_hazard_direct+ci'로, ci_hit_count 보존.
    - CI 경유만 있는 Guide는 그대로 보충(직접 매핑이 없으므로 후순위).
    """
    by_code: dict[str, dict] = {}
    for g in direct:
        by_code[g["guide_code"]] = dict(g)
    for g in ci:
        code = g["guide_code"]
        if code in by_code:
            cur = by_code[code]
            cur["relevance_score"] = min(0.99, cur["relevance_score"] + 0.15)
            cur["mapping_type"] = "guide_hazard_direct+ci"
            cur["ci_hit_count"] = g.get("ci_hit_count", 0)
            cur["weighted_ci"] = g.get("weighted_ci", 0.0)
        else:
            g2 = dict(g)
            # 직접 위험 매핑이 CI fan-out보다 신뢰도 높음 → CI-only는 근소 demotion으로
            # 동점/근소차에서 직접 매핑 아래로. (예: ERGONOMIC에서 '오토바이 배달'(CI 경유)이
            #  근골격계 예방 직접 guide와 동점이라 위로 가던 문제 제거.)
            g2["relevance_score"] = max(0.0, float(g2.get("relevance_score", 0.0)) - 0.06)
            by_code[code] = g2
    merged = sorted(by_code.values(), key=lambda x: x["relevance_score"], reverse=True)
    return merged[:limit]


def _stack_semantic_first(sem: list[dict], direct: list[dict], limit: int) -> list[dict]:
    """semantic(정밀) 우선 — facet 직접은 semantic 미충족 슬롯만 보충(semantic 최저점 아래로 캡).

    facet GF-direct는 generic accident(FALL_ON_GROUND 등)에 건설/교량 가이드를 score=0.99로
    내보내 semantic을 압도하는 문제(전도/미끄럼→현수교)가 있음. semantic을 항상 위에 쌓고
    facet은 semantic 최저점 아래로 capping → 정밀 recall이 generic noise에 안 짐.
    """
    out = [dict(g) for g in sem]
    seen = {g.get("guide_code") for g in out}
    floor = min((float(g.get("relevance_score") or 0.0) for g in out), default=0.5)
    for g in direct or []:
        gc = g.get("guide_code")
        if not gc or gc in seen:
            continue
        g2 = dict(g)
        g2["relevance_score"] = round(min(float(g2.get("relevance_score") or 0.5), floor - 0.01), 3)
        out.append(g2)
        seen.add(gc)
    out.sort(key=lambda x: float(x.get("relevance_score") or 0.0), reverse=True)
    return out[:limit]


def _axis_field(axis: str) -> str:
    return {
        "accident_type": "accident_types",
        "hazardous_agent": "hazardous_agents",
        "work_context": "work_contexts",
    }.get(axis, "")


def match_hazards_to_guides(
    db: Session,
    hazards: list[dict],
    canonical: dict,
    industry_contexts: Optional[list[str]] = None,
    guides_per_hazard: int = 3,
    sr_limit_per_hazard: int = 20,
    context_work_contexts: Optional[list[str]] = None,
) -> tuple[list[dict], list[str]]:
    """⭐ Hazard-Direct Pivot 핵심 — hazard별 Guide 매핑.

    Args:
        hazards: GPT hazards[] (name, risk_level, location, description, preventive_measures)
        canonical: normalize_hazards_array 결과 (hazard_name_to_codes 포함)
        industry_contexts: Phase G.2 domain profile gating용
        guides_per_hazard: hazard 1건당 최대 Guide 수 (default 3)
        sr_limit_per_hazard: hazard별 SR 쿼리 limit

    Returns:
        (hazard_guide_relations, sr_ids_global)
        hazard_guide_relations: [
            {
                "hazard_name": "추락",
                "risk_level": "high",
                "location": "...",
                "description": "...",
                "preventive_measures": [...],
                "mapped_codes": ["accident_type.FALL_FROM_HEIGHT"],
                "guides": [{guide_code, title, classification, relevance_score, mapping_type, ci_hit_count, industry_alignment}],
                "matched_sr_count": int,
            },
            ...
        ]
        sr_ids_global: hazard들 union으로 매칭된 SR id 리스트 (penalty path 생성 시 재사용)
    """
    industry_contexts = industry_contexts or []
    hazard_name_to_codes: dict[str, list[str]] = canonical.get("hazard_name_to_codes", {}) or {}

    # breadth 게이팅용 관찰 work_context: 외부 전달(IMAGE risk_features) + 전체 hazard들의 work_context union.
    # 충돌(COLLISION)처럼 광범위한 accident 단독 매칭 시, 사진 work_context(VEHICLE=지게차)와도
    # 매칭되는 Guide를 hazard-direct에서 부스트해 "오토바이 배달" 류 오매칭 억제.
    global_wc: set[str] = set(context_work_contexts or [])
    for _h in hazards or []:
        for _c in hazard_name_to_codes.get((_h.get("name") or "").strip(), []) or []:
            if _c.startswith("work_context."):
                global_wc.add(_c.split(".", 1)[1])
    global_wc_list = sorted(global_wc)

    relations: list[dict] = []
    sr_id_set: set[str] = set()
    semantic_on = _semantic_attach_enabled()

    for h in hazards or []:
        name = (h.get("name") or "").strip()
        if not name:
            continue
        codes = hazard_name_to_codes.get(name) or []
        # codes 형식: "axis.code"
        accident_types: list[str] = []
        hazardous_agents: list[str] = []
        work_contexts: list[str] = []
        for compound in codes:
            if "." not in compound:
                continue
            axis, code = compound.split(".", 1)
            if axis == "accident_type":
                accident_types.append(code)
            elif axis == "hazardous_agent":
                hazardous_agents.append(code)
            elif axis == "work_context":
                work_contexts.append(code)

        has_facets = bool(accident_types or hazardous_agents or work_contexts)

        # Phase 4 — 학습 promoted 캐시 (결정적; recall 임베딩·rerank LLM 우회).
        # semantic_on & HYBRID_ATTACH_CACHE에서만. flag off면 cache_guides=∅ → 기존 경로 그대로(무회귀).
        cache_guides: list[dict] = []
        cache_sr_ids: list[str] = []
        if semantic_on and _attach_store.cache_enabled():
            if not has_facets:  # 0-코드 hazard → 학습 alias로 back-fill (normalize 보강)
                for compound in _attach_store.get_promoted_alias(name) or []:
                    if "." not in compound:
                        continue
                    ax, cd = compound.split(".", 1)
                    if ax == "accident_type":
                        accident_types.append(cd)
                    elif ax == "hazardous_agent":
                        hazardous_agents.append(cd)
                    elif ax == "work_context":
                        work_contexts.append(cd)
                codes = (
                    [f"accident_type.{c}" for c in accident_types]
                    + [f"hazardous_agent.{c}" for c in hazardous_agents]
                    + [f"work_context.{c}" for c in work_contexts]
                ) or codes
                has_facets = bool(accident_types or hazardous_agents or work_contexts)
            link = _attach_store.get_promoted_link(codes)
            if link and link.get("guide_codes"):
                cache_guides = _cached_guides(db, link["guide_codes"], guides_per_hazard)
                cache_sr_ids = link.get("sr_ids") or []

        # ① facet 경로 SR (기존) — broad @> recall. flag off면 이게 부착 SR 집합.
        facet_sr_ids: list[str] = []
        if has_facets:
            sr_rows = query_sr_for_facets(
                db,
                accident_types=accident_types,
                hazardous_agents=hazardous_agents,
                work_contexts=work_contexts,
                limit=sr_limit_per_hazard,
                industry_contexts=industry_contexts,
            )
            facet_sr_ids = [row["identifier"] for row in sr_rows]

        # ② semantic recall — 캐시 hit면 우회(recall 임베딩·rerank LLM 미호출).
        if cache_guides:
            rich_text, semantic_sr_ids = "", cache_sr_ids
        else:
            rich_text = _hazard_rich_text(h) if semantic_on else ""
            semantic_sr = (
                _semantic_sr_candidates(db, rich_text, n=sr_limit_per_hazard, industry_contexts=industry_contexts)
                if semantic_on
                else []
            )
            semantic_sr_ids = [s["identifier"] for s in semantic_sr]

        # 부착 SR 집합 결정 (semantic ∅·flag off → facet 그대로, 바이트 동일·무회귀).
        if semantic_sr_ids:
            sr_for_guides = list(dict.fromkeys(semantic_sr_ids + facet_sr_ids))[:sr_limit_per_hazard]
            attach_method = "hybrid_cache" if cache_guides else ("hybrid+facet" if facet_sr_ids else "hybrid")
        else:
            sr_for_guides = facet_sr_ids
            attach_method = "hybrid_cache" if cache_guides else "facet"
        sr_id_set.update(sr_for_guides)

        if not sr_for_guides and not has_facets and not cache_guides:
            # 매핑 실패 — guides 없이 hazard만 보여줌 (기존 동작)
            relations.append({
                "hazard_name": name,
                "risk_level": h.get("risk_level", ""),
                "location": h.get("location", ""),
                "description": h.get("description", ""),
                "preventive_measures": list(h.get("preventive_measures") or []),
                "mapped_codes": [],
                "guides": [],
                "matched_sr_count": 0,
                "attach_method": attach_method,
            })
            continue

        # facet 직접 매핑(GF, curated, deterministic)은 항상 base.
        guides_direct = get_guides_by_hazard_features(
            db,
            accident_types=accident_types,
            hazardous_agents=hazardous_agents,
            work_contexts=work_contexts,
            limit=guides_per_hazard,
            industry_contexts=industry_contexts,
            context_work_contexts=global_wc_list,
        )
        if cache_guides:
            # 학습 캐시 1차(결정적, semantic-first) + facet 직접은 아래로 캡. recall/rerank LLM 미호출.
            guides = _stack_semantic_first(cache_guides, guides_direct, guides_per_hazard)
        elif semantic_on:
            # semantic recall(+rerank) 1차 + facet 직접(GF)은 semantic 아래로 캡(generic FALL noise 차단).
            # SR→CI noise 경로 미사용. guides_sem ∅이면 facet-direct로 fallback.
            guides_sem = _semantic_guide_candidates(
                db, rich_text, n=guides_per_hazard, industry_contexts=industry_contexts
            )
            guides = (
                _stack_semantic_first(guides_sem, guides_direct, guides_per_hazard)
                if guides_sem
                else guides_direct[:guides_per_hazard]
            )
        else:
            # legacy(무회귀): facet 직접 + SR→CI 변별력 가중 union.
            guides_ci = get_guides_from_srs(
                db,
                sr_ids=sr_for_guides,
                limit=guides_per_hazard,
                industry_contexts=industry_contexts,
            )
            guides = _merge_guide_paths(guides_direct, guides_ci, limit=guides_per_hazard)

        relations.append({
            "hazard_name": name,
            "risk_level": h.get("risk_level", ""),
            "location": h.get("location", ""),
            "description": h.get("description", ""),
            "preventive_measures": list(h.get("preventive_measures") or []),
            "mapped_codes": codes,
            "guides": guides,
            "matched_sr_count": len(sr_for_guides),
            "attach_method": attach_method,
            "semantic_sr_ids": semantic_sr_ids,
        })

    sr_ids_global = sorted(sr_id_set)
    logger.info(
        f"[HazardToGuide] {len(relations)} hazards / {len(sr_ids_global)} unique SR / "
        f"{sum(len(r['guides']) for r in relations)} guide rows"
    )
    return relations, sr_ids_global
