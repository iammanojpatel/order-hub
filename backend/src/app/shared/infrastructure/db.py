"""Database plumbing: metadata, custom types, async engine and session factory."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.dialects.mysql import BINARY
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.types import TypeDecorator

# Deterministic constraint names → clean, reviewable Alembic migrations
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class BinaryUUID(TypeDecorator[uuid.UUID]):
    """UUID stored as BINARY(16): half the size of CHAR(36), faster index scans."""

    impl = BINARY(16)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> bytes | None:  # noqa: ARG002
        if value is None:
            return None
        return value.bytes if isinstance(value, uuid.UUID) else uuid.UUID(str(value)).bytes

    def process_result_value(self, value: Any, dialect: Dialect) -> uuid.UUID | None:  # noqa: ARG002
        return None if value is None else uuid.UUID(bytes=bytes(value))


def create_engine(url: str, *, pool_size: int = 10, echo: bool = False) -> AsyncEngine:
    return create_async_engine(
        url,
        pool_size=pool_size,
        max_overflow=pool_size,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=echo,
        isolation_level="READ COMMITTED",  # fewer gap locks than MySQL's REPEATABLE READ default
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
