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
        dev-pg-up dev-pg-down dev-pg-status \
        f1-mine f1-mine-gate2 f1-mine-log f1-promote f1-status \
        f1-eval f1-regression f1-recover f1-help \
        f2-help f2-patch-v32 f2-patch-v33 f2-enrich-sonnet f2-link-v31 \
        f3-help f3-shadow-validator f3-promote-candidates f3-compile-kb \
        f3-drift-check f3-weekly-cycle \
        phase-g-help phase-g1-schema phase-g1-import phase-g1-verify phase-g-verify she-import \
        verify-codes verify-codes-shape verify-prefixes gen-manifest verify-manifest gen-canonical-shape continual-pending \
        data-coverage

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


# ---------------------------------------------------------------------------
# Phase F.1 — Normalizer alias auto-registration (Layer 4 Module 4.1)
# 자세히: docs/dev-notes/F.1-auto-register-aliases.md
#
# 모든 target은 ARGS='--flag --flag2' 로 추가 옵션 전달 가능.
# 예: make f1-mine ARGS='--gate2 --min-confidence 0.7'
# ---------------------------------------------------------------------------

F1_SCRIPTS := $(ROOT)/data-team/05-enrichment/llm-scripts
F1_RUNTIME := $(ROOT)/data-team/05-enrichment/runtime-artifacts
F1_BASELINE := $(F1_RUNTIME)/replay_baseline_v3.json

f1-help:
	@echo "Phase F.1 — Normalizer alias auto-registration"
	@echo ""
	@echo "Mining (input → 4-Gate verification):"
	@echo "  make f1-mine                          dry-run (light + log, default)"
	@echo "  make f1-mine-gate2                    --gate2 (LLM verify, ~\$$0.05)"
	@echo "  make f1-mine-log                      --skip-light (log-only)"
	@echo "  make f1-mine ARGS='--apply --gate2'   apply candidate file write"
	@echo ""
	@echo "Promotion (candidate → vetted main):"
	@echo "  make f1-status                        list current candidates"
	@echo "  make f1-promote                       dry-run --auto (uses >= 5)"
	@echo "  make f1-promote ARGS='--apply --by-confidence --min-conf 0.85'"
	@echo "  make f1-promote ARGS='--apply --rollback CODE1 CODE2'"
	@echo ""
	@echo "Verification:"
	@echo "  make f1-regression                    2,360 synthetic replay + Gate 3"
	@echo "  make f1-eval                          8 real-test-photo ON/OFF (~\$$0.40 + 8min)"
	@echo ""
	@echo "Catalog recovery (F.1 후속, 1회성):"
	@echo "  make f1-recover ARGS='--skip-sonnet'  Stage 1+2 only (free)"
	@echo "  make f1-recover                       full 3-stage (Sonnet 4.6, ~\$$5)"

f1-mine:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/auto_register_aliases.py' $(ARGS)

f1-mine-gate2:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/auto_register_aliases.py' --gate2 $(ARGS)

f1-mine-log:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/auto_register_aliases.py' --skip-light --min-freq 1 --gate2 $(ARGS)

f1-promote:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/promote_aliases.py' $(ARGS)

f1-status:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/promote_aliases.py' --list

f1-eval:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' LLM_RERANK_MODE=shadow \
	  '$(VENV_PY)' '$(F1_SCRIPTS)/eval_real_photos_day6.py'

f1-regression:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' \
	  '$(VENV_PY)' -u scripts/replay_synthetic_observations.py --output /tmp/replay_f1.json
	@'$(VENV_PY)' '$(BACKEND_DIR)/scripts/regression_gate.py' /tmp/replay_f1.json --baseline '$(F1_BASELINE)'

f1-recover:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  '$(VENV_PY)' '$(F1_SCRIPTS)/recover_catalog_mismatch.py' $(ARGS)


# ---------------------------------------------------------------------------
# Phase F.2 — Taxonomy Discovery (Module 4.2)
# 자세히: docs/dev-notes/F.2-taxonomy-discovery.md
# ARGS='--flag --flag2' 추가 옵션 전달.
# ---------------------------------------------------------------------------

