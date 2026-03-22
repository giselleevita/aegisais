from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.rate_limit import reports_generate_rate_limit
from app.modules.auth.dependencies import require_admin
from app.modules.auth.models import User
from app.modules.reports.schemas import GenerateReportRequest
from app.modules.reports.service import build_alerts_pdf

router = APIRouter()


@router.post("/reports/generate")
def generate_alerts_report_pdf(
    _: Annotated[None, Depends(reports_generate_rate_limit)],
    body: GenerateReportRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Build a PDF summarizing alerts in the time range (admin only).
    Scoped to the current user's organisation (super_admin sees all organisations).
    """
    try:
        pdf = build_alerts_pdf(
            db,
            admin,
            start_time=body.start_time,
            end_time=body.end_time,
            mmsi=body.mmsi,
            zone_substring=body.zone_substring,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    data = pdf.getvalue()
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=aegisais_alerts_report.pdf",
        },
    )
