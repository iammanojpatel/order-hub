"""Authenticated principal and permission checks (RBAC), enforced in the application layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from app.shared.domain.errors import PermissionDeniedError


class Permission(StrEnum):
    CATALOG_READ = "catalog:read"
    CATALOG_WRITE = "catalog:write"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "viewer": frozenset({Permission.CATALOG_READ}),
    "editor": frozenset({Permission.CATALOG_READ, Permission.CATALOG_WRITE}),
    "admin": frozenset(Permission),
}


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    tenant_id: uuid.UUID
    roles: frozenset[str] = field(default_factory=frozenset)

    @property
    def permissions(self) -> frozenset[Permission]:
        granted: set[Permission] = set()
        for role in self.roles:
            granted |= ROLE_PERMISSIONS.get(role, frozenset())
        return frozenset(granted)

    def require(self, permission: Permission) -> None:
        if permission not in self.permissions:
            raise PermissionDeniedError(f"Missing permission '{permission}'")
