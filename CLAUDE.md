# Project: Order Hub

## Purpose
<!-- One paragraph: who uses this, what problem it solves, success metric. Updated by /new-project. -->

## Stack
- **Backend**: Python 3.13 · FastAPI · SQLAlchemy 2 (Core + explicit Data Mapper) · Alembic · MySQL 8.4 (asyncmy) · Pydantic v2 · structlog · uv
- **Frontend**: Next.js 16 (App Router, RSC, Server Actions) · React 19 · TypeScript strict · Zod · Vitest + Testing Library · Playwright · pnpm
- **Quality**: Ruff · mypy --strict · import-linter · ESLint · Prettier · Schemathesis · k6 · Semgrep · Gitleaks · Trivy · ZAP

## Architecture (read `docs/architecture/overview.md` and `docs/adr/` before changing structure)
Modular monolith, **one package per bounded context**, each with hexagonal layers:
```
backend/src/app/<context>/
  domain/          aggregates, value objects, domain events, repository PORTS   (pure Python)
  application/     use cases (commands/queries), UoW port, authorisation        (no frameworks)
  infrastructure/  SQLAlchemy tables, repository ADAPTERS, UoW + outbox
  api/             FastAPI router, Pydantic DTOs                                 (HTTP adapter)
backend/src/app/shared/   building blocks: AggregateRoot, errors, Principal, outbox, problem details
frontend/src/features/<feature>/  api/ (server-only loaders, server actions) · components/ · model/ (Zod) · index.ts (public API)
```
`make arch` enforces the layer rules. A failing import contract is a design error, so fix the design, never the contract.

## Conventions that matter here
- **Tenancy**: the tenant comes from the JWT `tid` claim → `Principal` → `UnitOfWork(tenant_id)` → `TenantScopedRepository`. Every query filters by tenant. Every new repository extends `TenantScopedRepository`, and every new use case gets a cross-tenant test.
- **Events**: aggregates call `self._record(Event(...))`. The UoW writes them to `outbox` on commit, and `OutboxRelay` publishes them. Subscribers are registered in `main.build_event_bus()` and must be idempotent.
- **Concurrency**: updates go through `repository.update()` (version check). The API exposes `ETag` and requires `If-Match` on mutations (412 when stale, 428 when missing).
- **Errors**: raise `DomainError` subclasses. They are mapped to RFC 9457 Problem Details in `shared/api/problems.py`. Document new status codes with `problem_responses(...)`.
- **Money**: decimal strings over the wire, `Decimal` in Python, `NUMERIC(14,2)` in MySQL. Never floats.
- **IDs**: UUIDv7 (`new_id()`) stored as `BINARY(16)`. Pagination is keyset (`cursor` = last id, newest first).
- **Migrations**: `make migration m="…"`, then review the generated file by hand. Migrations must be expand/contract and reversible (the integration tests run downgrade → upgrade).
- **Frontend**: server components by default. Data loaders live in `*.server.ts` (`import "server-only"`). Mutations use Server Actions with Zod. Import features only via `index.ts` / `server.ts`.

## Commands (always use these; CI runs the same ones)
| Goal | Command |
|---|---|
| First-time setup | `make setup up migrate` |
| Run locally | `make dev-api` + `make dev-web` (then `make seed`) |
| Fast gate (also the Stop hook) | `make check-fast` |
| All tests | `make test-all` |
| Security | `make security` · `make dast` |
| Performance | `make perf-smoke` · `make perf-load` · `make lighthouse` |
| Build images | `make build scan-images` |

## Definition of Done
Acceptance criteria proven by tests at the right level · `make check test-all security` green · coverage ≥ 80 % (domain ≥ 90 %) · no new HIGH/CRITICAL findings · perf budgets met for touched hot paths · ADR written for significant decisions · `code-reviewer` verdict APPROVE · PR opened via `/ship`.

## MCP in this project
- `mysql` connects to the **local dev DB only**. Use it to inspect schema, EXPLAIN queries and check data during debugging. Never point it at staging or production.
