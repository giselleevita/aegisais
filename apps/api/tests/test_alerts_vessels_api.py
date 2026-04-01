"""Smoke tests for authenticated alerts and vessel list endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.modules.auth.models import User
from app.modules.vessels.models import VesselLatest
from tests.conftest import TestingSessionLocal


def _register_login(client: TestClient) -> str:
    u = f"u_{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/v1/auth/register",
        json={"username": u, "email": f"{u}@test.local", "password": "p" * 12},
    )
    assert r.status_code == 200, r.text
    login = client.post(
        "/v1/auth/login",
        data={"username": u, "password": "p" * 12},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_list_alerts_unauthorized(client: TestClient):
    r = client.get("/v1/alerts")
    assert r.status_code == 401


def test_list_alerts_empty_ok(client: TestClient):
    token = _register_login(client)
    r = client.get("/v1/alerts", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_list_vessels_empty_ok(client: TestClient):
    token = _register_login(client)
    r = client.get("/v1/vessels", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_list_vessels_org_scoped(client: TestClient):
    token = _register_login(client)

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username.isnot(None)).order_by(User.id.desc()).first()
        assert user is not None

        db.add_all(
            [
                VesselLatest(
                    mmsi="111111111",
                    organisation_id=user.organisation_id,
                    timestamp=datetime.now(timezone.utc),
                    lat=1.0,
                    lon=2.0,
                    sog=3.0,
                    cog=4.0,
                    heading=5.0,
                    last_alert_severity=10,
                ),
                VesselLatest(
                    mmsi="222222222",
                    organisation_id=1 if user.organisation_id != 1 else 2,
                    timestamp=datetime.now(timezone.utc),
                    lat=9.0,
                    lon=8.0,
                    sog=7.0,
                    cog=6.0,
                    heading=5.0,
                    last_alert_severity=99,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    r = client.get("/v1/vessels", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    payload = r.json()
    assert len(payload) == 1
    assert payload[0]["mmsi"] == "111111111"
