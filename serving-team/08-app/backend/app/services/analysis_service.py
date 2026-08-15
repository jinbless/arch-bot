from __future__ import annotations

import logging
from typing import Awaitable, Callable, Optional

from sqlalchemy.orm import Session

from app.integrations.openai_client import openai_client
from app.models.analysis import AnalysisResponse
from app.services.analysis_pipeline import AnalysisRunInput, analysis_pipeline
from app.utils.exceptions import OpenAIAPIError
from app.utils.file_handler import file_handler

logger = logging.getLogger(__name__)


class AnalysisService:
    async def analyze_image(
        self,
        db: Session,
        image_base64: str,
        filename: str,
        workplace_type: Optional[str] = None,
        additional_context: Optional[str] = None,
    ) -> AnalysisResponse:
        result = await self._run_ai_analysis(
            lambda: openai_client.analyze_image(
                image_base64=image_base64,
                workplace_type=workplace_type,
                additional_context=additional_context,
            )
        )
        # 분석 사진 thumbnail(긴 변 480px) — history에서 결과와 함께 표시(best-effort, 실패 시 None).
        thumbnail = file_handler.make_thumbnail_data_uri(image_base64, max_dim=480)
        # ⚠ 업로드 파일명(filename)은 저장하지 않는다(2026-08-15 사용자 결정) — 감독 사진 파일명에
        #   실제 기업명·현장명이 들어가 히스토리 화면에 그대로 노출됐다. 화면 표시도 제거됨(HistoryPage).
        #   filename 인자는 API 계약 유지를 위해 받기만 하고 쓰지 않는다.
        _ = filename
        return await analysis_pipeline.run(
            db=db,
            run_input=AnalysisRunInput(
                result=result,
                analysis_type="image",
                input_preview="",
                declared_industry_text=workplace_type,
                thumbnail=thumbnail,
            ),
        )

    async def analyze_text(
        self,
        db: Session,
        description: str,
        workplace_type: Optional[str] = None,
        industry_sector: Optional[str] = None,
    ) -> AnalysisResponse:
        result = await self._run_ai_analysis(
            lambda: openai_client.analyze_text(
                description=description,
                workplace_type=workplace_type,
                industry_sector=industry_sector,
            )
        )
        input_preview = description[:100] + "..." if len(description) > 100 else description
        return await analysis_pipeline.run(
            db=db,
            run_input=AnalysisRunInput(
                result=result,
                analysis_type="text",
                input_preview=input_preview,
                full_description=description,
                declared_industry_text=industry_sector or workplace_type,
            ),
        )

    async def _run_ai_analysis(
        self,
        call: Callable[[], Awaitable[dict]],
    ) -> dict:
        try:
            return await call()
        except OpenAIAPIError:
            raise
        except Exception as exc:
            logger.exception("AI analysis failed")
            raise OpenAIAPIError(
                "AI 분석 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
            ) from exc


analysis_service = AnalysisService()
