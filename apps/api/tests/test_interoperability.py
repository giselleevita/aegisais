"""Interoperability conformance tests.

INT-001  Import maritime bundle  -> structured validation report returned
INT-002  Export alerts as JSON   -> records conform to documented AlertOut schema
INT-003  Reconstruct alert rationale  [pending BL-009]
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.modules.alerts.models import Alert
from app.modules.auth.models import Organisation, User
from app.modules.auth.org_scope import apply_org_filter
from app.modules.integrations.importers_ports import PortSeedRow
from app.modules.integrations.migration_validator import (
    MigrationValidationReport,
    validate_port_seed_rows,
)
from app.modules.vessels.models import VesselLatest
from tests.conftest import TestingSessionLocal, register_and_login_as_admin

# ---------------------------------------------------------------------------
# INT-001: maritime bundle import -> validation report
# ---------------------------------------------------------------------------

_SAMPLE_BUNDLE: list[PortSeedRow] = [
    PortSeedRow(
        source="ais-bundle",
        source_id="PORT-001",
        name="Portsmouth",
        country_code="GB",
        unlocode="GBPME",
        latitude=50.8198,
        longitude=-1.0880,
        geom_wkt="POINT(-1.0880 50.8198)",
        metadata_json={"harbor_type": "coastal"},
        license_tag="open",
    ),
    PortSeedRow(
        source="ais-bundle",
        source_id="PORT-002",
        name="Southampton",
        country_code="GB",
        unlocode="GBSOU",
        latitude=50.9000,
        longitude=-1.4040,
        geom_wkt="POINT(-1.4040 50.9000)",
        metadata_json={"harbor_type": "coastal"},
        license_tag="open",
    ),
]

_REPORT_FIELDS = {
    "total_rows",
    "valid_rows",
    "duplicate_source_keys",
    "missing_names",
    "missing_geometry",
    "missing_identifiers",
}


def test_int001_maritime_bundle_produces_validation_report():
    """INT-001: importing a maritime bundle returns a structured validation report."""
    report = validate_port_seed_rows(_SAMPLE_BUNDLE)

    assert isinstance(report, MigrationValidationReport)
    assert report.total_rows == 2
    assert report.valid_rows == 2
    assert report.duplicate_source_keys == 0
    assert report.missing_names == 0
    assert report.missing_geometry == 0
    assert report.missing_identifiers == 0

    # Validate machine-readable serialisation contract
    d = report.to_dict()
    assert set(d.keys()) == _REPORT_FIELDS
    assert all(isinstance(v, int) for v in d.values())


def test_int001_bundle_with_invalid_rows_reported():
    """INT-001: invalid rows are counted and reported correctly."""
    bundle = _SAMPLE_BUNDLE + [
        # duplicate source key
        PortSeedRow(
            source="ais-bundle",
            source_id="PORT-001",
            name="Portsmouth Dupe",
            country_code="GB",
            unlocode=None,
            latitude=50.8198,
            longitude=-1.0880,
            geom_wkt="POINT(-1.0880 50.8198)",
            metadata_json={},
            license_tag="open",
        ),
    ]
    report = validate_port_seed_rows(bundle)
    assert report.total_rows == 3
    assert report.duplicate_source_keys == 1


# ---------------------------------------------------------------------------
# INT-002: alert JSON export conforms to AlertOut schema
# ---------------------------------------------------------------------------

_REQUIRED_ALERT_OUT_FIELDS = {
    "id",
    "timestamp",
    "mmsi",
    "type",
    "severity",
    "summary",
    "evidence",
    "status",
}


def _seed_alert() -> None:
    db = TestingSessionLocal()
    try:
        alert = Alert(
            organisation_id=1,
            timestamp=datetime.now(timezone.utc),
            mmsi="987654321",
            type="TELEPORT",
            severity=80,
            summary="INT-002 conformance seed alert",
            evidence={"rule": "teleport", "delta_km": 120},
            status="new",
        )
        db.add(alert)
        db.commit()
    finally:
        db.close()


def test_int002_json_export_conforms_to_alertout_schema(client):
    """INT-002: alert JSON export records include all required AlertOut fields."""
    token = register_and_login_as_admin(client)
    _seed_alert()

    r = client.get(
        "/v1/alerts/export/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    payload = json.loads(r.content)
    assert isinstance(payload, list), "Expected a list of alert records"
    assert len(payload) >= 1, "Expected at least the seeded alert in the export"

    for record in payload:
        missing = _REQUIRED_ALERT_OUT_FIELDS - set(record.keys())
        assert not missing, f"Export record is missing required fields: {missing}"
        # Type spot-checks
        assert isinstance(record["id"], int)
        assert isinstance(record["mmsi"], str)
        assert isinstance(record["severity"], int)
        assert record["status"] in {"new", "reviewed", "resolved", "false_positive"}


def test_int002_json_export_respects_limit(client):
    token = register_and_login_as_admin(client)
    _seed_alert()
    _seed_alert()
    _seed_alert()

    r = client.get(
        "/v1/alerts/export/json?limit=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    payload = json.loads(r.content)
    assert isinstance(payload, list)
    assert len(payload) == 2


def test_int002_export_requires_admin(client):
    """INT-002 access control: non-admin callers are rejected."""
    r = client.get("/v1/alerts/export/json")
    assert r.status_code in {401, 403}


def _seed_vessel_and_alert_for_latest_user() -> tuple[int, str]:
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username.isnot(None)).order_by(User.id.desc()).first()
        assert user is not None

        vessel = VesselLatest(
            mmsi="265503690",
            organisation_id=user.organisation_id,
            timestamp=datetime.now(timezone.utc),
            lat=57.7123,
            lon=11.9668,
            sog=12.4,
            cog=184.2,
            heading=182.0,
            last_alert_severity=81,
        )
        db.add(vessel)
        db.flush()

        alert = Alert(
            organisation_id=user.organisation_id,
            timestamp=datetime.now(timezone.utc),
            mmsi=vessel.mmsi,
            type="TELEPORT",
            severity=81,
            summary="Interop export seed alert",
            evidence={"p2_lat": 57.7123, "p2_lon": 11.9668, "delta_km": 120},
            status="new",
        )
        db.add(alert)
        db.commit()
        return alert.id, vessel.mmsi
    finally:
        db.close()


def test_int002_cot_vessel_endpoint_uses_persisted_scoped_vessel(client):
    token = register_and_login_as_admin(client)
    _, mmsi = _seed_vessel_and_alert_for_latest_user()

    r = client.get(
        f"/v1/interop/cot/vessel/{mmsi}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/xml")
    assert mmsi in r.text
    assert "57.712300" in r.text
    assert "11.966800" in r.text


def test_int002_nffi_alert_endpoint_uses_persisted_scoped_alert(client):
    token = register_and_login_as_admin(client)
    alert_id, _ = _seed_vessel_and_alert_for_latest_user()

    r = client.get(
        f"/v1/interop/nffi/alert/{alert_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/xml")
    assert "Interop export seed alert" in r.text
    assert "TELEPORT" in r.text


def test_org_scope_rejects_unscoped_models_for_non_super_admin(client):
    token = register_and_login_as_admin(client)
    assert token

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username.isnot(None)).order_by(User.id.desc()).first()
        assert user is not None
        with pytest.raises(ValueError, match="organisation_id"):
            apply_org_filter(db.query(Organisation), Organisation, user)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# INT-003: alert rationale reconstruction  [pending BL-009]
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="INT-003 requires BL-009 (evidence preservation model) — not yet implemented",
    strict=False,
)
def test_int003_alert_rationale_reconstruction(client):
    """INT-003: reconstructing alert rationale from stored evidence is deterministic."""
    raise NotImplementedError("BL-009 evidence record model required")
