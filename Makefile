.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend dev-worker \
        infra infra-down test test-backend test-frontend test-e2e migrate migrate-revision \
        seed seed-catalogue lint format typecheck evaluate clean

PYTHON ?= python3
UV ?= uv
PNPM ?= pnpm
BACKEND_DIR := backend
FRONTEND_DIR := frontend

help:
	@echo "Common targets:"
	@echo "  install         Install backend and frontend dependencies"
	@echo "  dev             Start backend (:8000) and frontend (:3000) concurrently"
	@echo "  infra           Start postgres + redis via docker compose"
	@echo "  infra-down      Stop docker compose services"
	@echo "  migrate         Apply Alembic migrations"
	@echo "  seed            Seed dev organisation/user"
	@echo "  seed-catalogue  Seed the element_catalogue (Phase 1 doors/windows)"
	@echo "  test            Run backend and frontend test suites"
	@echo "  lint            Run ruff + eslint"
	@echo "  format          Run ruff format + prettier"
	@echo "  typecheck       Run mypy --strict + tsc --noEmit"
	@echo "  evaluate        Run accuracy evaluation against sample plans"

install: install-backend install-frontend

install-backend:
	cd $(BACKEND_DIR) && $(UV) sync --extra dev

install-frontend:
	cd $(FRONTEND_DIR) && $(PNPM) install

infra:
	docker compose up -d postgres redis

infra-down:
	docker compose down

dev:
	@echo "Starting backend (:8000) and frontend (:3000). Use Ctrl+C to stop."
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd $(BACKEND_DIR) && $(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd $(FRONTEND_DIR) && $(PNPM) dev

dev-worker:
	cd $(BACKEND_DIR) && $(UV) run celery -A app.workers.celery_app worker --loglevel=info

migrate:
	cd $(BACKEND_DIR) && $(UV) run alembic upgrade head

migrate-revision:
	cd $(BACKEND_DIR) && $(UV) run alembic revision --autogenerate -m "$(m)"

seed:
	cd $(BACKEND_DIR) && $(UV) run python scripts/seed_dev.py

seed-catalogue:
	cd $(BACKEND_DIR) && $(UV) run python scripts/seed_catalogue.py

test: test-backend test-frontend

test-backend:
	cd $(BACKEND_DIR) && $(UV) run pytest

test-frontend:
	cd $(FRONTEND_DIR) && $(PNPM) test

test-e2e:
	cd $(FRONTEND_DIR) && $(PNPM) exec playwright test

lint:
	cd $(BACKEND_DIR) && $(UV) run ruff check .
	cd $(FRONTEND_DIR) && $(PNPM) lint

format:
	cd $(BACKEND_DIR) && $(UV) run ruff format .
	cd $(FRONTEND_DIR) && $(PNPM) exec prettier --write .

typecheck:
	cd $(BACKEND_DIR) && $(UV) run mypy --strict app
	cd $(FRONTEND_DIR) && $(PNPM) typecheck

evaluate:
	cd $(BACKEND_DIR) && $(UV) run python scripts/evaluate.py

clean:
	rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.mypy_cache $(BACKEND_DIR)/.ruff_cache
	rm -rf $(FRONTEND_DIR)/.next $(FRONTEND_DIR)/node_modules/.cache
