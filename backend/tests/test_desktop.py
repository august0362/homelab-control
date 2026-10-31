from __future__ import annotations

import socket
import socketserver
import subprocess
import sys
import threading
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app
from app.services import desktop as desktop_service
from app.services.desktop import Desktop, Target, parse_target

from .conftest import ORIGIN, login

BANNER = b"RFB 003.008\n"
WS = "/api/desktop/ws"
UNIT = "hlc-desktop.service"
LOCAL = "http://127.0.0.1:8000"


class _FakeRfb(socketserver.BaseRequestHandler):
    """Protocol stand-in for Xvnc: the RFB banner, then echo. Not a desktop."""

    def handle(self):
        self.request.sendall(BANNER)
        while data := self.request.recv(4096):
            self.request.sendall(data)


class _Hangup(socketserver.BaseRequestHandler):
    """Accepts and closes, like an SSH tunnel whose far end is down."""

    def handle(self):
        pass


def _serve(handler):
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def rfb_port():
    server = _serve(_FakeRfb)
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


@pytest.fixture
def hangup_port():
    server = _serve(_Hangup)
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


@pytest.fixture
def closed_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def signed_in(cfg, **changes) -> TestClient:
    client = TestClient(create_app(replace(cfg, **changes)))
    assert login(client).status_code == 204
    return client


def fake_systemctl(monkeypatch, stdout="", returncode=0, raises=None):
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if raises:
            raise raises
        return subprocess.CompletedProcess(argv, returncode, stdout, "/home/<user> x")

    monkeypatch.setattr(desktop_service.subprocess, "run", run)
    return calls


# --- config ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "target"),
    [
        ("tcp:127.0.0.1:5901", Target(host="127.0.0.1", port=5901)),
        ("tcp:localhost:5901", Target(host="localhost", port=5901)),
        ("tcp:[::1]:5901", Target(host="::1", port=5901)),
    ],
)
def test_parse_tcp_target(raw, target):
    assert parse_target(raw) == target


@pytest.mark.parametrize(
    "raw",
    [
        "tcp:192.168.1.20:5901",  # LAN: never
        "tcp:0.0.0.0:5901",
        "tcp:127.0.0.1",
        "tcp:127.0.0.1:x",
        "vnc://127.0.0.1:5901",
        "unix:relative.sock",
    ],
)
def test_parse_rejects(raw, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(ValueError):
        parse_target(raw)


def test_unix_target_needs_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert parse_target("unix:/run/user/1/hlc-vnc.sock").path == (
        "/run/user/1/hlc-vnc.sock"
    )
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(ValueError, match="Linux"):
        parse_target("unix:/run/user/1/hlc-vnc.sock")


def test_not_configured_by_default(client):
    body = client.get("/api/desktop/status").json()
    assert set(body) == {
        "status",
        "message",
        "label",
        "can_control",
        "viewers",
        "connection_url",
    }
    assert body["status"] == "not_configured"
    assert body["connection_url"] is None and body["can_control"] is False
    assert "DESKTOP_VNC" in body["message"]
    caps = client.get("/api/system").json()["capabilities"]
    assert caps["desktop"]["status"] == "not_configured"
    res = client.post("/api/desktop/start", json={}, headers=ORIGIN)
    assert res.status_code == 503 and res.json()["code"] == "desktop_not_configured"


def test_non_loopback_target_is_ignored(cfg, caplog):
    client = signed_in(cfg, desktop_vnc="tcp:192.168.1.20:5901")
    assert "DESKTOP_VNC ignored" in caplog.text
    body = client.get("/api/desktop/status").json()
    assert body["status"] == "not_configured" and "not loopback" in body["message"]


def test_bad_unit_name_is_ignored(cfg, rfb_port):
    client = signed_in(
        cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}", desktop_unit="--user=evil"
    )
    assert client.get("/api/desktop/status").json()["can_control"] is False


# --- status ---------------------------------------------------------------------


def test_running_when_vnc_answers(cfg, rfb_port):
    client = signed_in(
        cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}", desktop_label="Dell"
    )
    body = client.get("/api/desktop/status").json()
    assert body["status"] == "running"
    assert body["connection_url"] == WS
    assert body["label"] == "Dell"
    assert body["can_control"] is False  # no unit: managed on the server
    caps = client.get("/api/system").json()["capabilities"]
    assert caps["desktop"] == {"status": "supported", "message": None}


@pytest.mark.parametrize("port_fixture", ["closed_port", "hangup_port"])
def test_stopped_when_nothing_answers(cfg, request, port_fixture):
    port = request.getfixturevalue(port_fixture)
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{port}")
    body = client.get("/api/desktop/status").json()
    assert body["status"] == "stopped" and body["connection_url"] is None


@pytest.mark.parametrize(
    ("unit_state", "expected"),
    [
        ("active", "running"),
        ("activating", "starting"),
        ("failed", "error"),
        ("inactive", "stopped"),
        ("deactivating", "stopped"),
        ("unknown", "stopped"),
    ],
)
def test_unit_state_mapping(cfg, rfb_port, monkeypatch, unit_state, expected):
    calls = fake_systemctl(monkeypatch, stdout=f"{unit_state}\n")
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}", desktop_unit=UNIT)
    body = client.get("/api/desktop/status").json()
    assert body["status"] == expected and body["can_control"] is True
    assert calls[0][0] == ["systemctl", "--user", "is-active", UNIT]


