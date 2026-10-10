"""Integration fixtures: a real MySQL 8.4 in Docker (Testcontainers), migrated with Alembic."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from testcontainers.community.mysql import MySqlContainer

from app.shared.infrastructure.db import create_engine, create_session_factory

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _migrate(url: str) -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()  # type: ignore[assignment]
    command.downgrade(cfg, "base")  # prove migrations are reversible…
    command.upgrade(cfg, "head")  # …and apply cleanly, on every run


@pytest.fixture(scope="session")
def mysql_url() -> Iterator[str]:
    """Use APP_TEST_DATABASE_URL when provided (CI service container / local MySQL),
    otherwise start a throwaway MySQL 8.4 with Testcontainers."""
    if url := os.environ.get("APP_TEST_DATABASE_URL"):
        _migrate(url)
        yield url
        return
    with MySqlContainer("mysql:8.4", username="app", password="app", dbname="app_test") as mysql:
        host, port = mysql.get_container_host_ip(), mysql.get_exposed_port(3306)
        url = f"mysql+asyncmy://app:app@{host}:{port}/app_test"
        _migrate(url)
        yield url


@pytest.fixture(scope="session")
async def engine(mysql_url: str) -> AsyncIterator[AsyncEngine]:
    eng = create_engine(mysql_url, pool_size=5)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session_factory(engine: AsyncEngine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield create_session_factory(engine)
    async with engine.begin() as conn:  # isolate tests: clean tables after each
        for table in ("outbox", "idempotency_keys", "products"):
            await conn.execute(text(f"DELETE FROM {table}"))  # noqa: S608 (static names)
