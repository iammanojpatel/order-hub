"""In-memory test doubles for the application ports (fast, deterministic unit tests)."""

from __future__ import annotations

import copy
import uuid
from types import TracebackType
from typing import Self

from app.catalog.domain.model import Product, Sku
from app.shared.domain.errors import ConcurrencyError
from app.shared.domain.model import DomainEvent


class InMemoryProductRepository:
    def __init__(self, store: dict[uuid.UUID, Product], tenant_id: uuid.UUID) -> None:
        self._store = store
        self._tenant_id = tenant_id
        self.seen: set[Product] = set()

    async def add(self, product: Product) -> None:
        self.seen.add(product)
        self._store[product.id] = copy.deepcopy(product)

    async def get(self, product_id: uuid.UUID) -> Product | None:
        p = self._store.get(product_id)
        if p is None or p.tenant_id != self._tenant_id:
            return None
        clone = copy.deepcopy(p)
        self.seen.add(clone)
        return clone

    async def get_by_sku(self, sku: Sku) -> Product | None:
        for p in self._store.values():
            if p.tenant_id == self._tenant_id and p.sku == sku:
                return copy.deepcopy(p)
        return None

    async def update(self, product: Product) -> None:
        current = self._store[product.id]
        if current.version != product.version:
            raise ConcurrencyError("stale")
        product.version += 1
        self.seen.add(product)
        self._store[product.id] = copy.deepcopy(product)

    async def list_page(self, *, after: uuid.UUID | None, limit: int) -> list[Product]:
        items = sorted(
            (p for p in self._store.values() if p.tenant_id == self._tenant_id),
            key=lambda p: p.id,
            reverse=True,  # newest first, like the SQL adapter
        )
        if after:
            items = [p for p in items if p.id < after]
        return [copy.deepcopy(p) for p in items[:limit]]


class InMemoryIdempotencyStore:
    def __init__(self, store: dict[tuple[uuid.UUID, str], uuid.UUID], tenant_id: uuid.UUID) -> None:
        self._store = store
        self._tenant_id = tenant_id

    async def get(self, key: str) -> uuid.UUID | None:
        return self._store.get((self._tenant_id, key))

    async def save(self, key: str, resource_id: uuid.UUID) -> None:
        self._store[(self._tenant_id, key)] = resource_id


class FakeDatabase:
    """Shared state across UoW instances (simulates one database, many tenants)."""

    def __init__(self) -> None:
        self.products: dict[uuid.UUID, Product] = {}
        self.idempotency: dict[tuple[uuid.UUID, str], uuid.UUID] = {}
        self.published: list[DomainEvent] = []

    def uow(self, tenant_id: uuid.UUID) -> FakeUnitOfWork:
        return FakeUnitOfWork(self, tenant_id)


class FakeUnitOfWork:
    def __init__(self, db: FakeDatabase, tenant_id: uuid.UUID) -> None:
        self._db = db
        self.products = InMemoryProductRepository(db.products, tenant_id)
        self.idempotency = InMemoryIdempotencyStore(db.idempotency, tenant_id)
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        for agg in self.products.seen:
            self._db.published.extend(agg.pull_events())
        self.committed = True

    async def rollback(self) -> None:
        return None
