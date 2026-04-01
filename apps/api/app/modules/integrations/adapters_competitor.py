"""BL-011: Competitor AIS-export import adapter and migration validator.

Converts track/position history exports from common maritime intelligence
platforms (MarineTraffic, VesselFinder, FleetMon, exactEarth) into the
AegisAIS canonical ``CanonicalTrackPoint`` model used by the detection pipeline.

Usage
-----
::

    from app.modules.integrations.adapters_competitor import CompetitorImportAdapter
    from app.modules.integrations.migration_validator import validate_competitor_rows

    adapter = CompetitorImportAdapter(format="marine_traffic")
    rows, report = adapter.import_csv("export.csv")
    print(report.to_dict())

Supported formats
-----------------
- ``marine_traffic``   — MarineTraffic vessel history CSV export
- ``vessel_finder``    — VesselFinder position history CSV export
- ``fleet_mon``        — FleetMon AIS track CSV export
- ``generic_nmea``     — Generic NMEA-style positional CSV (mmsi, lat, lon, ts, sog, cog)
"""
from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

from app.modules.integrations.adapters_opensky import CanonicalTrackPoint

_log = logging.getLogger("aegisais.integrations.competitor")

# Supported competitor format identifiers
CompetitorFormat = Literal["marine_traffic", "vessel_finder", "fleet_mon", "generic_nmea"]

# ---------------------------------------------------------------------------
# Migration validation report
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompetitorMigrationReport:
    """Per-import quality report (BL-011 acceptance criteria)."""

    format: str
    total_rows: int
    imported_rows: int
    failed_rows: int
    duplicate_track_keys: int
    missing_position: int
    missing_timestamp: int
    invalid_mmsi: int
    confidence_score: float  # imported_rows / total_rows, 0–1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Format-specific CSV field maps
# ---------------------------------------------------------------------------

# Each entry maps canonical field → list of candidate CSV header names (first match wins).
_FIELD_MAP: dict[CompetitorFormat, dict[str, list[str]]] = {
    "marine_traffic": {
        "mmsi": ["MMSI", "mmsi"],
        "lat": ["LAT", "lat", "latitude", "LATITUDE"],
        "lon": ["LON", "lon", "longitude", "LONGITUDE"],
        "timestamp": ["TIMESTAMP", "timestamp", "TIME", "time", "DATETIME"],
        "speed": ["SPEED", "speed", "SOG", "sog"],
        "course": ["COURSE", "course", "COG", "cog"],
        "heading": ["HEADING", "heading", "HDG", "hdg"],
        "ship_name": ["SHIPNAME", "ship_name", "vessel_name", "NAME"],
    },
    "vessel_finder": {
        "mmsi": ["MMSI", "mmsi", "mmsinumber"],
        "lat": ["Latitude", "lat", "LAT"],
        "lon": ["Longitude", "lon", "LON"],
        "timestamp": ["Time", "timestamp", "Timestamp", "UTC Time"],
        "speed": ["Speed", "SOG", "speed"],
        "course": ["Course", "COG", "course"],
        "heading": ["Heading", "heading"],
        "ship_name": ["VesselName", "vessel_name", "Name"],
    },
    "fleet_mon": {
        "mmsi": ["MMSI", "mmsi"],
        "lat": ["Latitude", "lat", "LAT"],
        "lon": ["Longitude", "lon", "LON"],
        "timestamp": ["UTC", "Timestamp", "timestamp", "Date/Time UTC"],
        "speed": ["Speed (kn)", "Speed", "SOG"],
        "course": ["Course", "Course (°)", "COG"],
        "heading": ["Heading", "True Heading"],
        "ship_name": ["Vessel Name", "Ship Name", "Name"],
    },
    "generic_nmea": {
        "mmsi": ["mmsi", "MMSI", "Mmsi"],
        "lat": ["lat", "latitude", "LAT", "Latitude"],
        "lon": ["lon", "longitude", "LON", "Longitude"],
        "timestamp": ["timestamp", "TIMESTAMP", "ts", "TS", "datetime", "UTC", "Time", "TIME"],
        "speed": ["sog", "SOG", "speed", "SPEED", "Speed"],
        "course": ["cog", "COG", "course", "COURSE", "Course"],
        "heading": ["heading", "HEADING", "Heading", "hdg", "HDG"],
        "ship_name": ["name", "NAME", "ship_name", "SHIPNAME"],
    },
}

_MMSI_RE = re.compile(r"^\d{9}$")


def _resolve_field(row: dict[str, str], candidates: list[str]) -> Optional[str]:
    """Return the first non-empty value matching any candidate header."""
    for c in candidates:
        v = row.get(c, "").strip()
        if v:
            return v
    return None


