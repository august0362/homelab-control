from __future__ import annotations

import sys
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import platform_adapter
from app.services.device import CAPABILITY_STATUSES, device_id

# Every write route, each one behind the guard (session + Origin + JSON).
WRITE_ROUTES = {
    ("/api/auth/login", "POST"),
    ("/api/auth/logout", "POST"),
    ("/api/device", "PATCH"),
    ("/api/desktop/start", "POST"),
    ("/api/desktop/stop", "POST"),
    ("/api/power/sleep", "POST"),
    ("/api/power/wake", "POST"),
    ("/api/power/cleanup", "POST"),
    ("/api/power/reboot", "POST"),
}


def test_health(anon):
    res = anon.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "timestamp", "version"}


def test_system_shape(client):
    body = client.get("/api/system").json()
    assert set(body) >= {"timestamp", "device", "os", "hardware", "app", "capabilities"}
    assert set(body["device"]) == {
        "id",
        "label",
        "label_source",
        "role",
        "platform",
        "device_type",
    }
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


def test_only_allowlisted_write_routes(client):
    # app.routes no longer lists included routers (FastAPI 0.16x); OpenAPI does.
    paths = client.app.openapi()["paths"]
    assert "/api/metrics" in paths  # sanity: the schema really lists our routes
    writes = {
        (path, method.upper())
        for path, ops in paths.items()
        for method in ops
        if method not in {"get", "head"}
    }
    assert writes == WRITE_ROUTES


def test_frontend_served_without_hiding_api_404(cfg, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>t</title>")
    client = TestClient(create_app(replace(cfg, frontend_dist=dist)))
    assert "<title>t</title>" in client.get("/").text  # the UI itself is public
    assert client.get("/api/health").status_code == 200
    res = client.get("/api/nope")
    assert res.status_code == 401 and res.json()["code"] == "unauthorized"


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
