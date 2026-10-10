"""Use cases (application services). Thin orchestration: authorise → load → invoke domain → commit.

Each command handler is one transaction. Queries return read DTOs, never aggregates.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.catalog.application.ports import CatalogUnitOfWork
from app.catalog.domain.model import Money, Product, ProductStatus, Sku
from app.shared.application.security import Permission, Principal
from app.shared.domain.errors import ConcurrencyError, ConflictError, NotFoundError


# ── Commands ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class CreateProduct:
    sku: str
    name: str
    price_amount: Decimal
    currency: str
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class ChangePrice:
    product_id: uuid.UUID
    new_amount: Decimal
    expected_version: int  # from If-Match / ETag → optimistic concurrency


# ── Read model ─────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class ProductView:
    id: uuid.UUID
    sku: str
    name: str
    price_amount: Decimal
    currency: str
    status: ProductStatus
    version: int

    @classmethod
    def from_aggregate(cls, p: Product) -> ProductView:
        return cls(
            id=p.id,
            sku=p.sku.value,
            name=p.name,
            price_amount=p.price.amount,
            currency=p.price.currency,
            status=p.status,
            version=p.version,
        )


@dataclass(frozen=True, slots=True)
class Page:
    items: list[ProductView]
    next_cursor: uuid.UUID | None


# ── Handlers ───────────────────────────────────────────────────────────────────
async def create_product(
    cmd: CreateProduct, *, uow: CatalogUnitOfWork, actor: Principal
) -> ProductView:
    actor.require(Permission.CATALOG_WRITE)
    async with uow:
        if cmd.idempotency_key and (existing_id := await uow.idempotency.get(cmd.idempotency_key)):
            existing = await uow.products.get(existing_id)
            if existing is None:  # pragma: no cover - defensive
                raise NotFoundError("Product not found")
            return ProductView.from_aggregate(existing)

        sku = Sku(cmd.sku.upper())
        if await uow.products.get_by_sku(sku) is not None:
            raise ConflictError(f"SKU '{sku.value}' already exists")

        product = Product.create(
            tenant_id=actor.tenant_id,
            sku=sku,
            name=cmd.name,
            price=Money(cmd.price_amount, cmd.currency.upper()),
        )
        await uow.products.add(product)
        if cmd.idempotency_key:
            await uow.idempotency.save(cmd.idempotency_key, product.id)
        await uow.commit()
        return ProductView.from_aggregate(product)


async def change_price(
    cmd: ChangePrice, *, uow: CatalogUnitOfWork, actor: Principal
) -> ProductView:
    actor.require(Permission.CATALOG_WRITE)
    async with uow:
        product = await uow.products.get(cmd.product_id)
        if product is None:
            raise NotFoundError("Product not found")
        if product.version != cmd.expected_version:
            raise ConcurrencyError("Product was modified by someone else; reload and retry")
        product.change_price(Money(cmd.new_amount, product.price.currency))
        await uow.products.update(product)
        await uow.commit()
        return ProductView.from_aggregate(product)


async def discontinue_product(
    product_id: uuid.UUID, *, uow: CatalogUnitOfWork, actor: Principal
) -> ProductView:
    actor.require(Permission.CATALOG_WRITE)
    async with uow:
        product = await uow.products.get(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        product.discontinue()
        await uow.products.update(product)
        await uow.commit()
        return ProductView.from_aggregate(product)


async def get_product(
    product_id: uuid.UUID, *, uow: CatalogUnitOfWork, actor: Principal
) -> ProductView:
    actor.require(Permission.CATALOG_READ)
    async with uow:
        product = await uow.products.get(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return ProductView.from_aggregate(product)


async def list_products(
    *, uow: CatalogUnitOfWork, actor: Principal, after: uuid.UUID | None, limit: int
) -> Page:
    actor.require(Permission.CATALOG_READ)
    async with uow:
        rows = await uow.products.list_page(after=after, limit=limit + 1)  # +1 detects next page
        has_more = len(rows) > limit
        items = [ProductView.from_aggregate(p) for p in rows[:limit]]
        return Page(items=items, next_cursor=items[-1].id if has_more and items else None)
