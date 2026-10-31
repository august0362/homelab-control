"""The single gate in front of /api (D-23): CSRF checks on writes, then the owner session.

A middleware rather than per-route checks, so a new route is protected by default
and unknown /api paths reveal nothing to anonymous callers.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import FastAPI, Request

from app.api.errors import error_response
from app.services.auth import COOKIE

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_PATH = "/api/health"
PUBLIC_PREFIX = "/api/auth/"  # login must work before a session exists


def _same_origin(request: Request) -> bool:
    """Origin must name this host (Vite's dev proxy keeps Host) or an allowed origin."""
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin:
        return False
    if origin in request.app.state.settings.allowed_origins:
        return True
    return urlsplit(origin).netloc.lower() == request.headers.get("host", "").lower()


def _is_json(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    return content_type.split(";")[0].strip().lower() == "application/json"


def register_guard(app: FastAPI) -> None:
    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        if path != "/api" and not path.startswith("/api/"):
            return await call_next(request)
        if request.method in UNSAFE_METHODS and not (
            _same_origin(request) and _is_json(request)
        ):
            return error_response(
                403, "forbidden_origin", "Cross-origin or non-JSON write rejected."
            )
        public = path == PUBLIC_PATH or path.startswith(PUBLIC_PREFIX)
        if (
            not public
            and request.app.state.auth.session_expiry(request.cookies.get(COOKIE))
            is None
        ):
            return error_response(401, "unauthorized", "Sign in to continue.")
        return await call_next(request)
