"""기인물 앵커 → 작업 전체 흐름 서비스.

제품 전제(2026-08-01 재정의): 산업재해는 ①위험한 기인물이 ②위험한 환경에서 ③위험한 행동을 할 때
**시간 흐름 속에서** 발생하는데, 사진은 그 흐름의 한 시점 스냅샷이다.
→ 스냅샷에서 기인물을 찾고, 그걸 앵커로 시간축 앞뒤로 해야 할 조치를 보여준다.

데이터: app/data/trackA/flow_slice_all.json (기인물 그룹 127종 × 골격 6칸).
  생성: data-team/01-parsing/rule-appendices/build_flow_slice_all.py
  ⚠ 재생성하면 이 파일도 **같이 동기화**해야 한다(runtime-artifacts → app/data/trackA).

플래그(기본 off → 이 모듈은 아무 것도 하지 않고 응답에 None):
  OHS_ENABLE_WORK_FLOW (env CUE_FLOW 우선)

⚠ 노출 전 반드시 알아야 할 두 가지
  1. **앵커가 단일 실패점** — 관 단위 정확 일치 0.711(감독관 gold 45장). 4장 중 1장 이상이
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
from app.services import cue_article_service

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("OHS_TRACKA_DATA_DIR", "") or (Path(__file__).resolve().parents[1] / "data" / "trackA"))

# 단계에 번호를 매기지 않는다 — '8단계 중 4단계'는 시간 추론이라 미측정 오류원이 된다(사용자 합의).
SLOTS = [("PLAN", "계획·사전조사"), ("ASSIGN", "인적 배치·자격"), ("PRECHECK", "작업 시작 전 점검"),
         ("EXEC", "작업 중"), ("POST", "종료·이탈"), ("PERIODIC", "정기점검")]

# 라벨 사람 검수 완료 여부. 검수 CSV를 반영하면 True로 바꾼다(화면 경고 문구가 사라진다).
LABELS_REVIEWED = False


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
    # 카탈로그 원래 그룹키(RESOLVE가 내는 값) → 흐름 행. 좌표가 섞여 분리된 그룹은 한 키에 여럿 붙는다.
    by_src: dict[str, list] = {}
    for r in d.get("rows", []):
        by_src.setdefault(r.get("src_key") or r["no"], []).append(r)
    v = {"rows": d.get("rows", []), "by_src": by_src}
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
                      periodic_source=ins.get("periodic_source", "없음"))


def _empty_reason(key: str, row: dict) -> str:
    """빈 칸을 그냥 비워두지 않는다 — '정보 없음'과 '해당 없음'은 다른 말이다."""
    if key == "PERIODIC":
        ins = row.get("inspection") or {}
        if not ins.get("is_target"):
            return ("산업안전보건법 제93조 안전검사 대상이 아니며, 관련 KOSHA 가이드에도 정기점검 절차가 없습니다 "
                    "— 자료가 없는 것이지 점검이 불필요하다는 뜻은 아닙니다")
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
                    "n_items": sum(len(v) for v in (r.get("items") or {}).values())})
    return out
