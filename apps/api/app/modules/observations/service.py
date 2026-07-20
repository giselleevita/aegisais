"""Validation, idempotency and persistence for canonical observations."""

from __future__ import annotations

import hashlib
import json
from datetime import timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .contracts import CanonicalObservation
from .models import Observation


def observation_idempotency_key(observation: CanonicalObservation) -> str:
    source_record_id = observation.provenance.sourceRecordId
    if source_record_id:
        material = f"{observation.provenance.source}:{source_record_id}"
    else:
        material = json.dumps(
            {
                "entityId": observation.entityId,
                "layerId": observation.layerId,
                "geometry": observation.geometry.model_dump(mode="json"),
                "observedAt": observation.observedAt.astimezone(timezone.utc).isoformat(),
                "properties": observation.properties,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    return hashlib.sha256(material.encode()).hexdigest()


def persist_observation(
    db: Session,
    observation: CanonicalObservation,
    organisation_id: int,
) -> tuple[Observation, bool]:
    key = observation_idempotency_key(observation)
    existing = (
        db.query(Observation)
        .filter(
            Observation.organisation_id == organisation_id,
            Observation.idempotency_key == key,
        )
        .first()
    )
    if existing is not None:
        return existing, False

    row = Observation(
        id=observation.id,
        organisation_id=organisation_id,
        entity_id=observation.entityId,
        layer_id=observation.layerId,
        observed_at=observation.observedAt,
        ingested_at=observation.ingestedAt,
        longitude=observation.longitude,
        latitude=observation.latitude,
        geometry=observation.geometry.model_dump(mode="json"),
        properties=observation.properties,
        confidence=observation.confidence.model_dump(mode="json", exclude_none=True),
        provenance=observation.provenance.model_dump(mode="json", exclude_none=True),
        access=observation.access.model_dump(mode="json", exclude_none=True),
        idempotency_key=key,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        existing = (
            db.query(Observation)
            .filter(
                Observation.organisation_id == organisation_id,
                Observation.idempotency_key == key,
            )
            .first()
        )
        if existing is None:
            raise
        return existing, False
    return row, True


def observation_to_contract(row: Observation) -> CanonicalObservation:
    return CanonicalObservation.model_validate(
        {
            "id": row.id,
            "entityId": row.entity_id,
            "layerId": row.layer_id,
            "geometry": row.geometry,
            "properties": row.properties or {},
            "observedAt": row.observed_at,
            "ingestedAt": row.ingested_at,
            "confidence": row.confidence,
            "provenance": row.provenance,
            "access": row.access,
        }
    )
