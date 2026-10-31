from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.config import set_env_value
from app.main import create_app
from app.services.auth import (
    COOKIE,
    LOCKOUT_SECONDS,
    MAX_FAILURES,
    SESSION_TTL,
    hash_password,
    verify_password,
)
from app.services.device import validate_label
from tests.conftest import ORIGIN, PASSWORD, login


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


def patch(client: TestClient, label, headers=ORIGIN):
    return client.patch("/api/device", json={"label": label}, headers=headers)


# --- password hashing ---------------------------------------------------------


def test_hash_roundtrip_and_salt():
    stored = hash_password("s3cret-passphrase")
    assert stored.startswith("scrypt$") and "s3cret" not in stored
    assert verify_password("s3cret-passphrase", stored)
    assert not verify_password("wrong-passphrase", stored)
    assert hash_password("s3cret-passphrase") != stored  # random salt
    assert not verify_password("x", "garbage")
    assert not verify_password("x", "scrypt$a$b$c$d$e")


def test_set_env_value_replaces_or_appends(tmp_path):
    env = tmp_path / ".env"
    env.write_text("HOST=127.0.0.1\nOWNER_PASSWORD_HASH=\nPORT=8000\n")
    set_env_value(env, "OWNER_PASSWORD_HASH", "scrypt$1$2$3$a$b")
    assert env.read_text().splitlines() == [
        "HOST=127.0.0.1",
        "OWNER_PASSWORD_HASH='scrypt$1$2$3$a$b'",
        "PORT=8000",
    ]
    set_env_value(env, "ALLOWED_ORIGINS", "x")
    assert env.read_text().splitlines()[-1] == "ALLOWED_ORIGINS='x'"


# --- access control -----------------------------------------------------------


def test_health_public_rest_needs_session(anon):
    assert anon.get("/api/health").status_code == 200
    for path in ("/api/system", "/api/metrics", "/api/nope"):
        res = anon.get(path)
        assert res.status_code == 401, path
        assert res.json() == {"code": "unauthorized", "message": "Sign in to continue."}
    assert anon.get("/api/auth/session").json() == {
        "authenticated": False,
        "login_required": True,
        "configured": True,
        "expires_at": None,
    }


def test_login_ok_sets_strict_cookie(anon):
    res = login(anon)
    assert res.status_code == 204
    cookie = res.headers["set-cookie"].lower()
    for flag in ("httponly", "samesite=strict", "path=/", f"max-age={SESSION_TTL}"):
        assert flag in cookie
    assert "secure" not in cookie  # dev over http
    assert PASSWORD not in res.headers["set-cookie"]
    assert anon.get("/api/system").status_code == 200
    session = anon.get("/api/auth/session").json()
    assert session["authenticated"] and session["expires_at"]


def test_production_cookie_is_secure(cfg):
    client = TestClient(create_app(replace(cfg, machine_role="production")))
    res = login(client)
    assert res.status_code == 204
    assert "secure" in res.headers["set-cookie"].lower()


def test_logout_clears_cookie(client):
    res = client.post("/api/auth/logout", json={}, headers=ORIGIN)
    assert res.status_code == 204
    assert f'{COOKIE}=""' in res.headers["set-cookie"]
    assert client.get("/api/metrics").status_code == 401


def test_wrong_password_then_lockout(anon):
    clock = FakeClock()
    anon.app.state.auth._clock = clock
    for _ in range(MAX_FAILURES):
        res = login(anon, "wrong password!")
        assert res.status_code == 401
        assert res.json()["code"] == "invalid_credentials"
    res = login(anon)  # even the right password waits out the lockout
    assert res.status_code == 429
    assert res.json()["code"] == "too_many_attempts"
    assert res.headers["retry-after"] == str(LOCKOUT_SECONDS)
    clock.now += LOCKOUT_SECONDS
    assert login(anon).status_code == 204


def test_not_configured_is_503_without_bypass(cfg):
    client = TestClient(create_app(replace(cfg, owner_password_hash=None)))
    res = login(client)
    assert res.status_code == 503
    assert res.json()["code"] == "auth_not_configured"
    assert "set-password" in res.json()["message"]
    assert client.get("/api/auth/session").json()["configured"] is False
    assert client.get("/api/system").status_code == 401


def test_expired_and_tampered_cookies_rejected(client):
    auth = client.app.state.auth
    token = client.cookies[COOKIE]
    expires, sig = token.split(".")
    for bad in (
        f"{int(expires) + 1}.{sig}",  # extended expiry, old signature
        f"{expires}.{'0' * len(sig)}",
        "garbage",
        f"{expires}.",
    ):
        client.cookies.set(COOKIE, bad)
        assert client.get("/api/metrics").status_code == 401, bad
    client.cookies.set(COOKIE, token)
    assert client.get("/api/metrics").status_code == 200
    auth._clock = lambda: int(expires)  # the moment it expires
    assert client.get("/api/metrics").status_code == 401


def test_session_survives_restart(cfg, client):
    restarted = TestClient(create_app(cfg))
    restarted.cookies.set(COOKIE, client.cookies[COOKIE])
    assert restarted.get("/api/system").status_code == 200


