"""Settings read from environment variables (and backend/.env if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Real environment variables win over values in .env.
load_dotenv(BACKEND_DIR / ".env", override=False)

APP_NAME = "HomeLab Control"
APP_VERSION = "0.1.0"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _resolve(raw: str) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    frontend_dist: Path | None
    state_dir: Path
    device_id: str | None
    device_label: str | None
    machine_role: str
    log_level: str
    owner_password_hash: str | None = None  # scrypt hash (D-23); unset = no login
    allowed_origins: tuple[str, ...] = ()  # extra write origins, e.g. Tailscale Serve


def load_settings() -> Settings:
    role = _env("MACHINE_ROLE", "dev").lower()
    return Settings(
        host=_env("HOST", "127.0.0.1") or "127.0.0.1",
        port=int(_env("PORT", "8000") or 8000),
        frontend_dist=_resolve(_env("FRONTEND_DIST", "../frontend/dist")),
        state_dir=_resolve(_env("STATE_DIR", ".state")) or BACKEND_DIR / ".state",
        device_id=_env("DEVICE_ID") or None,
        device_label=_env("DEVICE_LABEL") or None,
        machine_role=role if role in {"dev", "production"} else "dev",
        log_level=_env("LOG_LEVEL", "info").lower() or "info",
        owner_password_hash=_env("OWNER_PASSWORD_HASH") or None,
        allowed_origins=tuple(
            o.strip().rstrip("/")
            for o in _env("ALLOWED_ORIGINS").split(",")
            if o.strip()
        ),
    )


def set_env_value(path: Path, key: str, value: str) -> None:
    """Replace `key=...` in a .env file (or append it), keeping every other line."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    line = f"{key}='{value}'"  # single quotes: python-dotenv expands nothing inside
    for i, old in enumerate(lines):
        if old.strip().startswith(f"{key}="):
            lines[i] = line
            break
    else:
        lines.append(line)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


settings = load_settings()
