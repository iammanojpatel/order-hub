# 3. Transactional outbox for domain events

- Status: Accepted
- Date: 2026-10-10

## Context
State changes and the events announcing them must never diverge. If we publish without saving, we emit phantom events. If we save without publishing, events are lost.

## Decision
The Unit of Work inserts recorded domain events into an `outbox` table **in the same transaction** as the aggregate change. `OutboxRelay` polls with `SELECT … FOR UPDATE SKIP LOCKED` (safe across replicas), dispatches to subscribers and marks rows published. Delivery is **at-least-once**, so consumers dedupe by `event_id`. Poison events are retried up to `max_attempts` without blocking the batch.

## Consequences
Exactly-once *effects* need idempotent consumers. Throughput is bounded by polling. If needed, switch to CDC (Debezium reading the binlog), which needs no code changes in the domain.
