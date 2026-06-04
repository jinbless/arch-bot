from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OPENAI_API_KEY: str = ""

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]

    DATABASE_URL: str = "postgresql://kosha:1229@localhost/kosha"

    FUSEKI_ENDPOINT: str = "http://localhost:3030/kosha/sparql"
    FUSEKI_TIMEOUT: int = 5
    FUSEKI_ENABLED: bool = True

    # v5 semantic attach — 검증 완료, 기본 on. env(SEMANTIC_ATTACH/SEMANTIC_ATTACH_RERANK)가 우선.
    OHS_ENABLE_HYBRID_SEARCH: bool = True
    OHS_ENABLE_SEMANTIC_RERANK: bool = True
    # guide 섹션-청킹으로 **랭킹**할지 여부(ohs_guide_section). ablation(rerank 없는 vector-only/max)에선
    # +0.44(22:10) 승이나, full-pipeline 재검증(rerank ON=production)에선 wash(-0.17, 18건 6:8) —
    # rerank가 1벡터 평균-희석을 이미 보정. ∴ 랭킹은 검증된 1벡터+rerank 유지(**기본 off**, 무회귀).
    # §섹션 인용 근거는 _attach_section_evidence가 랭킹과 무관하게 항상 사후 부착(정확도 손실 0).
    # on이면 랭킹까지 섹션 기반으로 전환(A/B용). env(GUIDE_SECTION_RECALL) 우선.
    OHS_ENABLE_GUIDE_SECTION: bool = False
    # 학습 캐시는 opt-in — 전 코퍼스 재누적(accumulate_hybrid_attach) 후 활성. 데모 캐시는 stale.
    OHS_ENABLE_ATTACH_CACHE: bool = False


settings = Settings()
