"""Domain/application error taxonomy — mapped to RFC 9457 Problem Details at the API edge."""


class DomainError(Exception):
    """A business rule was violated (→ 422)."""

    code = "domain_rule_violated"


class NotFoundError(DomainError):
    """Aggregate does not exist for this tenant (→ 404). Never reveals other tenants' data."""

    code = "not_found"


class ConflictError(DomainError):
    """Uniqueness or state conflict (→ 409)."""

    code = "conflict"


class ConcurrencyError(DomainError):
    """Optimistic-lock version mismatch: someone else changed it first (→ 409/412)."""

    code = "concurrent_modification"


class PermissionDeniedError(DomainError):
    """Authenticated principal lacks the required permission (→ 403)."""

    code = "forbidden"
