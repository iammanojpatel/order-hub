"""Shared fixtures: settings, JWT minting, API client wired to in-memory fakes."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Callable

import httpx
import jwt
import pytest

from app.config import Settings, get_settings
from app.main import create_app
from tests.fakes import FakeDatabase

TEST_SETTINGS = Settings(env="test", run_outbox_relay=False, log_level="WARNING")

TokenFactory = Callable[..., str]


@pytest.fixture
def make_token() -> TokenFactory:
    def _make(
        tenant_id: uuid.UUID,
        roles: tuple[str, ...] = ("editor",),
        *,
        ttl: int = 300,
        sub: str = "user-1",
    ) -> str:
        now = int(time.time())
        claims = {
            "sub": sub,
            "tid": str(tenant_id),
            "roles": list(roles),
            "iss": TEST_SETTINGS.jwt_issuer,
            "aud": TEST_SETTINGS.jwt_audience,
            "iat": now,
            "exp": now + ttl,
        }
        return jwt.encode(claims, TEST_SETTINGS.jwt_secret.get_secret_value(), algorithm="HS256")

    return _make


@pytest.fixture
def fake_db() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
async def client(fake_db: FakeDatabase) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(TEST_SETTINGS, uow_factory=fake_db.uow)
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    app.state.uow_factory = fake_db.uow  # ASGITransport does not run lifespan
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
