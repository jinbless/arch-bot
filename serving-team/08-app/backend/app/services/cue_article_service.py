"""Track A cue-pool union 조문 후보 서비스 (research v2 검증 구성의 서빙 이식).

검증 근거: docs/status/evaluation-baseline.md 최상단 "RANK A/B v2" — 실제 감독관 gold 129장에서
union(기인물 앵커 ∪ 관찰단서 cue-pool)이 P@1 +4.6pt·Hit@3 +7.2pt·Hit@5 +9.1pt(전부 CI 0 배제).
로직 이식원: backend/scripts/rank_ab_gold.py(후보구성·정렬·필터) + scripts/gimulmul_match.py(RESOLVE/RANK 프롬프트).
**이식 시 연구 공식을 바꾸지 말 것** — scene/cue 텍스트 조립·observable 필터·조번호 단일 정렬·
출처 태그 미렌더(제시 중립화)·후보-밖 코드 필터가 전부 측정된 조건이다.

플래그(기본 off → 이 모듈은 아무 것도 하지 않고 응답에 빈 배열만):
  OHS_ENABLE_CUE_ARTICLES (env CUE_ARTICLES 우선) — 후보생성 + RESOLVE(LLM 1회)
  OHS_ENABLE_ARTICLE_RANK (env CUE_ARTICLE_RANK 우선) — RANK(LLM 1회 추가, applies yes/maybe만 노출)
안전장치:
  - **후보-밖 코드 필터**(채택 차단조건 — 랭커 환각 A31·B28/516랭킹 실측): RANK 출력 중 후보에 없는
    코드는 버리고 카운트 로깅.
  - RESOLVE/RANK 실패 시 graceful degrade(결정론 cue+횡단 후보만 / 미정렬) — 기존 경로 무영향.
  - 오탐 스모크(음성 9장, neg_fp_results.json): 랭커에 기권 경로 없음(abstain 0%) →
    본 필드는 "후보 제안" 표기이지 위반 확정이 아니다(표시 정책은 프론트 몫).
데이터: app/data/trackA/ (이미지에 포함, ~1.5MB). env OHS_TRACKA_DATA_DIR로 override 가능.
"""
from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import PgArticle
from app.models.analysis import ArticleCandidate

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("OHS_TRACKA_DATA_DIR", "") or (Path(__file__).resolve().parents[1] / "data" / "trackA"))
OBS_OK = ("yes", "partial")

# 횡단 일반의무 — scripts/gimulmul_match.py:45-47 이식(측정 구성의 일부, 변경 금지)
CROSS = ["제3조", "제5조", "제13조", "제14조", "제20조", "제22조", "제23조",
         "제32조", "제42조", "제43조", "제44조", "제45조", "제46조",
         "제88조", "제92조", "제93조"]

# RESOLVE — scripts/gimulmul_match.py:49-57 이식
RESOLVE_SYS = (
    "너는 산업안전보건 현장점검관이다. 작업장 장면 서술과 '기인물 그룹 카탈로그'(산업안전보건규칙의 "
    "절/관 = 기계·설비·물질·작업 분류)를 받는다. 이 장면에서 사고를 일으킬 수 있는 주요 기인물"
    "(기계/설비/물질/구조물/작업)을 식별하고, 카탈로그에서 해당하는 group_key를 1~4개 고르라. "
    "정확히 카탈로그에 있는 group_key 문자열만. 추측 금지.")
RESOLVE_SCHEMA = {"name": "resolve", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"gimulmul": {"type": "array", "items": {"type": "string"}},
                   "group_keys": {"type": "array", "items": {"type": "string"}}},
    "required": ["gimulmul", "group_keys"]}}

