"""Embedding 모델 SSOT (WS-DRIFT-5).

쿼리 임베딩(서빙)과 인덱스 임베딩(빌드)이 **같은 모델·차원 공간**에 있어야 cosine이
의미를 갖는다. 모델명이 여러 파일에 분산 하드코딩되면 한쪽만 바뀌어도(또는 OpenAI가
same-name 모델을 갱신해도) 질의·인덱스 벡터가 다른 공간에 놓여, 차원만 같으면 예외도
없이 결과만 조용히 나빠진다. 이 단일 정본을 모든 임베딩 호출부가 import한다.

env override: OPENAI_EMBEDDING_MODEL / OPENAI_EMBEDDING_DIM.
"""
from __future__ import annotations

import os

EMBEDDING_MODEL: str = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM: int = int(os.environ.get("OPENAI_EMBEDDING_DIM", "1536"))
