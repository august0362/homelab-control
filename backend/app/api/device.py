"""Owner-editable device settings (D-24). The first write route: guarded like all /api."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.errors import ApiError
from app.services.device import device_info, save_label, validate_label

router = APIRouter()


class DeviceIn(BaseModel):
    label: str | None  # null = back to DEVICE_LABEL / hostname


@router.patch("/device")
def rename_device(body: DeviceIn, request: Request) -> dict[str, Any]:
    cfg = request.app.state.settings
    try:
        label = None if body.label is None else validate_label(body.label)
    except ValueError as exc:
        raise ApiError(422, "invalid_label", str(exc)) from None
    save_label(cfg, label)
    return device_info(cfg, request.app.state.adapter)
