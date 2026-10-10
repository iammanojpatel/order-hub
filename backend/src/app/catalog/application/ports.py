"""Application-layer ports: Unit of Work and idempotency store."""

from __future__ import annotations

import uuid
from types import TracebackType
from typing import Protocol, Self

from app.catalog.domain.repository import ProductRepository


class IdempotencyStore(Protocol):
    """Remembers the result of a non-idempotent command keyed by a client-supplied key."""

    async def get(self, key: str) -> uuid.UUID | None: ...

    async def save(self, key: str, resource_id: uuid.UUID) -> None: ...


class CatalogUnitOfWork(Protocol):
    """Atomic business transaction. On commit, state changes AND outbox events are
    written in the same database transaction (Transactional Outbox pattern)."""

    @property
    def products(self) -> ProductRepository: ...

    @property
    def idempotency(self) -> IdempotencyStore: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
