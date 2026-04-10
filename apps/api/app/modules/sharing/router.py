"""Multi-national sharing endpoints (GAP-12)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.modules.auth.dependencies import require_analyst, require_viewer_or_above
from app.modules.auth.models import User
from app.modules.interop.classification import TLPMarking
from app.modules.sharing.service import (
    create_shared_alert,
    create_shared_watchlist_entry,
    generate_cop_feed,
)

_log = logging.getLogger("aegisais.sharing.api")

router = APIRouter()


class ShareAlertRequest(BaseModel):
    alert_type: str
    severity: int
    mmsi: str
    summary: str
    timestamp: Optional[str] = None
    target_org_ids: list[int]
    share_reason: str = ""
    tlp: str = "TLP:GREEN"


class SharedWatchlistRequest(BaseModel):
    mmsi: str
    target_org_ids: list[int]
    reason: str
    priority: str = "medium"
    tlp: str = "TLP:GREEN"


@router.post("/alerts")
async def share_alert(
    req: ShareAlertRequest,
    actor: User = Depends(require_analyst),
):
    """Share an alert with allied organisations."""
    tlp = TLPMarking(req.tlp) if req.tlp in [m.value for m in TLPMarking] else TLPMarking.GREEN
    return create_shared_alert(
        alert_data={
            "type": req.alert_type,
            "severity": req.severity,
            "mmsi": req.mmsi,
            "summary": req.summary,
            "timestamp": req.timestamp,
        },
        source_org_id=actor.organisation_id,
        target_org_ids=req.target_org_ids,
        tlp=tlp,
        share_reason=req.share_reason,
    )


@router.post("/watchlist")
async def share_watchlist_entry(
    req: SharedWatchlistRequest,
    actor: User = Depends(require_analyst),
):
    """Add a vessel to the shared allied watchlist."""
    tlp = TLPMarking(req.tlp) if req.tlp in [m.value for m in TLPMarking] else TLPMarking.GREEN
    return create_shared_watchlist_entry(
        mmsi=req.mmsi,
        source_org_id=actor.organisation_id,
        target_org_ids=req.target_org_ids,
        reason=req.reason,
        priority=req.priority,
        tlp=tlp,
    )


@router.get("/cop")
async def get_cop_feed(
    tlp: str = Query("TLP:GREEN"),
    _: User = Depends(require_viewer_or_above),
):
    """Get Common Operational Picture feed for shared tactical display."""
    tlp_enum = TLPMarking(tlp) if tlp in [m.value for m in TLPMarking] else TLPMarking.GREEN
    return generate_cop_feed(vessels=[], alerts=[], tlp=tlp_enum)
