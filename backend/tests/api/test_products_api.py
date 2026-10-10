"""API tests — HTTP contract: status codes, headers, Problem Details, auth, tenancy, ETags."""

import uuid

import httpx

from tests.conftest import TokenFactory

TENANT_A, TENANT_B = uuid.uuid4(), uuid.uuid4()
BODY = {"sku": "MUG-001", "name": "Coffee Mug", "price_amount": "250.00", "currency": "INR"}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_create_returns_201_with_location_and_etag(
    client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    r = await client.post("/api/v1/products", json=BODY, headers=auth(make_token(TENANT_A)))

    assert r.status_code == 201
    assert r.headers["Location"].endswith(r.json()["id"])
    assert r.headers["ETag"] == '"0"'
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Correlation-ID" in r.headers


async def test_missing_token_returns_401_problem(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/products")

    assert r.status_code == 401
    assert r.headers["content-type"] == "application/problem+json"
    assert r.headers["WWW-Authenticate"] == "Bearer"


async def test_expired_token_returns_401(
    client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    r = await client.get("/api/v1/products", headers=auth(make_token(TENANT_A, ttl=-10)))

    assert r.status_code == 401


async def test_viewer_cannot_create(client: httpx.AsyncClient, make_token: TokenFactory) -> None:
    r = await client.post(
        "/api/v1/products", json=BODY, headers=auth(make_token(TENANT_A, ("viewer",)))
    )

    assert r.status_code == 403
    assert r.json()["status"] == 403


async def test_invalid_body_returns_422_with_field_errors(
    client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    bad = {**BODY, "price_amount": "-5", "unexpected": True}

    r = await client.post("/api/v1/products", json=bad, headers=auth(make_token(TENANT_A)))

    assert r.status_code == 422
    fields = {tuple(e["loc"])[-1] for e in r.json()["errors"]}
    assert {"price_amount", "unexpected"} <= fields


async def test_duplicate_sku_returns_409(
    client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    h = auth(make_token(TENANT_A))
    await client.post("/api/v1/products", json=BODY, headers=h)

    r = await client.post("/api/v1/products", json=BODY, headers=h)

    assert r.status_code == 409


async def test_idempotency_key_returns_same_resource(
    client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    h = {**auth(make_token(TENANT_A)), "Idempotency-Key": "abc-123"}

    first = await client.post("/api/v1/products", json=BODY, headers=h)
    second = await client.post("/api/v1/products", json=BODY, headers=h)

    assert second.json()["id"] == first.json()["id"]


async def test_cross_tenant_read_returns_404(
    client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    created = await client.post("/api/v1/products", json=BODY, headers=auth(make_token(TENANT_A)))

    r = await client.get(
        f"/api/v1/products/{created.json()['id']}", headers=auth(make_token(TENANT_B))
    )

    assert r.status_code == 404


async def test_change_price_requires_if_match(
    client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    h = auth(make_token(TENANT_A))
    pid = (await client.post("/api/v1/products", json=BODY, headers=h)).json()["id"]

    r = await client.patch(
        f"/api/v1/products/{pid}/price", json={"price_amount": "300.00"}, headers=h
    )

    assert r.status_code == 428


async def test_change_price_with_stale_etag_returns_412(
    client: httpx.AsyncClient, make_token: TokenFactory
) -> None:
    h = auth(make_token(TENANT_A))
    pid = (await client.post("/api/v1/products", json=BODY, headers=h)).json()["id"]
    ok = await client.patch(
        f"/api/v1/products/{pid}/price",
        json={"price_amount": "300.00"},
        headers={**h, "If-Match": '"0"'},
    )

    stale = await client.patch(
        f"/api/v1/products/{pid}/price",
        json={"price_amount": "310.00"},
        headers={**h, "If-Match": '"0"'},
    )

    assert ok.status_code == 200
    assert ok.headers["ETag"] == '"1"'
    assert stale.status_code == 412


async def test_list_is_paginated(client: httpx.AsyncClient, make_token: TokenFactory) -> None:
    h = auth(make_token(TENANT_A))
    for i in range(3):
        await client.post("/api/v1/products", json={**BODY, "sku": f"MUG-00{i}"}, headers=h)

    page = (await client.get("/api/v1/products?limit=2", headers=h)).json()
    rest = (
        await client.get(f"/api/v1/products?limit=2&cursor={page['next_cursor']}", headers=h)
    ).json()

    assert len(page["items"]) == 2
    assert len(rest["items"]) == 1
    assert rest["next_cursor"] is None


async def test_liveness(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health/live")).json() == {"status": "ok"}


async def test_docs_page_csp_allows_swagger_assets(client: httpx.AsyncClient) -> None:
    r = await client.get("/docs")

    assert r.status_code == 200
    assert "cdn.jsdelivr.net" in r.headers["Content-Security-Policy"]


async def test_api_responses_keep_strict_csp(client: httpx.AsyncClient) -> None:
    r = await client.get("/health/live")

    assert r.headers["Content-Security-Policy"].startswith("default-src 'none'")


async def test_cross_origin_isolation_headers(client: httpx.AsyncClient) -> None:
    r = await client.get("/health/live")

    assert r.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert r.headers["Cross-Origin-Opener-Policy"] == "same-origin"
