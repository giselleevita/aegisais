from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import VesselLatest
from ..schemas import VesselLatestOut

router = APIRouter()

@router.get("/vessels", response_model=list[VesselLatestOut])
def list_vessels(
    min_severity: int = Query(0, ge=0, le=100, description="Minimum alert severity"),
    limit: int = Query(500, ge=1, le=5000, description="Maximum number of results"),
    db: Session = Depends(get_db),
):
    """List vessels with optional severity filtering. Ordered by most recent timestamp."""
    q = (
        db.query(VesselLatest)
        .filter(VesselLatest.last_alert_severity >= min_severity)
        .order_by(VesselLatest.timestamp.desc())
        .limit(limit)
    )
    return [VesselLatestOut.model_validate(v.__dict__) for v in q.all()]

@router.get("/vessels/{mmsi}", response_model=VesselLatestOut)
def get_vessel(
    mmsi: str,
    db: Session = Depends(get_db),
):
    """Get a specific vessel by MMSI."""
    vessel = db.query(VesselLatest).filter(VesselLatest.mmsi == mmsi).first()
    if vessel is None:
        raise HTTPException(status_code=404, detail=f"Vessel with MMSI {mmsi} not found")
    return VesselLatestOut.model_validate(vessel.__dict__)
