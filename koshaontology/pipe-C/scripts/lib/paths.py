"""Pipe-C 경로 상수."""
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SCRIPTS_DIR.parent  # pipe-C/
REPO_ROOT = PROJECT_ROOT.parent    # koshaontology/
PIPE_A_ROOT = REPO_ROOT / "pipe-A"
PIPE_B_ROOT = REPO_ROOT / "pipe-B"
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = PROJECT_ROOT / "db"
SCHEMA_DIR = PROJECT_ROOT / "schemas"
GUIDES_ROOT = REPO_ROOT.parent / "kosha-guides"
PARSED_DIR = GUIDES_ROOT / "parsed"

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"
