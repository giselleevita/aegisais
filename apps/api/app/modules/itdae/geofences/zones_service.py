"""
Load active ITDAE geofence zones for point-in-polygon checks, with Redis caching.
Cache key: {redis_prefix}:itdae_zones, TTL 300s.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional, cast

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.itdae.models import ItdaeGeofenceZone

_log = logging.getLogger("aegisais.itdae.zones")

CACHE_TTL_SEC = 300
CACHE_KEY = f"{settings.redis_prefix}:itdae_zones"


def _zones_from_baltic_seed() -> list[dict[str, Any]]:
    """Fallback when DB is unavailable (e.g. unit tests without migrations). Not used in production."""
    from app.modules.itdae.geofences.baltic_cables import BALTIC_CABLE_ZONES

    out: list[dict[str, Any]] = []
    for z in BALTIC_CABLE_ZONES:
        out.append(
            {
                "id": z["id"],
                "name": z["name"],
                "description": z.get("description") or "",
                "risk_level": z["risk_level"],
                "polygon": z["polygon"],
            }
        )
    return out


def polygon_ring_from_geojson(polygon_geojson: dict[str, Any]) -> list[list[float]]:
    """Extract the exterior ring [lon, lat], ... from a GeoJSON Polygon dict."""
    if not polygon_geojson or polygon_geojson.get("type") != "Polygon":
        raise ValueError("polygon_geojson must be a GeoJSON Polygon")
    coords = polygon_geojson.get("coordinates")
    if not coords or not isinstance(coords, list):
        raise ValueError("Polygon coordinates missing")
    ring = coords[0]
    if not ring or len(ring) < 4:
        raise ValueError("Polygon exterior ring must have at least 4 positions")
    out: list[list[float]] = []
    for pt in ring:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            raise ValueError("Invalid polygon vertex")
        out.append([float(pt[0]), float(pt[1])])
    return out


def row_to_checker_zone(row: ItdaeGeofenceZone) -> dict[str, Any]:
    """Shape expected by checker.get_zone_for_position (includes polygon ring)."""
    ring = polygon_ring_from_geojson(cast(dict[str, Any], row.polygon_geojson))
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "risk_level": row.risk_level,
        "polygon": ring,
    }


def _load_zones_from_db(db: Session) -> list[dict[str, Any]]:
    try:
        rows = (
            db.query(ItdaeGeofenceZone)
            .filter(ItdaeGeofenceZone.is_active.is_(True))
            .order_by(ItdaeGeofenceZone.name)
            .all()
        )
        return [row_to_checker_zone(r) for r in rows]
    except OperationalError as e:
        if settings.app_env == "production":
            _log.critical("itdae_geofence_zones query failed in production: %s", e)
            raise
        _log.warning(
            "itdae_geofence_zones not available (%s), using baltic_cables seed fallback",
            e,
        )
        return _zones_from_baltic_seed()


def invalidate_itdae_zones_cache() -> None:
    try:
        from app.infrastructure.cache.redis_client import get_redis_client

        get_redis_client().delete(CACHE_KEY)
    except Exception as e:
        _log.warning("itdae zones cache invalidate failed: %s", e)


def get_active_zones_for_checker(db: Optional[Session] = None) -> list[dict[str, Any]]:
    """
    Zones for point-in-polygon checks: Redis first, else DB, then repopulate Redis.
    If db is None, opens a short-lived session (workers / detection rules).
    """
    try:
        from app.infrastructure.cache.redis_client import get_redis_client

        r = get_redis_client()
        raw = r.get(CACHE_KEY)
        if isinstance(raw, bytes):
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, list):
                return data
        elif isinstance(raw, str):
            data = json.loads(raw)
            if isinstance(data, list):
                return data
    except Exception as e:
        _log.warning("itdae zones cache read failed, falling back to DB: %s", e)

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        zones = _load_zones_from_db(db)
        try:
            from app.infrastructure.cache.redis_client import get_redis_client

            get_redis_client().setex(CACHE_KEY, CACHE_TTL_SEC, json.dumps(zones))
        except Exception as e:
            _log.warning("itdae zones cache write failed: %s", e)
        return zones
    finally:
        if close_db:
            db.close()
