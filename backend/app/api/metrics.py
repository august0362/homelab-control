"""Live metrics, polled by the dashboard about every 2 s."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from app.services.device import device_info

router = APIRouter()


@router.get("/metrics")
def metrics(request: Request) -> dict[str, Any]:
    state = request.app.state
    return {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "device": device_info(state.settings, state.adapter),
        **state.metrics.collect(),
    }
