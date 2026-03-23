import csv
import io
import json
from datetime import datetime
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.rate_limit import api_read_rate_limit
from app.modules.auth.dependencies import require_admin
from app.modules.audit.mappers import audit_log_to_out
from app.modules.audit.schemas import AuditLogOut
from app.modules.audit.services import AuditService

router = APIRouter()


@router.get("/audit/logs/export/csv")
def export_audit_logs_csv(
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    admin: Any = Depends(require_admin),
    action: Optional[str] = Query(None, description="Filter by exact action string"),
    user_id: Optional[str] = Query(None, description="Filter by user_id (often username)"),
    resource_id: Optional[str] = Query(None, description="Filter by resource_id"),
    resource_type: Optional[str] = Query(None, description="Filter by resource_type"),
    start_time: Optional[datetime] = Query(
        None, description="Include rows with timestamp >= start (ISO)"
    ),
    end_time: Optional[datetime] = Query(
        None, description="Include rows with timestamp <= end (ISO)"
    ),
    max_rows: int = Query(
        10000,
        ge=1,
        le=100000,
        description="Maximum rows in export (newest first)",
    ),
):
    """
    Download audit log rows as CSV (admin only). Same filters as GET /v1/audit/logs.
    """
    rows = AuditService.list_logs_for_export(
        db,
        scope_user=admin,
        action=action,
        user_id=user_id,
        resource_id=resource_id,
        resource_type=resource_type,
        start_time=start_time,
        end_time=end_time,
        max_rows=max_rows,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID",
        "Timestamp",
        "User ID",
        "Action",
        "Resource ID",
        "Resource Type",
        "Change Summary",
        "Details JSON",
        "Correlation ID",
    ])
    for row in rows:
        writer.writerow([
            row.id,
            row.timestamp.isoformat() if row.timestamp else "",
            row.user_id or "",
            row.action,
            row.resource_id or "",
            row.resource_type or "",
            row.change_summary,
            json.dumps(row.details) if row.details is not None else "",
            row.correlation_id or "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs_export.csv"},
    )


@router.get("/audit/logs", response_model=list[AuditLogOut])
def list_audit_logs(
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    admin: Any = Depends(require_admin),
    action: Optional[str] = Query(None, description="Filter by exact action string"),
    user_id: Optional[str] = Query(None, description="Filter by user_id (often username)"),
    resource_id: Optional[str] = Query(None, description="Filter by resource_id"),
    resource_type: Optional[str] = Query(None, description="Filter by resource_type"),
    start_time: Optional[datetime] = Query(
        None, description="Include rows with timestamp >= start (ISO)"
    ),
    end_time: Optional[datetime] = Query(
        None, description="Include rows with timestamp <= end (ISO)"
    ),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    List audit log entries (admin only). Newest first.
    """
    rows = AuditService.list_logs(
        db,
        scope_user=admin,
        action=action,
        user_id=user_id,
        resource_id=resource_id,
        resource_type=resource_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    return [audit_log_to_out(r) for r in rows]
