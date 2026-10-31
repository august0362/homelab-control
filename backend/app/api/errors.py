"""Every error leaves the API as {code, message} (SPEC §4)."""

from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


def _error(
    status: int, code: str, message: str, headers: dict | None = None
) -> JSONResponse:
    return JSONResponse(
        {"code": code, "message": message}, status_code=status, headers=headers
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        try:
            phrase = HTTPStatus(exc.status_code).phrase
        except ValueError:
            phrase = "Error"
        code = phrase.lower().replace(" ", "_").replace("-", "_")  # 404 -> not_found
        message = exc.detail if isinstance(exc.detail, str) else phrase
        return _error(exc.status_code, code, message, getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(422, "validation_error", "Invalid request parameters.")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return _error(500, "internal_error", "Internal server error.")
