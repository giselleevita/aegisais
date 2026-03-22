from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.modules.itdae.models import ItdaePosition
from app.modules.itdae.mappers import itdae_position_to_schema
from app.modules.itdae.ingestion.stream import stream_manager
from app.modules.itdae.geofences.checker import get_all_zones_for_position
from app.modules.itdae.geofences.zones_service import get_active_zones_for_checker
from app.modules.itdae.geofences import crud_service as geofence_crud
from app.modules.itdae.schemas import GeofenceZoneCreate, GeofenceZoneUpdate, GeofenceZoneOut

from app.middleware.rate_limit import api_read_rate_limit, api_write_rate_limit
from app.modules.auth.dependencies import require_admin, require_viewer_or_above

router = APIRouter()


@router.get("/health")
def itdae_health(
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_viewer_or_above),
):
    """Health endpoint for ITDAE module"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count = db.query(ItdaePosition).filter(ItdaePosition.timestamp >= today_start).count()
    return {
        "user": current_user.username,
        "positions_today": count,
        "stream_status": "running" if stream_manager.is_running else "stopped",
    }


@router.get("/dump-track/{mmsi}")
def dump_track(
    mmsi: str,
    _: Annotated[None, Depends(api_read_rate_limit)],
    hours: int = Query(6, description="Hours of history to dump"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_viewer_or_above),
):
    """Dump track history as JSON"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    positions = (
        db.query(ItdaePosition)
        .filter(ItdaePosition.mmsi == mmsi, ItdaePosition.timestamp >= cutoff)
        .order_by(ItdaePosition.timestamp.desc())
        .all()
    )
    return {
        "mmsi": mmsi,
        "hours": hours,
        "count": len(positions),
        "track": [itdae_position_to_schema(p).model_dump() for p in positions],
    }


@router.post("/stream/start")
async def start_stream(
    _: Annotated[None, Depends(api_write_rate_limit)],
    admin: Any = Depends(require_admin),
):
    await stream_manager.start()
    return {"status": "ok", "message": "Stream starting", "by": admin.username}


@router.post("/stream/stop")
async def stop_stream(
    _: Annotated[None, Depends(api_write_rate_limit)],
    admin: Any = Depends(require_admin),
):
    await stream_manager.stop()
    return {"status": "ok", "message": "Stream stopping", "by": admin.username}


# ─── Geofence zones (DB-backed) ───────────────────────────────────────────


@router.get("/zones", response_model=list[GeofenceZoneOut])
def list_geofence_zones(
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_viewer_or_above),
):
    rows = geofence_crud.list_active_zones(db, user=user)
    return [GeofenceZoneOut.model_validate(r) for r in rows]


@router.get("/zones/{zone_id}", response_model=GeofenceZoneOut)
def get_geofence_zone(
    zone_id: str,
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_viewer_or_above),
):
    row = geofence_crud.get_zone_by_id(db, zone_id, user=user)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return GeofenceZoneOut.model_validate(row)


@router.post("/zones", response_model=GeofenceZoneOut, status_code=status.HTTP_201_CREATED)
def create_geofence_zone(
    body: GeofenceZoneCreate,
    _: Annotated[None, Depends(api_write_rate_limit)],
    db: Session = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    try:
        row = geofence_crud.create_zone(
            db,
            organisation_id=admin.organisation_id,
            name=body.name,
            description=body.description,
            risk_level=body.risk_level,
            polygon_geojson=body.polygon_geojson,
            created_by_id=admin.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return GeofenceZoneOut.model_validate(row)


@router.patch("/zones/{zone_id}", response_model=GeofenceZoneOut)
def patch_geofence_zone(
    zone_id: str,
    body: GeofenceZoneUpdate,
    _: Annotated[None, Depends(api_write_rate_limit)],
    db: Session = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    try:
        row = geofence_crud.update_zone(
            db,
            zone_id,
            user=admin,
            name=body.name,
            description=body.description,
            risk_level=body.risk_level,
            polygon_geojson=body.polygon_geojson,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return GeofenceZoneOut.model_validate(row)


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_geofence_zone(
    zone_id: str,
    _: Annotated[None, Depends(api_write_rate_limit)],
    db: Session = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    if not geofence_crud.soft_delete_zone(db, zone_id, user=admin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return None


# ─── Geofence helpers (legacy paths) ─────────────────────────────────────


@router.get("/geofences/baltic")
def list_baltic_geofences(
    _: Annotated[None, Depends(api_read_rate_limit)],
    current_user: Any = Depends(require_viewer_or_above),
):
    """
    Return all active geofence zones with polygons (same shape as historical Baltic seed).
    """
    zones = get_active_zones_for_checker()
    return {
        "count": len(zones),
        "zones": [
            {
                "id": z["id"],
                "name": z["name"],
                "description": z["description"],
                "risk_level": z["risk_level"],
                "polygon": z["polygon"],
            }
            for z in zones
        ],
    }


@router.get("/geofences/check")
def check_geofence(
    _: Annotated[None, Depends(api_read_rate_limit)],
    lat: float = Query(..., description="Latitude of position to check"),
    lon: float = Query(..., description="Longitude of position to check"),
    current_user: Any = Depends(require_viewer_or_above),
):
    """
    Check if a lat/lon position falls within any geofence zone.
    Returns all matching zones (may be more than one if zones overlap).
    """
    matches = get_all_zones_for_position(lon=lon, lat=lat)
    return {
        "lat": lat,
        "lon": lon,
        "in_zone": len(matches) > 0,
        "zones": matches,
    }
