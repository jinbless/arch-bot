"""앵커 정정용 흐름 조회 API.

기인물 인식은 관 단위 정확 일치 0.711이고 **완전 오인식이 26.7%**다(감독관 gold 45장).
완전 오인식이란 RESOLVE가 제시한 1~4개 후보 안에 정답이 아예 없다는 뜻이다.
→ 대안 칩만으로는 4장 중 1장을 못 고친다. 전체 목록에서 고를 수 있어야 한다.

두 엔드포인트 모두 LLM을 부르지 않는다(로드된 흐름 데이터 조회만). 플래그 off면 비활성.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.analysis import WorkFlowWithActions
from app.services import flow_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _guard() -> None:
    if not flow_service.enabled():
        raise HTTPException(status_code=404, detail="작업 흐름 기능이 활성화되어 있지 않습니다.")


@router.get("/groups")
async def flow_groups():
    """앵커 선택기용 기인물 그룹 전체 목록(LLM 호출 없음)."""
    _guard()
    groups = flow_service.list_groups()
    return {"groups": groups, "count": len(groups)}


@router.get("/always")
async def flow_always():
    """사진과 무관하게 늘 지켜야 하는 것(LLM 호출 없음).

    흐름은 앵커에 매달리므로, 앵커가 될 수 없는 의무(작업장 시설·통로 구조·보호구 지급 등)는
    여기서만 볼 수 있다. 앵커 정확도와 무관하게 항상 정확한 유일한 화면이다.
    """
    _guard()
    return flow_service.always_applicable()


@router.get("", response_model=WorkFlowWithActions)
async def flow_by_group(
    group_key: str = Query(..., description="기인물 그룹 키"),
    alternate: Optional[list[str]] = Query(None, description="유지할 대안 후보 키(되돌아갈 길)"),
    from_group_key: Optional[str] = Query(None, description="정정 전 앵커 — 정정 빈도 관측용"),
    accident_code: Optional[list[str]] = Query(
        None, description="'지금 당장' 순위용 사고형태 코드 — 원래 분석의 신호를 그대로 잇는다"),
    db: Session = Depends(get_db),
):
    """지정한 기인물의 흐름 + '지금 당장' 재선별(LLM 호출 없음).

    기인물을 바꾸면 즉시조치 선별의 모집단(그 기인물의 검수 조문)도 바뀌므로 여기서 다시
    계산한다(2026-08-12). 분석 시점과 같은 규칙(flow_service.statute_actions) · 같은 사고형태
    신호(accident_code로 승계). 재료가 전부 로컬 파일 + PG 조회라 GPT 없이 즉시 응답한다.
    """
    _guard()
    wf = flow_service.by_group_key(group_key, alternate)
    if wf is None:
        raise HTTPException(status_code=404, detail="해당 기인물의 흐름이 없습니다.")
    if from_group_key and from_group_key != group_key:
        # 사용자가 앵커를 바꿨다는 사실 자체가 앵커 정확도의 현장 신호다.
        # 개인정보 없이 그룹키만 남긴다 — 나중에 오인식률을 실사용에서 재는 재료가 된다.
        logger.info("[WorkFlow] 앵커 정정: %s → %s", from_group_key, group_key)
    try:
        actions = flow_service.statute_actions_corrective(wf, list(accident_code or []), db)
    except Exception as exc:  # noqa: BLE001 — 선별 실패가 흐름 정정 자체를 막으면 안 된다
        logger.warning("[WorkFlow] '지금 당장' 재선별 실패 — 흐름만 반환: %s", exc)
        actions = []
    return WorkFlowWithActions(**wf.model_dump(), statute_actions=actions)