# RANK — scripts/gimulmul_match.py:59-76 이식 후 **태그중립화**(측정 조건: rank_ab_gold.py RANK_SYS_BLIND)
RANK_SYS = (
    "너는 대한민국 산업안전보건 현장점검관이다. 작업장 장면과 후보 산업안전보건규칙 조(제목·위반장면·전문발췌)를 받는다. "
    "목표: 이 사진을 보면 점검관이 '가장 먼저 지적할' 위반 조문을 1순위로, 구체성·가시성 순으로 정렬한다. "
    "'적용 가능한 모든 의무'를 나열하는 게 아니라, 사진이 '구체적으로 보여주는' 위반을 위로 올린다. "
    "순위 원칙: "
    "(1) 특정 > 일반: 사진에 직접 보이는 구체적 결여(개구부 방호 없음, 안전난간 없음, 보호구 미착용, "
    "방호장치·덮개 없음, 식별된 설비 전용 의무 미충족)를 최상위. 구체 위험조 우선. "
    "(2) 포괄 의무 강등: 제3조(안전조치 일반)·제5조·제23조 등 '거의 모든 작업장에 성립하는 포괄/우산 의무'는 "
    "이 사진의 핵심 위반이 아니면 하위로 내리거나 maybe. 구체 조가 있으면 절대 포괄 조를 그 위에 두지 않는다. "
    "(3) 사람이 안 보이면 설비/구조의 결여상태(방호장치·덮개·난간 없음 등)로 판단. "
    "(4) 식별된 기인물(설비)에 당연히 요구되나 사진에서 충족 확인 안 되는 조는 maybe로 포함하되, 명백 무관은 no "
    "(예: 지게차면 좌석안전띠·헤드가드·백레스트). "
    "applies yes(사진에 구체적으로 보임)/maybe(정황·미확인)/no(무관). "
    "적용 조를 '점검관이 지적할 순서'(구체성·가시성 순, 범용 적용성 순 아님)로 정렬해 반환.")
RANK_SCHEMA = {"name": "rank", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"ranked": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"article_code": {"type": "string"}, "applies": {"type": "string", "enum": ["yes", "maybe", "no"]}},
        "required": ["article_code", "applies"]}}}, "required": ["ranked"]}}


# ── 플래그 (idiom: hazard_to_guide_service.py:33-45) ──
def _flag(env_name: str, setting_value: bool) -> bool:
    env = os.environ.get(env_name)
    if env is not None and env.strip() != "":
        return env.strip().lower() in ("1", "true", "on", "yes")
    return bool(setting_value)


def enabled() -> bool:
    return _flag("CUE_ARTICLES", getattr(settings, "OHS_ENABLE_CUE_ARTICLES", False))


def rank_enabled() -> bool:
    return _flag("CUE_ARTICLE_RANK", getattr(settings, "OHS_ENABLE_ARTICLE_RANK", False))


