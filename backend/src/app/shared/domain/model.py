"""Domain building blocks: identities, aggregate roots and domain events.

Pure Python — no framework imports (enforced by import-linter).
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar

_id_lock = threading.Lock()
_last_ms = 0
_counter = 0
_MAX_COUNTER = 0x0FFF  # 12-bit rand_a field


def new_id() -> uuid.UUID:
    """Generate a monotonic, time-ordered UUIDv7 (RFC 9562, method 1: 12-bit counter).

    Time ordering keeps InnoDB clustered-index inserts sequential (no page splits)
    and makes IDs usable as stable keyset-pagination cursors. Thread-safe.
    """
    global _last_ms, _counter  # noqa: PLW0603
    with _id_lock:
        unix_ms = time.time_ns() // 1_000_000
        if unix_ms <= _last_ms:
            _counter += 1
            if _counter > _MAX_COUNTER:  # counter overflow: borrow the next millisecond
                _last_ms += 1
                _counter = 0
            unix_ms = _last_ms
        else:
            _last_ms, _counter = unix_ms, int.from_bytes(os.urandom(1), "big")
        counter = _counter
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFF_FFFF_FFFF_FFFF
    value = (unix_ms & 0xFFFF_FFFF_FFFF) << 80
    value |= 0x7 << 76  # version 7
    value |= counter << 64  # rand_a used as monotonic counter
    value |= 0b10 << 62  # RFC 9562 variant
    value |= rand_b
    return uuid.UUID(int=value)


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Immutable fact that happened in the domain. Past-tense names, versioned payloads."""

    event_type: ClassVar[str] = "domain_event"
    event_version: ClassVar[int] = 1

    tenant_id: uuid.UUID
    event_id: uuid.UUID = field(default_factory=new_id)
    occurred_at: datetime = field(default_factory=utcnow)


class AggregateRoot:
    """Consistency boundary. Records domain events; the Unit of Work persists them
    to the transactional outbox in the same DB transaction as the state change."""

    def __init__(self, *, id: uuid.UUID, tenant_id: uuid.UUID, version: int = 0) -> None:
        self.id = id
        self.tenant_id = tenant_id
        self.version = version  # optimistic-locking token
        self._events: list[DomainEvent] = []

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events

    def __eq__(self, other: object) -> bool:
        return (
            type(other) is type(self) and isinstance(other, AggregateRoot) and other.id == self.id
        )

    def __hash__(self) -> int:
        return hash(self.id)
