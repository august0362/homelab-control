from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.config import APP_VERSION

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "version": APP_VERSION,
    }
