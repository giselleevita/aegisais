"""Minimal tests for /v1/sais (S-AIS stub)."""

import uuid

from fastapi.testclient import TestClient

from app.modules.auth.models import User
from tests.conftest import TestingSessionLocal


def _token_for_role(client: TestClient, role: str) -> str:
    u = f"u_{uuid.uuid4().hex[:12]}"
    assert (
        client.post(
            "/v1/auth/register",
            json={"username": u, "email": f"{u}@test.local", "password": "p" * 12},
        ).status_code
        == 200
    )
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == u).first()
        assert user is not None
        user.role = role
        db.commit()
    finally:
        db.close()
    login = client.post(
        "/v1/auth/login",
        data={"username": u, "password": "p" * 12},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_sais_health_and_status_require_auth(client: TestClient):
    assert client.get("/v1/sais/health").status_code == 401
    assert client.get("/v1/sais/status").status_code == 401


def test_sais_forbidden_for_viewer(client: TestClient):
    token = _token_for_role(client, "viewer")
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/v1/sais/health", headers=h).status_code == 403
    assert client.get("/v1/sais/status", headers=h).status_code == 403


def test_sais_ok_for_analyst(client: TestClient):
    token = _token_for_role(client, "analyst")
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/v1/sais/health", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["module"] == "sais"

    s = client.get("/v1/sais/status", headers=h)
    assert s.status_code == 200
    st = s.json()
    assert st["provider"] == "none"
    assert st["api_key_configured"] is False
    assert st["api_key_masked"] is None


def test_stub_client_returns_empty_and_logs(caplog):
    from datetime import datetime, timezone

    from app.modules.sais.client import StubSatelliteAISClient

    caplog.set_level("INFO", logger="aegisais.sais.client")
    c = StubSatelliteAISClient()
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t1 = datetime(2025, 1, 2, tzinfo=timezone.utc)
    assert c.fetch_vessel_positions("123456789", (t0, t1)) == []
    assert any("StubSatelliteAISClient" in rec.message for rec in caplog.records)
