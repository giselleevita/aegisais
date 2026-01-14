from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from ..db import get_db
from ..models import VesselLatest, VesselPosition
from ..schemas import VesselLatestOut, VesselPositionOut
from ..api.validators import validate_mmsi

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
    """
    Get a specific vessel by MMSI.
    
    Args:
        mmsi: Vessel MMSI (9 digits)
        db: Database session
    
    Returns:
        Vessel information
    
    Raises:
        HTTPException: If MMSI is invalid or vessel not found
    """
    validate_mmsi(mmsi)
    vessel = db.query(VesselLatest).filter(VesselLatest.mmsi == mmsi).first()
    if vessel is None:
        raise HTTPException(status_code=404, detail=f"Vessel with MMSI {mmsi} not found")
    return VesselLatestOut.model_validate(vessel.__dict__)

@router.get("/vessels/{mmsi}/track", response_model=list[VesselPositionOut])
def get_vessel_track(
    mmsi: str,
    start_time: Optional[datetime] = Query(None, description="Start timestamp (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (ISO format)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of positions"),
    db: Session = Depends(get_db),
):
    """
    Get historical track positions for a vessel.
    
    Args:
        mmsi: Vessel MMSI (9 digits)
        start_time: Optional start timestamp filter
        end_time: Optional end timestamp filter
        limit: Maximum number of positions to return (1-10000)
        db: Database session
    
    Returns:
        List of vessel positions
    
    Raises:
        HTTPException: If MMSI is invalid
    """
    validate_mmsi(mmsi)
    query = db.query(VesselPosition).filter(VesselPosition.mmsi == mmsi)
    
    if start_time:
        query = query.filter(VesselPosition.timestamp >= start_time)
    if end_time:
        query = query.filter(VesselPosition.timestamp <= end_time)
    
    positions = query.order_by(VesselPosition.timestamp.asc()).limit(limit).all()
    
    return [VesselPositionOut.model_validate(p.__dict__) for p in positions]
