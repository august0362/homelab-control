from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import runner as runner_module
from app.services.power import SYSTEM_UNITS, USER_UNITS

from .conftest import ORIGIN, login

ALIAS = "dell-test"
SSH_PREFIX = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", ALIAS]
UNIT = "hlc-desktop.service"
RULES = Path(__file__).resolve().parents[2] / "deploy/linux/50-homelab-control.rules"
ESSENTIAL = ("ssh", "tailscaled", "NetworkManager", "systemd", "dbus")


class FakeServer:
    """systemctl on a pretend Dell, reached through the SSH prefix."""

    def __init__(self, active: set[str]) -> None:
        self.active = set(active)
        self.calls: list[list[str]] = []
        self.fail: tuple[int, str] | None = (
            None  # (exit code, stderr) for the next call
        )
        self.rebooted = False

    def run(self, argv, **kwargs):
        assert not kwargs.get("shell")
        assert argv[: len(SSH_PREFIX)] == SSH_PREFIX
        cmd = argv[len(SSH_PREFIX) :]
        self.calls.append(cmd)
        if self.fail:
            code, err = self.fail
            self.fail = None
            return subprocess.CompletedProcess(argv, code, "", err)
        args = [a for a in cmd[1:] if a != "--user"]
        verb, units = args[0], args[1:]
        out = ""
        if verb == "is-active":
            out = "\n".join("active" if u in self.active else "inactive" for u in units)
        elif verb == "stop":
            self.active -= set(units)
        elif verb == "start":
            self.active |= set(units)
        elif verb == "reboot":
            self.rebooted = True
        return subprocess.CompletedProcess(argv, 0, out + "\n", "")


@pytest.fixture
def server(monkeypatch):
    fake = FakeServer({UNIT, "docker.service", "cups.service", "pipewire.service"})
    monkeypatch.setattr(runner_module.subprocess, "run", fake.run)
    return fake


@pytest.fixture
def staged(cfg, server):
    """The ASUS app controlling the Dell over SSH (D-28)."""
    client = TestClient(
        create_app(
            replace(
                cfg,
                remote_ssh=ALIAS,
                desktop_vnc="tcp:127.0.0.1:1",  # never answers: only start/stop matter here
                desktop_unit=UNIT,
                desktop_label="Dell",
            )
        )
    )
    assert login(client).status_code == 204
    return client


def post(client, path, body=None):
    return client.post(f"/api/power/{path}", json=body or {}, headers=ORIGIN)


