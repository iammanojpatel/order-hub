"""REST adapter for the catalog context (/api/v1/products)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.catalog.api.schemas import (
    ChangePriceRequest,
    CreateProductRequest,
    ListParams,
    ProductPage,
    ProductResponse,
)
from app.catalog.application import services
from app.catalog.application.ports import CatalogUnitOfWork
from app.shared.api.auth import CurrentPrincipal
from app.shared.api.problems import problem_responses

router = APIRouter(
    prefix="/api/v1/products",
    tags=["catalog"],
    responses=problem_responses(400, 401, 403, 422),
)

UowFactory = Callable[[uuid.UUID], CatalogUnitOfWork]


def get_uow(request: Request, principal: CurrentPrincipal) -> CatalogUnitOfWork:
    factory: UowFactory = request.app.state.uow_factory
    return factory(principal.tenant_id)


Uow = Annotated[CatalogUnitOfWork, Depends(get_uow)]


def _etag(version: int) -> str:
    return f'"{version}"'


def _parse_if_match(value: str) -> int:
    try:
        return int(value.strip().removeprefix("W/").strip('"'))
    except ValueError as exc:
        raise HTTPException(status.HTTP_412_PRECONDITION_FAILED, "Malformed If-Match") from exc


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductResponse,
    responses=problem_responses(409),
)
async def create_product(
    body: CreateProductRequest,
    response: Response,
    uow: Uow,
    principal: CurrentPrincipal,
    idempotency_key: Annotated[str | None, Header(max_length=100)] = None,
) -> ProductResponse:
    view = await services.create_product(
        services.CreateProduct(
            sku=body.sku,
            name=body.name,
            price_amount=Decimal(body.price_amount),
            currency=body.currency,
            idempotency_key=idempotency_key,
        ),
        uow=uow,
        actor=principal,
    )
    response.headers["Location"] = f"{router.prefix}/{view.id}"
    response.headers["ETag"] = _etag(view.version)
    return ProductResponse.of(view)


@router.get("", response_model=ProductPage)
async def list_products(
    uow: Uow,
    principal: CurrentPrincipal,
    params: Annotated[ListParams, Query()],
) -> ProductPage:
    page = await services.list_products(
        uow=uow, actor=principal, after=params.cursor, limit=params.limit
    )
    return ProductPage(
        items=[ProductResponse.of(v) for v in page.items], next_cursor=page.next_cursor
    )


@router.get("/{product_id}", response_model=ProductResponse, responses=problem_responses(404))
async def get_product(
    product_id: uuid.UUID, response: Response, uow: Uow, principal: CurrentPrincipal
) -> ProductResponse:
    view = await services.get_product(product_id, uow=uow, actor=principal)
    response.headers["ETag"] = _etag(view.version)
    return ProductResponse.of(view)


@router.patch(
    "/{product_id}/price",
    response_model=ProductResponse,
    responses=problem_responses(404, 412, 428),
)
async def change_price(
    product_id: uuid.UUID,
    body: ChangePriceRequest,
    response: Response,
    uow: Uow,
    principal: CurrentPrincipal,
    if_match: Annotated[
        str, Header(pattern=r'^(W/)?"?[0-9]{1,9}"?$', description='ETag from GET, e.g. "3"')
    ],
) -> ProductResponse:
    view = await services.change_price(
        services.ChangePrice(
            product_id=product_id,
            new_amount=Decimal(body.price_amount),
            expected_version=_parse_if_match(if_match),
        ),
        uow=uow,
        actor=principal,
    )
    response.headers["ETag"] = _etag(view.version)
    return ProductResponse.of(view)


@router.post(
    "/{product_id}/discontinue",
    response_model=ProductResponse,
    responses=problem_responses(404),
)
async def discontinue_product(
    product_id: uuid.UUID, response: Response, uow: Uow, principal: CurrentPrincipal
) -> ProductResponse:
    view = await services.discontinue_product(product_id, uow=uow, actor=principal)
    response.headers["ETag"] = _etag(view.version)
    return ProductResponse.of(view)
