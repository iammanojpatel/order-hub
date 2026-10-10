"""Mint a short-lived dev JWT for local testing, k6 and Bruno.

Usage: uv run python scripts/dev_token.py [--tenant UUID] [--roles editor,viewer] [--ttl 3600]
"""

import argparse
import time
import uuid

import jwt

from app.config import get_settings

DEFAULT_TENANT = "00000000-0000-7000-8000-000000000001"


def mint(tenant: str = DEFAULT_TENANT, roles: str = "admin", ttl: int = 3600) -> str:
    settings = get_settings()
    if settings.env == "production":
        raise SystemExit("Refusing to mint tokens in production")
    now = int(time.time())
    return jwt.encode(
        {
            "sub": "dev-user",
            "tid": str(uuid.UUID(tenant)),
            "roles": roles.split(","),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + ttl,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", default=DEFAULT_TENANT)
    parser.add_argument("--roles", default="admin")
    parser.add_argument("--ttl", type=int, default=3600)
    args = parser.parse_args()
    print(mint(args.tenant, args.roles, args.ttl))  # noqa: T201


if __name__ == "__main__":
    main()
