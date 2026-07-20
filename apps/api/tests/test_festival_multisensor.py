from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.auth.models import Organisation
from app.modules.fusion.observation_fusion import (
    UNMATCHED_SAR_NEAR_CABLE,
    VESSEL_ACTIVITY_NEAR_CABLE,
    AIS_SILENCE_NEAR_CABLE,
    associate_sar_batch,
    event_to_alert,
    fuse_observation,
    scan_stale_ais_near_cables,
)
from app.modules.observations.contracts import (
    AccessMetadata,
    CanonicalObservation,
    Confidence,
    GeoPoint,
    Provenance,
    ais_observation,
)
from app.modules.observations.providers import GFWSARGeoJSONProvider, ReplayObservationProvider
from app.modules.observations.service import persist_observation


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(Organisation(id=1, name="Festival", slug="festival"))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _sar(*, observed_at: datetime, org_id: int, record_id: str = "sar-dark") -> CanonicalObservation:
    now = datetime.now(timezone.utc)
    return CanonicalObservation(
        id="11111111-1111-4111-8111-111111111111",
        entityId=f"sensor-target:sar:{record_id}",
        layerId="maritime.sar.gfw",
        geometry=GeoPoint(coordinates=(24.725, 59.475)),
        properties={"sensorType": "sar", "matched": False, "licenceTag": "simulation"},
        observedAt=observed_at,
        ingestedAt=now,
        confidence=Confidence(score=0.94, method="provider_detection_score"),
        provenance=Provenance(
            source="festival-replay",
            sourceRecordId=record_id,
            processor="test",
            ingestedAt=now,
        ),
        access=AccessMetadata(
            classification="internal",
            allowedRoles=["viewer", "analyst", "admin", "super_admin"],
            ownerOrgId=str(org_id),
        ),
    )


def test_replay_provider_emits_canonical_ais_and_sar():
    path = Path(__file__).resolve().parents[3] / "data/demo/festival_cable_multisensor.json"
    observations = ReplayObservationProvider(path).load(7)
    assert len(observations) == 5
    assert observations[-1].layerId == "maritime.sar.gfw"
    assert observations[-1].access.ownerOrgId == "7"
    assert observations[-1].provenance.source == "festival-replay"


def test_gfw_provider_skips_malformed_records_and_applies_licence_gate(tmp_path):
    report = tmp_path / "gfw-sar.geojson"
    report.write_text(
        """{
          "type": "FeatureCollection",
          "features": [
            {"id":"valid","type":"Feature","geometry":{"type":"Point","coordinates":[24.725,59.475]},"properties":{"timestamp":"2026-08-20T09:45:00Z","presence_score":0.91}},
            {"id":"line","type":"Feature","geometry":{"type":"LineString","coordinates":[]},"properties":{}},
            {"id":"missing-time","type":"Feature","geometry":{"type":"Point","coordinates":[24.7,59.4]},"properties":{}}
          ]
        }""",
        encoding="utf-8",
    )
    observations = GFWSARGeoJSONProvider(report).load(9)
    assert len(observations) == 2
    valid = observations[0]
    assert valid.provenance.source == "global-fishing-watch"
    assert valid.properties["historical"] is True
    assert valid.properties["licenceTag"] == "noncommercial_only"
    assert valid.access.classification == "restricted"
    assert valid.access.compartments == ["NONCOMMERCIAL_ONLY"]


def test_observation_idempotency_and_dark_sar_fusion(db):
    try:
        org_id = 1
        base = datetime(2026, 8, 20, 9, 10, tzinfo=timezone.utc)
        ais = ais_observation(
            mmsi="273000002",
            observed_at=base,
            lat=59.47,
            lon=24.72,
            source="festival-replay",
            layer_id="maritime.ais.terrestrial",
            organisation_id=org_id,
            sog=0.6,
            cog=25.0,
            confidence=0.92,
            source_record_id="ais-last",
            licence_tag="simulation",
        )
        ais_row, created = persist_observation(db, ais, org_id)
        assert created is True
        duplicate, duplicate_created = persist_observation(db, ais, org_id)
        assert duplicate.id == ais_row.id
        assert duplicate_created is False
        ais_events = fuse_observation(db, ais_row)
        assert [event.event_type for event in ais_events] == [VESSEL_ACTIVITY_NEAR_CABLE]
        db.commit()

        silence_events = scan_stale_ais_near_cables(
            db,
            organisation_id=org_id,
            now=base + timedelta(minutes=16),
        )
        assert [event.event_type for event in silence_events] == [AIS_SILENCE_NEAR_CABLE]
        assert silence_events[0].confidence["method"] == "prospective_track_staleness"
        db.commit()

        sar = _sar(observed_at=base + timedelta(minutes=35), org_id=org_id)
        sar_row, created = persist_observation(db, sar, org_id)
        assert created is True
        sar_events = fuse_observation(db, sar_row)
        assert [event.event_type for event in sar_events] == [UNMATCHED_SAR_NEAR_CABLE]
        assert sar_events[0].severity == "critical"
        assert sar_events[0].attributes["aisSilenceSec"] == 2100.0
        alert = event_to_alert(sar_events[0])
        assert alert["confidence"]["score"] == 0.92
        assert len(alert["evidence"]["observationIds"]) == 2
    finally:
        db.rollback()