# ── 데이터 로드(1회) ──
@lru_cache(maxsize=1)
def _knowledge() -> Optional[dict]:
    try:
        pool = json.loads((DATA_DIR / "cue-pool.json").read_text(encoding="utf-8"))["cues"]
        sig = {}
        for ln in (DATA_DIR / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines():
            if ln.strip():
                o = json.loads(ln)
                sig[o["article_code"]] = o
        idx = json.loads((DATA_DIR / "gimulmul_index.json").read_text(encoding="utf-8"))
        alias = json.loads((DATA_DIR / "gimulmul_alias.json").read_text(encoding="utf-8"))
        curated = json.loads((DATA_DIR / "case_rule_mapping.json").read_text(encoding="utf-8")).get("gimulmul_articles", {})
    except Exception as exc:  # noqa: BLE001 — 파일 없으면 조용히 비활성(graceful degrade)
        logger.warning("[CueArticles] 지식 파일 로드 실패(%s) — 기능 비활성", exc)
        return None
    cue_terms = []
    for c in pool:
        ts = set()
        for a in (c.get("aliases") or []) + (c.get("vision_keywords") or []):
            a = a.strip()
            if len(a) >= 2:
                ts.add(a)
        can = re.split(r"[(/·]", c["canonical"])[0].strip()
        if len(can) >= 2:
            ts.add(can)
        cue_terms.append((c, ts))
    catalog = []
    for gk, g in idx["groups"].items():
        nobs = sum(1 for a in g["articles"] if a["observable"] in OBS_OK)
        if nobs >= 1 and gk not in idx["cross_cutting"]:
            catalog.append(f"{gk} ::기인물={g['gimulmul']} ({nobs}조)")
    return {"cue_terms": cue_terms, "sig": sig, "idx": idx, "alias": alias, "curated": curated,
            "cross_set": sorted(set(CROSS) & set(idx["observable_codes"])),
            "catalog_text": "\n".join(sorted(catalog))}


# ── 장면 텍스트 (연구 공식 — rank_ab_gold.py scene_text/cue_text. 변경 금지) ──
def _scene_text(result: dict) -> str:
    obs = " ".join(o.get("text", "") for o in result.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in result.get("visual_cues") or [])
    haz = "; ".join(h.get("name", "") for h in result.get("hazards") or [])
    return f"{obs} 시각단서: {cues} 위험: {haz}".strip()


def _cue_text(result: dict) -> str:
    parts = []
    for o in result.get("visual_observations") or []:
        parts.append(o.get("text", ""))
    for o in result.get("visual_cues") or []:
        parts.append(o.get("text", ""))
    for h in result.get("hazards") or []:
        parts += [h.get("name", ""), h.get("description", ""), h.get("location", "")]
    return " | ".join(parts)


def _code_num(c: str):
    m = re.match(r"제(\d+)조(?:의(\d+))?", c)
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (99999, 0)


def cue_candidates(result: dict) -> tuple[set, set, dict]:
    """관찰단서 발화 → (entry, flow, code→매칭 cue명). observable 필터 포함."""
    kn = _knowledge()
    if kn is None:
        return set(), set(), {}
    txt = _cue_text(result)
    entry, flow, why = set(), set(), {}
    for c, ts in kn["cue_terms"]:
        if any(t in txt for t in ts):
            for code in c.get("articles") or []:
                entry.add(code)
                why.setdefault(code, c["canonical"])
            for code in c.get("flow_articles") or []:
                flow.add(code)
                why.setdefault(code, c["canonical"])
    sig = kn["sig"]
    entry = {a for a in entry if sig.get(a, {}).get("observable") in OBS_OK}
    flow = {a for a in flow if sig.get(a, {}).get("observable") in OBS_OK} - entry
    return entry, flow, why


def _baseline_candidates(rv: dict) -> dict:
    """기인물 앵커(RESOLVE 결과 → 큐레이션∪alias∪그룹∪횡단). rank_ab_gold.baseline_candidates 이식."""
    kn = _knowledge()
    kind: dict[str, str] = {}
    sig = kn["sig"]

    def add(code: str, tag: str) -> None:
        if code in kind or sig.get(code, {}).get("observable") not in OBS_OK:
            return
        kind[code] = tag

    gims = rv.get("gimulmul", [])
    curated = kn["curated"]
    for gim in gims:
        base = gim.split("(")[0].strip()
        for k, v in curated.items():
            if k.split("(")[0].strip() == base or base in k or k in base:
                for a in v["articles"]:
                    add(a["code"], "큐레이션")
                break
    groups = kn["idx"]["groups"]
    for gim in gims:
        for gk in kn["alias"].get(gim, {}).get("group_keys", []):
            for a in groups.get(gk, {}).get("articles", []):
                add(a["code"], "기인물")
    for gk in [k for k in rv.get("group_keys", []) if k in groups]:
        for a in groups[gk]["articles"]:
            add(a["code"], "기인물")
    for c in kn["cross_set"]:
        add(c, "횡단")
    return kind


# ── LLM ──
_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import AsyncOpenAI

        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", ""))
    return _client


async def _chat(model: str, sysp: str, user: str, schema: dict) -> dict:
    r = await _get_client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": sysp}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": schema},
    )
    return json.loads(r.choices[0].message.content)


