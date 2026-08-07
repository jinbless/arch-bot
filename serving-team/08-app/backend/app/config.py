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

    # 보안(item 19, CWE-798): 소스에 자격증명 하드코딩 금지. .env/환경변수로 주입 필수.
    # 미설정 시 database.py 가 기동을 차단(fail-safe). 예: postgresql://<user>:<password>@<host>/<db>
    DATABASE_URL: str = ""

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
    # WS-GATE-3 — semantic attach 도메인-부적합 guide hard reject. **기본 off(무회귀)**.
    # on이면 shadow_validate(industry, codes) 중 level=='vetted' AND confidence>=임계인 guide만
    # semantic 후보에서 hard-drop. facet(CI-corroborated) guide는 영향 없음(DEEP-1 merge가 재보존) →
    # FN 보수. env(OHS_ENABLE_DOMAIN_REJECT/OHS_DOMAIN_REJECT_CONF) 우선. 임계는 매우 높게(0.9)=FN 보수.
    OHS_ENABLE_DOMAIN_REJECT: bool = False
    OHS_DOMAIN_REJECT_CONF: float = 0.9

    # Track A cue-pool union 조문 후보 (research v2 검증: P@1 +4.6pt·Hit@5 +9.1pt CI 0 배제 —
    # docs/status/evaluation-baseline.md 최상단). **기본 off(무회귀)** — off면 응답의
    # article_candidates가 빈 배열로만 추가되고 기존 경로(trace.articles=PG 결정론)는 무변화.
    # env(CUE_ARTICLES/CUE_ARTICLE_RANK) 우선. RANK on 시 분석당 LLM +2회(RESOLVE+RANK).
    OHS_ENABLE_CUE_ARTICLES: bool = False
    OHS_ENABLE_ARTICLE_RANK: bool = False

    # 앱('app.*') 로거 레벨. 지금까지 로깅 설정이 없어 우리 모듈의 logger.info가 전부 버려졌다.
    OHS_LOG_LEVEL: str = "INFO"

    # ⭐ 기인물 앵커 기준 작업 흐름(work_flow). off면 응답에 None — 기존 경로 무변화.
    # env(CUE_FLOW) 우선. RESOLVE는 cue_article_service와 **공유**하므로 이 플래그만 켜도 LLM +1회다
    # (CUE_ARTICLES와 같이 켜도 RESOLVE는 여전히 1회).
    # 2026-08-07 기본 on 전환. 노출 조건 충족: 라벨 검수 체계 완료(flow_service.LABELS_REVIEWED 주석),
    # 서빙 전 게이트 감사 통과. 앵커 0.647(51장) — 오인식 대비는 정정 UI(대안 칩 + 전체 검색)가 담당.
    OHS_ENABLE_WORK_FLOW: bool = True


settings = Settings()
