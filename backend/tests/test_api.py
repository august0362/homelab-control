from __future__ import annotations

import sys
from dataclasses import replace

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app
from app.services import platform_adapter
from app.services.device import CAPABILITY_STATUSES, device_id


@pytest.fixture
def cfg(tmp_path):
    return replace(
        settings, state_dir=tmp_path / "state", device_id=None, frontend_dist=None
    )


@pytest.fixture
def client(cfg):
    return TestClient(create_app(cfg))


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "timestamp", "version"}


def test_system_shape(client):
    body = client.get("/api/system").json()
    assert set(body) >= {"timestamp", "device", "os", "hardware", "app", "capabilities"}
    assert set(body["device"]) == {"id", "label", "role", "platform", "device_type"}
    assert body["device"]["role"] in {"dev", "production"}
    caps = body["capabilities"]
    assert set(caps) == {
        "metrics",
        "temperature",
        "fans",
        "battery",
        "desktop",
        "files",
        "services",
    }
    assert all(c["status"] in CAPABILITY_STATUSES for c in caps.values())
    assert caps["metrics"]["status"] == "supported"
    assert caps["desktop"]["status"] == "not_configured"


def test_unknown_route_is_json_404(client):
    res = client.get("/api/nope")
    assert res.status_code == 404
    assert res.json() == {"code": "not_found", "message": "Not Found"}


def test_api_is_get_only(client):
    for route in client.app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            assert route.methods <= {"GET", "HEAD"}, route.path


def test_frontend_served_without_hiding_api_404(cfg, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>t</title>")
    client = TestClient(create_app(replace(cfg, frontend_dist=dist)))
    assert "<title>t</title>" in client.get("/").text
    assert client.get("/api/health").status_code == 200
    res = client.get("/api/nope")
    assert res.status_code == 404 and res.json()["code"] == "not_found"


@pytest.mark.parametrize(
    ("plat", "name"), [("win32", "windows"), ("linux", "linux"), ("darwin", "generic")]
)
def test_adapter_selection(monkeypatch, plat, name):
    monkeypatch.setattr(sys, "platform", plat)
    assert platform_adapter.get_adapter().name == name


def test_device_id_persists(cfg):
    first = device_id(cfg)
    assert first == device_id(cfg)
    assert (cfg.state_dir / "device_id").read_text().strip() == first
    assert device_id(replace(cfg, device_id="fixed")) == "fixed"