async def _resolve(scene: str) -> dict:
    kn = _knowledge()
    model = os.environ.get("CUE_RESOLVE_MODEL", "gpt-5.4")
    return await _chat(model, RESOLVE_SYS,
                       f"[장면]\n{scene}\n\n[기인물 그룹 카탈로그]\n{kn['catalog_text']}\n\n주요 기인물의 group_key 선택.",
                       RESOLVE_SCHEMA)


def _full_texts(db: Session, codes: list[str]) -> dict:
    rows = (db.query(PgArticle.article_code, PgArticle.full_text)
            .filter(PgArticle.law_type == "RULE", PgArticle.article_code.in_(codes)).all())
    return {r[0]: (r[1] or "") for r in rows}


def filter_to_candidates(ranked: list[dict], valid: set) -> tuple[list[dict], int]:
    """후보-밖 코드 필터(채택 차단조건). 환각 코드는 버리고 카운트."""
    keep, halluc = [], 0
    for x in ranked:
        if x.get("applies") not in ("yes", "maybe"):
            continue
        if x.get("article_code") in valid:
            keep.append(x)
        else:
            halluc += 1
    return keep, halluc


async def recommend(db: Session, result: dict) -> list[ArticleCandidate]:
    """union 후보(측정된 B 구성) 생성 + 선택적 RANK. 실패 시 graceful degrade."""
    kn = _knowledge()
    if kn is None:
        return []
    scene = _scene_text(result)
    entry, flow, why = cue_candidates(result)

    kind: dict[str, str] = {}
    try:
        rv = await _resolve(scene)
        kind = _baseline_candidates(rv)
    except Exception as exc:  # noqa: BLE001 — RESOLVE 실패 → 결정론 부분(cue+횡단)만
        logger.warning("[CueArticles] RESOLVE 실패(%s) — cue+횡단 후보만 사용", exc)
        sig = kn["sig"]
        for c in kn["cross_set"]:
            if sig.get(c, {}).get("observable") in OBS_OK:
                kind[c] = "횡단"
    for c in entry:
        kind.setdefault(c, "단서")
    for c in flow:
        kind.setdefault(c, "흐름")
    codes = sorted(kind.keys(), key=_code_num)  # 조번호 단일 정렬(제시 중립화 — 측정 조건)
    if not codes:
        return []

    sig = kn["sig"]
    title_of = {c: sig.get(c, {}).get("title", "") for c in codes}

    if not rank_enabled():
        return [ArticleCandidate(article_code=c, title=title_of[c], applies="unranked", rank=0,
                                 source=kind[c], evidence=why.get(c, "")) for c in codes]

    try:
        full = _full_texts(db, codes)
        lines = [f"[장면]\n{scene}", "", "[후보 조]"]
        for c in codes:  # 출처 태그 미렌더(측정 조건 — rank_ab_gold rank_prompt)
            s = sig.get(c, {})
            lines.append(f"- {c} {s.get('title','')} | {(s.get('violation_scene','') or '')[:90]}\n"
                         f"  전문: {full.get(c, '')[:160]}")
        model = os.environ.get("CUE_RANK_MODEL", "gpt-5.4")
        rk = await _chat(model, RANK_SYS, "\n".join(lines) + "\n\n적용 조를 확신순 정렬.", RANK_SCHEMA)
        keep, halluc = filter_to_candidates(rk.get("ranked", []), set(codes))
        if halluc:
            logger.info("[CueArticles] 후보-밖 코드 %d건 필터됨", halluc)
        return [ArticleCandidate(article_code=x["article_code"], title=title_of.get(x["article_code"], ""),
                                 applies=x["applies"], rank=i + 1,
                                 source=kind.get(x["article_code"], ""),
                                 evidence=why.get(x["article_code"], ""))
                for i, x in enumerate(keep)]
    except Exception as exc:  # noqa: BLE001 — RANK 실패 → 미정렬 후보 반환
        logger.warning("[CueArticles] RANK 실패(%s) — 미정렬 후보 반환", exc)
        return [ArticleCandidate(article_code=c, title=title_of[c], applies="unranked", rank=0,
                                 source=kind[c], evidence=why.get(c, "")) for c in codes]
