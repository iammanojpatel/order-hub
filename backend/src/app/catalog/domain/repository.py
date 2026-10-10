"""Repository port (interface) for the Product aggregate. Adapters live in infrastructure."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.catalog.domain.model import Product, Sku


class ProductRepository(Protocol):
    """Collection-like access to Product aggregates, always scoped to the current tenant."""

    async def add(self, product: Product) -> None: ...

    async def get(self, product_id: uuid.UUID) -> Product | None: ...

    async def get_by_sku(self, sku: Sku) -> Product | None: ...

    async def update(self, product: Product) -> None:
        """Persist changes using optimistic locking; raises ConcurrencyError on a stale version."""
        ...

    async def list_page(self, *, after: uuid.UUID | None, limit: int) -> list[Product]:
        """Newest first; `after` is the last ID of the previous page (keyset pagination)."""
        ...
