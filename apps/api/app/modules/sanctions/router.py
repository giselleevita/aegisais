"""Sanctions module API endpoints (GAP-09)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.modules.sanctions.service import (
    check_vessel_sanctions,
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


@router.get("/check/{mmsi}", response_model=SanctionsCheckResponse)
async def check_sanctions(
    mmsi: str,
    imo: Optional[str] = Query(None),
    vessel_name: Optional[str] = Query(None),
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


@router.post("/watchlist/reload", response_model=WatchlistLoadResponse)
async def reload_watchlist():
    """Reload sanctions watchlist from disk."""
    counts = load_watchlist()
    return WatchlistLoadResponse(
        mmsi_count=counts["mmsi"],
        imo_count=counts["imo"],
        name_count=counts["names"],
    )


@router.post("/watchlist/sync")
async def sync_from_official_sources():
    """Download and sync OFAC SDN + EU consolidated sanctions lists.

    Fetches real vessel sanctions data from treasury.gov and
    data.europa.eu, merges them, and updates the local watchlist.
    """
    counts = await update_watchlist_from_official_sources()
    return {
        "status": "synced",
        "source": "OFAC SDN + EU Consolidated",
        "mmsi_count": counts["mmsi"],
        "imo_count": counts["imo"],
        "name_count": counts["names"],
    }
