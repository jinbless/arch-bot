"""기인물 앵커 → 작업 전체 흐름 서비스.

제품 전제(2026-08-01 재정의): 산업재해는 ①위험한 기인물이 ②위험한 환경에서 ③위험한 행동을 할 때
**시간 흐름 속에서** 발생하는데, 사진은 그 흐름의 한 시점 스냅샷이다.
→ 스냅샷에서 기인물을 찾고, 그걸 앵커로 시간축 앞뒤로 해야 할 조치를 보여준다.

데이터: app/data/trackA/flow_slice_all.json (기인물 그룹 127종 중 우산 16종을 뺀 111종 × 골격 6칸).
  생성: data-team/01-parsing/rule-appendices/build_flow_slice_all.py
  ⚠ 재생성하면 이 파일도 **같이 동기화**해야 한다(runtime-artifacts → app/data/trackA).
  우산 = 총칙·통칙처럼 **자기만의 의무가 없는** 그룹. 내용이 전부 하위 기인물에 상속돼 있거나
  (양중기 > 총칙) 조문이 목적·정의뿐이다(편3 각 장 통칙). 앵커로 고르면 오히려 덜 보인다 —
  크레인 사진에 '양중기 > 총칙'을 잡으면 21건만 뜨고 크레인 전용 55건을 통째로 놓친다.

플래그(기본 off → 이 모듈은 아무 것도 하지 않고 응답에 None):
  OHS_ENABLE_WORK_FLOW (env CUE_FLOW 우선)

⚠ 노출 전 반드시 알아야 할 두 가지
  1. **앵커가 단일 실패점** — 관 단위 정확 일치 0.647(감독관 gold 51장). 3장 중 1장 이상이
     통째로 틀린다. 그래서 alternates(사용자 정정 후보)를 항상 함께 낸다.
  2. **라벨 정확도 미검수** — 각 항목이 그 칸에 맞는지는 사람 검수 전이다. 오탐은 사람이 걸러도
     잘못된 선후관계는 못 걸러낸다. `reviewed=False`로 내려보내 화면이 경고를 띄우게 한다.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models.analysis import FlowAnchor, FlowItem, FlowSlot, WorkFlow
from app.models.hazard import CorrectiveAction
from app.services import cue_article_service

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("OHS_TRACKA_DATA_DIR", "") or (Path(__file__).resolve().parents[1] / "data" / "trackA"))

# 단계에 번호를 매기지 않는다 — '8단계 중 4단계'는 시간 추론이라 미측정 오류원이 된다(사용자 합의).
SLOTS = [("PLAN", "계획·사전조사"), ("ASSIGN", "인적 배치·자격"), ("PRECHECK", "작업 시작 전 점검"),
         ("EXEC", "작업 중"), ("POST", "종료·이탈"), ("PERIODIC", "정기점검")]

# 라벨 사람 검수 완료 여부 — True (2026-08-07 전환).
# 근거: ① Sol 전수 재판정 885건 + Claude 판정 + 재감사(agree 57%·이견은 정책/개별 처리)
#       ② 사람 검수 CSV 174건 반영  ③ 서빙 전 게이트 감사(agree 40·disagree 32 → 10건 수용 수정)
# 전 항목 개별 검수는 아니다 — 우선순위 검수 + LLM 전수 재판정 체계로 검증됐다.
LABELS_REVIEWED = True


def _flag(env_name: str, setting_value: bool) -> bool:
    env = os.environ.get(env_name)
    if env is not None and env.strip() != "":
        return env.strip().lower() in ("1", "true", "on", "yes")
    return bool(setting_value)


def enabled() -> bool:
    return _flag("CUE_FLOW", getattr(settings, "OHS_ENABLE_WORK_FLOW", False))


# 성공한 결과만 캐시한다(cue_article_service와 같은 이유 — 최초 로드 실패가 프로세스 수명 내내 굳으면
# 조용히 비활성 상태로 남는다).
_CACHE: dict = {}


def _flows() -> Optional[dict]:
    if "v" in _CACHE:
        return _CACHE["v"]
    try:
        d = json.loads((DATA_DIR / "flow_slice_all.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[WorkFlow] 흐름 데이터 로드 실패: %s", exc)
        return None
    # ★ 우산 그룹(총칙·통칙 등)은 흐름으로 내보내지 않는다. 내용이 전부 하위 기인물에 상속돼 있어서
    #   '양중기 > 총칙'을 앵커로 잡으면 21건만 보이고 크레인 전용 55건을 통째로 놓친다.
    #   행 자체는 데이터에 남아 있다(상속의 원본이다) — 서빙에서만 가린다.
    umb = set(d.get("umbrella_group_keys") or [])
    rows = [r for r in d.get("rows", []) if r["no"] not in umb]
    # 카탈로그 원래 그룹키(RESOLVE가 내는 값) → 흐름 행. 좌표가 섞여 분리된 그룹은 한 키에 여럿 붙는다.
    by_src: dict[str, list] = {}
    for r in rows:
        by_src.setdefault(r.get("src_key") or r["no"], []).append(r)
    if umb:
        logger.info("[WorkFlow] 우산 그룹 %d종 제외 — 흐름 %d종", len(umb), len(rows))
    v = {"rows": rows, "by_src": by_src, "umbrella": umb}
    _CACHE["v"] = v
    return v


def _tier(source: str) -> str:
    return "권고" if "권고" in source else "법정"


def _anchor(row: dict) -> FlowAnchor:
    ins = row.get("inspection") or {}
    return FlowAnchor(group_key=row["no"], label=row.get("subject", ""), path=row.get("path", ""),
                      is_inspection_target=bool(ins.get("is_target")),
                      machines=list(ins.get("machines") or []),
                      inspection_scopes=[f"{k}: {v}" for k, v in (ins.get("scopes") or {}).items()],
                      periodic_source=ins.get("periodic_source", "없음"),
                      kind=row.get("anchor_kind", ""), kind_why=row.get("anchor_why", ""))


def _empty_reason(key: str, row: dict) -> str:
    """빈 칸을 그냥 비워두지 않는다 — '정보 없음'과 '해당 없음'은 다른 말이다."""
    if key == "PERIODIC":
        ins = row.get("inspection") or {}
        if not ins.get("is_target"):
            # 정기 칸의 근거는 세 갈래다(규칙 조문 · 안전검사 · 가이드). 안전검사만 언급하면
            # 나머지 둘을 확인했다는 사실이 전달되지 않는다.
            return ("산업안전보건법 제93조 안전검사 대상이 아니고, 산업안전보건기준규칙과 관련 KOSHA 가이드에도 "
                    "이 기인물의 정기점검 주기가 없습니다 — 자료가 없는 것이지 점검이 불필요하다는 뜻은 아닙니다")
        return "정기점검 항목이 확인되지 않았습니다"
    # 이 그룹의 조문이 목적·정의·적용범위뿐이면 '할 일'이 원래 없다. 자료 결손이 아니다.
    nd = row.get("no_duty_articles") or []
    if key == "EXEC" and nd and not (row.get("items") or {}).get("EXEC"):
        # 어디에 실제 의무가 있는지는 그룹마다 다르다(형제 관일 수도, 전혀 다른 곳일 수도).
        # 모르는 것을 아는 것처럼 쓰지 않는다.
        return (f"이 항목은 규칙의 정의·적용범위 조문({', '.join(nd[:3])}"
                f"{' 등' if len(nd) > 3 else ''})으로만 이루어져 있어 그 자체로는 할 일이 없습니다 "
                "— 구체적인 의무는 다른 기인물 항목에 있습니다")
    return "이 기인물에 대해 규칙·가이드에서 확인된 항목이 없습니다"


def _slots(row: dict) -> list[FlowSlot]:
    out = []
    for key, label in SLOTS:
        items = [FlowItem(text=x.get("text", ""), source=x.get("source", ""), ref=x.get("ref", ""),
                          tier=_tier(x.get("source", "")), uncertain="이름매칭" in x.get("source", ""),
                          evidence=x.get("evidence", ""))
                 for x in (row.get("items") or {}).get(key, [])]
        # 법정 → 권고 순. 근거가 강한 것을 위에 둔다.
        items.sort(key=lambda x: 0 if x.tier == "법정" else 1)
        out.append(FlowSlot(key=key, label=label, items=items,
                            empty_reason="" if items else _empty_reason(key, row)))
    return out


async def build(result: dict) -> Optional[WorkFlow]:
    """장면 → 앵커 → 흐름. 실패 시 None(기존 경로 무영향)."""
    fl = _flows()
    if fl is None:
        return None
    try:
        rv = await cue_article_service.resolve(cue_article_service.scene_text(result))
    except Exception as exc:  # noqa: BLE001 — RESOLVE 실패는 흐름 없음으로 떨어진다
        logger.warning("[WorkFlow] RESOLVE 실패 — 흐름 생략: %s", exc)
        return None

    # ★ RESOLVE가 주는 순서를 그대로 쓴다. '가장 두꺼운 흐름을 고른다' 같은 규칙은 그럴듯하지만
    #   측정된 바 없다. 주 기인물 선별은 별도 과제이고, 그 전까지는 사용자 정정(alternates)에 맡긴다.
    rows: list[dict] = []
    for gk in rv.get("group_keys", []):
        for r in fl["by_src"].get(gk, []):
            if r not in rows:
                rows.append(r)
    if not rows:
        # 우산 그룹만 지목된 경우를 따로 남긴다. 카탈로그에서 뺐으니 나와선 안 되는 일인데,
        # 나온다면 카탈로그와 흐름 데이터가 어긋난 것이다(동기화 누락). 조용히 넘기면 못 찾는다.
        picked_umb = [g for g in rv.get("group_keys", []) if g in fl.get("umbrella", ())]
        if picked_umb:
            logger.warning("[WorkFlow] RESOLVE가 우산 그룹만 지목했다 — 카탈로그 동기화 확인 필요: %s", picked_umb)
        else:
            logger.info("[WorkFlow] 앵커에 해당하는 흐름 없음: %s", rv.get("group_keys"))
        return None

    return WorkFlow(anchor=_anchor(rows[0]), alternates=[_anchor(r) for r in rows[1:]],
                    slots=_slots(rows[0]), reviewed=LABELS_REVIEWED)


def by_group_key(group_key: str, alternates: Optional[list[str]] = None) -> Optional[WorkFlow]:
    """사용자가 앵커를 정정했을 때 — LLM 없이 해당 그룹의 흐름만 다시 만든다.

    alternates에 원래 후보 키들을 넘기면 그대로 유지한다(되돌아갈 길을 남긴다).
    """
    fl = _flows()
    if fl is None:
        return None
    row = next((r for r in fl["rows"] if r["no"] == group_key), None)
    if row is None:
        return None
    alts = [_anchor(r) for k in (alternates or []) if k != group_key
            for r in fl["rows"] if r["no"] == k]
    return WorkFlow(anchor=_anchor(row), alternates=alts, slots=_slots(row), reviewed=LABELS_REVIEWED)


# legacy addresses_hazard → canonical accident 축 별칭 (2026-08-12 Track B).
# FIRE_EXPLOSION은 SR canonical 컬럼에도 vocab rollup에도 없어(rollup은 UNCLASSIFIED로 보냄)
# 이 별칭 없이는 화재 사진의 순위 신호가 **영구 공집합**이다 — prod 5222 실측(6건 전부 '계획 조치').
# 1:2 대응이라 rollup(1:1 dict)으로 표현 불가 → 국소 dict가 의미를 보존하는 유일한 자리다
# (canonical_vocab 수정은 태거·export·SHACL 전체 파급이라 기각). 근본 해소는 SR canonical
# 데이터 이관(백로그 Phase B-D) — 완료 후에도 벨트-앤-서스펜더로 유지한다.
# CONFINED_SPACE→OXYGEN_DEFICIENCY 등 같은 클래스 후보는 사진 시나리오 계측이 생기면 추가(선반영 금지).
SR_LEGACY_ACCIDENT_ALIASES: dict = {"FIRE_EXPLOSION": {"EXPLOSION", "FIRE_INJURY"}}


def statute_actions(flow, accident_codes: list[str], db,
                    matched_refs: Optional[set] = None) -> list[dict]:
    """앵커 흐름의 조문에서 즉시조치 후보를 만든다 — 가이드 CI 광역 매칭의 대체.

    사용자 판단(2026-08-09): "즉시조치를 확실하지만 간략한 곳에서" — 근거는 이렇다:
      · 가이드 CI 54,631건을 사고형태로 긁으면 개폐장치·연삭 지침까지 걸린다(실측 잡음)
      · 규칙 조문이 즉시조치를 이미 담고 있다(제172조 유도자 배치, 제179조 후진경보 등)
      · 앵커 흐름의 조문은 **검수 완료**(2등급) — 모집단을 여기로 좁히면 잡음이 못 들어온다

    구성: 내용 = 흐름의 작업전·작업중 항목(검수된 조문 인용) ·
          순위 = SR(sr_article_mapping)의 사고형태 코드 ∩ 사진 사고형태 (SR은 순위에만 쓴다 —
          내용까지 SR을 쓰면 미검증 추출(3등급)이 화면에 올라온다. 단 SR 제목이 행동형이라
          제목만 빌려 쓰되 조문 ref를 항상 병기해 역추적 가능하게 한다)
    matched_refs = AI 제안 대조(align)가 '같은 취지'로 판정한 항목 ref 집합 — **순위 신호로만** 쓴다.
          내용은 여전히 검수 조문 그대로이고 urgency에도 관여하지 않는다(아래 정렬 주석 참조).
    """
    if flow is None:
        return []
    import re as _re

    items = []
    seen = set()
    for slot in flow.slots:
        if slot.key not in ("PRECHECK", "EXEC"):
            continue
        for it in slot.items:
            ref = (it.ref or "").strip()
            if _re.fullmatch(r"제\d+조(의\d+)?", ref):
                if ref in seen:
                    continue
                seen.add(ref)
                items.append({"ref": it.ref, "title": it.text, "evidence": it.evidence,
                              "tier": it.tier, "slot": slot.key, "appendix": False})
            elif it.tier == "법정" and _re.match(r"제\d+조(의\d+)?제\d+항", ref):
                # 별표 항목 클래스(2026-08-12 Track B): 별표 3(작업 시작 전 점검) 류는 ref가
                # 표시용 문자열('제35조제2항 · <subject 절단>')이라 fullmatch 모집단에 못 들어온다 —
                # 화기 그룹의 유일한 '소화기구' 문구가 정확히 이 클래스였다.
                # · dedup 키 = (ref, text): 여러 항목이 같은 조문 ref를 공유한다(화기 5건 실측).
                # · SR join·제목 대체는 적용하지 않는다 — 제35조 SR(SR-MGMT-001)로 join하면
                #   화재와 무관한 가짜 hazard_hit(FALL)과 제목 덮어쓰기가 생긴다(실측 함정).
                #   노출은 matched 부스트 + PRECHECK 정렬로만.
                if (ref, it.text) in seen:
                    continue
                seen.add((ref, it.text))
                items.append({"ref": it.ref, "title": it.text, "evidence": it.evidence,
                              "tier": it.tier, "slot": slot.key, "appendix": True})
    if not items:
        return []

    # SR 순위 신호 (없어도 동작한다 — DB 조회 실패는 순위 없이 진행)
    # ★ 어휘 변환은 **canonical 기준**이어야 한다: 사진 코드는 _facet_canon으로 신 카탈로그
    #   canonical화한다(_facet_canon은 원래 *_canonical 컬럼 매칭용 — query_ci_for_facets 참조).
    #   ⚠ 2026-08-12 실측: 이전 코드는 SR의 구 enum 원컬럼(addresses_hazard=STRUCK_BY·CAUGHT_IN)**만**
    #   읽어 canonical화된 사진 코드(COLLISION)와 교집합이 이름 우연 일치(ELECTRIC_SHOCK 등) 빼고는
    #   공집합 — 순위 신호가 2026-08-09 통합 이후 사실상 죽어 있었다(urgency 전부 planned).
    #   SR은 **두 컬럼 합집합**으로 히트를 잡는다: accident_types_canonical은 626행 중 284행·7종
    #   (COLLISION·CAUGHT_IN·FALL…)만 채워져 있고, FIRE_EXPLOSION·ELECTRIC_SHOCK·CHEMICAL_EXPOSURE
    #   계열은 레거시 addresses_hazard에만 있다(그중 canonical과 이름이 같은 ELECTRIC_SHOCK·
    #   CHEMICAL_EXPOSURE는 레거시 컬럼으로 히트 가능 — canonical 단독으로 좁히면 그 클래스가 회귀).
    #   UNCLASSIFIED는 미지 코드의 변환 잔여라 히트에서 뺀다(양쪽에 있으면 가짜 히트가 된다).
    try:
        from app.services.hazard_rule_engine import _facet_canon
        accident_codes = sorted(
            c for c in _facet_canon(accident_codes, [], [])["accident_type"] if c != "UNCLASSIFIED")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[WorkFlow] 사고형태 어휘 변환 실패 — 원코드로 진행: %s", exc)
    sr_by_article: dict = {}
    try:
        from sqlalchemy import text as _sql
        rows = db.execute(_sql(
            "select m.article_code, sr.identifier, sr.title, sr.accident_types_canonical, "
            "sr.addresses_hazard, sr.requirement_type "
            "from safety_requirements sr join sr_article_mapping m on m.sr_id = sr.identifier "
            "where m.article_code = any(:codes)"),
            {"codes": [x["ref"] for x in items if not x["appendix"]]}).fetchall()
        for code, sr_id, title, hz_canon, hz_legacy, rtype in rows:
            legacy = set(hz_legacy or [])
            aliased = {a for c in legacy for a in SR_LEGACY_ACCIDENT_ALIASES.get(c, ())}
            hits = (set(hz_canon or []) | legacy | aliased) & set(accident_codes or [])
            cur = sr_by_article.get(code)
            if cur is None or (hits and not cur["hits"]):
                sr_by_article[code] = {"sr_id": sr_id, "title": title, "hits": hits, "rtype": rtype}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[WorkFlow] SR 순위 신호 조회 실패 — 순위 없이 진행: %s", exc)

    # matched = align이 "GPT가 이 분석에서 낸 제안과 같은 취지"로 판정한 항목. 축 수준 교집합
    # (hazard_hit)보다 강한 상황 특이 신호라 최우선으로 둔다. ★ urgency에는 절대 관여하지 않는다 —
    # immediate 게이트는 hazard_hit×actable 결정론 유지(LLM이 급박도를 정하면 정책 위반).
    # matched_refs 원소 = (ref, text) 쌍. ref 단독 비교는 안 된다 — 별표 항목들은 같은 조문 ref
    # 문자열을 공유해서(빌드 스크립트의 subject 절단) ref만 보면 5건이 한꺼번에 부스트된다(스모크 실측).
    # 조문 항목은 ref가 유일키라 ref만 비교(제목은 이후 SR 행동형으로 대체되므로 text 비교 불가).
    m_pairs = set()
    for m in (matched_refs or ()):
        r, t = (m if isinstance(m, tuple) else (m, ""))
        r = (r or "").strip()
        if r:
            m_pairs.add((r, (t or "").strip()))
    m_ref_only = {r for r, _ in m_pairs}

    # '지금 당장'은 행위형이다. 헤드가드 장착(EQUIPMENT_STANDARD)은 법정 의무지만 구매·설치가
    # 필요한 것이라 즉시조치로 앞세우면 안내가 어긋난다 — 출입통제·유도자(PROCEDURAL)가 먼저다.
    ACT_NOW = {"PROCEDURAL", "EMERGENCY_RESPONSE", "PPE_REQUIREMENT"}
    for x in items:
        ref_s = (x["ref"] or "").strip()
        x["matched"] = ((ref_s, (x["title"] or "").strip()) in m_pairs
                        if x["appendix"] else ref_s in m_ref_only)
        if x["appendix"]:
            # 별표 항목은 SR 신호 없음 — hazard_hit/actable 모두 False 고정.
            # actable=True를 주면 무히트 장면에서 별표 점검 5건이 행위형 금지 조문(제239조류)을
            # 통째로 밀어내는 과잉이 생긴다(설계 검토에서 기각) — 노출은 matched 부스트로만.
            x["hazard_hit"] = False
            x["actable"] = False
            x["sr_id"] = None
            continue
        sr = sr_by_article.get(x["ref"])
        x["hazard_hit"] = bool(sr and sr["hits"])
        x["actable"] = bool(sr and sr.get("rtype") in ACT_NOW)
        x["sr_id"] = sr["sr_id"] if sr else None
        # SR 제목이 행동형('접촉 위험 장소 출입 제한')이라 조문 제목('접촉의 방지')보다 낫다
        if sr and sr["title"]:
            x["title"] = sr["title"]
    items.sort(key=lambda x: (not x["matched"], not x["hazard_hit"], not x["actable"],
                              x["tier"] != "법정", x["slot"] != "PRECHECK"))
    return items[:6]


def statute_actions_corrective(flow, accident_codes: list[str], db,
                               matched_refs: Optional[set] = None) -> list[CorrectiveAction]:
    """statute_actions 행 → 화면 계약(CorrectiveAction) 매핑.

    분석 응답(immediate_actions)과 앵커 정정 API(GET /flow)가 **같은 매핑**을 써야 한다 —
    urgency/confidence 규칙이 두 곳으로 갈라지면 같은 조문이 화면마다 다른 급박도로 보인다
    (2026-08-12 정정 API에 '지금 당장' 재선별을 붙이면서 여기로 통합).
    matched_refs(원소 = (ref, text) 쌍)는 분석 경로만 전달한다 — 정정 API에서는 원 분석의 align이
    원 앵커의 흐름 후보 기준이라 재사용하지 않는다(정정 시 화면의 AI 대조 자체가 숨는 것과 대칭).
    """
    rows = statute_actions(flow, accident_codes, db, matched_refs=matched_refs)
    actions = []
    for r in rows:
        desc = f"{r['ref']} 원문: “{r['evidence']}”" if r.get("evidence") else r["ref"]
        actions.append(
            CorrectiveAction(
                action_id=r["ref"],
                title=r["title"],
                description=desc,
                source_type="rule:Article",
                source_id=(r.get("sr_id") or r["ref"]),
                # 설비 장착 의무(헤드가드 등)는 법정이라도 '지금 당장'이 아니라 planned다
                urgency="immediate" if (r.get("hazard_hit") and r.get("actable")) else "planned",
                confidence=1.0 if r["tier"] == "법정" else 0.7,
                matched=bool(r.get("matched")),
            )
        )
    return actions


# ── AI 자유 제안 ↔ 흐름 조문 정렬 ──────────────────────────────────────
# 사용자 정책(2026-08-09): GPT가 사진에서 낸 조치 제안이 흐름 조문에 대응하면 그 조문을 보여주고,
# 대응이 없으면 폐기가 아니라 '구체 조문 불비 후보'로 적립한다(ohs_action_statute_gaps).
# ★ 이건 법 적용 판단이 아니다 — 이미 검수로 확정된 의무 목록(닫힌 소집합)에 대한 텍스트 정렬이고
#   기본값은 무매칭(추측 금지)이다. 폐기했던 광역 매칭(CI 54,631 열린 집합)과는 다른 문제.
# ★ 후보를 ref 문자열이 아니라 **번호**로 답하게 한다 — RESOLVE에서 LLM이 카탈로그 줄 전체를
#   복사하는 실측 사례(129장 중 5장)가 있었다. 번호면 그 실패 클래스가 원천 차단된다.
ALIGN_SYS = (
    "너는 산업안전보건 규정 검토자다. AI가 현장 사진을 보고 낸 조치 제안 각각에 대해, "
    "'확정 의무 목록'(검수 체계를 거쳐 확정된 이 작업의 조문 항목) 중 실질적으로 같은 취지의 "
    "항목이 있으면 그 후보 번호 c를, 없으면 -1을 답하라. 비슷해 보인다고 억지로 맞추지 말라 — "
    "확실하지 않으면 -1이 정답이다. 각 판단에 한 줄 이유를 붙여라.")
ALIGN_SCHEMA = {"name": "align", "strict": True, "schema": {
    "type": "object", "additionalProperties": False,
    "properties": {"alignments": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"a": {"type": "integer"}, "c": {"type": "integer"},
                       "reason": {"type": "string"}},
        "required": ["a", "c", "reason"]}}},
    "required": ["alignments"]}}


async def align_llm_actions(flow, llm_actions: list[str]) -> list[dict]:
    """GPT 자유 제안 각각을 흐름 항목(닫힌 집합)에 정렬한다.

    status 3값을 구별한다 — 'unmatched'(모델이 '대응 없음' 판정 = 불비 후보로 적립 대상)와
    'unaligned'(정렬 자체가 실패/무효 = 적립하면 원장이 오염되므로 표시만)는 다른 상태다.
    실패해도 제안을 잃지 않는다(전부 unaligned로 반환).
    """
    # 중복 제거(순서 보존) — GPT가 같은 제안을 두 번 내면 원장에 같은 항목이 행 2개로 쪼개져
    # occurrence_count 신호가 분산된다(autoflush=False라 같은 요청 안 SELECT가 pending INSERT를 못 본다).
    acts = list(dict.fromkeys(t.strip() for t in (llm_actions or []) if t and t.strip()))
    if len(acts) > 8:
        logger.info("[WorkFlow] AI 제안 %d건 중 8건만 대조(캡)", len(acts))
    acts = acts[:8]
    out = [{"text": t, "status": "unaligned", "matched_ref": "", "matched_title": "",
            "slot_key": "", "slot_label": "", "reason": ""} for t in acts]
    if flow is None or not acts:
        return out
    cands, seen = [], set()
    for slot in flow.slots:
        for it in slot.items:
            # ★ 후보는 **법정만** — 불비 판단의 기준집합은 법정 조문이다. 권고(가이드)를 넣으면
            #   '권고에만 있고 조문에 없는' 제안(핵심 불비 후보)이 matched로 빠져나간다(실측:
            #   적치물 제거 제안이 가이드 13단계에 매칭돼 원장에 안 남았다).
            if not it.ref or it.tier != "법정" or (it.ref, it.text) in seen:
                continue
            seen.add((it.ref, it.text))
            cands.append({"ref": it.ref, "title": it.text, "slot_key": slot.key,
                          "slot_label": slot.label, "evidence": (it.evidence or "")[:60]})
    if len(cands) > 60:
        logger.info("[WorkFlow] 흐름 법정 후보 %d건 중 60건만 대조에 사용(캡)", len(cands))
    cands = cands[:60]
    if not cands:
        return out
    a_lines = "\n".join(f"{i}. {t}" for i, t in enumerate(acts))
    c_lines = "\n".join(
        f"{i}. [{c['ref']}] ({c['slot_label']}) {c['title']}"
        + (f" — “{c['evidence']}”" if c["evidence"] else "")
        for i, c in enumerate(cands))
    try:
        model = os.environ.get("FLOW_ALIGN_MODEL", "gpt-5.4")
        # cue_article_service._chat 재사용 — RESOLVE와 같은 클라이언트·json_schema 규율
        rv = await cue_article_service._chat(  # noqa: SLF001
            model, ALIGN_SYS,
            f"[AI 조치 제안]\n{a_lines}\n\n[확정 의무 목록]\n{c_lines}\n\n"
            "각 제안 번호 a에 대해 후보 번호 c(대응 없으면 -1)와 이유.", ALIGN_SCHEMA)
    except Exception as exc:  # noqa: BLE001 — 정렬 실패가 분석 응답을 막지 않는다
        logger.warning("[WorkFlow] AI 제안 정렬 실패 — 대조 전 상태로 표시: %s", exc)
        return out
    for al in rv.get("alignments", []):
        a, c = al.get("a"), al.get("c")
        if not isinstance(a, int) or not 0 <= a < len(out):
            continue
        reason = str(al.get("reason") or "")[:200]
        if isinstance(c, int) and 0 <= c < len(cands):
            cd = cands[c]
            out[a].update(status="matched", matched_ref=cd["ref"], matched_title=cd["title"],
                          slot_key=cd["slot_key"], slot_label=cd["slot_label"], reason=reason)
        elif c == -1:
            out[a].update(status="unmatched", reason=reason)
        else:
            # 목록 밖 번호 지목 = 판정 무효. unmatched로 두면 불비 원장에 잘못 적립된다.
            out[a].update(status="unaligned", reason="모델이 목록 밖 번호를 지목 — 무효 처리")
    return out


_ALWAYS: dict = {}


def always_applicable() -> dict:
    """사진과 무관하게 늘 지켜야 하는 것 — '기본 안전수칙' 카테고리.

    ★ 흐름 6칸은 사진에서 잡은 앵커에 매달린다. 그런데 작업장 시설·통로 구조·보호구 지급처럼
      **시간축이 없고 현장이 늘 갖춰야 할 상태**인 의무가 있다. 앵커에 안 걸리면
      사업주가 볼 방법이 아예 없어서 따로 모은다.
      생성: data-team/01-parsing/rule-appendices/build_always_applicable.py
    """
    if "v" in _ALWAYS:
        return _ALWAYS["v"]
    try:
        d = json.loads((DATA_DIR / "always_applicable.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — 없으면 조용히 빈 목록(기존 경로 무영향)
        logger.warning("[WorkFlow] 상시 준수 데이터 로드 실패: %s", exc)
        return {"topics": [], "n_total": 0, "reviewed": False}
    v = {"topics": d.get("topics", []), "n_total": d.get("n_total", 0),
         "reviewed": bool(d.get("reviewed_by_human"))}
    _ALWAYS["v"] = v
    return v


def list_groups() -> list[dict]:
    """앵커 선택기용 전체 목록.

    ★ 대안 후보만으로는 정정이 안 된다 — 앵커가 **완전히** 빗나가는 사진이 26.7%다(감독관 gold 45장).
      그런 사진은 RESOLVE가 제시한 1~4개 안에 정답이 아예 없다. 전체에서 고를 수 있어야 한다.
    """
    fl = _flows()
    if fl is None:
        return []
    out = []
    for r in fl["rows"]:
        ins = r.get("inspection") or {}
        out.append({"group_key": r["no"], "label": r.get("subject", ""), "path": r.get("path", ""),
                    "is_inspection_target": bool(ins.get("is_target")),
                    "kind": r.get("anchor_kind", ""),
                    "n_items": sum(len(v) for v in (r.get("items") or {}).values())})
    # ★ 사진으로 지목할 수 없는 칸(통칙·보호구·관리)을 목록 뒤로 민다. 지우지는 않는다 —
    #   사용자가 굳이 그 조문 묶음을 보고 싶을 수 있고, 지우면 아예 닿을 수 없게 된다.
    out.sort(key=lambda g: (g["kind"] == "부적격", 0))
    return out
