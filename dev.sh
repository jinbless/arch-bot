#!/usr/bin/env bash
# Thin wrapper around the Makefile. Runs from any cwd.
#   ./dev.sh up | down | restart | check | status | logs | pg-up | pg-down | pg-status | help
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
cmd="${1:-help}"
shift || true
exec make "dev-${cmd}" "$@"
