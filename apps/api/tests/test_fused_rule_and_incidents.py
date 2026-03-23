from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.infrastructure.ingest.loaders import AisPoint
from app.modules.alerts.models import Alert
from app.modules.fusion.fused_rules import (
    FUSED_PROVENANCE_VERSION,
    FUSED_RULE_SCHEMA_VERSION,
    map_ais_to_surface_activity_event,
    rule_surface_activity_near_cable_segment,
    simulation_surface_activity_fixture,
)
from app.modules.incidents.service import (
    EvidenceBundle,
    INCIDENT_PROVENANCE_VERSION,
    INCIDENT_SCHEMA_VERSION,
    build_incident_evidence_bundle,
    create_incident_from_alert,
    create_incident_from_alert_with_flag,
)
from tests.conftest import TestingSessionLocal


def _pt(lat: float, lon: float, offset_sec: int = 0) -> AisPoint:
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    return AisPoint(
        mmsi="265503690",
        timestamp=base + timedelta(seconds=offset_sec),
        lat=lat,
        lon=lon,
        sog=9.2,
        cog=185.0,
        heading=183.0,
    )


def test_adapter_mapping_for_surface_event():
    point = _pt(54.6, 10.9)
    event = map_ais_to_surface_activity_event(point)
    assert event.source == "ais"
    assert event.event_id.startswith("ais-265503690-")
    assert event.lat == pytest.approx(point.lat)
    assert event.lon == pytest.approx(point.lon)


def test_fused_rule_geospatial_proximity_triggers_alert():
    # Near Nord Stream polygon vertex.
    p1 = _pt(54.595, 10.905, 0)
    p2 = _pt(54.601, 10.912, 120)
    result = rule_surface_activity_near_cable_segment(p1, p2)
    assert result is not None
    assert result["type"] == "FUSED_ACTIVITY_NEAR_CABLE"
    ev = result["evidence"]
    assert ev["distance_to_segment_m"] <= ev["proximity_threshold_m"]
    assert ev["schema_version"] == FUSED_RULE_SCHEMA_VERSION
    assert ev["provenance_version"] == FUSED_PROVENANCE_VERSION


def test_fused_rule_replay_determinism_for_same_input():
    p1 = _pt(54.595, 10.905, 0)
    p2 = _pt(54.601, 10.912, 120)
    r1 = rule_surface_activity_near_cable_segment(p1, p2)
    r2 = rule_surface_activity_near_cable_segment(p1, p2)
    assert r1 == r2
    fx1 = simulation_surface_activity_fixture(p2)
    fx2 = simulation_surface_activity_fixture(p2)
    assert fx1.event_id == fx2.event_id


def test_incident_evidence_schema_validation():
    bundle = EvidenceBundle(
        generated_at=datetime.now(timezone.utc),
        source_alert={"alert_id": 1},
        lineage={"created_from": "test"},
        legal={"subsurface_tracking": "not_performed"},
    )
    assert bundle.schema_version == INCIDENT_SCHEMA_VERSION
    assert bundle.provenance_version == INCIDENT_PROVENANCE_VERSION
    with pytest.raises(ValidationError):
        EvidenceBundle(
            generated_at=datetime.now(timezone.utc),
            source_alert={"alert_id": 1},
            lineage={"created_from": "test"},
            legal={"subsurface_tracking": "not_performed"},
            unexpected="x",
        )


def test_create_incident_from_alert_builds_bundle(client):
    db = TestingSessionLocal()
    try:
        alert = Alert(
            organisation_id=1,
            timestamp=datetime.now(timezone.utc),
            mmsi="265503690",
            type="FUSED_ACTIVITY_NEAR_CABLE",
            severity=82,
            summary="Near cable activity",
            evidence={"schema_version": FUSED_RULE_SCHEMA_VERSION},
        )
        db.add(alert)
        db.flush()

        incident = create_incident_from_alert(db, alert)
        db.commit()
        bundle = build_incident_evidence_bundle(alert)

        assert incident.alert_id == alert.id
        assert incident.evidence_bundle["schema_version"] == INCIDENT_SCHEMA_VERSION
        assert incident.evidence_bundle["provenance_version"] == INCIDENT_PROVENANCE_VERSION
        assert bundle["source_alert"]["alert_id"] == alert.id
        assert bundle["legal"]["subsurface_tracking"] == "not_performed"
    finally:
        db.close()


def test_create_incident_from_alert_with_flag_reports_existing(client):
    db = TestingSessionLocal()
    try:
        alert = Alert(
            organisation_id=1,
            timestamp=datetime.now(timezone.utc),
            mmsi="265503691",
            type="FUSED_ACTIVITY_NEAR_CABLE",
            severity=75,
            summary="Near cable activity",
            evidence={"schema_version": FUSED_RULE_SCHEMA_VERSION},
        )
        db.add(alert)
        db.flush()

        first, first_created = create_incident_from_alert_with_flag(db, alert)
        second, second_created = create_incident_from_alert_with_flag(db, alert)
        db.commit()

        assert first_created is True
        assert second_created is False
        assert first.id == second.id
    finally:
        db.close()
