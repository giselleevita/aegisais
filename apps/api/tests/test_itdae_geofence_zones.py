"""CRUD and access control for ITDAE geofence zones (Sprint 3 Task 3.1)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.modules.auth.models import User
from tests.conftest import TestingSessionLocal, register_and_login_as_admin

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [10.0, 54.0],
            [11.0, 54.0],
            [11.0, 55.0],
            [10.0, 55.0],
            [10.0, 54.0],
        ]
    ],
}


def _register_and_login_as_role(client: TestClient, role: str) -> str:
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


def test_zones_list_viewer_ok(client: TestClient):
    token = _register_and_login_as_role(client, "viewer")
    r = client.get(
        "/api/v1/itdae/zones",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


def test_zones_crud_admin_and_analyst(client: TestClient):
    admin_tok = register_and_login_as_admin(client)
    analyst_tok = _register_and_login_as_role(client, "analyst")

    # List (analyst) — seed may have Baltic zones
    r = client.get(
        "/api/v1/itdae/zones",
        headers={"Authorization": f"Bearer {analyst_tok}"},
    )
    assert r.status_code == 200
    initial = r.json()
    assert isinstance(initial, list)

    # Create (admin)
    r = client.post(
        "/api/v1/itdae/zones",
        headers={"Authorization": f"Bearer {admin_tok}"},
        json={
            "name": f"Test Zone {uuid.uuid4().hex[:8]}",
            "description": "pytest",
            "risk_level": "high",
            "polygon_geojson": SAMPLE_POLYGON,
        },
    )
    assert r.status_code == 201, r.text
    z = r.json()
    zone_id = z["id"]
    assert z["is_active"] is True
    assert z["polygon_geojson"]["type"] == "Polygon"

    # Detail (analyst)
    r = client.get(
        f"/api/v1/itdae/zones/{zone_id}",
        headers={"Authorization": f"Bearer {analyst_tok}"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == zone_id

    # Soft delete (admin)
    r = client.delete(
        f"/api/v1/itdae/zones/{zone_id}",
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert r.status_code == 204

    # Still retrievable by id, inactive
    r = client.get(
        f"/api/v1/itdae/zones/{zone_id}",
        headers={"Authorization": f"Bearer {analyst_tok}"},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # Not in active list
    r = client.get(
        "/api/v1/itdae/zones",
        headers={"Authorization": f"Bearer {analyst_tok}"},
    )
    assert r.status_code == 200
    ids = {row["id"] for row in r.json()}
    assert zone_id not in ids


def test_zones_invalid_polygon_400(client: TestClient):
    admin_tok = register_and_login_as_admin(client)
    r = client.post(
        "/api/v1/itdae/zones",
        headers={"Authorization": f"Bearer {admin_tok}"},
        json={
            "name": "Bad poly",
            "risk_level": "low",
            "polygon_geojson": {"type": "Point", "coordinates": [1, 2]},
        },
    )
    assert r.status_code == 400
