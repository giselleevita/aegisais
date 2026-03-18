from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import json

from app.core.database import get_db
from app.modules.itdae.models import ItdaePosition
from app.modules.itdae.schemas import ItdaePositionSchema
from app.modules.itdae.ingestion.stream import stream_manager
from app.modules.itdae.geofences.baltic_cables import BALTIC_CABLE_ZONES
from app.modules.itdae.geofences.checker import get_zone_for_position, get_all_zones_for_position

from app.modules.auth.dependencies import require_admin, get_current_user

router = APIRouter()

@router.get("/health")
def itdae_health(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    """Health endpoint for ITDAE module"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count = db.query(ItdaePosition).filter(ItdaePosition.timestamp >= today_start).count()
    return {
        "user": current_user.username,
        "positions_today": count,
        "stream_status": "running" if stream_manager.is_running else "stopped"
    }

@router.get("/dump-track/{mmsi}")
def dump_track(
    mmsi: str,
    hours: int = Query(6, description="Hours of history to dump"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    """Dump track history as JSON"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    positions = db.query(ItdaePosition).filter(
        ItdaePosition.mmsi == mmsi,
        ItdaePosition.timestamp >= cutoff
    ).order_by(ItdaePosition.timestamp.desc()).all()
    return {
        "mmsi": mmsi,
        "hours": hours,
        "count": len(positions),
        "track": [ItdaePositionSchema.model_validate(p.__dict__).model_dump() for p in positions]
    }

@router.post("/stream/start")
async def start_stream(admin: Any = Depends(require_admin)):
    await stream_manager.start()
    return {"status": "ok", "message": "Stream starting", "by": admin.username}

@router.post("/stream/stop")
async def stop_stream(admin: Any = Depends(require_admin)):
    await stream_manager.stop()
    return {"status": "ok", "message": "Stream stopping", "by": admin.username}

# ─── Geofence endpoints ────────────────────────────────────────────────────

@router.get("/geofences/baltic")
def list_baltic_geofences(current_user: Any = Depends(get_current_user)):
    """
    Return all defined Baltic Sea cable corridor geofence zones with polygons.
    """
    return {
        "count": len(BALTIC_CABLE_ZONES),
        "zones": [
            {
                "id": z["id"],
                "name": z["name"],
                "description": z["description"],
                "risk_level": z["risk_level"],
                "polygon": z["polygon"],
            }
            for z in BALTIC_CABLE_ZONES
        ]
    }

@router.get("/geofences/check")
def check_geofence(
    lat: float = Query(..., description="Latitude of position to check"),
    lon: float = Query(..., description="Longitude of position to check"),
    current_user: Any = Depends(get_current_user)
):
    """
    Check if a lat/lon position falls within any Baltic cable geofence zone.
    Returns all matching zones (may be more than one if zones overlap).
    """
    matches = get_all_zones_for_position(lon=lon, lat=lat)
    return {
        "lat": lat,
        "lon": lon,
        "in_zone": len(matches) > 0,
        "zones": matches
    }
