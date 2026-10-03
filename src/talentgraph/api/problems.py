"""RFC 7807 problem+json error responses (plan §8.1)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from talentgraph.core.errors import TalentGraphError

ERROR_BASE = "https://talentgraph.dev/errors/"
PROBLEM_JSON = "application/problem+json"


def problem(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    errors: list[Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": ERROR_BASE + code,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "trace_id": getattr(request.state, "trace_id", None),
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def register_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(TalentGraphError)
    async def _tg_error(request: Request, exc: TalentGraphError) -> JSONResponse:
        return problem(
            request, status=exc.http_status, code=exc.code, title=exc.title, detail=exc.detail
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem(
            request,
            status=422,
            code="validation_error",
            title="Request validation failed",
            detail="One or more fields are invalid.",
            errors=list(exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem(
            request,
            status=exc.status_code,
            code=f"http_{exc.status_code}",
            title=str(exc.detail),
            detail=str(exc.detail),
        )
