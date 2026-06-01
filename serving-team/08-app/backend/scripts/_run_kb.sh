#!/usr/bin/env bash
set -e
cd /mnt/c/project/arch-bot/serving-team/08-app/backend
export DATABASE_URL='postgresql://kosha:1229@localhost:5432/kosha'
export PYTHONIOENCODING=utf-8
./.venv/bin/python scripts/build_kb_embeddings.py "$@"
