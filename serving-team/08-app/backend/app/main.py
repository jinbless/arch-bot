import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import router as api_v1_router
from app.config import settings
from app.db.database import SessionLocal, create_tables
from app.services.article_service import article_service
from app.services.guide_service import guide_service

logger = logging.getLogger(__name__)


def _client_ip_key(request: Request) -> str:
    """nginx 프록시 뒤 실제 클라이언트 IP — 레이트리밋 키.
    X-Real-IP($remote_addr, nginx가 덮어써 위조 불가) 우선. XFF 첫값은 클라가 위조 가능하므로 후순위."""
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


# 레이트리밋(F1, CWE-770) — 익명 대량요청·OpenAI 비용 남용 방지. 전역 기본한도(엔드포인트별 튜닝 가능).
# 주의: 기본 in-memory(프로세스별) — 다중 워커/스케일아웃 시 redis 등 공유 저장 권장.
limiter = Limiter(key_func=_client_ip_key, default_limits=["120/minute", "1000/day"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()

    # 배포 옵션: startup의 legacy article/guide 인덱스 빌드 생략(uvicorn 기동 지연·OpenAI 비용 방지).
    # 핵심 사진→4패널 서빙은 ohs_* 컬렉션(hybrid_search) + PG를 쓰므로 이 인덱스 불요.
    # (article 검색·guide 브라우저 보조 기능만 영향. env OHS_SKIP_STARTUP_INDEX=true로 활성)
    import os as _os
    _skip_idx = _os.environ.get("OHS_SKIP_STARTUP_INDEX", "").lower() in ("1", "true", "on", "yes")

    if _skip_idx:
        logger.info("Startup article/guide 인덱스 빌드 생략(OHS_SKIP_STARTUP_INDEX) — 핵심 4패널은 ohs_* 컬렉션 사용.")
    else:
        try:
            count = article_service.build_index(force=False)
            logger.info("Article index ready: %s articles", count)
        except Exception as exc:
            logger.warning("Article index startup skipped: %s", exc)

        try:
            db = SessionLocal()
            try:
                parse_result = guide_service.parse_and_store_all(db, force=False)
                if not parse_result.get("skipped"):
                    mappings = guide_service.build_mappings(db)
                    logger.info(
                        "KOSHA Guide parsed: %s guides, %s mappings",
                        parse_result.get("total_parsed", 0),
                        mappings,
                    )
                indexed = guide_service.build_index(db, force=False)
                logger.info("KOSHA Guide index ready: %s sections", indexed)
            finally:
                db.close()
        except Exception as exc:
            logger.warning("KOSHA Guide startup skipped: %s", exc)

    try:
        from app.integrations.sparql_client import sparql_client

        health = await sparql_client.health_check()
        if health.get("fuseki_reachable"):
            logger.info("Fuseki SPARQL reachable: %s", settings.FUSEKI_ENDPOINT)
        else:
            logger.info("Fuseki SPARQL unavailable; running with materialized PG data")
    except Exception as exc:
        logger.info("Fuseki probe skipped: %s", exc)

    yield


app = FastAPI(
    title="OHS ontology analysis API",
    description="Photo/text observation to risk features, SHE patterns, SR, guide, and penalty paths.",
    version="3.1.0",   # 3.1.0: Track A ② — /sparql SR-inference 엔드포인트(exemptions/co-applicable/depends-on/inferred-graph) PG 전환
    lifespan=lifespan,
)

# CORS — '*' 출처와 자격증명 동시 허용은 취약(F5, CWE-942). '*' 포함 시 자격증명 비활성으로 강등.
_allow_credentials = True
if "*" in settings.ALLOWED_ORIGINS:
    logger.warning("ALLOWED_ORIGINS에 '*' 포함 — allow_credentials 비활성화(보안). 운영은 출처를 명시하세요.")
    _allow_credentials = False
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 레이트리밋(F1)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도하세요.", "error_code": "RATE_LIMITED"},
    )


# 보안 응답헤더(F7) — defense-in-depth. HSTS/CSP는 nginx 권장(여기선 안전한 3종).
@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


# 미처리 예외 일반화(F7, CWE-209) — 내부정보 노출 차단. HTTPException(OHSException)은 기본 핸들러가 처리.
@app.exception_handler(Exception)
async def _unhandled_exception(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다.", "error_code": "INTERNAL_ERROR"},
    )


app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "OHS ontology analysis API", "version": "3.1.0"}
