"""Tests for sanctions API hardening and watchlist operations."""

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from tests.conftest import TestingSessionLocal, register_and_login_as_admin


def _register_login_with_role(client, role: str) -> str:
    username = f"s_{uuid.uuid4().hex[:12]}"
    response = client.post(
        "/v1/auth/register",
        json={"username": username, "email": f"{username}@test.local", "password": "p" * 12},
    )
    assert response.status_code == 200, response.text

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        user.role = role
        db.commit()
    finally:
        db.close()

    login = client.post("/v1/auth/login", data={"username": username, "password": "p" * 12})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_sanctions_check_requires_auth(client):
    response = client.get("/v1/sanctions/check/123456789")
    assert response.status_code == 401


def test_sanctions_check_analyst_ok(client):
    from app.modules.sanctions import service as svc

    token = _register_login_with_role(client, "analyst")
    svc._sanctioned_names = {"BLACK PEARL"}
    try:
        response = client.get(
            "/v1/sanctions/check/123456789",
            params={"vessel_name": "Black Pearl"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["sanctioned"] is True
    finally:
        svc._sanctioned_names = set()


def test_sanctions_reload_requires_admin(client):
    token = _register_login_with_role(client, "analyst")
    response = client.post(
        "/v1/sanctions/watchlist/reload",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_sanctions_reload_uses_configured_path_and_audits(client, tmp_path, monkeypatch):
    watchlist_path = tmp_path / "sanctions.json"
    watchlist_path.write_text(
        json.dumps(
            {
                "mmsi": ["123456789"],
                "imo": ["7654321"],
                "names": ["BLACK PEARL"],
                "_source": "offline import",
                "_updated_at": "2026-04-09T12:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.modules.sanctions.service.settings.SANCTIONS_WATCHLIST_PATH", str(watchlist_path))

    token = register_and_login_as_admin(client)
    response = client.post(
        "/v1/sanctions/watchlist/reload",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"mmsi_count": 1, "imo_count": 1, "name_count": 1}

    status = client.get(
        "/v1/sanctions/watchlist/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status.status_code == 200, status.text
    assert status.json()["path"] == str(watchlist_path)
    assert status.json()["source"] == "offline import"

    db = TestingSessionLocal()
    try:
        audit = db.query(AuditLog).filter(AuditLog.action == "sanctions.watchlist.reload").one()
        assert audit.resource_type == "sanctions_watchlist"
        assert audit.details["path"] == str(watchlist_path)
    finally:
        db.close()


def test_sanctions_sync_requires_admin(client):
    token = _register_login_with_role(client, "viewer")
    response = client.post(
        "/v1/sanctions/watchlist/sync",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_sanctions_sync_admin_calls_sources_and_audits(client, monkeypatch):
    token = register_and_login_as_admin(client)
    mocked_sync = AsyncMock(return_value={"mmsi": 2, "imo": 1, "names": 3})
    monkeypatch.setattr("app.modules.sanctions.router.update_watchlist_from_official_sources", mocked_sync)
    monkeypatch.setattr(
        "app.modules.sanctions.router.get_watchlist_status",
        lambda: {
            "path": "/tmp/sanctions.json",
            "exists": True,
            "mmsi_count": 2,
            "imo_count": 1,
            "name_count": 3,
            "source": "OFAC SDN + EU Consolidated + UN Consolidated",
            "updated_at": "2026-04-09T12:30:00+00:00",
        },
    )

    response = client.post(
        "/v1/sanctions/watchlist/sync",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "synced"
    assert body["source"] == "OFAC SDN + EU Consolidated + UN Consolidated"
    mocked_sync.assert_awaited_once()

    db = TestingSessionLocal()
    try:
        audit = db.query(AuditLog).filter(AuditLog.action == "sanctions.watchlist.sync").one()
        assert audit.details["mmsi"] == 2
        assert audit.details["path"] == "/tmp/sanctions.json"
    finally:
        db.close()


def test_flag_hopping_analysis_requires_auth(client):
    response = client.post(
        "/v1/sanctions/analysis/flag-hopping",
        json={"snapshots": []},
    )
    assert response.status_code == 401


def test_flag_hopping_analysis_detects_for_analyst(client):
    token = _register_login_with_role(client, "analyst")
    response = client.post(
        "/v1/sanctions/analysis/flag-hopping",
        json={
            "snapshots": [
                {
                    "mmsi": "111111111",
                    "imo": "7654321",
                    "vessel_name": "Shadow Fleet One",
                    "flag_state": "PA",
                    "timestamp": "2026-03-01T00:00:00Z",
                },
                {
                    "mmsi": "222222222",
                    "imo": "7654321",
                    "vessel_name": "Shadow Fleet One",
                    "flag_state": "GA",
                    "timestamp": "2026-03-12T00:00:00Z",
                },
            ]
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["detected"] is True
    assert body["alert"]["type"] == "FLAG_HOPPING"


def test_dark_activity_analysis_detects_for_analyst(client):
    token = _register_login_with_role(client, "analyst")
    response = client.post(
        "/v1/sanctions/analysis/dark-activity",
        json={
            "mmsi": "123456789",
            "dark_duration_sec": 10800,
            "last_known_position": {"lat": 42.31, "lon": 36.33, "timestamp": "2026-03-01T00:00:00Z"},
            "reappearance_position": {"lat": 42.28, "lon": 36.38, "timestamp": "2026-03-01T03:00:00Z"},
            "sanctioned_ports": [
                {
                    "name": "Port Kavkaz",
                    "lat": 42.30,
                    "lon": 36.35,
                    "country": "RU",
                    "sanctions_regime": "EU oil cap",
                }
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["detected"] is True
    assert body["alert"]["type"] == "SANCTIONS_DARK_ACTIVITY"