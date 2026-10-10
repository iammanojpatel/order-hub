# 2. Modular monolith with hexagonal, DDD-structured bounded contexts

- Status: Accepted
- Date: 2026-10-10

## Context and drivers
We need fast delivery now and the option to scale or deploy parts independently later. We want testability without I/O, and clear ownership boundaries for humans and AI agents.

## Options considered
1. **Microservices from day one.** Pros: independent scaling and deploys. Cons: distributed-systems tax (network failures, consistency, ops) before product-market fit.
2. **Layered monolith (by technical layer).** Pros: simple. Cons: business rules leak across features, and it is hard to split later.
3. **Modular monolith: one module per bounded context, hexagonal layers inside.** Pros: strong boundaries, a single deploy, extractable later. Cons: needs discipline, which import-linter enforces.

## Decision
Option 3. Each context has `domain` / `application` / `infrastructure` / `api`. Dependencies point inward, and the domain is framework-free. Contexts communicate via **domain events through the outbox** or via application services, never via each other's tables.

## Consequences
- Unit tests run in milliseconds against pure domain code and in-memory fakes.
- A context can be extracted into a service by replacing the in-process event bus with a broker. The outbox already guarantees delivery.
- More files per feature than a CRUD app. This is accepted for the clarity it buys.
