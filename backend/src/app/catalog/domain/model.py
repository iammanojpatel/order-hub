"""Catalog bounded context — Product aggregate, value objects and domain events."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar

from app.shared.domain.errors import DomainError
from app.shared.domain.model import AggregateRoot, DomainEvent, new_id

_SKU_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,31}$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
MAX_NAME_LENGTH = 200
MAX_DECIMAL_PLACES = 2


# ── Value objects (immutable, equality by value, self-validating) ──────────────
@dataclass(frozen=True, slots=True)
class Sku:
    value: str

    def __post_init__(self) -> None:
        if not _SKU_PATTERN.fullmatch(self.value):
            raise DomainError(f"Invalid SKU '{self.value}': use 3-32 chars A-Z, 0-9, '-'")


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not _CURRENCY_PATTERN.fullmatch(self.currency):
            raise DomainError(f"Invalid ISO-4217 currency '{self.currency}'")
        if self.amount.as_tuple().exponent < -MAX_DECIMAL_PLACES:  # type: ignore[operator]
            raise DomainError("Money supports at most 2 decimal places")

    def is_positive(self) -> bool:
        return self.amount > 0


class ProductStatus(StrEnum):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"


# ── Domain events ──────────────────────────────────────────────────────────────
@dataclass(frozen=True, kw_only=True)
class ProductCreated(DomainEvent):
    event_type: ClassVar[str] = "catalog.product_created"
    product_id: uuid.UUID
    sku: str
    name: str
    price_amount: str
    price_currency: str


@dataclass(frozen=True, kw_only=True)
class ProductPriceChanged(DomainEvent):
    event_type: ClassVar[str] = "catalog.product_price_changed"
    product_id: uuid.UUID
    old_amount: str
    new_amount: str
    currency: str


@dataclass(frozen=True, kw_only=True)
class ProductDiscontinued(DomainEvent):
    event_type: ClassVar[str] = "catalog.product_discontinued"
    product_id: uuid.UUID


# ── Aggregate root ─────────────────────────────────────────────────────────────
class Product(AggregateRoot):
    """Invariants:
    1. name is 1..200 chars after trimming
    2. price is strictly positive
    3. a discontinued product's price cannot change
    4. currency never changes after creation
    """

    def __init__(
        self,
        *,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        sku: Sku,
        name: str,
        price: Money,
        status: ProductStatus = ProductStatus.ACTIVE,
        version: int = 0,
    ) -> None:
        super().__init__(id=id, tenant_id=tenant_id, version=version)
        self.sku = sku
        self.name = self._validated_name(name)
        self.price = price
        self.status = status

    @classmethod
    def create(cls, *, tenant_id: uuid.UUID, sku: Sku, name: str, price: Money) -> Product:
        """Factory method: the only way to bring a new Product into existence."""
        if not price.is_positive():
            raise DomainError("Price must be greater than zero")
        product = cls(id=new_id(), tenant_id=tenant_id, sku=sku, name=name, price=price)
        product._record(
            ProductCreated(
                tenant_id=tenant_id,
                product_id=product.id,
                sku=sku.value,
                name=product.name,
                price_amount=str(price.amount),
                price_currency=price.currency,
            )
        )
        return product

    def change_price(self, new_price: Money) -> None:
        if self.status is ProductStatus.DISCONTINUED:
            raise DomainError("Cannot change the price of a discontinued product")
        if new_price.currency != self.price.currency:
            raise DomainError("Currency cannot change; create a new product instead")
        if not new_price.is_positive():
            raise DomainError("Price must be greater than zero")
        if new_price == self.price:
            return  # idempotent: no state change, no event
        old = self.price
        self.price = new_price
        self._record(
            ProductPriceChanged(
                tenant_id=self.tenant_id,
                product_id=self.id,
                old_amount=str(old.amount),
                new_amount=str(new_price.amount),
                currency=new_price.currency,
            )
        )

    def discontinue(self) -> None:
        if self.status is ProductStatus.DISCONTINUED:
            return
        self.status = ProductStatus.DISCONTINUED
        self._record(ProductDiscontinued(tenant_id=self.tenant_id, product_id=self.id))

    @staticmethod
    def _validated_name(name: str) -> str:
        cleaned = name.strip()
        if not 1 <= len(cleaned) <= MAX_NAME_LENGTH:
            raise DomainError(f"Name must be 1-{MAX_NAME_LENGTH} characters")
        return cleaned
