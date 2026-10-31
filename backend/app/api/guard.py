"""The single gate in front of /api (D-23): CSRF checks on writes, then the owner session
(skipped only in dev on loopback, D-25).

A middleware rather than per-route checks, so a new route is protected by default
and unknown /api paths reveal nothing to anonymous callers. WebSockets skip HTTP
middleware, so WebSocket endpoints call `denial()` themselves: same rules, one place.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from starlette.requests import HTTPConnection

from app.api.errors import error_response
from app.services.auth import COOKIE

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_PATH = "/api/health"
PUBLIC_PREFIX = "/api/auth/"  # login must work before a session exists
FORBIDDEN = (403, "forbidden_origin", "Cross-origin or non-JSON write rejected.")


def _same_origin(conn: HTTPConnection) -> bool:
    """Origin must name this host (Vite's dev proxy keeps Host) or an allowed origin."""
    origin = conn.headers.get("origin", "").rstrip("/")
    if not origin:
        return False
    if origin in conn.app.state.settings.allowed_origins:
        return True
    return urlsplit(origin).netloc.lower() == conn.headers.get("host", "").lower()


def _is_json(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    return content_type.split(";")[0].strip().lower() == "application/json"


def denial(conn: HTTPConnection, *, check_origin: bool) -> tuple[int, str, str] | None:
    """(status, code, message) when this /api request must be refused, else None.
    check_origin: writes, and every WebSocket (cross-site WebSocket hijacking)."""
    if check_origin and not _same_origin(conn):
        return FORBIDDEN
    path = conn.url.path
    if path == PUBLIC_PATH or path.startswith(PUBLIC_PREFIX):
        return None
    auth = conn.app.state.auth
    if auth.open_to(conn.headers.get("host", "")):
        return None
    if auth.session_expiry(conn.cookies.get(COOKIE)) is None:
        return 401, "unauthorized", "Sign in to continue."
    return None


def register_guard(app: FastAPI) -> None:
    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        if path != "/api" and not path.startswith("/api/"):
            return await call_next(request)
        unsafe = request.method in UNSAFE_METHODS
        refused = FORBIDDEN if unsafe and not _is_json(request) else None
        refused = refused or denial(request, check_origin=unsafe)
        if refused:
            return error_response(*refused)
        return await call_next(request)
