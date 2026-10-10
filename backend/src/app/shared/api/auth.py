"""Authentication at the edge: bearer JWT → Principal (user, tenant, roles).

The tenant comes ONLY from the verified token, never from the request body or path.
"""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.shared.application.security import Principal

_bearer = HTTPBearer(auto_error=False)


def get_principal(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    if creds is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = jwt.decode(
            creds.credentials,
            settings.jwt_secret.get_secret_value(),
            algorithms=settings.jwt_algorithms,
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "tid"]},
        )
        return Principal(
            user_id=str(claims["sub"]),
            tenant_id=uuid.UUID(str(claims["tid"])),
            roles=frozenset(claims.get("roles", [])),
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid token", headers={"WWW-Authenticate": "Bearer"}
        ) from exc


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
