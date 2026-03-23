"""World Port Index + UN/LOCODE ingestion helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from app.modules.integrations.models import PortReference, UnlocodeReference


@dataclass(frozen=True)
class PortSeedRow:
    """Canonical import row for ports reference table."""

    source: str
    source_id: str
    name: str
    country_code: str | None
    unlocode: str | None
    latitude: float
    longitude: float
    geom_wkt: str
    metadata_json: dict
    license_tag: str


def parse_wpi_csv(path: str) -> list[PortSeedRow]:
    rows: list[PortSeedRow] = []
    for raw in _read_csv_dicts(path):
        name = (raw.get("port_name") or raw.get("name") or "").strip()
        if not name:
            continue
        lat = _to_float(raw.get("latitude") or raw.get("lat"))
        lon = _to_float(raw.get("longitude") or raw.get("lon"))
        if lat is None or lon is None:
            continue
        source_id = (raw.get("world_port_index_number") or raw.get("id") or name).strip()
        country = _clean_or_none(raw.get("country_code") or raw.get("iso2"))
        unlocode = _clean_or_none(raw.get("unlocode") or raw.get("locode"))
        rows.append(
            PortSeedRow(
                source="world_port_index",
                source_id=source_id,
                name=name,
                country_code=country,
                unlocode=unlocode,
                latitude=lat,
                longitude=lon,
                geom_wkt=f"POINT({lon} {lat})",
                metadata_json={
                    "raw_country": raw.get("country"),
                    "harbor_size": raw.get("harbor_size"),
                    "harbor_type": raw.get("harbor_type"),
                },
                license_tag="restricted_non_commercial",
            )
        )
    return rows


def parse_unlocode_csv(path: str) -> list[PortSeedRow]:
    rows: list[PortSeedRow] = []
    for raw in _read_csv_dicts(path):
        locode = (raw.get("locode") or raw.get("code") or "").strip()
        name = (raw.get("name") or raw.get("location_name") or "").strip()
        if not locode or not name:
            continue
        lat = _to_float(raw.get("latitude") or raw.get("lat"))
        lon = _to_float(raw.get("longitude") or raw.get("lon"))
        if lat is None or lon is None:
            continue
        country = _clean_or_none(raw.get("country_code") or locode[:2])
        rows.append(
            PortSeedRow(
                source="unlocode",
                source_id=locode,
                name=name,
                country_code=country,
                unlocode=locode,
                latitude=lat,
                longitude=lon,
                geom_wkt=f"POINT({lon} {lat})",
                metadata_json={
                    "function": raw.get("function"),
                    "status": raw.get("status"),
                    "subdivision": raw.get("subdivision"),
                },
                license_tag="restricted_non_commercial",
            )
        )
    return rows


def ingest_port_datasets(
    db: Session,
    *,
    world_port_index_rows: Iterable[PortSeedRow] = (),
    unlocode_rows: Iterable[PortSeedRow] = (),
) -> dict[str, int]:
    """Insert WPI and UN/LOCODE rows into PostGIS-friendly reference tables."""
    ports_written = 0
    locodes_written = 0

    for row in world_port_index_rows:
        db.merge(
            PortReference(
                source=row.source,
                source_id=row.source_id,
                name=row.name,
                country_code=row.country_code,
                unlocode=row.unlocode,
                latitude=row.latitude,
                longitude=row.longitude,
                geom_wkt=row.geom_wkt,
                metadata_json=row.metadata_json,
                license_tag=row.license_tag,
            )
        )
        ports_written += 1

    for row in unlocode_rows:
        if row.unlocode:
            db.merge(
                UnlocodeReference(
                    unlocode=row.unlocode,
                    name=row.name,
                    country_code=row.country_code,
                    latitude=row.latitude,
                    longitude=row.longitude,
                    geom_wkt=row.geom_wkt,
                    metadata_json=row.metadata_json,
                    license_tag=row.license_tag,
                )
            )
            locodes_written += 1
    db.commit()
    return {"ports_written": ports_written, "locodes_written": locodes_written}


def _read_csv_dicts(path: str) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Import file not found: {path}")
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader]


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _clean_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    return s or None

