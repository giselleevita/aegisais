"""BL-009: Alert evidence hash tests.

Verifies that:
  1. derive_evidence_hash produces a deterministic 64-char hex string.
  2. Key-order variance in the evidence dict produces the same hash.
  3. Evidence mutation changes the hash.
  4. handle_alert persists evidence_hash on new alerts.
  5. When stream message omits evidence_hash the worker recomputes it from evidence.
  6. evidence_hash is exposed in the AlertOut schema.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.modules.alerts.models import Alert, derive_evidence_hash
from app.modules.alerts.schemas import AlertOut
from app.services.workers.alert_worker import handle_alert
from tests.conftest import TestingSessionLocal


# ---------------------------------------------------------------------------
# Unit tests for derive_evidence_hash
# ---------------------------------------------------------------------------


def test_evidence_hash_deterministic():
    ev = {"dt_sec": 1.5, "distance_m": 500.0, "implied_speed_kn": 35.2}
    h1 = derive_evidence_hash(ev)
    h2 = derive_evidence_hash(ev)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_evidence_hash_key_order_independent():
    """Regardless of Python dict insertion order the hash must be stable."""
    ev1 = {"a": 1, "b": 2, "c": 3}
    ev2 = {"c": 3, "a": 1, "b": 2}
    assert derive_evidence_hash(ev1) == derive_evidence_hash(ev2)


def test_evidence_hash_mutation_changes_hash():
    ev = {"dt_sec": 1.5, "distance_m": 500.0}
    h1 = derive_evidence_hash(ev)
    h2 = derive_evidence_hash({**ev, "distance_m": 501.0})
    assert h1 != h2


def test_evidence_hash_non_serialisable_coerced():
    """datetime values are coerced via str; no TypeError is raised."""
    ev = {"ts": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    h = derive_evidence_hash(ev)
    assert len(h) == 64


def test_evidence_hash_empty_dict():
    h = derive_evidence_hash({})
    assert len(h) == 64


# ---------------------------------------------------------------------------
# Integration: worker persists evidence_hash

# ---------------------------------------------------------------------------


def _make_alert_payload(**kwargs) -> dict:
    base = {
        "timestamp": "2026-03-01T12:30:00+00:00",
        "mmsi": "123456789",
        "type": "TELEPORT",
        "severity": "70",
        "summary": "Teleport detected",
        "evidence": {"dt_sec": 45.0, "distance_m": 95000.0},
    }
    base.update(kwargs)
    return base


def test_handle_alert_persists_evidence_hash(client):
    """handle_alert stores evidence_hash on the Alert row."""
    data = _make_alert_payload()
    evidence_hash = derive_evidence_hash(data["evidence"])

    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("1-1", data)

    with TestingSessionLocal() as db:
        alert = db.query(Alert).filter_by(mmsi="123456789", type="TELEPORT").first()
        assert alert is not None
        assert alert.evidence_hash == evidence_hash


def test_handle_alert_accepts_precomputed_evidence_hash(client):
    """If the stream message already contains evidence_hash the worker uses it."""
    data = _make_alert_payload(mmsi="111222333", type="ACCELERATION")
    precomputed = "a" * 64
    data["evidence_hash"] = precomputed

    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("2-1", data)

    with TestingSessionLocal() as db:
        alert = db.query(Alert).filter_by(mmsi="111222333", type="ACCELERATION").first()
        assert alert is not None
        assert alert.evidence_hash == precomputed


def test_handle_alert_recomputes_hash_when_absent(client):
    """If evidence_hash is absent from the stream message the worker derives it."""
    data = _make_alert_payload(mmsi="999888777", type="TURN_RATE")
    assert "evidence_hash" not in data

    with patch("app.services.workers.alert_worker.SessionLocal", TestingSessionLocal):
        handle_alert("3-1", data)

    with TestingSessionLocal() as db:
        alert = db.query(Alert).filter_by(mmsi="999888777", type="TURN_RATE").first()
        assert alert is not None
        expected = derive_evidence_hash(data["evidence"])
        assert alert.evidence_hash == expected


# ---------------------------------------------------------------------------
# Schema: evidence_hash surfaces in AlertOut
# ---------------------------------------------------------------------------


def test_alert_out_includes_evidence_hash():
    """AlertOut must expose the evidence_hash field."""
    alert = Alert(
        id=1,
        organisation_id=1,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        mmsi="555666777",
        type="TELEPORT",
        severity=80,
        summary="test",
        evidence={"dt_sec": 1.0},
        evidence_hash="b" * 64,
        status="new",
    )
    out = AlertOut.model_validate(alert, from_attributes=True)
    assert out.evidence_hash == "b" * 64


def test_alert_out_evidence_hash_nullable():
    """AlertOut must not fail on legacy rows where evidence_hash is NULL."""
    alert = Alert(
        id=2,
        organisation_id=1,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        mmsi="555666778",
        type="TELEPORT",
        severity=80,
        summary="test",
        evidence={"dt_sec": 1.0},
        evidence_hash=None,
        status="new",
    )
    out = AlertOut.model_validate(alert, from_attributes=True)
    assert out.evidence_hash is None
