"""Unit tests — Product aggregate invariants and events (pure domain, no I/O)."""

import uuid
from decimal import Decimal

import pytest

from app.catalog.domain.model import (
    Money,
    Product,
    ProductCreated,
    ProductDiscontinued,
    ProductPriceChanged,
    ProductStatus,
    Sku,
)
from app.shared.domain.errors import DomainError
from app.shared.domain.model import new_id

TENANT = uuid.uuid4()


def make_product(price: str = "100.00") -> Product:
    return Product.create(
        tenant_id=TENANT,
        sku=Sku("SKU-001"),
        name="  Red T-Shirt ",
        price=Money(Decimal(price), "INR"),
    )


class TestCreate:
    def test_should_record_product_created_event(self) -> None:
        product = make_product()

        events = product.pull_events()

        assert len(events) == 1
        assert isinstance(events[0], ProductCreated)
        assert events[0].product_id == product.id
        assert events[0].tenant_id == TENANT

    def test_should_trim_name(self) -> None:
        assert make_product().name == "Red T-Shirt"

    @pytest.mark.parametrize("price", ["0", "-1.00"])
    def test_should_reject_non_positive_price(self, price: str) -> None:
        with pytest.raises(DomainError, match="greater than zero"):
            make_product(price)

    @pytest.mark.parametrize("name", ["", "   ", "x" * 201])
    def test_should_reject_invalid_name(self, name: str) -> None:
        with pytest.raises(DomainError, match="Name"):
            Product.create(
                tenant_id=TENANT, sku=Sku("SKU-001"), name=name, price=Money(Decimal(1), "INR")
            )


class TestValueObjects:
    @pytest.mark.parametrize("value", ["ab", "lower-case", "-STARTS-DASH", "A" * 33])
    def test_should_reject_invalid_sku(self, value: str) -> None:
        with pytest.raises(DomainError):
            Sku(value)

    def test_should_reject_more_than_two_decimals(self) -> None:
        with pytest.raises(DomainError):
            Money(Decimal("1.001"), "INR")

    def test_money_equality_is_by_value(self) -> None:
        assert Money(Decimal("1.50"), "INR") == Money(Decimal("1.50"), "INR")


class TestChangePrice:
    def test_should_change_price_and_record_event(self) -> None:
        product = make_product()
        product.pull_events()

        product.change_price(Money(Decimal("120.00"), "INR"))

        assert product.price.amount == Decimal("120.00")
        (event,) = product.pull_events()
        assert isinstance(event, ProductPriceChanged)
        assert (event.old_amount, event.new_amount) == ("100.00", "120.00")

    def test_should_be_idempotent_for_same_price(self) -> None:
        product = make_product()
        product.pull_events()

        product.change_price(Money(Decimal("100.00"), "INR"))

        assert product.pull_events() == []

    def test_should_reject_currency_change(self) -> None:
        with pytest.raises(DomainError, match="Currency"):
            make_product().change_price(Money(Decimal("5.00"), "USD"))

    def test_should_reject_price_change_when_discontinued(self) -> None:
        product = make_product()
        product.discontinue()

        with pytest.raises(DomainError, match="discontinued"):
            product.change_price(Money(Decimal("90.00"), "INR"))


class TestDiscontinue:
    def test_should_discontinue_once(self) -> None:
        product = make_product()
        product.pull_events()

        product.discontinue()
        product.discontinue()

        assert product.status is ProductStatus.DISCONTINUED
        assert [type(e) for e in product.pull_events()] == [ProductDiscontinued]


def test_new_id_is_uuid_v7_and_time_ordered() -> None:
    ids = [new_id() for _ in range(1000)]
    assert all(i.version == 7 for i in ids)
    assert ids == sorted(ids)
