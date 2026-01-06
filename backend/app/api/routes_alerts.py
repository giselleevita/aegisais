from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from ..db import get_db
from ..models import Alert
from ..schemas import AlertOut

router = APIRouter()

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    mmsi: Optional[str] = Query(None, description="Filter by MMSI"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type (e.g., TELEPORT, TURN_RATE)"),
    min_severity: int = Query(0, ge=0, le=100, description="Minimum severity (0-100)"),
    max_severity: int = Query(100, ge=0, le=100, description="Maximum severity (0-100)"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    List alerts with optional filtering by MMSI, type, severity, and time range.
    Results are ordered by timestamp descending (most recent first).
    """
    query = db.query(Alert)
    
    # Apply filters
    if mmsi:
        query = query.filter(Alert.mmsi == mmsi)
    if alert_type:
        query = query.filter(Alert.type == alert_type)
    if min_severity is not None:
        query = query.filter(Alert.severity >= min_severity)
    if max_severity is not None:
        query = query.filter(Alert.severity <= max_severity)
    if start_time:
        query = query.filter(Alert.timestamp >= start_time)
    if end_time:
        query = query.filter(Alert.timestamp <= end_time)
    
    # Order and paginate
    query = query.order_by(Alert.timestamp.desc())
    total = query.count()
    results = query.offset(offset).limit(limit).all()
    
    return [AlertOut.model_validate(a.__dict__) for a in results]

@router.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific alert by ID."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut.model_validate(alert.__dict__)

@router.get("/alerts/stats/summary")
def get_alert_stats(
    start_time: Optional[datetime] = Query(None, description="Start timestamp (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (ISO format)"),
    db: Session = Depends(get_db),
):
    """Get summary statistics about alerts."""
    query = db.query(Alert)
    
    if start_time:
        query = query.filter(Alert.timestamp >= start_time)
    if end_time:
        query = query.filter(Alert.timestamp <= end_time)
    
    total = query.count()
    
    # Count by type
    from sqlalchemy import func
    type_counts = (
        query.with_entities(Alert.type, func.count(Alert.id).label("count"))
        .group_by(Alert.type)
        .all()
    )
    
    # Average severity
    avg_severity = query.with_entities(func.avg(Alert.severity)).scalar() or 0.0
    
    # Count by severity ranges
    high_severity = query.filter(Alert.severity >= 70).count()
    medium_severity = query.filter(Alert.severity >= 30, Alert.severity < 70).count()
    low_severity = query.filter(Alert.severity < 30).count()
    
    return {
        "total": total,
        "by_type": {t: c for t, c in type_counts},
        "average_severity": round(float(avg_severity), 2),
        "by_severity_range": {
            "high": high_severity,
            "medium": medium_severity,
            "low": low_severity,
        },
    }

