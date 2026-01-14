from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import csv
import io
import json
from ..db import get_db
from ..models import Alert
from ..schemas import AlertOut, AlertStatusUpdate

router = APIRouter()

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    mmsi: Optional[str] = Query(None, description="Filter by MMSI"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type (e.g., TELEPORT, TURN_RATE)"),
    min_severity: int = Query(0, ge=0, le=100, description="Minimum severity (0-100)"),
    max_severity: int = Query(100, ge=0, le=100, description="Maximum severity (0-100)"),
    status: Optional[str] = Query(None, description="Filter by status (new, reviewed, resolved, false_positive)"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    List alerts with optional filtering by MMSI, type, severity, status, and time range.
    Results are ordered by timestamp descending (most recent first).
    """
    query = db.query(Alert)
    
    # Apply filters
    if mmsi:
        query = query.filter(Alert.mmsi == mmsi)
    if alert_type:
        query = query.filter(Alert.type == alert_type)
    if status:
        query = query.filter(Alert.status == status)
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

@router.patch("/alerts/{alert_id}/status")
def update_alert_status(
    alert_id: int,
    update: AlertStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update alert status and/or notes."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    valid_statuses = ["new", "reviewed", "resolved", "false_positive"]
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    alert.status = update.status
    if update.notes is not None:
        alert.notes = update.notes
    
    db.commit()
    db.refresh(alert)
    return AlertOut.model_validate(alert.__dict__)

@router.get("/alerts/export/csv")
def export_alerts_csv(
    mmsi: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_severity: int = Query(0),
    max_severity: int = Query(100),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Export alerts as CSV."""
    query = db.query(Alert)
    
    if mmsi:
        query = query.filter(Alert.mmsi == mmsi)
    if alert_type:
        query = query.filter(Alert.type == alert_type)
    if status:
        query = query.filter(Alert.status == status)
    if min_severity is not None:
        query = query.filter(Alert.severity >= min_severity)
    if max_severity is not None:
        query = query.filter(Alert.severity <= max_severity)
    if start_time:
        query = query.filter(Alert.timestamp >= start_time)
    if end_time:
        query = query.filter(Alert.timestamp <= end_time)
    
    alerts = query.order_by(Alert.timestamp.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Timestamp", "MMSI", "Type", "Severity", "Status", "Summary", "Notes", "Evidence"
    ])
    
    # Write data
    for alert in alerts:
        writer.writerow([
            alert.id,
            alert.timestamp.isoformat(),
            alert.mmsi,
            alert.type,
            alert.severity,
            alert.status,
            alert.summary,
            alert.notes or "",
            json.dumps(alert.evidence)
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alerts_export.csv"}
    )

@router.get("/alerts/export/json")
def export_alerts_json(
    mmsi: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_severity: int = Query(0),
    max_severity: int = Query(100),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Export alerts as JSON."""
    query = db.query(Alert)
    
    if mmsi:
        query = query.filter(Alert.mmsi == mmsi)
    if alert_type:
        query = query.filter(Alert.type == alert_type)
    if status:
        query = query.filter(Alert.status == status)
    if min_severity is not None:
        query = query.filter(Alert.severity >= min_severity)
    if max_severity is not None:
        query = query.filter(Alert.severity <= max_severity)
    if start_time:
        query = query.filter(Alert.timestamp >= start_time)
    if end_time:
        query = query.filter(Alert.timestamp <= end_time)
    
    alerts = query.order_by(Alert.timestamp.desc()).all()
    
    alerts_data = [AlertOut.model_validate(a.__dict__).model_dump() for a in alerts]
    
    return StreamingResponse(
        iter([json.dumps(alerts_data, indent=2, default=str)]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=alerts_export.json"}
    )

