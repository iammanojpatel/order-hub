"""Initial catalog schema: products, idempotency_keys, outbox.

Revision ID: 0001
Revises:
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = mysql.BINARY(16)
TABLE_OPTS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", UUID, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("sku", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("price_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("price_currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_id_sku"),
        sa.CheckConstraint("price_amount > 0", name="ck_products_price_positive"),
        **TABLE_OPTS,
    )
    op.create_index("ix_products_tenant_id_id", "products", ["tenant_id", "id"])

    op.create_table(
        "idempotency_keys",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("resource_id", UUID, nullable=False),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()
        ),
        sa.PrimaryKeyConstraint("tenant_id", "idempotency_key", name="pk_idempotency_keys"),
        **TABLE_OPTS,
    )

    op.create_table(
        "outbox",
        sa.Column("event_id", UUID, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("event_version", sa.Integer, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("event_id", name="pk_outbox"),
        **TABLE_OPTS,
    )
    op.create_index("ix_outbox_unpublished", "outbox", ["published_at", "occurred_at"])


def downgrade() -> None:
    op.drop_table("outbox")
    op.drop_table("idempotency_keys")
    op.drop_table("products")
