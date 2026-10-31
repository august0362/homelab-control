"""Device identity and capability map (SPEC §4, ARCHITECTURE §5).

Every payload carries `device` so the UI can later switch between machines (M7).
"""

from __future__ import annotations

import json
import socket
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.platform_adapter import PlatformAdapter

LABEL_MAX_LENGTH = 40
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


def validate_label(raw: str) -> str:
    """Trimmed label, or ValueError with a message the UI can show (D-24)."""
    label = raw.strip()
    if not label:
        raise ValueError("Name cannot be empty.")
    if len(label) > LABEL_MAX_LENGTH:
        raise ValueError(f"Name must be at most {LABEL_MAX_LENGTH} characters.")
    if any(unicodedata.category(ch) in {"Cc", "Zl", "Zp"} for ch in label):
        raise ValueError("Name cannot contain control characters or line breaks.")
    return label


def _settings_path(cfg: Settings) -> Path:
    return cfg.state_dir / "device.json"


def saved_label(cfg: Settings) -> str | None:
    """Name set on the UI; a missing or broken file just means "no custom name"."""
    try:
        label = json.loads(_settings_path(cfg).read_text(encoding="utf-8"))["label"]
        return validate_label(label)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def save_label(cfg: Settings, label: str | None) -> None:
    """Store a validated label; None removes it (back to DEVICE_LABEL / hostname)."""
    path = _settings_path(cfg)
    if label is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"label": label}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def device_label(cfg: Settings) -> tuple[str, str]:
    """(label, source): UI name > DEVICE_LABEL > hostname."""
    if custom := saved_label(cfg):
        return custom, "custom"
    if cfg.device_label:
        return cfg.device_label, "env"
    return socket.gethostname(), "hostname"


def device_info(cfg: Settings, adapter: PlatformAdapter) -> dict[str, Any]:
    label, source = device_label(cfg)
    return {
        "id": device_id(cfg),
        "label": label,
        "label_source": source,
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