def test_new_password_signs_everyone_out(cfg, client):
    new_cfg = replace(cfg, owner_password_hash=hash_password("another password"))
    restarted = TestClient(create_app(new_cfg))
    restarted.cookies.set(COOKIE, client.cookies[COOKIE])
    assert restarted.get("/api/system").status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {},  # no Origin
        {"Origin": "https://evil.example"},
        {"Origin": "null"},
        {"Origin": "http://testserver.evil.example"},
    ],
)
def test_write_with_bad_origin_is_403(client, headers):
    for res in (
        patch(client, "x", headers),
        client.post("/api/auth/login", json={"password": PASSWORD}, headers=headers),
    ):
        assert res.status_code == 403
        assert res.json()["code"] == "forbidden_origin"


def test_write_needs_json_content_type(client):
    res = client.patch(
        "/api/device",
        content='{"label": "x"}',
        headers={**ORIGIN, "Content-Type": "text/plain"},
    )
    assert res.status_code == 403


def test_allowed_origins(cfg):
    origin = "https://dell.tailnet.ts.net"
    client = TestClient(create_app(replace(cfg, allowed_origins=(origin,))))
    assert login(client).status_code == 204
    assert patch(client, "Dell", {"Origin": origin}).status_code == 200


def test_write_needs_session(anon):
    assert patch(anon, "x").status_code == 401


# --- dev on loopback needs no login (D-25) ---------------------------------------

LOCAL = "http://127.0.0.1:8000"


def test_dev_on_loopback_is_open(cfg):
    client = TestClient(
        create_app(replace(cfg, owner_password_hash=None)), base_url=LOCAL
    )
    assert client.get("/api/system").status_code == 200
    assert (
        client.get("/api/metrics", headers={"Host": "localhost:5173"}).status_code
        == 200
    )
    assert client.get("/api/auth/session").json() == {
        "authenticated": True,
        "login_required": False,
        "configured": False,
        "expires_at": None,
    }
    # Writes still need Origin + JSON.
    assert patch(client, "x", {}).status_code == 403
    assert patch(client, "Laptop", {"Origin": LOCAL}).status_code == 200


def test_dns_rebinding_host_is_not_open(cfg):
    client = TestClient(create_app(cfg), base_url=LOCAL)
    res = client.get("/api/system", headers={"Host": "evil.example:8000"})
    assert res.status_code == 401


@pytest.mark.parametrize(
    "changes", [{"machine_role": "production"}, {"host": "0.0.0.0"}]
)
def test_login_required_outside_dev_loopback(cfg, changes):
    client = TestClient(create_app(replace(cfg, **changes)), base_url=LOCAL)
    assert client.get("/api/system").status_code == 401
    assert client.get("/api/auth/session").json()["login_required"] is True


# --- device rename (D-24) -------------------------------------------------------


def test_rename_reset_and_sources(cfg, client):
    default = client.get("/api/system").json()["device"]
    assert default["label_source"] == "hostname"

    res = patch(client, "  Dell server  ")
    assert res.status_code == 200
    assert res.json()["label"] == "Dell server"
    assert res.json()["label_source"] == "custom"
    assert client.get("/api/metrics").json()["device"]["label"] == "Dell server"
    assert client.get("/api/system").json()["device"]["label"] == "Dell server"

    res = patch(client, None)
    assert res.json() == default
    assert not (cfg.state_dir / "device.json").exists()


def test_env_label_is_the_default(cfg):
    client = TestClient(create_app(replace(cfg, device_label="this ASUS")))
    login(client)
    assert patch(client, "Laptop").json()["label"] == "Laptop"
    res = patch(client, None).json()
    assert (res["label"], res["label_source"]) == ("this ASUS", "env")


def test_rename_persists_across_instances(cfg, client):
    patch(client, "Phòng khách ☕")
    restarted = TestClient(create_app(cfg))
    login(restarted)
    device = restarted.get("/api/metrics").json()["device"]
    assert (device["label"], device["label_source"]) == ("Phòng khách ☕", "custom")


@pytest.mark.parametrize(
    "label", ["", "   ", "x" * 41, "bad\nname", "tab\there", "nul\x00"]
)
def test_rename_validation(client, label):
    res = patch(client, label)
    assert res.status_code == 422
    assert res.json()["code"] == "invalid_label"
    assert res.json()["message"]
    assert client.get("/api/system").json()["device"]["label_source"] == "hostname"


def test_rename_body_shape(client):
    for body in ({}, {"label": 5}):
        res = client.patch("/api/device", json=body, headers=ORIGIN)
        assert res.status_code == 422
        assert res.json()["code"] == "validation_error"


def test_validate_label_limits():
    assert validate_label("x" * 40) == "x" * 40
    assert validate_label(" a b ") == "a b"


def test_broken_device_file_falls_back(cfg, client):
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    (cfg.state_dir / "device.json").write_text("{not json")
    assert client.get("/api/system").json()["device"]["label_source"] == "hostname"


def test_set_password_cli(monkeypatch, tmp_path, capsys):
    import app.__main__ as cli

    monkeypatch.setattr(cli, "BACKEND_DIR", tmp_path)
    pw = "long enough pw"
    answers = iter(["short", pw, "different pw!", pw, pw])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(answers))
    assert cli.set_password() == 1  # too short
    assert cli.set_password() == 1  # mismatch
    assert not (tmp_path / ".env").exists()
    assert cli.set_password() == 0
    stored = (tmp_path / ".env").read_text().strip().split("=", 1)[1].strip("'")
    assert verify_password(pw, stored)
    assert pw not in capsys.readouterr().out
