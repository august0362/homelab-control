"""Owner-editable names (D-24): this device, and the Linux server while staging."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.errors import ApiError
from app.services.device import (
    device_info,
    save_label,
    save_server_label,
    server_label,
    validate_label,
)

router = APIRouter()


class DeviceIn(BaseModel):
    label: str | None  # null = back to DEVICE_LABEL / hostname


def _checked(body: DeviceIn) -> str | None:
    try:
        return None if body.label is None else validate_label(body.label)
    except ValueError as exc:
        raise ApiError(422, "invalid_label", str(exc)) from None


@router.patch("/device")
def rename_device(body: DeviceIn, request: Request) -> dict[str, Any]:
    cfg = request.app.state.settings
    save_label(cfg, _checked(body))
    return device_info(cfg, request.app.state.adapter)


@router.patch("/server")
def rename_server(body: DeviceIn, request: Request) -> dict[str, str]:
    """The name of the machine behind Remote Desktop and Power (D-24)."""
    cfg = request.app.state.settings
    save_server_label(cfg, _checked(body))
    label, source = server_label(cfg)
    return {"label": label, "label_source": source}