f2-help:
	@echo "Phase F.2 — Taxonomy Discovery"
	@echo ""
	@echo "Catalog patches (1회성):"
	@echo "  make f2-patch-v32                     v3.1 → v3.2 (+25 codes + 2 axes ppe/env)"
	@echo "  make f2-patch-v33                     v3.2 → v3.3 (+52 codes matcher + synthetic)"
	@echo ""
	@echo "SHE enrichment (Sonnet 4.6):"
	@echo "  make f2-enrich-sonnet                 dry-run (cost preview)"
	@echo "  make f2-enrich-sonnet ARGS='--apply'  ~\$$6 → 790 SHE OTHER 교체"
	@echo ""
	@echo "v3.1 codes → SHE (pending_review):"
	@echo "  make f2-link-v31                      dry-run"
	@echo "  make f2-link-v31 ARGS='--apply'       ~\$$2 → 77 new SHE pending"
	@echo ""
	@echo "검증: make f1-regression / make f1-eval (F.1 target 공유)"
	@echo "Runbook: docs/dev-notes/F.2-taxonomy-discovery.md"

f2-patch-v32:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/patch_catalog_v3_2.py' $(ARGS)

f2-patch-v33:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/patch_catalog_v3_3.py' $(ARGS)

f2-enrich-sonnet:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' \
	  '$(VENV_PY)' '$(F1_SCRIPTS)/enrich_she_with_sonnet.py' $(ARGS)

f2-link-v31:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' \
	  '$(VENV_PY)' '$(F1_SCRIPTS)/link_v31_codes_to_she.py' $(ARGS)


# ---------------------------------------------------------------------------
# Phase F.3 — Axiom Discovery + Reasoner Shadow + Drift Detection (Module 4.4)
# Tier 2 sprints T2.A/B/C/D 통합 운영 인터페이스.
# 자세히: docs/workplans/llm-accelerated-ontology-engineering.md (Tier 2)
# ---------------------------------------------------------------------------

f3-help:
	@echo "Phase F.3 — Axiom Discovery / Reasoner Shadow / Drift"
	@echo ""
	@echo "T2.A — Reasoner shadow channel (F.3.1):"
	@echo "  make f3-shadow-validator              offline batch (analysis_log → shadow_reasoner_log)"
	@echo "  make f3-shadow-validator ARGS='--pyshacl --limit 50'   pyshacl cross-check"
	@echo ""
	@echo "T2.D — F.3.2 candidates → vetted (1-by-1 + Gate 3 wrap):"
	@echo "  make f3-promote-candidates            dry-run (8 candidates listed)"
	@echo "  make f3-promote-candidates ARGS='--apply'              실제 promote + regression"
	@echo "  make f3-promote-candidates ARGS='--apply --only-index 1,3'   특정 candidate만"
	@echo ""
	@echo "T2.B — KB compile (F.3.4):"
	@echo "  make f3-compile-kb                    candidate → kb-candidates.ttl (SHACL sh:Info)"
	@echo "  make f3-compile-kb ARGS='--scope vetted'               vetted scope 검증"
	@echo "  Fuseki reload: 별도 Java rebuild + container restart 필요 (~30 min)"
	@echo ""
	@echo "T2.C — Drift detection (F.3.5):"
	@echo "  make f3-drift-check                   가장 최근 replay_results_*.json 비교"
	@echo "  make f3-drift-check ARGS='--current /tmp/replay.json'  명시적 입력"
	@echo "  make f3-drift-check ARGS='--json'     CI/slack 통합용 JSON output"
	@echo ""
	@echo "Weekly cron-able (no LLM cost):"
	@echo "  make f3-weekly-cycle                  shadow → compile → replay → drift check"

f3-shadow-validator:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/pyshacl_shadow_validator.py' $(ARGS)

f3-promote-candidates:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' \
	  '$(VENV_PY)' '$(F1_SCRIPTS)/promote_f32_per_candidate.py' $(ARGS)

f3-compile-kb:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/compile_kb_to_ttl.py' $(ARGS)

f3-drift-check:
	@'$(VENV_PY)' '$(F1_SCRIPTS)/f3_drift_check.py' $(ARGS)

