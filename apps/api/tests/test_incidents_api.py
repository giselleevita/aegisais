from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.alerts.models import Alert
from app.modules.audit.models import AuditLog
from app.modules.incidents.models import Incident
from app.modules.incidents.service import create_incident_from_alert
from tests.conftest import TestingSessionLocal, register_and_login_as_admin


def _seed_alert_and_incident() -> int:
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
        incident = create_incident_from_alert(db, alert)
        db.commit()
        return incident.id
    finally:
        db.close()


def test_incidents_list_and_get(client):
    token = register_and_login_as_admin(client)
    incident_id = _seed_alert_and_incident()

    r = client.get("/v1/incidents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    rows = r.json()
    assert any(x["id"] == incident_id for x in rows)

    g = client.get(f"/v1/incidents/{incident_id}", headers={"Authorization": f"Bearer {token}"})
    assert g.status_code == 200
    assert g.json()["id"] == incident_id


def test_incident_patch_writes_audit_row(client):
    token = register_and_login_as_admin(client)
    incident_id = _seed_alert_and_incident()

    p = client.patch(
        f"/v1/incidents/{incident_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "investigating", "title": "Updated incident title"},
    )
    assert p.status_code == 200, p.text
    assert p.json()["status"] == "investigating"

    db = TestingSessionLocal()
    try:
        row = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "incident.update",
                AuditLog.resource_id == str(incident_id),
            )
            .first()
        )
        assert row is not None
        assert row.resource_type == "incident"
    finally:
        db.close()


def test_alert_export_writes_audit_rows(client):
    token = register_and_login_as_admin(client)
    _seed_alert_and_incident()

    rcsv = client.get("/v1/alerts/export/csv", headers={"Authorization": f"Bearer {token}"})
    assert rcsv.status_code == 200
    rjson = client.get("/v1/alerts/export/json", headers={"Authorization": f"Bearer {token}"})
    assert rjson.status_code == 200

    db = TestingSessionLocal()
    try:
        csv_row = db.query(AuditLog).filter(AuditLog.action == "alert.export.csv").first()
        json_row = db.query(AuditLog).filter(AuditLog.action == "alert.export.json").first()
        assert csv_row is not None
        assert json_row is not None
    finally:
        db.close()


def test_incident_alert_id_unique_constraint_enforced_at_db_level(client):
    """Database-level UniqueConstraint on incidents.alert_id prevents duplicates.

    Concurrency note: the application layer uses savepoint-based optimistic
    checks (create_incident_from_alert_with_flag) to handle races, but the
    DB constraint is the authoritative last-resort guard.  This test proves
    the constraint is present and populated by the migration so that any future
    migration regression is caught in CI before reaching production.
    """
    db = TestingSessionLocal()
    try:
        alert = Alert(
            organisation_id=1,
            timestamp=datetime.now(timezone.utc),
            mmsi="999000001",
            type="FUSED_ACTIVITY_NEAR_CABLE",
            severity=70,
            summary="Uniqueness constraint regression test",
            evidence={"rule": "test"},
            status="new",
        )
        db.add(alert)
        db.flush()

        # First incident insert must succeed.
        inc1 = Incident(
            organisation_id=1,
            alert_id=alert.id,
            created_at=datetime.now(timezone.utc),
            status="open",
            title="First incident",
            evidence_bundle={"schema_version": "1"},
        )
        db.add(inc1)
        db.flush()

        # A second Incident sharing the same alert_id must violate the
        # unique constraint enforced at the database level.
        with pytest.raises(IntegrityError):
            inc2 = Incident(
                organisation_id=1,
                alert_id=alert.id,
                created_at=datetime.now(timezone.utc),
                status="open",
                title="Duplicate incident",
                evidence_bundle={"schema_version": "1"},
            )
            db.add(inc2)
            db.flush()
    finally:
        db.rollback()
        db.close()

