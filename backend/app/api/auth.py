"""Owner login / logout / session (D-23). Public: the guard lets /api/auth/* through."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app.api.errors import ApiError
from app.services.auth import COOKIE, SESSION_TTL

router = APIRouter(prefix="/auth")


class LoginIn(BaseModel):
    password: str


def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, UTC).isoformat(timespec="seconds")


@router.post("/login", status_code=204)
def login(body: LoginIn, request: Request, response: Response) -> None:
    auth = request.app.state.auth
    if not auth.configured:
        raise ApiError(
            503,
            "auth_not_configured",
            "No owner password set. Run scripts\\set-password.ps1 on the server, "
            "then restart the backend.",
        )
    wait = auth.locked_for()
    if wait:
        raise ApiError(
            429,
            "too_many_attempts",
            f"Too many failed attempts. Try again in {wait} s.",
            {"Retry-After": str(wait)},
        )
    if not auth.login(body.password):
        raise ApiError(401, "invalid_credentials", "Wrong password.")
    token, _ = auth.issue()
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_TTL,
        path="/",
        httponly=True,
        samesite="strict",
        secure=auth.secure_cookie,
    )


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    response.delete_cookie(
        COOKIE,
        path="/",
        httponly=True,
        samesite="strict",
        secure=request.app.state.auth.secure_cookie,
    )


@router.get("/session")
def session(request: Request) -> dict[str, Any]:
    auth = request.app.state.auth
    expires = auth.session_expiry(request.cookies.get(COOKIE))
    return {
        "authenticated": expires is not None,
        "configured": auth.configured,
        "expires_at": _iso(expires) if expires else None,
    }