f3-weekly-cycle:
	@echo "[f3-weekly] 1/4 shadow validator (offline batch)"
	@'$(VENV_PY)' '$(F1_SCRIPTS)/pyshacl_shadow_validator.py'
	@echo "[f3-weekly] 2/4 compile KB to TTL (kb-candidates.ttl)"
	@'$(VENV_PY)' '$(F1_SCRIPTS)/compile_kb_to_ttl.py'
	@echo "[f3-weekly] 3/4 replay synthetic"
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' \
	  '$(VENV_PY)' -u scripts/replay_synthetic_observations.py \
	    --output '$(F1_RUNTIME)/replay_results_weekly.json'
	@echo "[f3-weekly] 4/4 drift check vs baseline_v3"
	@'$(VENV_PY)' '$(F1_SCRIPTS)/f3_drift_check.py' \
	  --current '$(F1_RUNTIME)/replay_results_weekly.json'


# ---------------------------------------------------------------------------
# Phase G — 7단계 PG 재물질화 (Tier 3 옵션 3C)
# 사용자 구조 step 4: "온톨로지화된 KB → PG 적재 → 실 서비스 자동 반영"
# Sprint G.1: guide_domain_incompatibilities | G.2: guide_usage_profiles |
#             G.3: penalty_rules | G.4: she_patterns reasoner-derived
# 자세히: docs/dev-notes/phase-g.*-pg.md
# ---------------------------------------------------------------------------

PHASE_G_DIR := $(ROOT)/serving-team/07-materialization

phase-g-help:
	@echo "Phase G — 7단계 PG 재물질화"
	@echo ""
	@echo "Sprint G.1 — guide_domain_incompatibilities (완료, ontology backing: core:Incompatibility):"
	@echo "  make phase-g1-schema                  PG DDL 적용 (1회)"
	@echo "  make phase-g1-import                  JSON → PG UPSERT (dry-run)"
	@echo "  make phase-g1-import ARGS='--apply'   실제 적재"
	@echo "  make phase-g1-verify                  sample query equality + Gate 3"
	@echo ""
	@echo "검증 통합:"
	@echo "  make phase-g-verify                   모든 sprint G.* sample equality"
	@echo ""
	@echo "Sprint G.2-4 (예정): phase-g2/3/4-{schema,import,verify}"

phase-g1-schema:
	@cd '$(BACKEND_DIR)' && DATABASE_URL='$(DATABASE_URL)' \
	  '$(VENV_PY)' -c "import os; from sqlalchemy import create_engine; \
	    e = create_engine(os.environ['DATABASE_URL']); \
	    ddl = open('$(PHASE_G_DIR)/pg-sync-scripts/schema_guide_domain_incompatibilities.sql', encoding='utf-8').read(); \
	    conn = e.raw_connection(); cur = conn.cursor(); cur.execute(ddl); conn.commit(); conn.close(); \
	    print('Schema applied')"

phase-g1-import:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' PYTHONIOENCODING=utf-8 \
	  '$(VENV_PY)' -u '$(PHASE_G_DIR)/pg-sync-scripts/import_domain_incompatibilities_to_pg.py' $(ARGS)

# SHE 패턴(phase3c proposals.json) → PG she_catalog UPSERT (ON CONFLICT DO NOTHING).
# 배포 재현: main pull 후 1회 실행해야 패턴이 실서비스(PG)에 반영. 자세히: docs/deliverables/airgap-deploy-runbook.md
#   make she-import                                        dry-run
#   make she-import ARGS='--apply --status approved_auto'  실제 적재
she-import:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' PYTHONIOENCODING=utf-8 \
	  '$(VENV_PY)' -u scripts/import_she_phase3c_to_pg.py $(ARGS)

phase-g1-verify:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' PYTHONIOENCODING=utf-8 \
	  '$(VENV_PY)' -u '$(PHASE_G_DIR)/validation-scripts/sample_query_equality.py' --sprint g1

phase-g-verify:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  DATABASE_URL='$(DATABASE_URL)' PYTHONIOENCODING=utf-8 \
	  '$(VENV_PY)' -u '$(PHASE_G_DIR)/validation-scripts/sample_query_equality.py' --sprint all


