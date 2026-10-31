"""Power controls for the Linux server (D-27): light sleep / wake up, clean up, restart.
There is no shut down: nothing could switch the Dell back on remotely (Wi-Fi only, no
Wake-on-LAN), so a restart is the strongest action the web offers.

Only the units listed here are ever stopped or started; what the server needs (ssh,
tailscaled, NetworkManager, systemd, this app) is never touched. Stopping system units and
rebooting go through polkit: deploy/linux/power-setup.sh installs a rule allowing exactly
this list (and reboot) for one user. The list must match
deploy/linux/50-homelab-control.rules (tested).
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.config import Settings
from app.services.runner import SSH_FAILED, Runner

log = logging.getLogger(__name__)

# Optional background work a home server can do without. Socket-activated ones (docker,
# cups, avahi, pipewire) may start again by themselves if something asks for them.
SYSTEM_UNITS = (
    "docker.service",
    "containerd.service",
    "cups.service",
    "cups-browsed.service",
    "fwupd.service",
    "ModemManager.service",
    "colord.service",
    "udisks2.service",
    "avahi-daemon.service",
)
USER_UNITS = (
    "pipewire.service",
    "pipewire-pulse.service",
    "wireplumber.service",
    "filter-chain.service",
)
TIMEOUT = 30


@dataclass(frozen=True)
class Task:
    unit: str
    scope: str  # "system" | "user"
    active: bool


class PowerError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class Power:
    def __init__(
        self, cfg: Settings, runner: Runner, desktop_unit: str | None = None
    ) -> None:
        self.runner = runner
        self._state = cfg.state_dir / "power.json"
        self.user_units = (desktop_unit, *USER_UNITS) if desktop_unit else USER_UNITS

    # --- commands ---------------------------------------------------------------

    def _systemctl(self, scope: str, *args: str) -> subprocess.CompletedProcess[str]:
        base = ["systemctl", "--user"] if scope == "user" else ["systemctl"]
        try:
            result = self.runner.run([*base, *args], TIMEOUT)
        except FileNotFoundError:
            raise PowerError(
                503, "power_unavailable", "systemctl is not available here."
            ) from None
        except subprocess.TimeoutExpired:
            raise PowerError(
                504, "server_timeout", f"The server did not answer within {TIMEOUT} s."
            ) from None
        if result.returncode == SSH_FAILED and self.runner.remote:
            raise PowerError(
                502, "server_unreachable", "Cannot reach the server over SSH."
            )
        return result

    def _check(self, result: subprocess.CompletedProcess[str], what: str) -> None:
        if result.returncode == 0:
            return
        # stderr may name paths or users: logged by exit code only, never returned.
        log.warning("%s failed (exit %s)", what, result.returncode)
        err = result.stderr.lower()
        if "authentication" in err or "access denied" in err or "not authorized" in err:
            raise PowerError(
                403,
                "power_not_permitted",
                "The server refused. Install the power rule once: "
                "bash deploy/linux/power-setup.sh (see deploy/linux/README.md).",
            )
        raise PowerError(
            500, "power_failed", f"{what} failed (exit {result.returncode})."
        )

    def tasks(self) -> list[Task]:
        found: list[Task] = []
        for scope, units in (("system", SYSTEM_UNITS), ("user", self.user_units)):
            states = self._systemctl(scope, "is-active", *units).stdout.split()
            if len(states) != len(units):  # is-active prints one line per unit
                raise PowerError(
                    502, "server_unreachable", "Unexpected answer from the server."
                )
            found += [
                Task(u, scope, s == "active")
                for u, s in zip(units, states, strict=True)
            ]
        return found

    def _stop_running(self) -> list[Task]:
        running = [t for t in self.tasks() if t.active]
        # System first: without the polkit rule it fails before anything has stopped.
        for scope in ("system", "user"):
            units = [t.unit for t in running if t.scope == scope]
            if units:
                self._check(
                    self._systemctl(scope, "stop", *units), f"Stopping {scope} tasks"
                )
        return running

    # --- actions ----------------------------------------------------------------

    def sleep(self) -> int:
        """Stop the optional tasks that are running and remember them for wake()."""
        stopped = self._stop_running()
        previous = self._saved()
        keep = previous["stopped"] if previous else []
        names = {(t["unit"], t["scope"]) for t in keep}
        keep += [
            {"unit": t.unit, "scope": t.scope}
            for t in stopped
            if (t.unit, t.scope) not in names
        ]
        since = (
            previous["since"]
            if previous
            else datetime.now(UTC).isoformat(timespec="seconds")
        )
        self._save({"since": since, "stopped": keep})
        return len(stopped)

    def wake(self) -> int:
        """Start again exactly what sleep() stopped."""
        saved = self._saved()
        if not saved:
            return 0
        for scope in ("system", "user"):  # services first, then the desktop and audio
            units = [t["unit"] for t in saved["stopped"] if t["scope"] == scope]
            if units:
                self._check(
                    self._systemctl(scope, "start", *units), f"Starting {scope} tasks"
                )
        self._state.unlink(missing_ok=True)
        return len(saved["stopped"])

    def cleanup(self) -> int:
        """Back to the basics: stop every optional task, remember nothing."""
        stopped = self._stop_running()
        self._state.unlink(missing_ok=True)
        return len(stopped)

    def reboot(self) -> None:
        """Restart the server. Every service comes back as at boot, so the light-sleep
        memory is dropped (the desktop stays off: it never starts at boot)."""
        self._check(self._systemctl("system", "reboot"), "Restart")
        self._state.unlink(missing_ok=True)

    # --- light-sleep memory -------------------------------------------------------

    def _saved(self) -> dict[str, Any] | None:
        try:
            data = json.loads(self._state.read_text(encoding="utf-8"))
            return data if isinstance(data.get("stopped"), list) else None
        except (OSError, ValueError, AttributeError):
            return None

    def _save(self, data: dict[str, Any]) -> None:
        self._state.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._state.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(self._state)

    def sleeping_since(self) -> str | None:
        saved = self._saved()
        return saved["since"] if saved else None
