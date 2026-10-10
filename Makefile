# ─────────────────────────────────────────────────────────────────────────────
#  One command per SDLC activity. Claude Code and CI call these same targets.
#  `make help` lists everything.
# ─────────────────────────────────────────────────────────────────────────────
SHELL := /bin/bash
.DEFAULT_GOAL := help
BE := cd backend &&
FE := cd frontend &&
DB_URL ?= mysql+asyncmy://app:app@127.0.0.1:3306/app
TEST_DB_URL ?= mysql+asyncmy://app:app@127.0.0.1:3306/app_test
TOKEN = $$(cd $(CURDIR)/backend && uv run python scripts/dev_token.py 2>/dev/null)

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

# ── Setup ───────────────────────────────────────────────────────────────────
setup: ## Install all deps + git hooks
	$(BE) uv sync
	$(FE) pnpm install
	$(FE) pnpm exec playwright install chromium
	pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
	@test -f .env || cp .env.example .env

# ── Run ─────────────────────────────────────────────────────────────────────
up: ## Start MySQL (Docker) and wait until healthy
	docker compose up -d --wait mysql

up-all: ## Start full stack in containers (mysql + api + web)
	API_TOKEN=$(TOKEN) docker compose --profile full up -d --build --wait

down: ## Stop containers
	docker compose --profile full down

migrate: ## Apply DB migrations
	$(BE) APP_DATABASE_URL=$(DB_URL) uv run alembic upgrade head

migration: ## Create a migration: make migration m="add orders table"
	$(BE) APP_DATABASE_URL=$(DB_URL) uv run alembic revision --autogenerate -m "$(m)"

dev-api: ## Run API with hot reload on :8000
	$(BE) uv run uvicorn app.main:app --reload --port 8000

dev-web: ## Run Next.js dev server on :3000
	$(FE) API_TOKEN=$(TOKEN) pnpm dev

seed: ## Seed demo data through the API (API must be running)
	$(BE) uv run python scripts/seed.py --count 500

token: ## Print a dev JWT (admin, default tenant)
	@$(BE) uv run python scripts/dev_token.py

# ── Quality gates ───────────────────────────────────────────────────────────
lint: ## Lint + format check (backend + frontend)
	$(BE) uv run ruff check . && uv run ruff format --check .
	$(FE) pnpm lint && pnpm format:check

typecheck: ## Static types (mypy --strict, tsc)
	$(BE) uv run mypy
	$(FE) pnpm typecheck

arch: ## Architecture fitness functions (layering rules)
	$(BE) uv run lint-imports

check-fast: lint typecheck arch test-unit ## Fast gate used by the Claude Code Stop hook

check: check-fast ## Full static gate

# ── Tests ───────────────────────────────────────────────────────────────────
test-unit: ## Unit + API tests (no Docker), frontend unit tests
	$(BE) uv run pytest tests/unit tests/api -q -n auto
	$(FE) pnpm test

test-integration: ## Integration tests vs real MySQL (uses TEST_DB_URL, or Testcontainers if unset)
	$(BE) APP_TEST_DATABASE_URL=$(TEST_DB_URL) uv run pytest tests/integration -q

test-contract: ## OpenAPI contract tests (Schemathesis)
	$(BE) uv run pytest tests/contract -q

test-e2e: ## Playwright system tests (needs `make up migrate` + running api)
	$(FE) API_TOKEN=$(TOKEN) pnpm e2e

coverage: ## Backend coverage report (fails under 80 %)
	$(BE) APP_TEST_DATABASE_URL=$(TEST_DB_URL) uv run pytest --cov --cov-report=term --cov-report=html -q

mutation: ## Mutation testing on the domain layer
	$(BE) uv run mutmut run

test-all: test-unit test-integration test-contract test-e2e perf-smoke ## Entire test pyramid

# ── Performance ─────────────────────────────────────────────────────────────
perf-smoke: ## k6 smoke (1 VU, 30 s)
	TOKEN=$(TOKEN) k6 run perf/k6/smoke.js

perf-load: ## k6 load at TARGET_RPS (default 200) with SLO thresholds
	TOKEN=$(TOKEN) k6 run perf/k6/load.js

perf-stress: ## k6 stress + spike
	TOKEN=$(TOKEN) k6 run perf/k6/stress.js

perf-soak: ## k6 soak (default 1 h)
	TOKEN=$(TOKEN) k6 run perf/k6/soak.js

lighthouse: ## Lighthouse CI against the running web app
	npx -y @lhci/cli@0.15 autorun --collect.url=http://localhost:3000/products

# ── Security ────────────────────────────────────────────────────────────────
security: ## SAST + secrets + dependency + filesystem vuln scans
	semgrep scan --config p/owasp-top-ten --config p/python --config p/typescript --config p/secrets --error --quiet
	gitleaks detect --no-banner --redact
	$(BE) uv export --frozen --no-emit-project --format requirements-txt -o /tmp/reqs.txt -q && uv run pip-audit --strict --disable-pip -r /tmp/reqs.txt --progress-spinner off
	$(FE) pnpm audit --audit-level high
	trivy fs --scanners vuln,misconfig,secret --severity HIGH,CRITICAL --exit-code 1 .

dast: ## OWASP ZAP baseline scan against the running API
	docker run --rm --network host -v $(PWD):/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable \
	  zap-baseline.py -t http://localhost:8000/openapi.json -I -r zap-report.html

# ── Build ───────────────────────────────────────────────────────────────────
build: ## Build production images (multi-arch capable)
	docker build -t app-api:local backend
	docker build -t app-web:local frontend

scan-images: build ## Scan built images for CVEs
	trivy image --severity HIGH,CRITICAL --exit-code 1 app-api:local
	trivy image --severity HIGH,CRITICAL --exit-code 1 app-web:local

clean: ## Remove caches and build output
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache backend/htmlcov frontend/.next frontend/coverage
