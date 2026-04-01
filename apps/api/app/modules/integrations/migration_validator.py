"""Validation helpers for migration/import batches."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from app.modules.integrations.importers_ports import PortSeedRow


@dataclass(frozen=True)
class MigrationValidationReport:
    total_rows: int
    valid_rows: int
    duplicate_source_keys: int
    missing_names: int
    missing_geometry: int
    missing_identifiers: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def validate_port_seed_rows(rows: Iterable[PortSeedRow]) -> MigrationValidationReport:
    seen: set[tuple[str, str]] = set()
    total_rows = 0
    duplicate_source_keys = 0
    missing_names = 0
    missing_geometry = 0
    missing_identifiers = 0

    for row in rows:
        total_rows += 1
        source_key = (row.source, row.source_id)
        if source_key in seen:
            duplicate_source_keys += 1
        seen.add(source_key)

        if not row.name.strip():
            missing_names += 1
        if row.latitude is None or row.longitude is None or not row.geom_wkt:
            missing_geometry += 1
        if not row.source_id.strip():
            missing_identifiers += 1

    invalid_rows = duplicate_source_keys + missing_names + missing_geometry + missing_identifiers
    valid_rows = max(total_rows - invalid_rows, 0)
    return MigrationValidationReport(
        total_rows=total_rows,
        valid_rows=valid_rows,
        duplicate_source_keys=duplicate_source_keys,
        missing_names=missing_names,
        missing_geometry=missing_geometry,
        missing_identifiers=missing_identifiers,
    )