def test_unit_active_but_vnc_not_ready_is_starting(cfg, closed_port, monkeypatch):
    fake_systemctl(monkeypatch, stdout="active\n")
    client = signed_in(
        cfg, desktop_vnc=f"tcp:127.0.0.1:{closed_port}", desktop_unit=UNIT
    )
    assert client.get("/api/desktop/status").json()["status"] == "starting"


def test_systemctl_missing_is_error(cfg, rfb_port, monkeypatch):
    fake_systemctl(monkeypatch, raises=FileNotFoundError())
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}", desktop_unit=UNIT)
    assert client.get("/api/desktop/status").json()["status"] == "error"


# --- start / stop -----------------------------------------------------------------


@pytest.mark.parametrize("action", ["start", "stop"])
def test_start_stop_run_fixed_argv(cfg, rfb_port, monkeypatch, action):
    calls = fake_systemctl(monkeypatch)
    closed = []
    monkeypatch.setattr(Desktop, "close_viewers", lambda self: closed.append(1))
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}", desktop_unit=UNIT)
    res = client.post(f"/api/desktop/{action}", json={"unit": "evil"}, headers=ORIGIN)
    assert res.status_code == 204
    argv, kwargs = calls[-1]
    assert argv == ["systemctl", "--user", action, UNIT]  # nothing from the request
    assert not kwargs.get("shell") and kwargs["timeout"] == 15
    assert closed == ([1] if action == "stop" else [])


def test_start_stop_unmanaged_without_unit(cfg, rfb_port):
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}")
    for action in ("start", "stop"):
        res = client.post(f"/api/desktop/{action}", json={}, headers=ORIGIN)
        assert res.status_code == 409 and res.json()["code"] == "desktop_unmanaged"


@pytest.mark.parametrize(
    ("kwargs", "text"),
    [
        ({"returncode": 1}, "exit 1"),
        ({"raises": FileNotFoundError()}, "not available"),
        ({"raises": subprocess.TimeoutExpired("systemctl", 15)}, "15 s"),
    ],
)
def test_start_failure_is_mapped(cfg, rfb_port, monkeypatch, kwargs, text):
    fake_systemctl(monkeypatch, **kwargs)
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}", desktop_unit=UNIT)
    res = client.post("/api/desktop/start", json={}, headers=ORIGIN)
    body = res.json()
    assert res.status_code == 500 and body["code"] == "desktop_start_failed"
    assert text in body["message"] and "/home/" not in body["message"]  # no stderr


def test_desktop_writes_are_guarded(cfg, rfb_port):
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}", desktop_unit=UNIT)
    assert client.post("/api/desktop/stop", json={}).status_code == 403  # no Origin
    anon = TestClient(client.app)
    assert anon.post("/api/desktop/stop", json={}, headers=ORIGIN).status_code == 401


# --- WebSocket bridge -------------------------------------------------------------


def test_bridge_round_trip(cfg, rfb_port):
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}")
    with client.websocket_connect(WS, headers=ORIGIN, subprotocols=["binary"]) as ws:
        assert ws.accepted_subprotocol == "binary"
        assert ws.receive_bytes() == BANNER
        ws.send_bytes(b"\x00hello\xff")
        assert ws.receive_bytes() == b"\x00hello\xff"
        assert client.get("/api/desktop/status").json()["viewers"] == 1
    assert client.get("/api/desktop/status").json()["viewers"] == 0


def test_bridge_closes_when_desktop_is_down(cfg, closed_port):
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{closed_port}")
    with (
        client.websocket_connect(WS, headers=ORIGIN) as ws,
        pytest.raises(WebSocketDisconnect) as exc,
    ):
        ws.receive_bytes()
    assert exc.value.code == 1011


def _refused(client: TestClient, headers: dict, url: str = WS) -> int:
    with (
        pytest.raises(WebSocketDisconnect) as exc,
        client.websocket_connect(url, headers=headers),
    ):
        pass
    return exc.value.code


def test_ws_refused_without_session(cfg, rfb_port):
    anon = TestClient(create_app(replace(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}")))
    assert _refused(anon, ORIGIN) == 1008


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "https://evil.example"},
        {"Origin": "http://testserver.evil.example"},
    ],
)
def test_ws_refused_with_bad_origin(cfg, rfb_port, headers):
    client = signed_in(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}")
    assert _refused(client, headers) == 1008  # session alone is not enough


def test_ws_dev_loopback_open_but_not_to_rebinding(cfg, rfb_port):
    app = create_app(replace(cfg, desktop_vnc=f"tcp:127.0.0.1:{rfb_port}"))
    client = TestClient(app)
    local_ws = "ws://127.0.0.1:8000" + WS  # websocket_connect ignores base_url
    with client.websocket_connect(local_ws, headers={"Origin": LOCAL}) as ws:  # D-25
        assert ws.receive_bytes() == BANNER
    evil = {"Host": "evil.example:8000", "Origin": "http://evil.example:8000"}
    assert _refused(client, evil, local_ws) == 1008


def test_close_viewers_signals_every_bridge(cfg):
    desktop = Desktop(cfg)
    with desktop.viewer() as first, desktop.viewer() as second:
        assert desktop.viewers == 2
        desktop.close_viewers()
        assert first.is_set() and second.is_set()
    assert desktop.viewers == 0


def test_open_viewer_counts_as_running_without_probing(cfg, closed_port):
    desktop = Desktop(replace(cfg, desktop_vnc=f"tcp:127.0.0.1:{closed_port}"))
    assert desktop.status()[0] == "stopped"
    with desktop.viewer():
        assert desktop.status()[0] == "running"  # the bridge is the proof; no probe
