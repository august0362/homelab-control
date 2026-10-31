"""Static machine info: identity, OS, hardware and what this device can do."""

from __future__ import annotations

import platform
import socket
from datetime import UTC, datetime
from typing import Any

import psutil
from fastapi import APIRouter, Request

from app.config import APP_NAME, APP_VERSION
from app.services.device import capabilities, device_info

router = APIRouter()


@router.get("/system")
def system(request: Request) -> dict[str, Any]:
    cfg = request.app.state.settings
    adapter = request.app.state.adapter
    return {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "device": device_info(cfg, adapter),
        "os": adapter.os_details(),
        "hardware": {
            "hostname": socket.gethostname(),
            "architecture": platform.machine(),
            "cpu_model": adapter.cpu_model(),
            "cpu_logical": psutil.cpu_count(),
            "cpu_physical": psutil.cpu_count(logical=False),
            "memory_total_bytes": psutil.virtual_memory().total,
            "boot_time": datetime.fromtimestamp(psutil.boot_time(), UTC).isoformat(
                timespec="seconds"
            ),
        },
        "app": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "python": platform.python_version(),
        },
        "capabilities": capabilities(adapter),
    }
