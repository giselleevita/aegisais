"""Sanctions module API endpoints (GAP-09)."""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.middleware.rate_limit import api_read_rate_limit, api_write_rate_limit
from app.modules.audit.services import AuditService
from app.modules.auth.dependencies import require_admin, require_analyst
from app.modules.auth.models import User
from app.modules.sanctions.service import (
    check_vessel_sanctions,
    correlate_dark_activity_with_sanctioned_port,
    detect_flag_hopping,
    get_watchlist_status,
    load_watchlist,
)
from app.modules.sanctions.official_lists import update_watchlist_from_official_sources

_log = logging.getLogger("aegisais.sanctions.api")

router = APIRouter()


class SanctionsCheckResponse(BaseModel):
    sanctioned: bool
    matches: list[dict] = []
    mmsi: str
    imo: Optional[str] = None
    vessel_name: Optional[str] = None


class WatchlistLoadResponse(BaseModel):
    mmsi_count: int
    imo_count: int
    name_count: int


class WatchlistStatusResponse(WatchlistLoadResponse):
    source: str
    updated_at: Optional[str] = None
    path: str
    exists: bool


class IdentitySnapshotRequest(BaseModel):
    mmsi: str
    timestamp: str
    imo: Optional[str] = None
    vessel_name: Optional[str] = None
    flag_state: Optional[str] = None


class FlagHoppingAnalysisRequest(BaseModel):
    snapshots: list[IdentitySnapshotRequest]


class DarkActivityPositionRequest(BaseModel):
    lat: float
    lon: float
    timestamp: Optional[str] = None


class SanctionedPortRequest(BaseModel):
    name: str
    lat: float
    lon: float
    country: Optional[str] = None
    sanctions_regime: Optional[str] = None


class DarkActivityAnalysisRequest(BaseModel):
    mmsi: str
    dark_duration_sec: int
    last_known_position: DarkActivityPositionRequest
    reappearance_position: DarkActivityPositionRequest
    sanctioned_ports: list[SanctionedPortRequest]


class EvasionAnalysisResponse(BaseModel):
    detected: bool
    alert: Optional[dict] = None


@router.get("/check/{mmsi}", response_model=SanctionsCheckResponse)
async def check_sanctions(
    _: Annotated[None, Depends(api_read_rate_limit)],
    mmsi: str,
    imo: Optional[str] = Query(None),
    vessel_name: Optional[str] = Query(None),
    _user: User = Depends(require_analyst),
):
    """Check a vessel against sanctions watchlists."""
    result = check_vessel_sanctions(mmsi, imo=imo, vessel_name=vessel_name)
    return SanctionsCheckResponse(
        sanctioned=result is not None,
        matches=result.get("evidence", {}).get("matches", []) if result else [],
        mmsi=mmsi,
        imo=imo,
        vessel_name=vessel_name,
    )


@router.get("/watchlist/status", response_model=WatchlistStatusResponse)
async def watchlist_status(
    _: Annotated[None, Depends(api_read_rate_limit)],
    _user: User = Depends(require_analyst),
):
    """Return current sanctions watchlist metadata and loaded counts."""
    status = get_watchlist_status()
    return WatchlistStatusResponse(**status)


@router.post("/watchlist/reload", response_model=WatchlistLoadResponse)
async def reload_watchlist(
    _: Annotated[None, Depends(api_write_rate_limit)],
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reload sanctions watchlist from disk."""
    counts = load_watchlist()
    if settings.enable_audit_logging:
        AuditService.log_event(
            db,
            action="sanctions.watchlist.reload",
            change_summary="Reloaded sanctions watchlist from configured path",
            organisation_id=int(admin.organisation_id),
            user_id=str(admin.username),
            resource_type="sanctions_watchlist",
            details=get_watchlist_status(),
        )
        db.commit()
    return WatchlistLoadResponse(
        mmsi_count=counts["mmsi"],
        imo_count=counts["imo"],
        name_count=counts["names"],
    )


@router.post("/watchlist/sync")
async def sync_from_official_sources(
    _: Annotated[None, Depends(api_write_rate_limit)],
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Download and sync OFAC, EU, and UN sanctions lists.

    Fetches real vessel sanctions data from treasury.gov and
    data.europa.eu, merges them with the UN consolidated list,
    and updates the local watchlist.
    """
    counts = await update_watchlist_from_official_sources()
    if settings.enable_audit_logging:
        AuditService.log_event(
            db,
            action="sanctions.watchlist.sync",
            change_summary="Synchronized sanctions watchlist from official sources",
            organisation_id=int(admin.organisation_id),
            user_id=str(admin.username),
            resource_type="sanctions_watchlist",
            details={
                **counts,
                **get_watchlist_status(),
            },
        )
        db.commit()
    return {
        "status": "synced",
        "source": "OFAC SDN + EU Consolidated + UN Consolidated",
        "mmsi_count": counts["mmsi"],
        "imo_count": counts["imo"],
        "name_count": counts["names"],
    }


@router.post("/analysis/flag-hopping", response_model=EvasionAnalysisResponse)
async def analyze_flag_hopping(
    payload: FlagHoppingAnalysisRequest,
    _: Annotated[None, Depends(api_read_rate_limit)],
    _user: User = Depends(require_analyst),
):
    """Analyze historical identity snapshots for flag-hopping behavior."""
    alert = detect_flag_hopping([snapshot.model_dump() for snapshot in payload.snapshots])
    return EvasionAnalysisResponse(detected=alert is not None, alert=alert)


@router.post("/analysis/dark-activity", response_model=EvasionAnalysisResponse)
async def analyze_dark_activity(
    payload: DarkActivityAnalysisRequest,
    _: Annotated[None, Depends(api_read_rate_limit)],
    _user: User = Depends(require_analyst),
):
    """Correlate dark AIS activity with sanctioned-port proximity."""
    alert = correlate_dark_activity_with_sanctioned_port(
        mmsi=payload.mmsi,
        dark_duration_sec=payload.dark_duration_sec,
        last_known_position=payload.last_known_position.model_dump(),
        reappearance_position=payload.reappearance_position.model_dump(),
        sanctioned_ports=[port.model_dump() for port in payload.sanctioned_ports],
    )
    return EvasionAnalysisResponse(detected=alert is not None, alert=alert)
