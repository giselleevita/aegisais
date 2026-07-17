"""Python representation of packages/contracts/schemas/Observation.schema.json.

The JSON schema remains the public source of truth.  This model mirrors it for
backend validation and deliberately uses the schema's camelCase field names on
the wire.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeoPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]

    @field_validator("coordinates")
    @classmethod
    def valid_coordinates(cls, value: tuple[float, float]) -> tuple[float, float]:
        lon, lat = value
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("GeoPoint coordinates must be [longitude, latitude]")
        return value


class Confidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0, le=1)
    method: str
    lowerBound: float | None = Field(default=None, ge=0, le=1)
    upperBound: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    sourceRecordId: str | None = None
    processor: str
    ingestedAt: datetime
    lineage: list[str] = Field(default_factory=list)


class AccessMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: Literal["public", "internal", "restricted", "secret"]
    allowedRoles: list[str]
    compartments: list[str] = Field(default_factory=list)
    ownerOrgId: str | None = None


class CanonicalObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    entityId: str
    layerId: str
    geometry: GeoPoint
    properties: dict[str, Any] = Field(default_factory=dict)
    observedAt: datetime
    ingestedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: Confidence
    provenance: Provenance
    access: AccessMetadata

    @property
    def longitude(self) -> float:
        return self.geometry.coordinates[0]

    @property
    def latitude(self) -> float:
        return self.geometry.coordinates[1]


def ais_observation(
    *,
    mmsi: str,
    observed_at: datetime,
    lat: float,
    lon: float,
    source: str,
    layer_id: str,
    organisation_id: int,
    sog: float | None = None,
    cog: float | None = None,
    heading: float | None = None,
    confidence: float = 0.8,
    source_record_id: str | None = None,
    licence_tag: str = "tenant",
) -> CanonicalObservation:
    ingested_at = datetime.now(timezone.utc)
    return CanonicalObservation(
        entityId=f"vessel:mmsi:{mmsi}",
        layerId=layer_id,
        geometry=GeoPoint(coordinates=(lon, lat)),
        properties={
            "sensorType": "ais",
            "mmsi": mmsi,
            "sog": sog,
            "cog": cog,
            "heading": heading,
            "licenceTag": licence_tag,
        },
        observedAt=observed_at,
        ingestedAt=ingested_at,
        confidence=Confidence(score=confidence, method="provider_and_completeness"),
        provenance=Provenance(
            source=source,
            sourceRecordId=source_record_id,
            processor="aegisais.ais-normalizer/v1",
            ingestedAt=ingested_at,
        ),
        access=AccessMetadata(
            classification="internal",
            allowedRoles=["viewer", "analyst", "admin", "super_admin"],
            ownerOrgId=str(organisation_id),
        ),
    )
