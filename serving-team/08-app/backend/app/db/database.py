from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# 보안 fail-safe(item 19) — 소스 기본 자격증명을 제거했으므로 .env/환경변수 주입 필수.
if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL이 설정되지 않았습니다. .env 또는 환경변수에 DATABASE_URL을 지정하세요 "
        "(예: postgresql://<user>:<password>@<host>/<db>). "
        "보안을 위해 소스코드의 기본 DB 자격증명을 제거했습니다."
    )

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    from app.db import models

    Base.metadata.create_all(
        bind=engine,
        tables=[
            models.OhsAnalysisRecord.__table__,
            models.OhsHazardCodeGap.__table__,
            models.OhsActionStatuteGap.__table__,
        ],
    )
