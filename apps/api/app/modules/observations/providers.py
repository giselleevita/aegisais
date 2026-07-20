"""Provider adapters that emit canonical observations, never provider payloads."""

from __future__ import annotations

import json
import csv
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import AccessMetadata, CanonicalObservation, Confidence, GeoPoint, Provenance, ais_observation


class ObservationProvider(ABC):
    provider_id: str
    layer_id: str
    licence_tag: str

    @abstractmethod
    def load(self, organisation_id: int) -> list[CanonicalObservation]:
        raise NotImplementedError


class ReplayObservationProvider(ObservationProvider):
    provider_id = "festival-replay"
    layer_id = "maritime.ais.terrestrial"
    licence_tag = "simulation"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self, organisation_id: int) -> list[CanonicalObservation]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        rows = payload.get("observations", payload) if isinstance(payload, dict) else payload
        result: list[CanonicalObservation] = []
        for index, row in enumerate(rows):
            sensor_type = str(row.get("sensorType") or row.get("sensor_type") or "ais").lower()
            if sensor_type == "sar":
                result.append(_sar_observation(row, organisation_id, self.provider_id, index))
            else:
                mmsi = str(row["mmsi"])
                result.append(
                    ais_observation(
                        mmsi=mmsi,
                        observed_at=_parse_datetime(row.get("observedAt") or row.get("timestamp")),
                        lat=float(row["lat"]),
                        lon=float(row["lon"]),
                        source=self.provider_id,
                        layer_id=str(row.get("layerId") or self.layer_id),
                        organisation_id=organisation_id,
                        sog=_optional_float(row.get("sog")),
                        cog=_optional_float(row.get("cog")),
                        heading=_optional_float(row.get("heading")),
                        confidence=float(row.get("confidence", 0.95)),
                        source_record_id=str(row.get("id") or f"replay-{index}"),
                        licence_tag=self.licence_tag,
                    )
                )
        return result


class GFWSARGeoJSONProvider(ObservationProvider):
    provider_id = "global-fishing-watch"
    layer_id = "maritime.sar.gfw"
    licence_tag = "noncommercial_only"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self, organisation_id: int) -> list[CanonicalObservation]:
        if self.path.suffix.lower() == ".csv":
            csv_result: list[CanonicalObservation] = []
            with self.path.open("r", encoding="utf-8", newline="") as handle:
                for index, raw in enumerate(csv.DictReader(handle)):
                    row = dict(raw)
                    row["lat"] = row.get("lat") or row.get("latitude") or row.get("detect_lat")
                    row["lon"] = row.get("lon") or row.get("longitude") or row.get("detect_lon")
                    if row.get("matched") in {"true", "True", "1"}:
                        row["matched"] = True
                    elif row.get("matched") in {"false", "False", "0"}:
                        row["matched"] = False
                    try:
                        csv_result.append(_sar_observation(row, organisation_id, self.provider_id, index))
                    except (KeyError, TypeError, ValueError):
                        continue
            return csv_result
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        features = payload.get("features", [])
        geojson_result: list[CanonicalObservation] = []
        for index, feature in enumerate(features):
            geometry = feature.get("geometry") or {}
            coordinates = geometry.get("coordinates") or []
            if geometry.get("type") != "Point" or len(coordinates) < 2:
                continue
            properties = dict(feature.get("properties") or {})
            properties.update({"lat": coordinates[1], "lon": coordinates[0]})
            properties.setdefault("id", feature.get("id") or f"gfw-sar-{index}")
            geojson_result.append(_sar_observation(properties, organisation_id, self.provider_id, index))
        return geojson_result


# GFW bulk reports are CSV or GeoJSON downloads; keep the older class name as
# an alias while exposing the provider-neutral report name to new callers.
GFWSARReportProvider = GFWSARGeoJSONProvider


def _sar_observation(
    row: dict[str, Any],
    organisation_id: int,
    source: str,
    index: int,
) -> CanonicalObservation:
    observed_at = _parse_datetime(
        row.get("observedAt") or row.get("timestamp") or row.get("detect_timestamp")
    )
    record_id = str(row.get("id") or row.get("detection_id") or f"sar-{index}")
    matched = row.get("matched")
    matched_mmsi = row.get("mmsi") or row.get("matched_mmsi")
    entity_id = f"vessel:mmsi:{matched_mmsi}" if matched_mmsi else f"sensor-target:sar:{record_id}"
    confidence_score = float(row.get("confidence") or row.get("presence_score") or 0.8)
    ingested_at = datetime.now(timezone.utc)
    return CanonicalObservation(
        id=str(uuid4()),
        entityId=entity_id,
        layerId="maritime.sar.gfw",
        geometry=GeoPoint(coordinates=(float(row["lon"]), float(row["lat"]))),
        properties={
            "sensorType": "sar",
            "matched": matched,
            "matchedMmsi": str(matched_mmsi) if matched_mmsi else None,
            "lengthM": _optional_float(row.get("length_m")),
            "presenceScore": _optional_float(row.get("presence_score")),
            "matchingScore": _optional_float(row.get("matching_score")),
            "licenceTag": "noncommercial_only" if source == "global-fishing-watch" else "simulation",
            "historical": source == "global-fishing-watch",
        },
        observedAt=observed_at,
        ingestedAt=ingested_at,
        confidence=Confidence(score=max(0.0, min(1.0, confidence_score)), method="provider_detection_score"),
        provenance=Provenance(
            source=source,
            sourceRecordId=record_id,
            processor="aegisais.sar-normalizer/v1",
            ingestedAt=ingested_at,
            lineage=["Copernicus Sentinel-1"] if source == "global-fishing-watch" else ["festival simulation"],
        ),
        access=AccessMetadata(
            classification="restricted" if source == "global-fishing-watch" else "internal",
            allowedRoles=["viewer", "analyst", "admin", "super_admin"],
            compartments=["NONCOMMERCIAL_ONLY"] if source == "global-fishing-watch" else [],
            ownerOrgId=str(organisation_id),
        ),
    )


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _optional_float(value: Any) -> float | None:
    return None if value in (None, "") else float(value)
