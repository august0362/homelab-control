"""Run the server: `python -m app [--reload]` (from backend/)."""

from __future__ import annotations

import argparse
import ipaddress
import logging

import uvicorn

from app.config import BACKEND_DIR, settings

log = logging.getLogger("app")


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app")
    parser.add_argument(
        "--reload", action="store_true", help="restart on code changes (dev)"
    )
    args = parser.parse_args()

    if not _is_loopback(settings.host):
        log.warning(
            "HOST=%s is not loopback; remote access should go through Tailscale Serve.",
            settings.host,
        )

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=args.reload,
        reload_dirs=[str(BACKEND_DIR / "app")] if args.reload else None,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
