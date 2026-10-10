# Architecture overview

## C4 · System context
```mermaid
C4Context
  Person(user, "Tenant user", "Manages the product catalogue")
  System(app, "App", "Multi-tenant catalogue platform")
  System_Ext(idp, "Identity provider", "OIDC / JWT issuer")
  System_Ext(obs, "Observability", "Logs, traces, metrics")
  Rel(user, app, "Uses", "HTTPS")
  Rel(app, idp, "Validates tokens")
  Rel(app, obs, "Emits telemetry")
```

## C4 · Containers
```mermaid
flowchart LR
  B[Browser] -->|HTTPS| W[Next.js web<br/>RSC + Server Actions]
  W -->|REST /api/v1 + JWT| A[FastAPI API<br/>modular monolith]
  A -->|asyncmy| M[(MySQL 8.4<br/>InnoDB)]
  A -->|outbox relay| E{{Event bus<br/>in-process → broker later}}
  E --> S[Subscribers<br/>projections · notifications · integrations]
```

## Request flow: change price (optimistic concurrency + outbox)
```mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant API as FastAPI router
  participant UC as change_price use case
  participant P as Product aggregate
  participant R as Repository (tenant-scoped)
  participant DB as MySQL
  C->>API: PATCH /products/{id}/price  If-Match: "3"
  API->>UC: ChangePrice(expected_version=3), Principal(tenant, roles)
  UC->>UC: actor.require(catalog:write)
  UC->>R: get(id)  -- WHERE tenant_id=? AND id=?
  R->>DB: SELECT
  UC->>P: change_price(Money)
  P-->>UC: records ProductPriceChanged
  UC->>R: update(product)  -- WHERE version=3
  R->>DB: UPDATE … SET version=4
  UC->>DB: INSERT outbox(event)  (same transaction)
  UC->>DB: COMMIT
  API-->>C: 200 OK  ETag: "4"
  Note over DB: OutboxRelay later publishes the event (at-least-once)
```

## Quality attributes and how they are met
| Attribute | Mechanism | Verified by |
|---|---|---|
| Correctness | Aggregates enforce invariants; value objects self-validate | unit tests, mutation tests |
| Tenant isolation | JWT-derived tenant → tenant-scoped repositories | cross-tenant unit + integration + API tests |
| Concurrency | Optimistic locking (version), ETag / If-Match, idempotency keys | concurrent-update integration test |
| Reliability | Transactional outbox, timeouts, graceful shutdown | outbox integration tests |
| Performance | Keyset pagination, composite indexes, pooled async I/O | k6 SLO thresholds, slow-query log |
| Security | OWASP ASVS L2 controls, Problem Details without internals, headers/CSP | Semgrep, CodeQL, ZAP, Trivy, Gitleaks |
| Evolvability | Hexagonal layers, ADRs, import contracts | `make arch` |
