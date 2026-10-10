"""Composition root: wires adapters to ports and builds the FastAPI application."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.catalog.api.router import UowFactory
from app.catalog.api.router import router as catalog_router
from app.catalog.infrastructure.uow import SqlCatalogUnitOfWork
from app.config import Settings, get_settings
from app.shared.api.logging import configure_logging
from app.shared.api.middleware import RequestContextMiddleware
from app.shared.api.problems import problem_responses, register_problem_handlers
from app.shared.infrastructure.db import create_engine, create_session_factory
from app.shared.infrastructure.outbox import EventBus, OutboxRelay

log = structlog.get_logger(__name__)


def build_event_bus() -> EventBus:
    """Register event subscribers here (projections, notifications, integration publishers)."""
    bus = EventBus()

    async def log_event(payload: dict[str, Any]) -> None:
        log.info("event.published", event_id=payload.get("event_id"))

    for event_type in (
        "catalog.product_created",
        "catalog.product_price_changed",
        "catalog.product_discontinued",
    ):
        bus.subscribe(event_type, log_event)
    return bus


def create_app(
    settings: Settings | None = None, *, uow_factory: UowFactory | None = None
) -> FastAPI:
    """Build the app. Pass `uow_factory` to swap persistence (e.g. in-memory fakes in tests)."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, json=settings.env != "local")

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings.database_url, pool_size=settings.db_pool_size)
        session_factory = create_session_factory(engine)
        app.state.engine = engine
        app.state.uow_factory = uow_factory or (
            lambda tenant_id: SqlCatalogUnitOfWork(session_factory, tenant_id)
        )
        relay_task: asyncio.Task[None] | None = None
        if settings.run_outbox_relay:
            relay = OutboxRelay(session_factory, build_event_bus())
            relay_task = asyncio.create_task(relay.run_forever())
        log.info("app.started", env=settings.env)
        try:
            yield
        finally:  # graceful shutdown
            if relay_task:
                relay_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await relay_task
            await engine.dispose()

    app = FastAPI(
        title="App API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.env != "production" else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "If-Match",
            "X-Correlation-ID",
        ],
        expose_headers=["ETag", "Location", "X-Correlation-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_problem_handlers(app)
    app.include_router(catalog_router)

    @app.get("/health/live", tags=["ops"])
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["ops"], responses=problem_responses(503))
    async def ready(request: Request) -> JSONResponse:
        try:
            async with request.app.state.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
