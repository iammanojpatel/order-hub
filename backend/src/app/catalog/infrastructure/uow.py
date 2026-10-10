"""SQLAlchemy Unit of Work: one DB transaction per business operation, with outbox."""

from __future__ import annotations

import uuid
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.catalog.infrastructure.repository import SqlIdempotencyStore, SqlProductRepository
from app.shared.infrastructure.outbox import append_to_outbox


class SqlCatalogUnitOfWork:
    products: SqlProductRepository
    idempotency: SqlIdempotencyStore

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], tenant_id: uuid.UUID
    ) -> None:
        self._session_factory = session_factory
        self._tenant_id = tenant_id
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.products = SqlProductRepository(self._session, self._tenant_id)
        self.idempotency = SqlIdempotencyStore(self._session, self._tenant_id)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            await self.rollback()  # no-op after a successful commit
        finally:
            if self._session is not None:
                await self._session.close()
                self._session = None

    async def commit(self) -> None:
        assert self._session is not None, "UnitOfWork used outside 'async with'"
        events = [e for agg in self.products.seen for e in agg.pull_events()]
        await append_to_outbox(self._session, events)  # same transaction as state change
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()
