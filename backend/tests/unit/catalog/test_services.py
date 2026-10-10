"""Unit tests — use cases with in-memory fakes: authorisation, tenancy, idempotency, concurrency."""

import uuid
from decimal import Decimal

import pytest

from app.catalog.application import services
from app.catalog.domain.model import ProductCreated, ProductPriceChanged
from app.shared.application.security import Principal
from app.shared.domain.errors import (
    ConcurrencyError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from tests.fakes import FakeDatabase

TENANT_A, TENANT_B = uuid.uuid4(), uuid.uuid4()
EDITOR_A = Principal(user_id="u1", tenant_id=TENANT_A, roles=frozenset({"editor"}))
VIEWER_A = Principal(user_id="u2", tenant_id=TENANT_A, roles=frozenset({"viewer"}))
EDITOR_B = Principal(user_id="u3", tenant_id=TENANT_B, roles=frozenset({"editor"}))


def cmd(sku: str = "SKU-001", key: str | None = None) -> services.CreateProduct:
    return services.CreateProduct(
        sku=sku, name="Mug", price_amount=Decimal("250.00"), currency="inr", idempotency_key=key
    )


@pytest.fixture
def db() -> FakeDatabase:
    return FakeDatabase()


async def test_should_create_product_and_publish_event(db: FakeDatabase) -> None:
    view = await services.create_product(cmd(), uow=db.uow(TENANT_A), actor=EDITOR_A)

    assert view.currency == "INR"
    assert [type(e) for e in db.published] == [ProductCreated]


async def test_should_forbid_viewer_from_creating(db: FakeDatabase) -> None:
    with pytest.raises(PermissionDeniedError):
        await services.create_product(cmd(), uow=db.uow(TENANT_A), actor=VIEWER_A)


async def test_should_reject_duplicate_sku_within_tenant(db: FakeDatabase) -> None:
    await services.create_product(cmd(), uow=db.uow(TENANT_A), actor=EDITOR_A)

    with pytest.raises(ConflictError):
        await services.create_product(cmd(), uow=db.uow(TENANT_A), actor=EDITOR_A)


async def test_should_allow_same_sku_in_different_tenants(db: FakeDatabase) -> None:
    await services.create_product(cmd(), uow=db.uow(TENANT_A), actor=EDITOR_A)

    view = await services.create_product(cmd(), uow=db.uow(TENANT_B), actor=EDITOR_B)

    assert view.sku == "SKU-001"


async def test_should_return_same_product_for_repeated_idempotency_key(db: FakeDatabase) -> None:
    first = await services.create_product(cmd(key="k-1"), uow=db.uow(TENANT_A), actor=EDITOR_A)
    second = await services.create_product(cmd(key="k-1"), uow=db.uow(TENANT_A), actor=EDITOR_A)

    assert first.id == second.id
    assert len(db.published) == 1


async def test_should_hide_other_tenants_products(db: FakeDatabase) -> None:
    created = await services.create_product(cmd(), uow=db.uow(TENANT_A), actor=EDITOR_A)

    with pytest.raises(NotFoundError):
        await services.get_product(created.id, uow=db.uow(TENANT_B), actor=EDITOR_B)


async def test_should_change_price_with_matching_version(db: FakeDatabase) -> None:
    created = await services.create_product(cmd(), uow=db.uow(TENANT_A), actor=EDITOR_A)

    updated = await services.change_price(
        services.ChangePrice(created.id, Decimal("300.00"), expected_version=created.version),
        uow=db.uow(TENANT_A),
        actor=EDITOR_A,
    )

    assert updated.version == created.version + 1
    assert isinstance(db.published[-1], ProductPriceChanged)


async def test_should_reject_stale_version(db: FakeDatabase) -> None:
    created = await services.create_product(cmd(), uow=db.uow(TENANT_A), actor=EDITOR_A)

    with pytest.raises(ConcurrencyError):
        await services.change_price(
            services.ChangePrice(
                created.id, Decimal("300.00"), expected_version=created.version + 5
            ),
            uow=db.uow(TENANT_A),
            actor=EDITOR_A,
        )


async def test_should_paginate_with_cursor(db: FakeDatabase) -> None:
    for i in range(5):
        await services.create_product(cmd(sku=f"SKU-00{i}"), uow=db.uow(TENANT_A), actor=EDITOR_A)

    page1 = await services.list_products(uow=db.uow(TENANT_A), actor=VIEWER_A, after=None, limit=3)
    page2 = await services.list_products(
        uow=db.uow(TENANT_A), actor=VIEWER_A, after=page1.next_cursor, limit=3
    )

    assert len(page1.items) == 3
    assert [v.id for v in page1.items] == sorted((v.id for v in page1.items), reverse=True)
    assert page1.next_cursor is not None
    assert len(page2.items) == 2
    assert page2.next_cursor is None
    assert {v.id for v in page1.items}.isdisjoint({v.id for v in page2.items})
