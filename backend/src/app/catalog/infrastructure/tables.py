"""Catalog persistence schema (SQLAlchemy Core). Mapped explicitly by the repository
(Data Mapper pattern) so the domain model stays free of ORM concerns."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    func,
)

from app.shared.infrastructure.db import BinaryUUID, metadata

products_table = Table(
    "products",
    metadata,
    Column("id", BinaryUUID, nullable=False),
    Column("tenant_id", BinaryUUID, nullable=False),
    Column("sku", String(32), nullable=False),
    Column("name", String(200), nullable=False),
    Column("price_amount", Numeric(14, 2), nullable=False),
    Column("price_currency", String(3), nullable=False),
    Column("status", String(20), nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    ),
    PrimaryKeyConstraint("id"),
    UniqueConstraint("tenant_id", "sku"),  # SKU unique per tenant, not globally
    Index("ix_products_tenant_id_id", "tenant_id", "id"),  # tenant-scoped cursor pagination
    CheckConstraint("price_amount > 0", name="price_positive"),
)

idempotency_keys_table = Table(
    "idempotency_keys",
    metadata,
    Column("tenant_id", BinaryUUID, nullable=False),
    Column("idempotency_key", String(100), nullable=False),
    Column("resource_id", BinaryUUID, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    PrimaryKeyConstraint("tenant_id", "idempotency_key"),
)
