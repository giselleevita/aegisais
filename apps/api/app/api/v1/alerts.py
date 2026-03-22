from typing import Annotated, Optional, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from datetime import datetime
import csv
import io
import json
from app.middleware.rate_limit import api_read_rate_limit, api_write_rate_limit
from app.modules.auth.dependencies import get_org_scope, require_admin, require_analyst
from app.modules.alerts.schemas import AlertOut
from app.modules.alerts.schemas import AlertStatusUpdate
from app.modules.alerts.mappers import alert_to_out
from app.modules.alerts.service import AlertServiceDep

router = APIRouter()

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    _: Annotated[None, Depends(api_read_rate_limit)],
    svc: AlertServiceDep,
    user: Any = Depends(get_org_scope),
    mmsi: Optional[str] = Query(None, description="Filter by MMSI"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type (e.g., TELEPORT, TURN_RATE)"),
    min_severity: int = Query(0, ge=0, le=100, description="Minimum severity (0-100)"),
    max_severity: int = Query(100, ge=0, le=100, description="Maximum severity (0-100)"),
    status: Optional[str] = Query(None, description="Filter by status (new, reviewed, resolved, false_positive)"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List alerts with optional filtering by MMSI, type, severity, status, and time range.
    Watchlisted MMSIs are ordered first (priority high → low), then by time descending.
    """
    return svc.list_alerts(
        user=user,
        mmsi=mmsi,
        alert_type=alert_type,
        min_severity=min_severity,
        max_severity=max_severity,
        status=status,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

@router.get("/alerts/stats/summary")
def get_alert_stats(
    _: Annotated[None, Depends(api_read_rate_limit)],
    svc: AlertServiceDep,
    user: Any = Depends(get_org_scope),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (ISO format)"),
):
    """Get summary statistics about alerts."""
    return svc.get_stats_summary(user=user, start_time=start_time, end_time=end_time)

@router.get("/alerts/export/csv")
def export_alerts_csv(
    _: Annotated[None, Depends(api_read_rate_limit)],
    svc: AlertServiceDep,
    admin: Any = Depends(require_admin),
    mmsi: Optional[str] = Query(None, description="Filter by MMSI"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    min_severity: int = Query(0, ge=0, le=100, description="Minimum severity"),
    max_severity: int = Query(100, ge=0, le=100, description="Maximum severity"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp filter"),
    end_time: Optional[datetime] = Query(None, description="End timestamp filter"),
):
    """
    Export alerts as CSV file.

    Supports all the same filters as GET /v1/alerts.
    Returns a CSV file download.
    """
    alerts = svc.list_alerts_matching(
        user=admin,
        mmsi=mmsi,
        alert_type=alert_type,
        status=status,
        min_severity=min_severity,
        max_severity=max_severity,
        start_time=start_time,
        end_time=end_time,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Timestamp", "MMSI", "Type", "Severity", "Status", "Summary", "Notes", "Evidence"
    ])

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
    _: Annotated[None, Depends(api_read_rate_limit)],
    svc: AlertServiceDep,
    admin: Any = Depends(require_admin),
    mmsi: Optional[str] = Query(None, description="Filter by MMSI"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    min_severity: int = Query(0, ge=0, le=100, description="Minimum severity"),
    max_severity: int = Query(100, ge=0, le=100, description="Maximum severity"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp filter"),
    end_time: Optional[datetime] = Query(None, description="End timestamp filter"),
):
    """
    Export alerts as JSON file.

    Supports all the same filters as GET /v1/alerts.
    Returns a JSON file download.
    """
    alerts = svc.list_alerts_matching(
        user=admin,
        mmsi=mmsi,
        alert_type=alert_type,
        status=status,
        min_severity=min_severity,
        max_severity=max_severity,
        start_time=start_time,
        end_time=end_time,
    )

    alerts_data = [alert_to_out(a).model_dump() for a in alerts]

    return StreamingResponse(
        iter([json.dumps(alerts_data, indent=2, default=str)]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=alerts_export.json"}
    )

@router.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert(
    alert_id: int,
    _: Annotated[None, Depends(api_read_rate_limit)],
    svc: AlertServiceDep,
    user: Any = Depends(get_org_scope),
):
    """Get a specific alert by ID."""
    return svc.get_alert(alert_id, user=user)

@router.patch("/alerts/{alert_id}/status")
def update_alert_status(
    alert_id: int,
    _: Annotated[None, Depends(api_write_rate_limit)],
    update: AlertStatusUpdate,
    svc: AlertServiceDep,
    actor: Any = Depends(require_analyst),
):
    """
    Update alert status and/or notes.

    Args:
        alert_id: Alert ID to update
        update: Status update request with status and optional notes

    Returns:
        Updated alert
    """
    return svc.update_status(
        alert_id,
        update,
        user=actor,
        actor_username=actor.username,
    )
