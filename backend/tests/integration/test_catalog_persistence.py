"""Integration tests against real MySQL: mapping, tenancy, optimistic locking, outbox, relay."""

import asyncio
import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.catalog.domain.model import Money, Product, Sku
from app.catalog.infrastructure.uow import SqlCatalogUnitOfWork
from app.shared.domain.errors import ConcurrencyError, ConflictError
from app.shared.infrastructure.outbox import EventBus, OutboxRelay, outbox_table

pytestmark = pytest.mark.integration

SF = async_sessionmaker[AsyncSession]
TENANT_A, TENANT_B = uuid.uuid4(), uuid.uuid4()


def new_product(tenant: uuid.UUID = TENANT_A, sku: str = "SKU-001") -> Product:
    return Product.create(
        tenant_id=tenant, sku=Sku(sku), name="Mug", price=Money(Decimal("10.50"), "INR")
    )


async def save(sf: SF, product: Product) -> None:
    async with SqlCatalogUnitOfWork(sf, product.tenant_id) as uow:
        await uow.products.add(product)
        await uow.commit()


async def test_round_trip_preserves_aggregate(session_factory: SF) -> None:
    product = new_product()
    await save(session_factory, product)

    async with SqlCatalogUnitOfWork(session_factory, TENANT_A) as uow:
        loaded = await uow.products.get(product.id)

    assert loaded is not None
    assert (loaded.sku, loaded.price, loaded.version) == (product.sku, product.price, 0)


async def test_other_tenant_cannot_load(session_factory: SF) -> None:
    product = new_product()
    await save(session_factory, product)

    async with SqlCatalogUnitOfWork(session_factory, TENANT_B) as uow:
        assert await uow.products.get(product.id) is None
        assert await uow.products.list_page(after=None, limit=10) == []


async def test_duplicate_sku_violates_unique_constraint(session_factory: SF) -> None:
    await save(session_factory, new_product())

    with pytest.raises(ConflictError):
        await save(session_factory, new_product())


async def test_concurrent_updates_one_wins_other_gets_conflict(session_factory: SF) -> None:
    product = new_product()
    await save(session_factory, product)

    async def change(amount: str) -> str:
        async with SqlCatalogUnitOfWork(session_factory, TENANT_A) as uow:
            p = await uow.products.get(product.id)
            assert p is not None
            await asyncio.sleep(0.05)  # widen the race window deliberately
            p.change_price(Money(Decimal(amount), "INR"))
            try:
                await uow.products.update(p)
                await uow.commit()
            except ConcurrencyError:
                return "conflict"
            return "ok"

    results = await asyncio.gather(change("11.00"), change("12.00"))

    assert sorted(results) == ["conflict", "ok"]


async def test_events_written_to_outbox_atomically_and_relayed(session_factory: SF) -> None:
    product = new_product()
    await save(session_factory, product)
    received: list[dict[str, Any]] = []
    bus = EventBus()

    async def handler(payload: dict[str, Any]) -> None:
        received.append(payload)

    bus.subscribe("catalog.product_created", handler)

    published = await OutboxRelay(session_factory, bus).run_once()

    assert published == 1
    assert received[0]["product_id"] == str(product.id)
    async with session_factory() as s:
        row = (await s.execute(select(outbox_table))).mappings().one()
    assert row["published_at"] is not None


async def test_failed_transaction_writes_no_outbox_rows(session_factory: SF) -> None:
    await save(session_factory, new_product())

    with pytest.raises(ConflictError):
        await save(session_factory, new_product())  # duplicate → rolled back

    async with session_factory() as s:
        rows = (await s.execute(select(outbox_table))).all()
    assert len(rows) == 1  # only the first product's event
