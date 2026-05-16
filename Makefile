# arch-bot dev launcher.
#
# Backend (FastAPI/uvicorn 8001) + Frontend (Vite 5173) run on the host using
# the existing serving-team/08-app/backend/.venv (WSL Linux) and serving-team/08-app/frontend/node_modules. PG
# is treated as an external dependency by default — `make dev-up` only health
# checks it. Use `make dev-pg-up` only when you need an isolated dev DB on
# host port 5433 (separate volume; the team's existing 5432 kosha DB is never
# touched).

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
LOG_DIR := $(ROOT)/.dev-logs
BACKEND_DIR := $(ROOT)/serving-team/08-app/backend
FRONTEND_DIR := $(ROOT)/serving-team/08-app/frontend
ENV_FILE := $(ROOT)/.env.dev

# Defaults if .env.dev is absent.
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8001
FRONTEND_HOST ?= 127.0.0.1
FRONTEND_PORT ?= 5173
DATABASE_URL ?= postgresql://kosha:1229@localhost:5432/kosha
VITE_API_TARGET ?= http://127.0.0.1:8001

# Pull overrides from .env.dev if present (no failure if absent).
ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
export
endif

VENV_PY := $(BACKEND_DIR)/.venv/bin/python

.PHONY: help dev-setup dev-up dev-down dev-restart dev-check dev-status dev-logs \
        dev-pg-up dev-pg-down dev-pg-status

help:
	@echo "arch-bot dev launcher"
	@echo ""
	@echo "One-time setup:"
	@echo "  cp .env.dev.example .env.dev      # then edit if needed"
	@echo "  make dev-setup                    # install backend deps into serving-team/08-app/backend/.venv"
	@echo "                                    # (frontend node_modules is preserved as-is)"
	@echo ""
	@echo "Daily:"
	@echo "  make dev-up        Start backend ($(BACKEND_PORT)) + frontend ($(FRONTEND_PORT)) in background."
	@echo "  make dev-down      Stop background backend + frontend."
	@echo "  make dev-restart   dev-down then dev-up."
	@echo "  make dev-check     Health-check PG + backend + frontend."
	@echo "  make dev-status    Show running PIDs."
	@echo "  make dev-logs      tail -f backend + frontend logs."
	@echo ""
	@echo "Optional isolated PG (host port 5433, separate volume — does NOT touch the team's 5432):"
	@echo "  make dev-pg-up / dev-pg-down / dev-pg-status"
	@echo ""
	@echo "URLs (after dev-up):"
	@echo "  Backend root  : http://$(BACKEND_HOST):$(BACKEND_PORT)/"
	@echo "  Backend docs  : http://$(BACKEND_HOST):$(BACKEND_PORT)/docs"
	@echo "  Frontend      : http://$(FRONTEND_HOST):$(FRONTEND_PORT)/ohs/"

dev-setup:
	@echo "[setup] backend deps -> serving-team/08-app/backend/.venv"
	@if [ ! -x '$(VENV_PY)' ]; then \
	  echo "[setup] creating venv at $(BACKEND_DIR)/.venv"; \
	  python3 -m venv '$(BACKEND_DIR)/.venv'; \
	fi
	@'$(VENV_PY)' -m pip install --upgrade pip setuptools wheel
	@'$(VENV_PY)' -m pip install -r '$(BACKEND_DIR)/requirements.txt'
	@echo "[setup] frontend node_modules — left as-is by policy (no npm ci/install)"
	@if [ ! -d '$(FRONTEND_DIR)/node_modules' ]; then \
	  echo "[setup] WARN: $(FRONTEND_DIR)/node_modules missing. Install manually:"; \
	  echo "         cd $(FRONTEND_DIR) && npm ci"; \
	fi
	@echo "[setup] done"

