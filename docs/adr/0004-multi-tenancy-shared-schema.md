# 4. Multi-tenancy: shared schema with tenant_id, enforced in repositories

- Status: Accepted
- Date: 2026-10-10

## Options
1. **Shared schema, `tenant_id` column.** Pros: cheapest, simplest ops, easy cross-tenant analytics. Cons: isolation depends on code discipline.
2. **Schema-per-tenant.** Pros: stronger isolation. Cons: migrations × N, connection routing.
3. **Database-per-tenant.** Pros: strongest isolation and per-tenant backup/restore. Cons: highest cost and ops burden.

## Decision
Option 1 by default, with defence in depth:
- the tenant is derived **only** from the verified JWT (`tid`)
- `TenantScopedRepository` adds `tenant_id` to every query and refuses foreign aggregates
- `tenant_id` is part of unique keys and leading index columns
- every use case has a cross-tenant test (expects 404, which does not reveal existence)

Premium or regulated tenants can move to option 3 later behind the same repository ports.
