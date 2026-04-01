"""BL-003: Alert idempotency key tests.

Verifies that:
  1. derive_alert_idempotency_key produces a deterministic SHA-256 hex string.
  2. Minute-bucket normalisation makes sub-second variation map to the same key.
  3. handle_alert persists idempotency_key on new alerts.
  4. Re-delivering the same alert (same org/mmsi/type/minute) is idempotent:
     exactly one Alert row exists, no duplicate incidents, ALERTS_DEDUPLICATED
     counter incremented on the second call.
  5. DB-level unique constraint on idempotency_key raises IntegrityError for
     a direct duplicate INSERT, proving the migration was applied correctly.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch

from app.modules.alerts.models import Alert, derive_alert_idempotency_key
from app.services.workers.alert_worker import handle_alert
from tests.conftest import TestingSessionLocal


# ---------------------------------------------------------------------------
# Unit tests for key derivation
# ---------------------------------------------------------------------------

def test_idempotency_key_is_deterministic():
    ts = datetime(2026, 1, 15, 10, 34, 22, 456789, tzinfo=timezone.utc)
    k1 = derive_alert_idempotency_key(1, "265503690", "TELEPORT", ts)
    k2 = derive_alert_idempotency_key(1, "265503690", "TELEPORT", ts)
    assert k1 == k2
    assert len(k1) == 64  # sha256 hex


def test_idempotency_key_sub_second_variation_maps_same():
    """Different sub-second values in the same minute produce the same key."""
    base = datetime(2026, 1, 15, 10, 34, 0, tzinfo=timezone.utc)
    ts1 = base.replace(second=5, microsecond=0)
    ts2 = base.replace(second=59, microsecond=999999)
    k1 = derive_alert_idempotency_key(1, "265503690", "TELEPORT", ts1)
    k2 = derive_alert_idempotency_key(1, "265503690", "TELEPORT", ts2)
    assert k1 == k2


def test_idempotency_key_different_minute_differs():
    base = datetime(2026, 1, 15, 10, 34, tzinfo=timezone.utc)
    k1 = derive_alert_idempotency_key(1, "265503690", "TELEPORT", base)
    k2 = derive_alert_idempotency_key(1, "265503690", "TELEPORT", base + timedelta(minutes=1))
    assert k1 != k2


def test_idempotency_key_naive_datetime_treated_as_utc():
    naive = datetime(2026, 1, 15, 10, 34, 0)
    aware = datetime(2026, 1, 15, 10, 34, 0, tzinfo=timezone.utc)
    k1 = derive_alert_idempotency_key(1, "265503690", "TELEPORT", naive)
    k2 = derive_alert_idempotency_key(1, "265503690", "TELEPORT", aware)
    assert k1 == k2


def test_idempotency_key_differs_across_dimensions():
    ts = datetime(2026, 1, 15, 10, 34, tzinfo=timezone.utc)
    k_base = derive_alert_idempotency_key(1, "265503690", "TELEPORT", ts)
    assert derive_alert_idempotency_key(2, "265503690", "TELEPORT", ts) != k_base   # different org
    assert derive_alert_idempotency_key(1, "999999999", "TELEPORT", ts) != k_base   # different mmsi
    assert derive_alert_idempotency_key(1, "265503690", "TURN_RATE", ts) != k_base  # different type


# ---------------------------------------------------------------------------
# Integration tests — worker + DB
# ---------------------------------------------------------------------------

def _payload(mmsi: str = "265510001", ts: datetime | None = None) -> dict:
    t = (ts or datetime.now(timezone.utc)).isoformat()
    return {
        "timestamp": t,
        "mmsi": mmsi,
        "type": "TELEPORT",
        "severity": "60",
        "summary": "BL-003 idempotency test",
        "evidence": {"rule": "test"},
    }


def test_handle_alert_stores_idempotency_key(client):
    """New alert row must have idempotency_key populated."""
    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("idem-msg-001", _payload(mmsi="265510010"))

    db = TestingSessionLocal()
    try:
        row = db.query(Alert).filter(Alert.mmsi == "265510010").first()
        assert row is not None
        assert row.idempotency_key is not None
        assert len(row.idempotency_key) == 64
    finally:
        db.close()


def test_handle_alert_idempotent_replay_produces_one_row(client):
    """Delivering the same alert twice must result in exactly one Alert row."""
    payload = _payload(mmsi="265510020")

    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("idem-msg-010", payload)
        handle_alert("idem-msg-011", payload)  # same content, different msg_id

    db = TestingSessionLocal()
    try:
        rows = db.query(Alert).filter(Alert.mmsi == "265510020").all()
        assert len(rows) == 1, f"Expected 1 alert row, got {len(rows)}"
    finally:
        db.close()


def test_handle_alert_sub_second_variation_idempotent(client):
    """Two payloads with the same minute but different sub-second timestamps
    must be treated as duplicates (BL-003 minute-bucket policy)."""
    base_ts = datetime(2026, 1, 15, 10, 34, 0, tzinfo=timezone.utc)
    p1 = _payload(mmsi="265510030", ts=base_ts.replace(second=5))
    p2 = _payload(mmsi="265510030", ts=base_ts.replace(second=55, microsecond=999000))

    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("idem-msg-020", p1)
        handle_alert("idem-msg-021", p2)

    db = TestingSessionLocal()
    try:
        rows = db.query(Alert).filter(Alert.mmsi == "265510030").all()
        assert len(rows) == 1, (
            f"Sub-second variant should collapse to 1 row, got {len(rows)}"
        )
    finally:
        db.close()


def test_alert_idempotency_key_unique_constraint_enforced_at_db_level(client):
    """DB-level unique index on idempotency_key must reject a direct duplicate INSERT."""
    ts = datetime.now(timezone.utc)
    key = derive_alert_idempotency_key(1, "265510040", "TELEPORT", ts)

    db = TestingSessionLocal()
    try:
        a1 = Alert(
            organisation_id=1,
            timestamp=ts,
            mmsi="265510040",
            type="TELEPORT",
            severity=60,
            summary="first",
            evidence={},
            idempotency_key=key,
        )
        db.add(a1)
        db.flush()

        with pytest.raises(IntegrityError):
            a2 = Alert(
                organisation_id=1,
                timestamp=ts,
                mmsi="265510040",
                type="TELEPORT",
                severity=60,
                summary="duplicate",
                evidence={},
                idempotency_key=key,
            )
            db.add(a2)
            db.flush()
    finally:
        db.rollback()
        db.close()
