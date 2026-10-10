"""MySQL adapters for the catalog ports. Every query is tenant-scoped by construction."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.domain.model import Money, Product, ProductStatus, Sku
from app.catalog.infrastructure.tables import idempotency_keys_table, products_table
from app.shared.domain.errors import ConcurrencyError, ConflictError
from app.shared.domain.model import AggregateRoot

_p = products_table.c


class TenantScopedRepository:
    """Base class: binds a session + tenant, and tracks aggregates seen in this UoW
    (so the UoW can collect their domain events on commit)."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self.seen: set[AggregateRoot] = set()

    def _track(self, aggregate: AggregateRoot) -> None:
        if aggregate.tenant_id != self._tenant_id:  # defence in depth against tenant leaks
            msg = "Aggregate belongs to another tenant"
            raise PermissionError(msg)
        self.seen.add(aggregate)


class SqlProductRepository(TenantScopedRepository):
    async def add(self, product: Product) -> None:
        self._track(product)
        try:
            await self._session.execute(insert(products_table).values(**_to_row(product)))
        except IntegrityError as exc:
            raise ConflictError(f"SKU '{product.sku.value}' already exists") from exc

    async def get(self, product_id: uuid.UUID) -> Product | None:
        row = (
            (
                await self._session.execute(
                    select(products_table).where(
                        and_(_p.tenant_id == self._tenant_id, _p.id == product_id)
                    )
                )
            )
            .mappings()
            .first()
        )
        return self._hydrate(row)

    async def get_by_sku(self, sku: Sku) -> Product | None:
        row = (
            (
                await self._session.execute(
                    select(products_table).where(
                        and_(_p.tenant_id == self._tenant_id, _p.sku == sku.value)
                    )
                )
            )
            .mappings()
            .first()
        )
        return self._hydrate(row)

    async def update(self, product: Product) -> None:
        """Optimistic Offline Lock: the UPDATE only matches the version we read."""
        self._track(product)
        result = await self._session.execute(
            update(products_table)
            .where(
                and_(
                    _p.tenant_id == self._tenant_id,
                    _p.id == product.id,
                    _p.version == product.version,
                )
            )
            .values(
                name=product.name,
                price_amount=product.price.amount,
                price_currency=product.price.currency,
                status=product.status.value,
                version=product.version + 1,
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConcurrencyError("Product was modified concurrently")
        product.version += 1

    async def list_page(self, *, after: uuid.UUID | None, limit: int) -> list[Product]:
        stmt = select(products_table).where(_p.tenant_id == self._tenant_id)
        if after is not None:
            stmt = stmt.where(_p.id < after)  # UUIDv7 is time-ordered → stable keyset pagination
        rows = (
            (await self._session.execute(stmt.order_by(_p.id.desc()).limit(limit))).mappings().all()
        )
        return [p for r in rows if (p := self._hydrate(r)) is not None]

    def _hydrate(self, row: Any) -> Product | None:
        if row is None:
            return None
        product = Product(
            id=row["id"],
            tenant_id=row["tenant_id"],
            sku=Sku(row["sku"]),
            name=row["name"],
            price=Money(Decimal(row["price_amount"]), row["price_currency"]),
            status=ProductStatus(row["status"]),
            version=row["version"],
        )
        self._track(product)
        return product


def _to_row(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "tenant_id": product.tenant_id,
        "sku": product.sku.value,
        "name": product.name,
        "price_amount": product.price.amount,
        "price_currency": product.price.currency,
        "status": product.status.value,
        "version": product.version,
    }


class SqlIdempotencyStore:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def get(self, key: str) -> uuid.UUID | None:
        c = idempotency_keys_table.c
        value = (
            await self._session.execute(
                select(c.resource_id).where(
                    and_(c.tenant_id == self._tenant_id, c.idempotency_key == key)
                )
            )
        ).scalar_one_or_none()
        return value if isinstance(value, uuid.UUID) else None

    async def save(self, key: str, resource_id: uuid.UUID) -> None:
        await self._session.execute(
            insert(idempotency_keys_table).values(
                tenant_id=self._tenant_id, idempotency_key=key, resource_id=resource_id
            )
        )
