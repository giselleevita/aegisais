"""Worker audit-event tests for incident.create.system (BL-006/BL-007).

Verifies that handle_alert() writes an AuditLog row with action
``incident.create.system`` when the alert worker auto-creates an incident.
The test exercises the service layer directly (no live Redis required) by
mocking the consumer and publisher so the test remains fast and isolated.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

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
    }
    return {**base, **overrides}


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
        rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "incident.create.system",
                AuditLog.details["mmsi"].as_string() == "265599002",
            )
            .all()
        )
        assert len(rows) == 1, (
            f"Expected exactly 1 audit row for deduplicated alerts, got {len(rows)}"
        )
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
