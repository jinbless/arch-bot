"""프로젝트 경로 해석기 — Docker 호환 상대경로 기반.

환경변수로 모든 경로를 오버라이드할 수 있다.
기본값은 이 파일의 위치(scripts/lib/)에서 상대경로로 자동탐지한다.
"""
import os
from pathlib import Path


def _find_project_root() -> Path:
    """환경변수 PIPEB_ROOT > 자동탐지 순서로 프로젝트 루트를 결정."""
    env = os.getenv("PIPEB_ROOT")
    if env:
        return Path(env).resolve()
    # 자동탐지: scripts/lib/paths.py → scripts/lib/ → scripts/ → pipe-B/
    return Path(__file__).resolve().parent.parent.parent


# 프로젝트 루트 (pipe-B/)
PROJECT_ROOT = _find_project_root()

# 저장소 루트 (arch-bot/)
REPO_ROOT = Path(os.getenv("REPO_ROOT", str(PROJECT_ROOT.parent.parent))).resolve()

# 주요 경로
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SCHEMA_DIR = PROJECT_ROOT / "schemas"
DATA_DIR = PROJECT_ROOT / "data"
BATCHES_DIR = DATA_DIR / "ci-batches"
AGENTS_DIR = PROJECT_ROOT / "agents"
DB_DIR = PROJECT_ROOT / "db"

# 외부 데이터 (kosha-guides/ — 저장소 루트 레벨)
GUIDES_ROOT = Path(os.getenv("GUIDES_ROOT", str(REPO_ROOT / "kosha-guides"))).resolve()
GUIDES_PDF = GUIDES_ROOT  # {A,B,C,D,E}/ 하위
PARSED_DIR = GUIDES_ROOT / "parsed"

# Pipe-A 참조 (schema_validator 동적 임포트용)
PIPE_A_ROOT = Path(os.getenv("PIPE_A_ROOT", str(PROJECT_ROOT.parent / "pipe-A"))).resolve()

# DB 연결 (환경변수 우선)
DB_CONN_STR = os.getenv("KOSHA_DB_CONN", "dbname=kosha user=kosha password=1229 host=localhost")
