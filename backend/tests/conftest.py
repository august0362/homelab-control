from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app
from app.services.auth import hash_password

PASSWORD = "correct horse battery"
PASSWORD_HASH = hash_password(PASSWORD)
ORIGIN = {"Origin": "http://testserver"}  # TestClient's Host


def login(client: TestClient, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"password": password}, headers=ORIGIN)


@pytest.fixture
def cfg(tmp_path):
    return replace(
        settings,
        state_dir=tmp_path / "state",
        device_id=None,
        device_label=None,
        frontend_dist=None,
        machine_role="dev",
        owner_password_hash=PASSWORD_HASH,
        allowed_origins=(),
    )


@pytest.fixture
def anon(cfg):
    """Client without a session."""
    return TestClient(create_app(cfg))


@pytest.fixture
def client(anon):
    """Signed-in client: the session cookie is kept by the TestClient."""
    assert login(anon).status_code == 204
    return anon
