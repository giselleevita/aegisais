from typing import Annotated, Optional, Any

from fastapi import APIRouter, Depends, Query
from datetime import datetime
from app.middleware.rate_limit import api_read_rate_limit
from app.modules.auth.dependencies import require_viewer_or_above
from app.modules.vessels.schemas import VesselLatestOut
from app.modules.vessels.schemas import VesselPositionOut
from app.modules.vessels.service import VesselServiceDep

router = APIRouter()

@router.get("/vessels", response_model=list[VesselLatestOut])
def list_vessels(
    _: Annotated[None, Depends(api_read_rate_limit)],
    svc: VesselServiceDep,
    _viewer: Any = Depends(require_viewer_or_above),
    min_severity: int = Query(0, ge=0, le=100, description="Minimum alert severity"),
    limit: int = Query(500, ge=1, le=5000, description="Maximum number of results"),
):
    """List vessels with optional severity filtering. Ordered by most recent timestamp."""
    return svc.list_vessels(min_severity=min_severity, limit=limit)

@router.get("/vessels/{mmsi}/track", response_model=list[VesselPositionOut])
def get_vessel_track(
    mmsi: str,
    _: Annotated[None, Depends(api_read_rate_limit)],
    svc: VesselServiceDep,
    _viewer: Any = Depends(require_viewer_or_above),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (ISO format)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of positions"),
):
    """
    Get historical track positions for a vessel.

    Args:
        mmsi: Vessel MMSI (9 digits)
        start_time: Optional start timestamp filter
        end_time: Optional end timestamp filter
        limit: Maximum number of positions to return (1-10000)

    Returns:
        List of vessel positions

    Raises:
        HTTPException: If MMSI is invalid
    """
    return svc.get_track(
        mmsi, start_time=start_time, end_time=end_time, limit=limit
    )

@router.get("/vessels/{mmsi}", response_model=VesselLatestOut)
def get_vessel(
    mmsi: str,
    _: Annotated[None, Depends(api_read_rate_limit)],
    svc: VesselServiceDep,
    _viewer: Any = Depends(require_viewer_or_above),
):
    """
    Get a specific vessel by MMSI.

    Args:
        mmsi: Vessel MMSI (9 digits)

    Returns:
        Vessel information

    Raises:
        HTTPException: If MMSI is invalid or vessel not found
    """
    return svc.get_vessel(mmsi)
