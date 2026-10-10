"""RFC 9457 Problem Details: one consistent error format for every failure."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

from app.shared.domain.errors import (
    ConcurrencyError,
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)

PROBLEM_JSON = "application/problem+json"


class ProblemDetails(BaseModel):
    """RFC 9457 body. Documented on every route so clients and contract tests know errors."""

    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    instance: str
    correlation_id: str | None = None
    detail: str | None = None
    errors: list[dict[str, Any]] | None = None


_DESCRIPTIONS = {
    400: "Bad request",
    401: "Missing or invalid bearer token",
    403: "Authenticated but not permitted",
    404: "Resource not found (or belongs to another tenant)",
    409: "Conflict (e.g. duplicate SKU)",
    412: "Precondition failed: stale ETag / concurrent modification",
    422: "Validation or business-rule failure",
    428: "If-Match header required",
    503: "Dependency unavailable",
}


def problem_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` entries whose body is application/problem+json."""
    schema = ProblemDetails.model_json_schema()
    return {
        code: {
            "description": _DESCRIPTIONS.get(code, "Error"),
            "content": {PROBLEM_JSON: {"schema": schema}},
        }
        for code in codes
    }


_STATUS_FOR: list[tuple[type[DomainError], int]] = [
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConcurrencyError, status.HTTP_412_PRECONDITION_FAILED),
    (ConflictError, status.HTTP_409_CONFLICT),
    (PermissionDeniedError, status.HTTP_403_FORBIDDEN),
    (DomainError, status.HTTP_422_UNPROCESSABLE_CONTENT),
]


def problem(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str | None = None,
    code: str | None = None,
    **extra: object,
) -> JSONResponse:
    body: dict[str, object] = {
        "type": f"https://errors.example.com/{code or status_code}",
        "title": title,
        "status": status_code,
        "instance": request.url.path,
        "correlation_id": getattr(request.state, "correlation_id", None),
    }
    if detail:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(body, status_code=status_code, media_type=PROBLEM_JSON)


def _allowed_methods(request: Request) -> set[str]:
    """All methods any route serves at this path (Starlette only reports the first route's)."""
    methods: set[str] = set()
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match in {Match.PARTIAL, Match.FULL}:
            methods |= getattr(route, "methods", None) or set()
    return methods


def register_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        code = next(s for cls, s in _STATUS_FOR if isinstance(exc, cls))
        return problem(
            request,
            status_code=code,
            title=exc.code.replace("_", " ").capitalize(),
            detail=str(exc),
            code=exc.code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        if errors and all(
            e["loc"] == ["header", "if-match"] and e["type"] == "missing" for e in errors
        ):
            # RFC 6585: a missing precondition on a conditional update is 428, not 422
            return problem(
                request, status_code=428, title="If-Match header is required", code="precondition"
            )
        return problem(
            request,
            status_code=422,
            title="Validation failed",
            code="validation_error",
            errors=errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        response = problem(request, status_code=exc.status_code, title=str(exc.detail))
        for k, v in (exc.headers or {}).items():
            response.headers[k] = v
        if exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            response.headers["Allow"] = ", ".join(sorted(_allowed_methods(request)))
        return response

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, _exc: Exception) -> JSONResponse:
        # Never leak internals; the correlation_id links to the full error in logs.
        return problem(request, status_code=500, title="Internal server error", code="internal")
