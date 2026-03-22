"""Tests for /v1/watchlist and alert ordering with watchlist."""

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.modules.alerts.models import Alert
from app.modules.auth.models import User
from app.modules.vessels.models import WatchlistEntry
from tests.conftest import TestingSessionLocal


def _register_login_with_role(client: TestClient, role: str) -> str:
    u = f"u_{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/v1/auth/register",
        json={"username": u, "email": f"{u}@test.local", "password": "p" * 12},
    )
    assert r.status_code == 200, r.text
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


def _register_login_viewer(client: TestClient) -> str:
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


def test_watchlist_requires_auth(client: TestClient):
    assert client.get("/v1/watchlist").status_code == 401


def test_watchlist_forbidden_viewer(client: TestClient):
    token = _register_login_viewer(client)
    r = client.get("/v1/watchlist", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_watchlist_crud_analyst(client: TestClient):
    token = _register_login_with_role(client, "analyst")
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/v1/watchlist",
        headers=h,
        json={"mmsi": "123456789", "label": "Suspicious", "priority": "high"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mmsi"] == "123456789"
    assert body["label"] == "Suspicious"
    assert body["priority"] == "high"
    assert body["is_active"] is True

    listed = client.get("/v1/watchlist", headers=h)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["mmsi"] == "123456789"

    del_r = client.delete("/v1/watchlist/123456789", headers=h)
    assert del_r.status_code == 204

    empty = client.get("/v1/watchlist", headers=h)
    assert empty.json() == []


def test_watchlist_admin_ok(client: TestClient):
    from tests.conftest import register_and_login_as_admin

    token = register_and_login_as_admin(client)
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/v1/watchlist", headers=h)
    assert r.status_code == 200


def test_alerts_ordered_watchlist_first(client: TestClient):
    token = _register_login_with_role(client, "analyst")
    db = TestingSessionLocal()
    try:
        user = db.query(User).first()
        assert user is not None
        db.add(
            WatchlistEntry(
                organisation_id=user.organisation_id,
                mmsi="100000000",
                label="w",
                priority="high",
                added_by_id=user.id,
                is_active=True,
            )
        )
        db.add(
            Alert(
                organisation_id=user.organisation_id,
                timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
                mmsi="200000000",
                type="TELEPORT",
                severity=50,
                summary="newer non-wl",
                evidence={},
                status="new",
            )
        )
        db.add(
            Alert(
                organisation_id=user.organisation_id,
                timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
                mmsi="100000000",
                type="TELEPORT",
                severity=50,
                summary="older wl",
                evidence={},
                status="new",
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.get(
        "/v1/alerts?limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["mmsi"] == "100000000"
    assert data[1]["mmsi"] == "200000000"
