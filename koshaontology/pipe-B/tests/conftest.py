"""공통 fixtures — 경로, 스키마 로더."""
import json
import sys
from pathlib import Path

import pytest

# pipe-B 프로젝트 루트
PIPE_B_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PIPE_B_ROOT / "scripts"
SCHEMA_DIR = PIPE_B_ROOT / "schemas"
DATA_DIR = PIPE_B_ROOT / "data"
AGENTS_DIR = PIPE_B_ROOT / "agents"
DB_DIR = PIPE_B_ROOT / "db"
REPO_ROOT = PIPE_B_ROOT.parent.parent

# lib import 경로 설정
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def schema_dir():
    return SCHEMA_DIR


@pytest.fixture
def data_dir():
    return DATA_DIR


def load_schema(name: str) -> dict:
    """스키마 파일 로드."""
    path = SCHEMA_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))