# ---------------------------------------------------------------------------
# 코드 어휘 정합성 하드게이트 (Phase 5 재발 방지)
# catalog ↔ SR ↔ CI ↔ GUIDE ↔ ontology 정합 감사 + KOSHA-22 CamelCase 단일화 강제.
# CRITICAL(온톨로지 UPPER/dual-URI) 발견 시 exit 1 → CI에서 어휘 드리프트 차단.
# ---------------------------------------------------------------------------

ONT_SCRIPTS := $(ROOT)/ontology-team/06-reasoning/ontology/scripts
ONT_DIR := $(ROOT)/ontology-team/06-reasoning/ontology

verify-codes:
	@echo "[verify-codes] 코드 어휘 정합성 하드게이트 (온톨로지 UPPER/dual-URI 재발 차단)"
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  PYTHONIOENCODING=utf-8 '$(VENV_PY)' '$(ROOT)/scripts/audit_code_consistency.py' --gate

# 선언적 보완재 — ABox 코드 IRI ∈ KOSHA-22 정본 SHACL allowlist (pyshacl). 비정본 IRI 시 exit 1.
verify-codes-shape:
	@echo "[verify-codes-shape] ABox 코드 IRI ∈ canonical SHACL 검증 (pyshacl)"
	@PYTHONIOENCODING=utf-8 '$(VENV_PY)' '$(ONT_SCRIPTS)/validate_canonical_codes.py' --gate

# prefix/namespace 정본 가드레일 — 온톨로지팀 .ttl 전수 @prefix/sh:prefixes 검증. 비정본 시 exit 1.
verify-prefixes:
	@echo "[verify-prefixes] 온톨로지 .ttl prefix 정본 표준 검증 (canonical short name + IRI)"
	@PYTHONIOENCODING=utf-8 '$(VENV_PY)' '$(ONT_SCRIPTS)/validate_prefixes.py'

# assembly manifest — '무엇이 온톨로지인가' 단일 정본. SSOT(assembly/manifest_source.py) → JSON.
gen-manifest:
	@PYTHONIOENCODING=utf-8 '$(VENV_PY)' '$(ONT_DIR)/assembly/gen_manifest.py'

# manifest 정합 가드레일 — dir의 모든 파일이 단일 정본에 등록(silent orphan 0) + freshness. 위반 시 exit 1.
verify-manifest:
	@echo "[verify-manifest] assembly manifest 정합 (single source of truth)"
	@PYTHONIOENCODING=utf-8 '$(VENV_PY)' '$(ONT_SCRIPTS)/validate_manifest.py'

# SSOT 변경(canonical-code-vocabulary.json) 시 shape 재생성. 산출물은 git tracked.
gen-canonical-shape:
	@PYTHONIOENCODING=utf-8 '$(VENV_PY)' '$(ONT_SCRIPTS)/gen_canonical_code_shape.py'

# Layer 4.7 Continual — pending/UNKNOWN open-class 코드 승격 후보 추적 (live PG 빈도, 읽기전용).
# gate WARN을 빈도 랭킹 + tier(PROMOTE/WATCH/NOISE) queue로 형식화. 자세히: docs/dev-notes/phase5-incremental-guardrails.md
continual-pending:
	@cd '$(BACKEND_DIR)' && set -a && [ -f .env ] && . .env || true; set +a; \
	  PYTHONIOENCODING=utf-8 '$(VENV_PY)' '$(F1_SCRIPTS)/continual_pending_promotion.py' $(ARGS)

# 데이터 적재 커버리지 진단 — TBox엔 있으나 ABox 데이터(인스턴스/사용) 0인 클래스·property 검출.
# F5/SHE형 "스키마 있는데 데이터 미적재" 갭을 상시 탐지(우선 triage = app/rule-head/facet-fine 제외).
# 진단용(게이트 아님, exit 0). 전체 ABox 로드라 수 분 소요.
data-coverage:
	@echo "[data-coverage] 스키마-데이터 커버리지 진단 (빈 클래스 / dormant property)"
	@PYTHONIOENCODING=utf-8 '$(VENV_PY)' '$(ONT_SCRIPTS)/check_data_coverage.py'
