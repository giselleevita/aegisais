from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO

import app.api.v1.upload as upload_module
import pytest
from fastapi.testclient import TestClient

from app.modules.alerts.models import Alert
from app.modules.audit.models import AuditLog
from app.modules.incidents.service import create_incident_from_alert
from tests.conftest import TestingSessionLocal, register_and_login_as_admin


def _seed_alert() -> int:
    db = TestingSessionLocal()
    try:
        alert = Alert(
            organisation_id=1,
            timestamp=datetime.now(timezone.utc),
            mmsi="123456789",
            type="FUSED_ACTIVITY_NEAR_CABLE",
            severity=72,
            summary="Surface activity near cable segment",
            evidence={"rule": "fused"},
            status="new",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert.id
    finally:
        db.close()


def _seed_incident() -> int:
    db = TestingSessionLocal()
    try:
        alert = Alert(
            organisation_id=1,
            timestamp=datetime.now(timezone.utc),
            mmsi="987654321",
            type="FUSED_ACTIVITY_NEAR_CABLE",
            severity=78,
            summary="Surface activity near cable segment",
            evidence={"rule": "fused"},
            status="new",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        incident = create_incident_from_alert(db, alert)
        db.commit()
        return incident.id
    finally:
        db.close()


def _run_register(client: TestClient, _tmp_path, _monkeypatch) -> None:
    username = f"u_{uuid.uuid4().hex[:12]}"
    response = client.post(
        "/v1/auth/register",
        json={"username": username, "email": f"{username}@test.local", "password": "p" * 12},
    )
    assert response.status_code == 200, response.text


def _run_login(client: TestClient, _tmp_path, _monkeypatch) -> None:
    username = f"u_{uuid.uuid4().hex[:12]}"
    register = client.post(
        "/v1/auth/register",
        json={"username": username, "email": f"{username}@test.local", "password": "p" * 12},
    )
    assert register.status_code == 200, register.text
    response = client.post(
        "/v1/auth/login",
        data={"username": username, "password": "p" * 12},
    )
    assert response.status_code == 200, response.text


def _run_alert_status_update(client: TestClient, _tmp_path, _monkeypatch) -> None:
    token = register_and_login_as_admin(client)
    alert_id = _seed_alert()
    response = client.patch(
        f"/v1/alerts/{alert_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "reviewed"},
    )
    assert response.status_code == 200, response.text


def _run_incident_update(client: TestClient, _tmp_path, _monkeypatch) -> None:
    token = register_and_login_as_admin(client)
    incident_id = _seed_incident()
    response = client.patch(
        f"/v1/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "investigating", "title": "Coverage test incident"},
    )
    assert response.status_code == 200, response.text


def _run_alert_export_csv(client: TestClient, _tmp_path, _monkeypatch) -> None:
    token = register_and_login_as_admin(client)
    _seed_alert()
    response = client.get(
        "/v1/alerts/export/csv",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text


def _run_alert_export_json(client: TestClient, _tmp_path, _monkeypatch) -> None:
    token = register_and_login_as_admin(client)
    _seed_alert()
    response = client.get(
        "/v1/alerts/export/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text


def _run_upload_success(client: TestClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(upload_module, "DATA_RAW_DIR", tmp_path)
    token = register_and_login_as_admin(client)
    body = b"mmsi,timestamp,lat,lon\n123456789,1700000000,55.0,12.0\n"
    response = client.post(
        "/v1/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("coverage.csv", BytesIO(body), "text/csv")},
    )
    assert response.status_code == 200, response.text


AUDIT_COVERAGE_MATRIX = [
    {"name": "register", "action": "auth.register", "runner": _run_register},
    {"name": "login", "action": "auth.login.success", "runner": _run_login},
    {"name": "alert status update", "action": "alert.status.update", "runner": _run_alert_status_update},
    {"name": "incident update", "action": "incident.update", "runner": _run_incident_update},
    {"name": "alert export csv", "action": "alert.export.csv", "runner": _run_alert_export_csv},
    {"name": "alert export json", "action": "alert.export.json", "runner": _run_alert_export_json},
    {"name": "upload success", "action": "upload.file.success", "runner": _run_upload_success},
]


@pytest.mark.parametrize(
    ("case_name", "action", "runner"),
    [(case["name"], case["action"], case["runner"]) for case in AUDIT_COVERAGE_MATRIX],
    ids=[case["name"] for case in AUDIT_COVERAGE_MATRIX],
)
def test_audit_coverage_matrix(case_name, action, runner, client, tmp_path, monkeypatch):
    runner(client, tmp_path, monkeypatch)

    db = TestingSessionLocal()
    try:
        rows = db.query(AuditLog).filter(AuditLog.action == action).all()
        assert len(rows) == 1, f"Expected one audit row for {case_name}, found {len(rows)}"
    finally:
        db.close()