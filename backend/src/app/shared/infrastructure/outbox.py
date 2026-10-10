"""Transactional Outbox + relay.

Events are inserted into `outbox` in the same transaction as the aggregate change
(guaranteeing no lost or phantom events). A relay publishes them asynchronously,
at-least-once; consumers must therefore be idempotent (dedupe by event_id).
"""

from __future__ import annotations

import asyncio
import dataclasses
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import JSON, Column, DateTime, Index, Integer, String, Table, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.domain.model import DomainEvent, utcnow
from app.shared.infrastructure.db import BinaryUUID, metadata

log = structlog.get_logger(__name__)

outbox_table = Table(
    "outbox",
    metadata,
    Column("event_id", BinaryUUID, primary_key=True),
    Column("tenant_id", BinaryUUID, nullable=False),
    Column("event_type", String(120), nullable=False),
    Column("event_version", Integer, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("occurred_at", DateTime(timezone=False), nullable=False),
    Column("published_at", DateTime(timezone=False), nullable=True),
    Column("attempts", Integer, nullable=False, default=0),
    Index("ix_outbox_unpublished", "published_at", "occurred_at"),
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def to_outbox_row(event: DomainEvent) -> dict[str, Any]:
    payload = {f.name: _jsonable(getattr(event, f.name)) for f in dataclasses.fields(event)}
    return {
        "event_id": event.event_id,
        "tenant_id": event.tenant_id,
        "event_type": event.event_type,
        "event_version": event.event_version,
        "payload": payload,
        "occurred_at": event.occurred_at.replace(tzinfo=None),
        "attempts": 0,
    }


async def append_to_outbox(session: AsyncSession, events: list[DomainEvent]) -> None:
    if events:
        await session.execute(insert(outbox_table), [to_outbox_row(e) for e in events])


EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    """In-process pub/sub (Observer). Swap for Kafka/SNS/RabbitMQ by adding a publisher handler."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        for handler in self._handlers.get(event_type, []):
            await handler(payload)


class OutboxRelay:
    """Polls unpublished events and dispatches them. Safe to run on many replicas:
    `FOR UPDATE SKIP LOCKED` lets each replica claim a disjoint batch."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        bus: EventBus,
        *,
        batch_size: int = 100,
        max_attempts: int = 10,
    ) -> None:
        self._sf = session_factory
        self._bus = bus
        self._batch = batch_size
        self._max_attempts = max_attempts

    async def run_once(self) -> int:
        async with self._sf() as session, session.begin():
            rows = (
                (
                    await session.execute(
                        select(outbox_table)
                        .where(outbox_table.c.published_at.is_(None))
                        .where(outbox_table.c.attempts < self._max_attempts)
                        .order_by(outbox_table.c.occurred_at)
                        .limit(self._batch)
                        .with_for_update(skip_locked=True)
                    )
                )
                .mappings()
                .all()
            )
            published = 0
            for row in rows:
                try:
                    await self._bus.publish(row["event_type"], dict(row["payload"]))
                except Exception:  # one poison event must not block the batch
                    log.exception("outbox.publish_failed", event_id=str(row["event_id"]))
                    await session.execute(
                        update(outbox_table)
                        .where(outbox_table.c.event_id == row["event_id"])
                        .values(attempts=outbox_table.c.attempts + 1)
                    )
                    continue
                await session.execute(
                    update(outbox_table)
                    .where(outbox_table.c.event_id == row["event_id"])
                    .values(published_at=utcnow().replace(tzinfo=None))
                )
                published += 1
            return published

    async def run_forever(self, *, interval_s: float = 0.5) -> None:
        while True:
            try:
                if await self.run_once() == 0:
                    await asyncio.sleep(interval_s)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("outbox.relay_error")
                await asyncio.sleep(interval_s * 4)
