"""On-demand remote desktop (FR-02, ADR-008, D-26).

The VNC server (Xvnc on the Dell) listens on a Unix socket only; the backend is the
one way in: it probes the socket for status, starts/stops a systemd *user* unit with
a fixed argv (D-15), and bridges authenticated browser WebSockets to the socket
(api/desktop.py). On the ASUS a loopback TCP target (an SSH tunnel) is used instead.
"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.config import Settings, is_loopback
from app.services.runner import SSH_FAILED, Runner

log = logging.getLogger(__name__)

PROBE_TIMEOUT = 1.0  # seconds to connect and read the RFB banner
SYSTEMCTL_TIMEOUT = 15
NOT_CONFIGURED = "Set DESKTOP_VNC (see README)."
_BANNER = re.compile(rb"RFB \d{3}\.\d{3}\n")  # "RFB 003.008\n", always 12 bytes
_UNIT = re.compile(r"[A-Za-z0-9][A-Za-z0-9@._-]*")  # never starts with "-" (argv)


@dataclass(frozen=True)
class Target:
    """Where the VNC server listens: a Unix socket path, or a loopback host:port."""

    path: str | None = None
    host: str = ""
    port: int = 0


def parse_target(raw: str) -> Target:
    """DESKTOP_VNC value -> Target, or ValueError saying what is wrong."""
    kind, _, rest = raw.partition(":")
    if kind == "unix":
        if sys.platform == "win32":
            raise ValueError("unix: targets need Linux; use tcp:127.0.0.1:<port>")
        if not rest.startswith("/"):
            raise ValueError("unix: needs an absolute socket path")
        return Target(path=rest)
    if kind == "tcp":
        parts = urlsplit(f"//{rest}")
        try:
            port = parts.port
        except ValueError:
            port = None
        if not parts.hostname or not port:
            raise ValueError("tcp: needs host:port, e.g. tcp:127.0.0.1:5901")
        if not is_loopback(parts.hostname):
            raise ValueError(f"tcp host {parts.hostname} is not loopback (no LAN VNC)")
        return Target(host=parts.hostname, port=port)
    raise ValueError('use "unix:/path/to.sock" or "tcp:127.0.0.1:<port>"')


class DesktopError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Desktop:
    """One per app. Holds the parsed config and the open viewer bridges."""

    def __init__(self, cfg: Settings, runner: Runner | None = None) -> None:
        self.runner = runner or Runner(None)
        self.target: Target | None = None
        self.problem = NOT_CONFIGURED  # why there is no target
        if cfg.desktop_vnc:
            try:
                self.target = parse_target(cfg.desktop_vnc)
            except ValueError as exc:
                self.problem = f"DESKTOP_VNC ignored: {exc}."
                log.warning("%s Remote desktop stays not configured.", self.problem)
        self.unit = cfg.desktop_unit
        if self.unit and not _UNIT.fullmatch(self.unit):
            log.warning("DESKTOP_UNIT ignored: not a valid unit name.")
            self.unit = None
        self._viewers: set[asyncio.Event] = set()

    @property
    def can_control(self) -> bool:
        return bool(self.target and self.unit)

    @property
    def viewers(self) -> int:
        return len(self._viewers)

    # --- status ---------------------------------------------------------------

    def _connect(self) -> socket.socket:
        assert self.target
        if self.target.path:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(PROBE_TIMEOUT)
            try:
                sock.connect(self.target.path)
            except OSError:
                sock.close()
                raise
            return sock
        return socket.create_connection(
            (self.target.host, self.target.port), PROBE_TIMEOUT
        )

    def _probe(self) -> bool:
        """True when a VNC server answers with its RFB banner. A bare TCP accept is
        not enough: an SSH tunnel accepts even when the far end is down."""
        try:
            with self._connect() as sock:
                sock.settimeout(PROBE_TIMEOUT)
                banner = b""
                while len(banner) < 12:
                    chunk = sock.recv(12 - len(banner))
                    if not chunk:
                        break
                    banner += chunk
        except OSError:
            return False
        return bool(_BANNER.fullmatch(banner))

    def _systemctl(self, action: str) -> subprocess.CompletedProcess[str]:
        assert self.unit
        return self.runner.run(
            ["systemctl", "--user", action, self.unit], SYSTEMCTL_TIMEOUT
        )

    def _answering(self) -> bool:
        """An open viewer already proves the server is up: skip the probe (fewer
        half-open connections in the VNC log)."""
        return self.viewers > 0 or self._probe()

    def status(self) -> tuple[str, str]:
        """(state, message): not_configured | stopped | starting | running | error."""
        if not self.target:
            return "not_configured", self.problem
        if self.unit:
            try:
                result = self._systemctl("is-active")
            except (OSError, subprocess.TimeoutExpired):
                return "error", "Could not ask systemd about the desktop service."
            if result.returncode == SSH_FAILED and self.runner.remote:
                return "error", "Cannot reach the server over SSH."
            state = result.stdout.strip()
            if state == "failed":
                return "error", (
                    f"The desktop service failed. On the server: "
                    f"journalctl --user -u {self.unit}"
                )
            if state == "activating":
                return "starting", "Desktop is starting…"
            if state == "deactivating":
                return "stopped", "Desktop is stopping…"
            if state != "active":
                return "stopped", "Desktop is stopped."
            if not self._answering():
                return "starting", "Service is up, waiting for the VNC server…"
            return "running", "Desktop is running."
        if self._answering():
            return "running", "VNC server is answering."
        return "stopped", (
            "No VNC server answers: the desktop is stopped or the tunnel is down."
        )

    # --- start / stop ---------------------------------------------------------

    def _run(self, action: str) -> None:
        try:
            result = self._systemctl(action)
        except FileNotFoundError:
            raise DesktopError(
                f"desktop_{action}_failed", "systemctl is not available here."
            ) from None
        except subprocess.TimeoutExpired:
            raise DesktopError(
                f"desktop_{action}_failed",
                f"systemctl {action} took longer than {SYSTEMCTL_TIMEOUT} s.",
            ) from None
        if result.returncode == SSH_FAILED and self.runner.remote:
            raise DesktopError(
                f"desktop_{action}_failed", "Cannot reach the server over SSH."
            )
        if result.returncode != 0:
            # stderr may name paths or users: never logged or returned, point to journalctl.
            log.warning(
                "systemctl --user %s %s exited %s", action, self.unit, result.returncode
            )
            raise DesktopError(
                f"desktop_{action}_failed",
                f"systemctl {action} failed (exit {result.returncode}). On the server: "
                f"journalctl --user -u {self.unit}",
            )

    def start(self) -> None:
        self._run("start")

    def stop(self) -> None:
        """Blocking; the caller then closes the bridges on the event loop."""
        self._run("stop")

    # --- viewer bridges -------------------------------------------------------

    @contextmanager
    def viewer(self) -> Iterator[asyncio.Event]:
        """Registers one bridge; setting the event asks it to close."""
        stop = asyncio.Event()
        self._viewers.add(stop)
        try:
            yield stop
        finally:
            self._viewers.discard(stop)

    def close_viewers(self) -> None:
        for stop in list(self._viewers):
            stop.set()

    async def open(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        assert self.target
        if self.target.path:
            return await asyncio.wait_for(
                asyncio.open_unix_connection(self.target.path), PROBE_TIMEOUT
            )
        return await asyncio.wait_for(
            asyncio.open_connection(self.target.host, self.target.port), PROBE_TIMEOUT
        )