dev-up:
	@mkdir -p "$(LOG_DIR)"
	@echo "[backend] uvicorn on $(BACKEND_HOST):$(BACKEND_PORT) (reload) -> $(LOG_DIR)/backend.log"
	@cd "$(BACKEND_DIR)" && \
	  DATABASE_URL='$(DATABASE_URL)' \
	  HOST='$(BACKEND_HOST)' \
	  PORT='$(BACKEND_PORT)' \
	  setsid nohup '$(VENV_PY)' -m uvicorn app.main:app \
	    --host '$(BACKEND_HOST)' --port '$(BACKEND_PORT)' --reload \
	    > "$(LOG_DIR)/backend.log" 2>&1 < /dev/null & \
	  echo $$! > "$(LOG_DIR)/backend.pid"
	@echo "[frontend] vite on $(FRONTEND_HOST):$(FRONTEND_PORT) -> $(LOG_DIR)/frontend.log"
	@cd "$(FRONTEND_DIR)" && \
	  VITE_API_TARGET='$(VITE_API_TARGET)' \
	  setsid nohup npm run dev -- \
	    --host '$(FRONTEND_HOST)' --port '$(FRONTEND_PORT)' --strictPort \
	    > "$(LOG_DIR)/frontend.log" 2>&1 < /dev/null & \
	  echo $$! > "$(LOG_DIR)/frontend.pid"
	@echo "[wait] polling until backend + frontend respond (max ~30s)..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
	  sleep 3; \
	  b=$$(curl -s -o /dev/null -w '%{http_code}' -m 2 http://$(BACKEND_HOST):$(BACKEND_PORT)/ 2>/dev/null || echo 000); \
	  f=$$(curl.exe -s -o NUL -w '%{http_code}' -m 2 http://$(FRONTEND_HOST):$(FRONTEND_PORT)/ohs/ 2>/dev/null || echo 000); \
	  if [ "$$b" = "200" ] && [ "$$f" = "200" ]; then \
	    echo "[wait] both ready after $${i}x3s (backend=$$b frontend=$$f)"; break; \
	  fi; \
	  echo "  attempt $$i: backend=$$b frontend=$$f, retrying..."; \
	done
	@$(MAKE) -s dev-check

dev-down:
	@echo "[stop] backend"
	@-if [ -f "$(LOG_DIR)/backend.pid" ]; then \
	  pid=$$(cat "$(LOG_DIR)/backend.pid"); \
	  kill -- -$$pid 2>/dev/null || kill $$pid 2>/dev/null || true; \
	  rm -f "$(LOG_DIR)/backend.pid"; \
	fi
	@-pkill -f 'uvicorn app.main:app' 2>/dev/null || true
	@echo "[stop] frontend"
	@-if [ -f "$(LOG_DIR)/frontend.pid" ]; then \
	  pid=$$(cat "$(LOG_DIR)/frontend.pid"); \
	  kill -- -$$pid 2>/dev/null || kill $$pid 2>/dev/null || true; \
	  rm -f "$(LOG_DIR)/frontend.pid"; \
	fi
	@-pkill -f 'vite.*--port $(FRONTEND_PORT)' 2>/dev/null || true
	@echo "[stop] frontend (Windows-side $(FRONTEND_PORT) cleanup)"
	@-powershell.exe -NoProfile -Command "Get-NetTCPConnection -LocalPort $(FRONTEND_PORT) -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$$_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>/dev/null || true
	@echo "[stop] done"

dev-restart: dev-down dev-up

dev-check:
	@echo "=== dev-check ==="
	@echo "[1/3] postgres ($(DATABASE_URL))"
	@'$(VENV_PY)' -c "import psycopg2; c=psycopg2.connect('$(DATABASE_URL)'); cur=c.cursor(); cur.execute('SELECT 1, current_database(), current_user'); print('  PG OK:', cur.fetchone()); c.close()" 2>&1 \
	  || echo "  PG FAIL — start your existing kosha PG (5432), or run 'make dev-pg-up' for an isolated dev DB on 5433."
	@echo "[2/3] backend http://$(BACKEND_HOST):$(BACKEND_PORT)/"
	@if curl -sf -m 5 http://$(BACKEND_HOST):$(BACKEND_PORT)/ -o /tmp/arch-bot-backend.txt 2>/dev/null; then \
	  echo "  backend OK: $$(cat /tmp/arch-bot-backend.txt)"; \
	else \
	  echo "  backend FAIL — see $(LOG_DIR)/backend.log"; \
	fi
	@echo "[3/3] frontend http://$(FRONTEND_HOST):$(FRONTEND_PORT)/ohs/"
	@# Vite spawns under Windows node.exe (PATH inherited from Windows), so the
	@# socket binds in the Windows network namespace. WSL `127.0.0.1` does not
	@# see it, but Windows curl.exe via WSL interop does.
	@code=$$(curl.exe -s -o NUL -w '%{http_code}' -m 5 http://$(FRONTEND_HOST):$(FRONTEND_PORT)/ohs/ 2>/dev/null || echo "000"); \
	  if [ "$$code" = "200" ]; then echo "  frontend OK: HTTP 200"; \
	  else echo "  frontend FAIL: HTTP $$code — see $(LOG_DIR)/frontend.log"; fi

dev-status:
	@echo "=== dev-status ==="
	@for s in backend frontend; do \
	  if [ -f "$(LOG_DIR)/$$s.pid" ]; then \
	    pid=$$(cat "$(LOG_DIR)/$$s.pid"); \
	    if kill -0 $$pid 2>/dev/null; then \
	      echo "  $$s: RUNNING pid=$$pid log=$(LOG_DIR)/$$s.log"; \
	    else \
	      echo "  $$s: STOPPED (stale pid $$pid)"; \
	    fi; \
	  else \
	    echo "  $$s: not started"; \
	  fi; \
	done

dev-logs:
	@touch "$(LOG_DIR)/backend.log" "$(LOG_DIR)/frontend.log"
	@tail -n 40 -f "$(LOG_DIR)/backend.log" "$(LOG_DIR)/frontend.log"

dev-pg-up:
	@echo "[pg] starting isolated dev PG (host 5433, container arch-bot-dev-postgres)"
	@docker compose -f "$(ROOT)/docker-compose.dev.yml" --profile infra up -d postgres
	@echo "[pg] waiting for healthy (max ~30s)"
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do \
	  status=$$(docker inspect -f '{{.State.Health.Status}}' arch-bot-dev-postgres 2>/dev/null || echo unknown); \
	  if [ "$$status" = "healthy" ]; then echo "[pg] healthy"; exit 0; fi; \
	  printf '  status=%s\n' "$$status"; sleep 2; \
	done; \
	echo "[pg] WARN: not healthy. Inspect: docker logs arch-bot-dev-postgres"

dev-pg-down:
	@echo "[pg] stopping isolated dev PG (volume arch-bot-dev-pgdata preserved)"
	@docker compose -f "$(ROOT)/docker-compose.dev.yml" --profile infra down

dev-pg-status:
	@docker ps -a --filter name=arch-bot-dev-postgres --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
