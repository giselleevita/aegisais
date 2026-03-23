"""CRUD helpers for ITDAE geofence zones (DB + cache invalidation)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, cast

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.itdae.models import ItdaeGeofenceZone
from app.modules.itdae.geofences.zones_service import (
    invalidate_itdae_zones_cache,
    polygon_ring_from_geojson,
)

ALLOWED_RISK = frozenset({"low", "medium", "high", "critical"})


def validate_polygon_geojson(polygon_geojson: dict[str, Any]) -> dict[str, Any]:
    polygon_ring_from_geojson(polygon_geojson)
    return polygon_geojson


def validate_risk_level(risk_level: str) -> str:
    if risk_level not in ALLOWED_RISK:
        raise ValueError(f"risk_level must be one of {sorted(ALLOWED_RISK)}")
    return risk_level


def list_active_zones(db: Session, *, user: User) -> list[ItdaeGeofenceZone]:
    q = (
        db.query(ItdaeGeofenceZone)
        .filter(ItdaeGeofenceZone.is_active.is_(True))
    )
    if cast(str, user.role) != "super_admin":
        q = q.filter(ItdaeGeofenceZone.organisation_id == user.organisation_id)
    return q.order_by(ItdaeGeofenceZone.name).all()


def get_zone_by_id(db: Session, zone_id: str, *, user: User) -> Optional[ItdaeGeofenceZone]:
    q = db.query(ItdaeGeofenceZone).filter(ItdaeGeofenceZone.id == zone_id)
    if cast(str, user.role) != "super_admin":
        q = q.filter(ItdaeGeofenceZone.organisation_id == user.organisation_id)
    return q.first()


def create_zone(
    db: Session,
    *,
    organisation_id: int,
    name: str,
    description: Optional[str],
    risk_level: str,
    polygon_geojson: dict[str, Any],
    created_by_id: int,
) -> ItdaeGeofenceZone:
    validate_risk_level(risk_level)
    validate_polygon_geojson(polygon_geojson)
    now = datetime.now(timezone.utc)
    zone_id = f"zone-{uuid.uuid4().hex[:16]}"
    row = ItdaeGeofenceZone(
        id=zone_id,
        organisation_id=organisation_id,
        name=name.strip(),
        description=description,
        risk_level=risk_level,
        polygon_geojson=polygon_geojson,
        is_active=True,
        created_by_id=created_by_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    invalidate_itdae_zones_cache()
    return row


def update_zone(
    db: Session,
    zone_id: str,
    *,
    user: User,
    name: Optional[str] = None,
    description: Optional[str] = None,
    risk_level: Optional[str] = None,
    polygon_geojson: Optional[dict[str, Any]] = None,
    is_active: Optional[bool] = None,
) -> Optional[ItdaeGeofenceZone]:
    row = get_zone_by_id(db, zone_id, user=user)
    if row is None:
        return None
    row_any = cast(Any, row)
    if name is not None:
        row_any.name = name.strip()
    if description is not None:
        row_any.description = description
    if risk_level is not None:
        row_any.risk_level = validate_risk_level(risk_level)
    if polygon_geojson is not None:
        row_any.polygon_geojson = validate_polygon_geojson(polygon_geojson)
    if is_active is not None:
        row_any.is_active = is_active
    row_any.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    invalidate_itdae_zones_cache()
    return row


def soft_delete_zone(db: Session, zone_id: str, *, user: User) -> bool:
    row = update_zone(db, zone_id, user=user, is_active=False)
    return row is not None