def test_bipartite_association_is_one_to_one(db):
    try:
        from app.modules.observations.models import Observation

        org_id = 1
        base = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)
        ais_contract = ais_observation(
            mmsi="211000001",
            observed_at=base,
            lat=59.475,
            lon=24.725,
            source="festival-replay",
            layer_id="maritime.ais.terrestrial",
            organisation_id=org_id,
            sog=10,
            source_record_id="association-ais",
        )
        ais, _ = persist_observation(db, ais_contract, org_id)
        sar1, _ = persist_observation(db, _sar(observed_at=base, org_id=org_id, record_id="sar-1"), org_id)
        second = _sar(observed_at=base, org_id=org_id, record_id="sar-2").model_copy(
            update={"id": "22222222-2222-4222-8222-222222222222"}
        )
        sar2, _ = persist_observation(db, second, org_id)
        matches = associate_sar_batch([sar1, sar2], [ais])
        assert len(matches) == 1
        assert next(iter(matches.values()))[0].id == ais.id
        assert db.query(Observation).count() == 3
    finally:
        db.rollback()


def test_model_status_requires_authentication(client):
    response = client.get("/v1/models/anomaly/status")
    assert response.status_code == 401


def test_direct_api_auth_context_compatibility(client):
    from tests.conftest import register_and_login_as_admin

    token = register_and_login_as_admin(client)
    response = client.get("/v1/auth/context", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["viewer"]["role"] == "admin"
    assert response.json()["viewer"]["organizationId"]


def test_demo_reset_clears_only_festival_projection_rows(client):
    from app.modules.vessels.models import VesselLatest, VesselPosition
    from tests.conftest import TestingSessionLocal, register_and_login_as_admin

    token = register_and_login_as_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    context = client.get("/v1/auth/context", headers=headers).json()
    org_id = int(context["viewer"]["organizationId"])
    timestamp = datetime(2026, 8, 20, 9, 0)
    with TestingSessionLocal() as setup:
        setup.add_all(
            [
                VesselLatest(
                    organisation_id=org_id,
                    mmsi="273000002",
                    timestamp=timestamp,
                    lat=59.47,
                    lon=24.72,
                    source="festival-replay",
                    updated_at=timestamp,
                ),
                VesselLatest(
                    organisation_id=org_id,
                    mmsi="211999999",
                    timestamp=timestamp,
                    lat=59.0,
                    lon=24.0,
                    source="aisstream",
                    updated_at=timestamp,
                ),
                VesselPosition(
                    organisation_id=org_id,
                    mmsi="273000002",
                    timestamp=timestamp,
                    lat=59.47,
                    lon=24.72,
                    source="festival-replay",
                ),
                VesselPosition(
                    organisation_id=org_id,
                    mmsi="211999999",
                    timestamp=timestamp,
                    lat=59.0,
                    lon=24.0,
                    source="aisstream",
                ),
            ]
        )
        setup.commit()

    response = client.post("/v1/demo/scenarios/baltic-cable/reset", headers=headers)
    assert response.status_code == 200, response.text
    with TestingSessionLocal() as verify:
        assert verify.query(VesselPosition).filter_by(source="festival-replay").count() == 0
        assert verify.query(VesselLatest).filter_by(source="festival-replay").count() == 0
        assert verify.query(VesselPosition).filter_by(source="aisstream").count() == 1
        assert verify.query(VesselLatest).filter_by(source="aisstream").count() == 1


def test_worker_pipeline_persists_fused_alert_with_lineage(db, monkeypatch):
    from app.modules.alerts.models import Alert
    from app.services.workers import alert_worker, observation_worker

    factory = sessionmaker(bind=db.get_bind())
    published: list[tuple[str, dict]] = []
    monkeypatch.setattr(observation_worker, "SessionLocal", factory)
    monkeypatch.setattr(alert_worker, "SessionLocal", factory)
    monkeypatch.setattr(
        observation_worker.publisher,
        "publish",
        lambda stream, payload: published.append((stream, payload)),
    )

    base = datetime(2026, 8, 20, 9, 10, tzinfo=timezone.utc)
    ais = ais_observation(
        mmsi="273000002",
        observed_at=base,
        lat=59.47,
        lon=24.72,
        source="festival-replay",
        layer_id="maritime.ais.terrestrial",
        organisation_id=1,
        sog=0.6,
        source_record_id="worker-ais",
        licence_tag="simulation",
    )
    observation_worker.handle_observation("1-0", ais.model_dump(mode="json", exclude_none=True))
    sar = _sar(observed_at=base + timedelta(minutes=35), org_id=1, record_id="worker-sar")
    sar = sar.model_copy(update={"id": "33333333-3333-4333-8333-333333333333"})
    observation_worker.handle_observation("2-0", sar.model_dump(mode="json", exclude_none=True))

    fusion_alerts = [payload for stream, payload in published if payload["type"] == UNMATCHED_SAR_NEAR_CABLE]
    assert len(fusion_alerts) == 1
    alert_worker.handle_alert("3-0", fusion_alerts[0])

    db.expire_all()
    stored = db.query(Alert).filter(Alert.type == UNMATCHED_SAR_NEAR_CABLE).one()
    assert stored.confidence["method"] == "unmatched_independent_detection"
    assert stored.fusion_event_id == fusion_alerts[0]["fusion_event_id"]
    assert len(stored.evidence["observationIds"]) == 2
