"""Read APIs for canonical observations and immutable fusion events."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_org_scope
from app.modules.observations.models import FusionEvent, Observation
from app.modules.observations.service import observation_to_contract

router = APIRouter()

_MARITIME_LAYERS = [
    {
        "id": "maritime.ais.terrestrial",
        "name": "Terrestrial AIS",
        "domain": "maritime",
        "licensedFeature": "subsea:read",
        "source": "AISStream or attributed replay",
        "objectKeyPrefix": "maritime/ais/terrestrial/",
        "mode": "live",
        "licenceClass": "provider_terms",
        "confidenceMethod": "provider_and_completeness",
    },
    {
        "id": "maritime.ais.satellite",
        "name": "Satellite AIS",
        "domain": "maritime",
        "licensedFeature": "subsea:read",
        "source": "Configured S-AIS provider",
        "objectKeyPrefix": "maritime/ais/satellite/",
        "mode": "live",
        "licenceClass": "commercial",
        "confidenceMethod": "provider_and_completeness",
    },
    {
        "id": "maritime.sar.gfw",
        "name": "Sentinel-1 SAR vessel detections",
        "domain": "maritime",
        "licensedFeature": "subsea:read",
        "source": "Global Fishing Watch / Copernicus Sentinel-1",
        "objectKeyPrefix": "maritime/sar/gfw/",
        "mode": "historical_replay",
        "licenceClass": "noncommercial_only",
        "confidenceMethod": "provider_detection_score",
    },
    {
        "id": "maritime.fusion.cable-risk",
        "name": "Fused cable-risk events",
        "domain": "maritime",
        "licensedFeature": "subsea:read",
        "source": "AegisAIS fusion engine",
        "objectKeyPrefix": "maritime/fusion/cable-risk/",
        "mode": "derived",
        "licenceClass": "tenant",
        "confidenceMethod": "independent_sensor_corroboration",
    },
]


@router.get("/layers/manifest")
def layer_manifest(user: Any = Depends(get_org_scope)):
    now = datetime.now().astimezone().isoformat()
    return {
        "layers": [{**layer, "updatedAt": now} for layer in _MARITIME_LAYERS],
        "generatedAt": now,
        "organisationId": str(user.organisation_id),
    }


@router.get("/observations")
def list_observations(
    layer_id: str | None = Query(default=None, alias="layerId"),
    entity_id: str | None = Query(default=None, alias="entityId"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    min_lon: float | None = Query(default=None, alias="minLon", ge=-180, le=180),
    min_lat: float | None = Query(default=None, alias="minLat", ge=-90, le=90),
    max_lon: float | None = Query(default=None, alias="maxLon", ge=-180, le=180),
    max_lat: float | None = Query(default=None, alias="maxLat", ge=-90, le=90),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
    user: Any = Depends(get_org_scope),
):
    query = db.query(Observation).filter(Observation.organisation_id == user.organisation_id)
    if layer_id:
        query = query.filter(Observation.layer_id == layer_id)
    if entity_id:
        query = query.filter(Observation.entity_id == entity_id)
    if start_time:
        query = query.filter(Observation.observed_at >= start_time)
    if end_time:
        query = query.filter(Observation.observed_at <= end_time)
    if min_lon is not None:
        query = query.filter(Observation.longitude >= min_lon)
    if min_lat is not None:
        query = query.filter(Observation.latitude >= min_lat)
    if max_lon is not None:
        query = query.filter(Observation.longitude <= max_lon)
    if max_lat is not None:
        query = query.filter(Observation.latitude <= max_lat)
    rows = query.order_by(Observation.observed_at.desc()).limit(limit).all()
    return [observation_to_contract(row).model_dump(mode="json", exclude_none=True) for row in rows]


@router.get("/fusion/events")
def list_fusion_events(
    event_type: str | None = Query(default=None, alias="eventType"),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: Any = Depends(get_org_scope),
):
    query = db.query(FusionEvent).filter(FusionEvent.organisation_id == user.organisation_id)
    if event_type:
        query = query.filter(FusionEvent.event_type == event_type)
    rows = query.order_by(FusionEvent.occurred_at.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "eventType": row.event_type,
            "entityIds": row.entity_ids,
            "observationIds": row.observation_ids,
            "occurredAt": row.occurred_at,
            "severity": row.severity,
            "geometry": {"type": "Point", "coordinates": [row.longitude, row.latitude]},
            "attributes": row.attributes,
            "confidence": row.confidence,
            "provenance": row.provenance,
            "access": row.access,
        }
        for row in rows
    ]
