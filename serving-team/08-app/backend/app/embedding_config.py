"""Embedding 모델 SSOT (WS-DRIFT-5).

쿼리 임베딩(서빙)과 인덱스 임베딩(빌드)이 **같은 모델·차원 공간**에 있어야 cosine이
의미를 갖는다. 모델명이 여러 파일에 분산 하드코딩되면 한쪽만 바뀌어도(또는 OpenAI가
same-name 모델을 갱신해도) 질의·인덱스 벡터가 다른 공간에 놓여, 차원만 같으면 예외도
없이 결과만 조용히 나빠진다. 이 단일 정본을 모든 임베딩 호출부가 import한다.

env override: OPENAI_EMBEDDING_MODEL / OPENAI_EMBEDDING_DIM.
"""
from __future__ import annotations

import os
from typing import Any

EMBEDDING_MODEL: str = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM: int = int(os.environ.get("OPENAI_EMBEDDING_DIM", "1536"))

# 임베딩 호출 타임아웃/재시도 SSOT. OpenAI SDK 기본은 600s×재시도라 네트워크 행 시
# 분석 1건이 사실상 무한 블록된다(2,360-case replay가 ~950에서 17분 멈춘 실측 사례).
# 짧은 per-request 타임아웃 + 유한 재시도로 transient 행은 복구하고, 끝내 실패해도
# 호출부 try/except가 graceful degradation(semantic 없이 facet-direct)으로 흡수한다.
EMBEDDING_TIMEOUT_S: float = float(os.environ.get("OPENAI_EMBEDDING_TIMEOUT_S", "30"))
EMBEDDING_MAX_RETRIES: int = int(os.environ.get("OPENAI_EMBEDDING_MAX_RETRIES", "3"))


def build_embedding_client(api_key: str) -> Any:
    """타임아웃·재시도 설정된 OpenAI 클라이언트 (모든 임베딩 호출부 공용).

    성공 호출의 결과·지연은 불변(타임아웃은 행에서만 발동) → 매칭 품질 무영향.
    """
    from openai import OpenAI  # 지연 import (테스트/오프라인 경로 부담 회피)

    return OpenAI(
        api_key=api_key,
        timeout=EMBEDDING_TIMEOUT_S,
        max_retries=EMBEDDING_MAX_RETRIES,
    )
