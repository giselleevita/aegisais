"""Audit rows written on selected API actions (shared test DB)."""

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.modules.alerts.models import Alert
from app.modules.audit.models import AuditLog
from tests.conftest import TestingSessionLocal, register_and_login_as_admin


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


def test_register_creates_audit_row(client: TestClient):
    u = f"u_{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/v1/auth/register",
        json={"username": u, "email": f"{u}@t.local", "password": "p" * 12},
    )
    assert r.status_code == 200, r.text
    db = TestingSessionLocal()
    try:
        row = (
            db.query(AuditLog)
            .filter(AuditLog.action == "auth.register", AuditLog.user_id == u)
            .first()
        )
        assert row is not None
        assert row.resource_type == "user"
    finally:
        db.close()


def test_login_success_creates_audit_row(client: TestClient):
    u = f"u_{uuid.uuid4().hex[:12]}"
    assert (
        client.post(
            "/v1/auth/register",
            json={"username": u, "email": f"{u}@t.local", "password": "p" * 12},
        ).status_code
        == 200
    )
    client.post("/v1/auth/login", data={"username": u, "password": "p" * 12})
    db = TestingSessionLocal()
    try:
        rows = (
            db.query(AuditLog)
            .filter(AuditLog.action == "auth.login.success", AuditLog.user_id == u)
            .all()
        )
        assert len(rows) >= 1
    finally:
        db.close()


def test_viewer_cannot_patch_alert_status(client: TestClient):
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
    token = login.json()["access_token"]

    db = TestingSessionLocal()
    try:
        alert = Alert(
            organisation_id=1,
            timestamp=datetime.now(timezone.utc),
            mmsi="123456789",
            type="TELEPORT",
            severity=40,
            summary="test",
            evidence={},
            status="new",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        aid = alert.id
    finally:
        db.close()

    r = client.patch(
        f"/v1/alerts/{aid}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "reviewed"},
    )
    assert r.status_code == 403


def test_alert_status_patch_creates_audit_row(client: TestClient):
    token = register_and_login_as_admin(client)
    db = TestingSessionLocal()
    try:
        alert = Alert(
            organisation_id=1,
            timestamp=datetime.now(timezone.utc),
            mmsi="123456789",
            type="TELEPORT",
            severity=40,
            summary="test",
            evidence={},
            status="new",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        aid = alert.id
    finally:
        db.close()

    r = client.patch(
        f"/v1/alerts/{aid}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "reviewed"},
    )
    assert r.status_code == 200, r.text

    db = TestingSessionLocal()
    try:
        row = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "alert.status.update",
                AuditLog.resource_id == str(aid),
            )
            .first()
        )
        assert row is not None
        assert row.user_id is not None
    finally:
        db.close()


def test_audit_logs_unauthorized(client: TestClient):
    r = client.get("/v1/audit/logs")
    assert r.status_code == 401


def test_audit_logs_forbidden_for_viewer(client: TestClient):
    token = _viewer_token(client)
    r = client.get(
        "/v1/audit/logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_audit_logs_admin_lists_register_and_login_events(client: TestClient):
    token = register_and_login_as_admin(client)
    r = client.get(
        "/v1/audit/logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 2
    actions = {x["action"] for x in body}
    assert "auth.register" in actions
    assert "auth.login.success" in actions


def test_audit_logs_filter_by_action(client: TestClient):
    token = register_and_login_as_admin(client)
    r = client.get(
        "/v1/audit/logs",
        headers={"Authorization": f"Bearer {token}"},
        params={"action": "auth.register"},
    )
    assert r.status_code == 200
    for row in r.json():
        assert row["action"] == "auth.register"


def test_audit_logs_export_csv_admin(client: TestClient):
    token = register_and_login_as_admin(client)
    r = client.get(
        "/v1/audit/logs/export/csv",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "text/csv" in (r.headers.get("content-type") or "")
    assert "audit_logs_export" in (r.headers.get("content-disposition") or "")
    text = r.text
    assert "Action" in text
    assert "auth.register" in text


def test_audit_logs_export_csv_forbidden_viewer(client: TestClient):
    token = _viewer_token(client)
    r = client.get(
        "/v1/audit/logs/export/csv",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_audit_logs_filter_by_resource_id(client: TestClient):
    token = register_and_login_as_admin(client)
    db = TestingSessionLocal()
    try:
        row = AuditLog(
            organisation_id=1,
            timestamp=datetime.now(timezone.utc),
            user_id="tester",
            action="incident.update",
            resource_id="4242",
            resource_type="incident",
            change_summary="updated",
            details={"k": "v"},
        )
        db.add(row)
        db.commit()
    finally:
        db.close()

    r = client.get(
        "/v1/audit/logs",
        headers={"Authorization": f"Bearer {token}"},
        params={"resource_id": "4242", "resource_type": "incident"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 1
    assert all(x["resource_id"] == "4242" for x in body)