def test_unavailable_on_the_windows_dev_machine(client, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    body = client.get("/api/power").json()
    assert body["available"] is False and "REMOTE_SSH" in body["message"]
    for action in ("sleep", "wake", "cleanup"):
        res = post(client, action)
        assert res.status_code == 409 and res.json()["code"] == "power_unavailable"
    res = post(client, "reboot", {"confirm": "reboot"})
    assert res.status_code == 409  # nothing here can restart the ASUS


def test_bad_alias_is_ignored(cfg, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    client = TestClient(create_app(replace(cfg, remote_ssh="-oProxyCommand=x")))
    login(client)
    assert client.get("/api/power").json()["available"] is False


def test_status_lists_optional_tasks_over_ssh(staged, server):
    body = staged.get("/api/power").json()
    assert body["available"] and body["reachable"] and body["label"] == "Dell"
    assert body["sleeping_since"] is None
    units = {t["unit"]: t for t in body["tasks"]}
    assert set(units) == {*SYSTEM_UNITS, UNIT, *USER_UNITS}
    assert units[UNIT] == {"unit": UNIT, "scope": "user", "active": True}
    assert units["fwupd.service"]["active"] is False
    assert server.calls[0][:2] == ["systemctl", "is-active"]


def test_sleep_then_wake_restores_exactly_what_ran(staged, server):
    res = post(staged, "sleep")
    assert res.status_code == 200 and res.json() == {"stopped": 4}
    assert server.active == set()
    stops = [c for c in server.calls if "stop" in c]
    assert set(stops[0][2:]) == {"docker.service", "cups.service"}  # system first
    assert stops[1][:3] == ["systemctl", "--user", "stop"]
    assert staged.get("/api/power").json()["sleeping_since"]

    server.active.add("fwupd.service")  # something started meanwhile
    post(staged, "sleep")  # pressed twice: the first memory is kept
    res = post(staged, "wake")
    assert res.json() == {"started": 5}
    assert server.active == {
        UNIT,
        "docker.service",
        "cups.service",
        "pipewire.service",
        "fwupd.service",
    }
    assert staged.get("/api/power").json()["sleeping_since"] is None
    assert post(staged, "wake").json() == {"started": 0}


def test_cleanup_stops_everything_optional_and_forgets(staged, server):
    post(staged, "sleep")
    server.active.add("avahi-daemon.service")
    assert post(staged, "cleanup").json() == {"stopped": 1}
    assert server.active == set()
    assert staged.get("/api/power").json()["sleeping_since"] is None


def test_never_touches_essential_services(staged, server):
    post(staged, "sleep")
    post(staged, "wake")
    post(staged, "cleanup")
    touched = " ".join(" ".join(c) for c in server.calls)
    assert not any(
        re.search(rf"\b{name}(\.service)?\b", touched)
        for name in ESSENTIAL
        if name != "systemd"
    )
    assert all(c[0] == "systemctl" for c in server.calls)


def test_reboot_needs_confirmation(staged, server):
    res = post(staged, "reboot")
    assert res.status_code == 422 and res.json()["code"] == "confirm_required"
    assert not server.rebooted
    post(staged, "sleep")
    assert post(staged, "reboot", {"confirm": "reboot"}).status_code == 204
    assert server.rebooted and server.calls[-1] == ["systemctl", "reboot"]
    assert (
        staged.get("/api/power").json()["sleeping_since"] is None
    )  # boot restarts all


def test_errors_are_mapped(staged, server, monkeypatch):
    def deny_stop(argv, **kwargs):  # no polkit rule installed yet
        if "stop" in argv:
            return subprocess.CompletedProcess(argv, 4, "", "Access denied /home/x")
        return server.run(argv, **kwargs)

    monkeypatch.setattr(runner_module.subprocess, "run", deny_stop)
    res = post(staged, "sleep")
    body = res.json()
    assert res.status_code == 403 and body["code"] == "power_not_permitted"
    assert UNIT in server.active  # refused before anything stopped
    assert "power-setup.sh" in body["message"] and "/home/" not in body["message"]

    monkeypatch.setattr(runner_module.subprocess, "run", server.run)
    server.fail = (255, "ssh: connect to host failed")
    res = post(staged, "cleanup")
    assert res.status_code == 502 and res.json()["code"] == "server_unreachable"
    server.fail = (255, "")
    body = staged.get("/api/power").json()
    assert body["reachable"] is False and "SSH" in body["message"]


def test_power_writes_are_guarded(staged):
    assert staged.post("/api/power/cleanup", json={}).status_code == 403  # no Origin
    anon = TestClient(staged.app)
    assert anon.post("/api/power/cleanup", json={}, headers=ORIGIN).status_code == 401


def test_desktop_start_goes_over_ssh_too(staged, server):
    assert staged.get("/api/desktop/status").json()["can_control"] is True
    res = staged.post("/api/desktop/start", json={}, headers=ORIGIN)
    assert res.status_code == 204
    assert server.calls[-1] == ["systemctl", "--user", "start", UNIT]


def test_polkit_rule_matches_the_code():
    text = RULES.read_text(encoding="utf-8")
    listed = re.findall(r'"([\w.@-]+\.service)"', text)
    assert sorted(listed) == sorted(SYSTEM_UNITS)
    assert "@USER@" in text and "power-off" not in text