def _parse_timestamp(raw: str) -> Optional[datetime]:
    """Try multiple ISO/common timestamp formats."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S UTC",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y%m%dT%H%M%S",
    ]
    raw = raw.strip().rstrip("Z")
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _to_float(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Core adapter
# ---------------------------------------------------------------------------


class CompetitorImportAdapter:
    """Import and validate competitor AIS export CSVs into canonical form.

    Parameters
    ----------
    format:
        One of the supported ``CompetitorFormat`` identifiers.  When
        ``"generic_nmea"`` is used the adapter applies a broad field-match
        heuristic that should handle most plain NMEA-derived CSV exports.
    source_tag:
        Arbitrary label stored on the ``CanonicalTrackPoint.source``; used to
        track data provenance in the pipeline.
    """

    def __init__(
        self,
        *,
        format: CompetitorFormat = "generic_nmea",
        source_tag: Optional[str] = None,
    ) -> None:
        if format not in _FIELD_MAP:
            raise ValueError(
                f"Unknown competitor format '{format}'. "
                f"Supported: {list(_FIELD_MAP.keys())}"
            )
        self._format = format
        self._field_map = _FIELD_MAP[format]
        self._source_tag = source_tag or f"competitor:{format}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def import_csv(
        self,
        path_or_content: "str | Path | io.StringIO",
    ) -> tuple[list[CanonicalTrackPoint], CompetitorMigrationReport]:
        """Parse a CSV file/buffer and return (canonical_rows, report).

        All parse errors are captured; no exception is raised on bad rows.
        """
        rows_raw = list(self._read_csv(path_or_content))
        points, report = self._convert(rows_raw)
        _log.info(
            "competitor_import_complete",
            extra={
                "format": self._format,
                "total": report.total_rows,
                "imported": report.imported_rows,
                "failed": report.failed_rows,
                "confidence": report.confidence_score,
            },
        )
        return points, report

    def import_rows(
        self,
        rows: Iterable[dict[str, str]],
    ) -> tuple[list[CanonicalTrackPoint], CompetitorMigrationReport]:
        """Convert an iterable of pre-parsed dicts (useful for testing)."""
        return self._convert(list(rows))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_csv(
        self,
        source: "str | Path | io.StringIO",
    ) -> Iterable[dict[str, str]]:
        if isinstance(source, io.StringIO):
            yield from csv.DictReader(source)
            return
        with open(source, newline="", encoding="utf-8-sig") as f:
            yield from csv.DictReader(f)

    def _convert(
        self,
        raw_rows: list[dict[str, str]],
    ) -> tuple[list[CanonicalTrackPoint], CompetitorMigrationReport]:
        total = len(raw_rows)
        points: list[CanonicalTrackPoint] = []
        failed = 0
        dup_keys = 0
        missing_position = 0
        missing_timestamp = 0
        invalid_mmsi = 0
        seen_track_keys: set[tuple[str, str]] = set()

        fm = self._field_map
        for row in raw_rows:
            errors: list[str] = []

            mmsi = _resolve_field(row, fm["mmsi"]) or ""
            if not _MMSI_RE.match(mmsi):
                invalid_mmsi += 1
                errors.append("invalid_mmsi")

            lat_raw = _resolve_field(row, fm["lat"])
            lon_raw = _resolve_field(row, fm["lon"])
            lat = _to_float(lat_raw)
            lon = _to_float(lon_raw)
            if lat is None or lon is None:
                missing_position += 1
                errors.append("missing_position")

            ts_raw = _resolve_field(row, fm["timestamp"]) or ""
            ts = _parse_timestamp(ts_raw) if ts_raw else None
            if ts is None:
                missing_timestamp += 1
                errors.append("missing_timestamp")

            if errors:
                failed += 1
                continue

            # Deduplication by (mmsi, observed_at_utc) track key
            track_key = (mmsi, ts.isoformat())  # type: ignore[union-attr]
            if track_key in seen_track_keys:
                dup_keys += 1
                failed += 1
                continue
            seen_track_keys.add(track_key)

            speed_mps: Optional[float] = None
            sog_kn = _to_float(_resolve_field(row, fm["speed"]))
            if sog_kn is not None:
                speed_mps = sog_kn * 0.514444  # knots → m/s

            points.append(
                CanonicalTrackPoint(
                    source=self._source_tag,
                    provider=self._format,
                    track_id=f"{mmsi}:{ts.isoformat()}",  # type: ignore[union-attr]
                    transponder_id=mmsi,
                    latitude=lat,  # type: ignore[arg-type]
                    longitude=lon,  # type: ignore[arg-type]
                    altitude_m=None,  # AIS surface vessels — N/A
                    speed_mps=speed_mps,
                    heading_deg=_to_float(_resolve_field(row, fm["heading"])),
                    vertical_rate_mps=None,
                    observed_at_utc=ts.isoformat(),  # type: ignore[union-attr]
                    raw=dict(row),
                )
            )

        imported = len(points)
        confidence = round(imported / total, 4) if total else 0.0
        report = CompetitorMigrationReport(
            format=self._format,
            total_rows=total,
            imported_rows=imported,
            failed_rows=failed,
            duplicate_track_keys=dup_keys,
            missing_position=missing_position,
            missing_timestamp=missing_timestamp,
            invalid_mmsi=invalid_mmsi,
            confidence_score=confidence,
        )
        return points, report
