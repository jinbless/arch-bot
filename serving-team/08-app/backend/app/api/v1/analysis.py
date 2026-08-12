from fastapi import APIRouter, UploadFile, File, Form, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.rate_limit import limiter, RATE_LIMIT_IMAGE, RATE_LIMIT_TEXT
from app.db.database import get_db
from app.db import crud
from app.models.analysis import (
    TextAnalysisRequest,
    AnalysisResponse,
    AnalysisHistoryItem,
    AnalysisHistoryResponse
)
from app.services import cue_article_service, flow_service
from app.services.analysis_service import analysis_service
from app.utils.file_handler import file_handler
from app.utils.exceptions import AnalysisNotFoundError

router = APIRouter()


@router.post("/image", response_model=AnalysisResponse)
@limiter.limit(RATE_LIMIT_IMAGE)   # 비싼 OpenAI Vision 호출 — 엔드포인트별 강화 한도(item 16/F1)
async def analyze_image(
    request: Request,
    image: UploadFile = File(..., description="분석할 이미지 파일"),
    workplace_type: Optional[str] = Form(None, description="작업장 유형"),
    additional_context: Optional[str] = Form(None, description="추가 상황 설명"),
    db: Session = Depends(get_db)
):
    """
    이미지 기반 위험요소 분석

    작업현장 이미지를 업로드하면 AI가 산업재해 위험요소를 분석합니다.
    """
    # 파일 검증
    await file_handler.validate_image(image)

    # 이미지를 Base64로 변환
    image_base64 = await file_handler.image_to_base64(image)

    # 분석 수행
    result = await analysis_service.analyze_image(
        db=db,
        image_base64=image_base64,
        filename=image.filename or "unknown",
        workplace_type=workplace_type,
        additional_context=additional_context
    )

    return result


@router.post("/text", response_model=AnalysisResponse)
@limiter.limit(RATE_LIMIT_TEXT)   # OpenAI LLM 호출 — 엔드포인트별 강화 한도(item 16/F1)
async def analyze_text(
    request: Request,
    body: TextAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    텍스트 기반 위험요소 분석

    작업 상황을 텍스트로 설명하면 AI가 산업재해 위험요소를 분석합니다.
    """
    result = await analysis_service.analyze_text(
        db=db,
        description=body.description,
        workplace_type=body.workplace_type,
        industry_sector=body.industry_sector
    )

    return result


@router.get("/history", response_model=AnalysisHistoryResponse)
async def get_analysis_history(
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(20, ge=1, le=100, description="조회할 항목 수"),
    db: Session = Depends(get_db)
):
    """
    분석 기록 목록 조회

    저장된 분석 기록을 최신순으로 조회합니다.
    """
    total, records = crud.get_analysis_history(db, skip=skip, limit=limit)

    items = [
        AnalysisHistoryItem(
            analysis_id=r.id,
            analysis_type=r.analysis_type,
            overall_risk_level=r.overall_risk_level,
            summary=r.summary,
            analyzed_at=r.created_at,
            input_preview=r.input_preview,
            thumbnail=r.image_path,  # 분석 사진 thumbnail(data URI) — history 표시용
        )
        for r in records
    ]

    return AnalysisHistoryResponse(total=total, items=items)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """
    특정 분석 결과 조회

    저장된 분석 결과를 상세 조회합니다.
    """
    record = crud.get_analysis_record(db, analysis_id)
    if not record:
        raise AnalysisNotFoundError(analysis_id)

    result_data = record.result_json if isinstance(record.result_json, dict) else json.loads(record.result_json)
    # 플래그를 kill switch로 만든다 — off로 되돌렸는데 on 기간에 저장된 기록이 계속 조문 후보를
    # 보여주면 "끄면 안 보인다"가 성립하지 않는다. 저장 데이터는 보존하고 응답에서만 감춘다.
    if result_data.get("article_candidates") and not cue_article_service.enabled():
        result_data = {**result_data, "article_candidates": []}
    if result_data.get("work_flow") and not flow_service.enabled():
        result_data = {**result_data, "work_flow": None}
    # 장소성 라우팅 기록(kind=기인물없음)은 judge 스위치를 따른다 — off로 되돌렸는데 on 기간
    # 기록이 '기인물 없음' 화면을 계속 보여주면 "끄면 안 보인다"가 성립하지 않는다(kill switch 대칭).
    wf = result_data.get("work_flow")
    if (wf and isinstance(wf, dict) and (wf.get("anchor") or {}).get("kind") == "기인물없음"
            and not flow_service.judge_enabled()):
        result_data = {**result_data, "work_flow": None}
    # ai_action_alignments는 흐름 파생 필드('흐름 있을 때만' 계약) — 흐름과 같은 스위치를 따른다.
    # 빠뜨리면 flag-on 기간 기록이 off 조회에서 work_flow=None + 정렬만 남는 모순 응답이 된다.
    if result_data.get("ai_action_alignments") and not flow_service.enabled():
        result_data = {**result_data, "ai_action_alignments": []}
    return AnalysisResponse(**result_data)


@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """
    분석 기록 삭제
    """
    success = crud.delete_analysis_record(db, analysis_id)
    if not success:
        raise AnalysisNotFoundError(analysis_id)

    return {"message": "분석 기록이 삭제되었습니다.", "analysis_id": analysis_id}
