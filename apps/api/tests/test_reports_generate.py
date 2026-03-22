"""POST /v1/reports/generate — PDF alerts summary (admin only)."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.modules.alerts.models import Alert
from app.modules.auth.models import User
from tests.conftest import TestingSessionLocal


def _viewer_token(client: TestClient) -> str:
    u = f"u_{uuid.uuid4().hex[:12]}"
    assert (
        client.post(
            "/v1/auth/register",
            json={"username": u, "email": f"{u}@t.local", "password": "p" * 12},
        ).status_code
        == 200
    )
    login = client.post(
        "/v1/auth/login",
        data={"username": u, "password": "p" * 12},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def _register_admin_token_and_username(client: TestClient) -> tuple[str, str]:
    u = f"a_{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/v1/auth/register",
        json={"username": u, "email": f"{u}@test.local", "password": "p" * 12},
    )
    assert r.status_code == 200, r.text
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == u).first()
        assert user is not None
        user.role = "admin"
        db.commit()
    finally:
        db.close()
    login = client.post(
        "/v1/auth/login",
        data={"username": u, "password": "p" * 12},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"], u


def _organisation_id_for_username(username: str) -> int:
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        return user.organisation_id
    finally:
        db.close()


def test_reports_generate_forbidden_non_admin(client: TestClient):
    token = _viewer_token(client)
    start = datetime.now(timezone.utc) - timedelta(days=1)
    end = datetime.now(timezone.utc)
    r = client.post(
        "/v1/reports/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
    )
    assert r.status_code == 403


def test_reports_generate_admin_returns_pdf(client: TestClient):
    token, username = _register_admin_token_and_username(client)
    org_id = _organisation_id_for_username(username)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 12, 31, tzinfo=timezone.utc)

    db = TestingSessionLocal()
    try:
        db.add(
            Alert(
                organisation_id=org_id,
                timestamp=datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc),
                mmsi="123456789",
                type="TELEPORT",
                severity=75,
                summary="Test alert summary",
                evidence={"zone": "Baltic-1", "detail": "x"},
                status="new",
            )
        )
        db.add(
            Alert(
                organisation_id=org_id,
                timestamp=datetime(2025, 6, 16, 12, 0, tzinfo=timezone.utc),
                mmsi="987654321",
                type="TURN_RATE",
                severity=40,
                summary="Another",
                evidence={},
                status="new",
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/v1/reports/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert "attachment" in r.headers.get("content-disposition", "").lower()
    assert r.content[:5] == b"%PDF-"


def test_reports_generate_zone_substring_filters(client: TestClient):
    token, username = _register_admin_token_and_username(client)
    org_id = _organisation_id_for_username(username)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 12, 31, tzinfo=timezone.utc)

    db = TestingSessionLocal()
    try:
        db.add(
            Alert(
                organisation_id=org_id,
                timestamp=datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc),
                mmsi="111111111",
                type="TELEPORT",
                severity=80,
                summary="Alpha zone match",
                evidence={},
                status="new",
            )
        )
        db.add(
            Alert(
                organisation_id=org_id,
                timestamp=datetime(2025, 6, 15, 13, 0, tzinfo=timezone.utc),
                mmsi="222222222",
                type="TELEPORT",
                severity=80,
                summary="No match here",
                evidence={"note": "Baltic-1 ref"},
                status="new",
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/v1/reports/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "zone_substring": "Baltic",
        },
    )
    assert r.status_code == 200, r.text
    assert r.content[:5] == b"%PDF-"
    assert len(r.content) > 100
