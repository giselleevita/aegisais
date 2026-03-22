"""Smoke tests for authenticated alerts and vessel list endpoints."""

import uuid

from fastapi.testclient import TestClient


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
