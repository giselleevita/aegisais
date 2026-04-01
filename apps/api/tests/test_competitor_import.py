"""BL-011: Competitor import adapter tests.

Verifies:
  1. Valid rows produce CanonicalTrackPoints.
  2. Unknown competitor format raises ValueError.
  3. Rows with invalid MMSI are excluded from output.
  4. Rows with missing lat/lon are excluded.
  5. Rows with missing/unparseable timestamps are excluded.
  6. Duplicate (mmsi, timestamp) within the same batch are deduplicated.
  7. Confidence score is correct.
  8. All supported format identifiers initialise without error.
  9. Speed is correctly converted from knots to m/s.
"""
from __future__ import annotations

import io

import pytest

from app.modules.integrations.adapters_competitor import CompetitorImportAdapter


def _csv(headers: list[str], *rows: list[str]) -> io.StringIO:
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(row))
    return io.StringIO("\n".join(lines))


VALID_MT_CSV = _csv(
    ["MMSI", "LAT", "LON", "TIMESTAMP", "SPEED", "COURSE", "HEADING", "SHIPNAME"],
    ["265503690", "57.123", "18.456", "2026-03-01T10:00:00", "12.5", "270", "275", "TEST VESSEL"],
    ["265503690", "57.124", "18.457", "2026-03-01T10:05:00", "12.4", "271", "276", "TEST VESSEL"],
)

VALID_VF_CSV = _csv(
    ["MMSI", "Latitude", "Longitude", "Time", "Speed", "Course", "Heading", "VesselName"],
    ["123456789", "51.500", "-0.100", "2026-03-01 09:00:00", "8.0", "180", "182", "LONDON VESSEL"],
)


def test_marine_traffic_valid_rows():
    adapter = CompetitorImportAdapter(format="marine_traffic")
    points, report = adapter.import_csv(VALID_MT_CSV)
    assert report.total_rows == 2
    assert report.imported_rows == 2
    assert report.failed_rows == 0
    assert report.confidence_score == 1.0
    assert all(p.transponder_id == "265503690" for p in points)


def test_vessel_finder_valid_rows():
    adapter = CompetitorImportAdapter(format="vessel_finder")
    points, report = adapter.import_csv(VALID_VF_CSV)
    assert report.imported_rows == 1
    assert points[0].transponder_id == "123456789"


def test_unknown_format_raises():
    with pytest.raises(ValueError, match="Unknown competitor format"):
        CompetitorImportAdapter(format="not_a_format")  # type: ignore


def test_invalid_mmsi_excluded():
    csv_buf = _csv(
        ["MMSI", "LAT", "LON", "TIMESTAMP", "SPEED"],
        ["INVALID", "57.0", "18.0", "2026-03-01T10:00:00", "5.0"],
        ["265503690", "57.1", "18.1", "2026-03-01T10:01:00", "5.0"],
    )
    adapter = CompetitorImportAdapter(format="marine_traffic")
    points, report = adapter.import_csv(csv_buf)
    assert report.invalid_mmsi == 1
    assert report.imported_rows == 1
    assert report.failed_rows == 1


def test_missing_lat_lon_excluded():
    csv_buf = _csv(
        ["MMSI", "LAT", "LON", "TIMESTAMP", "SPEED"],
        ["265503690", "", "", "2026-03-01T10:00:00", "5.0"],
        ["265503691", "57.1", "18.1", "2026-03-01T10:01:00", "5.0"],
    )
    adapter = CompetitorImportAdapter(format="generic_nmea")
    points, report = adapter.import_csv(csv_buf)
    assert report.missing_position == 1
    assert report.imported_rows == 1


def test_missing_timestamp_excluded():
    csv_buf = _csv(
        ["MMSI", "LAT", "LON", "TIMESTAMP", "SPEED"],
        ["265503690", "57.0", "18.0", "", "5.0"],
        ["265503691", "57.1", "18.1", "2026-03-01T10:01:00", "5.0"],
    )
    adapter = CompetitorImportAdapter(format="generic_nmea")
    points, report = adapter.import_csv(csv_buf)
    assert report.missing_timestamp == 1
    assert report.imported_rows == 1


def test_duplicate_track_key_deduplicated():
    """Same MMSI + same timestamp twice must produce only one canonical point."""
    csv_buf = _csv(
        ["MMSI", "LAT", "LON", "TIMESTAMP", "SPEED"],
        ["265503690", "57.0", "18.0", "2026-03-01T10:00:00", "5.0"],
        ["265503690", "57.0", "18.0", "2026-03-01T10:00:00", "5.0"],
    )
    adapter = CompetitorImportAdapter(format="generic_nmea")
    points, report = adapter.import_csv(csv_buf)
    assert report.duplicate_track_keys == 1
    assert report.imported_rows == 1


def test_speed_converted_knots_to_ms():
    """12 knots → ~6.173 m/s."""
    csv_buf = _csv(
        ["MMSI", "LAT", "LON", "TIMESTAMP", "SPEED"],
        ["265503690", "57.0", "18.0", "2026-03-01T10:00:00", "12.0"],
    )
    adapter = CompetitorImportAdapter(format="generic_nmea")
    points, _ = adapter.import_csv(csv_buf)
    assert points[0].speed_mps is not None
    assert abs(points[0].speed_mps - 12.0 * 0.514444) < 0.001


def test_all_supported_formats_initialise():
    for fmt in ("marine_traffic", "vessel_finder", "fleet_mon", "generic_nmea"):
        adapter = CompetitorImportAdapter(format=fmt)  # type: ignore
        assert adapter is not None


def test_confidence_score_partial():
    csv_buf = _csv(
        ["MMSI", "LAT", "LON", "TIMESTAMP", "SPEED"],
        ["265503690", "57.0", "18.0", "2026-03-01T10:00:00", "5.0"],
        ["BADMMSI", "57.0", "18.0", "2026-03-01T10:01:00", "5.0"],
    )
    adapter = CompetitorImportAdapter(format="generic_nmea")
    _, report = adapter.import_csv(csv_buf)
    assert report.confidence_score == 0.5
