"""Run the server: `python -m app [--reload]`; set the owner password:
`python -m app set-password` (both from backend/)."""

from __future__ import annotations

import argparse
import getpass
import logging
import sys

import uvicorn

from app.config import BACKEND_DIR, is_loopback, set_env_value, settings
from app.services.auth import MIN_PASSWORD_LENGTH, hash_password

log = logging.getLogger("app")


def set_password() -> int:
    """Ask twice (hidden), store only the scrypt hash in backend/.env (D-23)."""
    password = getpass.getpass("New owner password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Too short: use at least {MIN_PASSWORD_LENGTH} characters.")
        return 1
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match. Nothing changed.")
        return 1
    set_env_value(BACKEND_DIR / ".env", "OWNER_PASSWORD_HASH", hash_password(password))
    print("Password saved to backend/.env (hash only).")
    print("Restart the backend to apply it; every existing session is signed out.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app")
    parser.add_argument(
        "--reload", action="store_true", help="restart on code changes (dev)"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("set-password", help="set the owner login password")
    args = parser.parse_args()
    if args.command == "set-password":
        sys.exit(set_password())

    # Uvicorn configures only its own loggers; this shows app.* lines (desktop viewers...).
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s:     %(name)s: %(message)s")
    if not is_loopback(settings.host):
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
