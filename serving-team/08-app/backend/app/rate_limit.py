"""레이트리밋 설정 — 익명 대량요청·OpenAI 비용 남용 방지 (F1, CWE-770 / item 16).

전역 기본 한도 + 비싼 엔드포인트(이미지/텍스트 분석 = OpenAI Vision/LLM 호출)별 강화 한도.
한도는 env 로 조정 가능. 다중 워커/스케일아웃 시 redis 등 공유 저장 권장(현재 in-memory).

  OHS_RATE_LIMIT_DEFAULT   전역(';' 구분)   기본 "120/minute;1000/day"
  OHS_RATE_LIMIT_IMAGE     POST /image     기본 "10/minute"   (Vision 호출 — 비용 큼)
  OHS_RATE_LIMIT_TEXT      POST /text      기본 "20/minute"   (LLM 호출)
"""
import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMIT_DEFAULT = os.environ.get("OHS_RATE_LIMIT_DEFAULT", "120/minute;1000/day")
RATE_LIMIT_IMAGE = os.environ.get("OHS_RATE_LIMIT_IMAGE", "10/minute")
RATE_LIMIT_TEXT = os.environ.get("OHS_RATE_LIMIT_TEXT", "20/minute")


def client_ip_key(request: Request) -> str:
    """nginx 프록시 뒤 실제 클라이언트 IP — 레이트리밋 키.
    X-Real-IP($remote_addr, nginx가 덮어써 위조 불가) 우선. XFF 첫값은 클라가 위조 가능하므로 후순위."""
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip_key, default_limits=RATE_LIMIT_DEFAULT.split(";"))
