"""HTTP DTOs (Pydantic). Validation at the boundary; never expose domain objects directly."""

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.catalog.application.services import ProductView
from app.catalog.domain.model import ProductStatus

# Money travels as a decimal STRING (never a float): exact, positive, max 12+2 digits.
_AMOUNT_PATTERN = r"^(?:[1-9][0-9]{0,11}(?:\.[0-9]{1,2})?|0\.(?:[1-9][0-9]?|0[1-9]))$"
Amount = Annotated[str, Field(pattern=_AMOUNT_PATTERN, examples=["19.99"])]


class CreateProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sku: Annotated[
        str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{2,31}$", examples=["TSHIRT-RED-M"])
    ]
    name: Annotated[str, Field(min_length=1, max_length=200)]
    price_amount: Amount
    currency: Annotated[str, Field(pattern=r"^[A-Za-z]{3}$", examples=["INR"])]


class ChangePriceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    price_amount: Amount


class ListParams(BaseModel):
    """Query parameters for listing; unknown parameters are rejected (fail loudly on typos)."""

    model_config = ConfigDict(extra="forbid")

    cursor: uuid.UUID | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 20


class ProductResponse(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    price_amount: Amount
    currency: str
    status: ProductStatus
    version: int

    @classmethod
    def of(cls, view: ProductView) -> ProductResponse:
        return cls(
            id=view.id,
            sku=view.sku,
            name=view.name,
            price_amount=f"{view.price_amount:.2f}",
            currency=view.currency,
            status=view.status,
            version=view.version,
        )


class ProductPage(BaseModel):
    items: list[ProductResponse]
    next_cursor: uuid.UUID | None
