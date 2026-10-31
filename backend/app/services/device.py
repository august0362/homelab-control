"""Device identity and capability map (SPEC §4, ARCHITECTURE §5).

Every payload carries `device` so the UI can later switch between machines (M7).
"""

from __future__ import annotations

import socket
import uuid
from typing import Any

from app.config import Settings
from app.services.platform_adapter import PlatformAdapter

CAPABILITY_STATUSES = {"supported", "unsupported", "not_configured", "requires_consent"}

# Features whose backend lands in a later milestone.
_PLANNED = {"desktop": "M3", "files": "M4", "services": "M5"}
_CAPABILITY_ORDER = (
    "metrics",
    "temperature",
    "fans",
    "battery",
    "desktop",
    "files",
    "services",
)


def device_id(cfg: Settings) -> str:
    """DEVICE_ID env wins; otherwise a UUID generated once and kept in STATE_DIR."""
    if cfg.device_id:
        return cfg.device_id
    path = cfg.state_dir / "device_id"
    if path.is_file():
        stored = path.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    new_id = str(uuid.uuid4())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_id, encoding="utf-8")
    return new_id


def device_info(cfg: Settings, adapter: PlatformAdapter) -> dict[str, Any]:
    return {
        "id": device_id(cfg),
        "label": cfg.device_label or socket.gethostname(),
        "role": cfg.machine_role,
        "platform": adapter.name,
        "device_type": "computer",
    }


def capabilities(adapter: PlatformAdapter) -> dict[str, dict[str, str | None]]:
    sensors = {"metrics": True, **adapter.sensor_support()}
    caps: dict[str, dict[str, str | None]] = {}
    for name in _CAPABILITY_ORDER:
        if name in _PLANNED:
            caps[name] = {
                "status": "not_configured",
                "message": f"Planned in {_PLANNED[name]}.",
            }
        elif sensors.get(name):
            caps[name] = {"status": "supported", "message": None}
        else:
            caps[name] = {
                "status": "unsupported",
                "message": f"Not exposed on {adapter.name}.",
            }
    return caps
