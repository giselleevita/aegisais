"""Idempotent seed of Baltic cable zones from baltic_cables.py into the database."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.itdae.models import ItdaeGeofenceZone
from app.modules.itdae.geofences.baltic_cables import BALTIC_CABLE_ZONES
from app.modules.itdae.geofences.zones_service import invalidate_itdae_zones_cache

_log = logging.getLogger("aegisais.itdae.seed")


def seed_baltic_geofence_zones(db: Session) -> None:
    """
    Upsert zones from BALTIC_CABLE_ZONES by name (idempotent).
    When a row exists with the same name, updates polygon/description/risk_level from seed.
    Primary key id is not changed on existing rows.
    """
    bind = db.get_bind()
    if bind is not None:
        try:
            if not inspect(bind).has_table("itdae_geofence_zones"):
                _log.info(
                    "Skipping ITDAE Baltic geofence seed: table itdae_geofence_zones is missing "
                    "(run `alembic upgrade head` in apps/api)."
                )
                return
        except Exception as exc:
            _log.debug("Could not inspect itdae_geofence_zones: %s", exc)

    now = datetime.now(timezone.utc)
    oid = settings.default_organisation_id
    for z in BALTIC_CABLE_ZONES:
        poly_geojson = {"type": "Polygon", "coordinates": [z["polygon"]]}
        existing = db.query(ItdaeGeofenceZone).filter(ItdaeGeofenceZone.name == z["name"]).first()
        if existing:
            existing_any = cast(Any, existing)
            existing_any.description = z.get("description")
            existing_any.risk_level = z["risk_level"]
            existing_any.polygon_geojson = poly_geojson
            existing_any.is_active = True
            existing_any.updated_at = now
            existing_any.organisation_id = oid
        else:
            db.add(
                ItdaeGeofenceZone(
                    id=z["id"],
                    organisation_id=oid,
                    name=z["name"],
                    description=z.get("description"),
                    risk_level=z["risk_level"],
                    polygon_geojson=poly_geojson,
                    is_active=True,
                    created_by_id=None,
                    created_at=now,
                    updated_at=now,
                )
            )
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        _log.warning("baltic geofence seed failed: %s", e)
        raise
    invalidate_itdae_zones_cache()
