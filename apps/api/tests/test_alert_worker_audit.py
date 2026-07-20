"""Worker audit-event tests for system-created alerts and incidents (BL-006/BL-007).

Verifies that handle_alert() writes an AuditLog row with action
``incident.create.system`` when the alert worker auto-creates an incident.
The test exercises the service layer directly (no live Redis required) by
mocking the consumer and publisher so the test remains fast and isolated.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from app.modules.alerts.models import Alert
from app.modules.audit.models import AuditLog
from app.services.workers.alert_worker import handle_alert
from tests.conftest import TestingSessionLocal


def _build_alert_payload(**overrides) -> dict:
    base = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mmsi": "265599001",
        "type": "FUSED_ACTIVITY_NEAR_CABLE",
        "severity": "75",
        "summary": "Worker audit test alert",
        "evidence": {"rule": "worker_audit_test"},
        "confidence": {"score": 0.91, "method": "test_corroboration"},
        "provenance": {"source": "festival-replay", "processor": "test-fusion-v1"},
    }
    return {**base, **overrides}


def test_handle_alert_emits_alert_create_system_audit_row(client):
    payload = _build_alert_payload(mmsi="265599000")
    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("test-msg-alert-001", payload)

    db = TestingSessionLocal()
    try:
        alert = db.query(Alert).filter(Alert.mmsi == "265599000").one()
        row = (
            db.query(AuditLog)
            .filter(AuditLog.action == "alert.create.system")
            .one()
        )
        assert row.user_id == "system:alert_worker"
        assert row.resource_type == "alert"
        assert row.resource_id == str(alert.id)
        assert row.correlation_id == "test-msg-alert-001"
        assert row.organisation_id == alert.organisation_id
        details = row.details or {}
        assert details["alert_id"] == alert.id
        assert details["mmsi"] == alert.mmsi
        assert details["alert_type"] == alert.type
        assert details["evidence_hash"] == alert.evidence_hash
        assert details["fusion_event_id"] is None
        assert details["confidence"] == payload["confidence"]
        assert details["provenance"] == payload["provenance"]
    finally:
        db.close()


def test_handle_alert_emits_incident_create_system_audit_row(client):
    """handle_alert must write an audit row with action=incident.create.system."""
    # Patch SessionLocal so handle_alert uses the shared in-memory test DB.
    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("test-msg-001", _build_alert_payload())

    db = TestingSessionLocal()
    try:
        row = (
            db.query(AuditLog)
            .filter(AuditLog.action == "incident.create.system")
            .first()
        )
        assert row is not None, "Expected audit row for incident.create.system"
        assert row.user_id == "system:alert_worker"
        assert row.resource_type == "incident"
        assert row.correlation_id == "test-msg-001"
        assert row.organisation_id is not None
        details = row.details or {}
        assert "mmsi" in details
        assert "alert_id" in details
        assert "alert_type" in details
        assert details["evidence_hash"]
        assert "fusion_event_id" in details
    finally:
        db.close()


def test_handle_alert_deduplication_does_not_emit_double_audit_row(client):
    """Re-delivering the same alert must not create a second audit row.

    The worker's deduplication guard (org_id + mmsi + type + timestamp) must
    short-circuit before the AuditService.log_event call, keeping the audit
    log idempotent for at-least-once stream delivery.
    """
    payload = _build_alert_payload(mmsi="265599002")

    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("test-msg-dup-001", payload)
        # Deliver the same message a second time (simulates Redis re-delivery).
        handle_alert("test-msg-dup-002", payload)

    db = TestingSessionLocal()
    try:
        incident_rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "incident.create.system",
                AuditLog.details["mmsi"].as_string() == "265599002",
            )
            .all()
        )
        alert_rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "alert.create.system",
                AuditLog.details["mmsi"].as_string() == "265599002",
            )
            .all()
        )
        assert len(incident_rows) == 1, (
            f"Expected exactly 1 incident audit row, got {len(incident_rows)}"
        )
        assert len(alert_rows) == 1, f"Expected exactly 1 alert audit row, got {len(alert_rows)}"
    finally:
        db.close()


def test_handle_alert_no_audit_row_when_incident_already_exists(client):
    """When an alert already has an incident (via service-layer race recovery),
    a second handle_alert call for the same alert must not emit a second
    incident.create.system row — the incident flag returned is False.
    """
    payload = _build_alert_payload(mmsi="265599003")

    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("test-msg-race-001", payload)

    # Simulate a second worker processing the same alert (different msg_id,
    # same content — deduplication by mmsi+type+timestamp catches this).
    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("test-msg-race-002", payload)

    db = TestingSessionLocal()
    try:
        rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "incident.create.system",
                AuditLog.details["mmsi"].as_string() == "265599003",
            )
            .all()
        )
        assert len(rows) == 1, (
            f"Expected exactly 1 audit row (idempotent re-delivery), got {len(rows)}"
        )
    finally:
        db.close()
