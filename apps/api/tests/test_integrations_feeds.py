"""Tests for GET /v1/integrations/feeds."""

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


def test_integration_feeds_requires_auth(client: TestClient):
    assert client.get("/v1/integrations/feeds").status_code == 401


def test_integration_feeds_ok_for_viewer(client: TestClient):
    token = _token_for_role(client, "viewer")
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/v1/integrations/feeds", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert "timestamp" in body
    assert "feeds" in body
    assert len(body["feeds"]) == 4
    ids = {f["id"] for f in body["feeds"]}
    assert ids == {"terrestrial_ais", "satellite_ais", "sar_eo", "rf_sigint"}
    for f in body["feeds"]:
        assert f["status"] in ("ready", "partial", "disconnected", "unavailable", "error")
        assert "label" in f
        assert "mode" in f
        assert "licenceClass" in f


def test_integration_feed_errors_never_expose_provider_tokens(client: TestClient, monkeypatch):
    from app.modules.itdae.ingestion.aisstream_client import aisstream_client

    token = _token_for_role(client, "viewer")
    monkeypatch.setattr(
        aisstream_client,
        "_stats",
        {"last_error": "websocket rejected api_key=super-secret-provider-token"},
    )
    response = client.get(
        "/v1/integrations/feeds",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    serialized = response.text
    assert "super-secret-provider-token" not in serialized
    terrestrial = next(row for row in response.json()["feeds"] if row["id"] == "terrestrial_ais")
    assert terrestrial["errorCode"] == "feed_runtime_error"
