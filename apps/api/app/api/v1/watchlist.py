from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.middleware.rate_limit import api_read_rate_limit, api_write_rate_limit
from app.modules.auth.dependencies import require_analyst
from app.modules.vessels.schemas import WatchlistCreate, WatchlistEntryOut
from app.modules.vessels.watchlist_service import WatchlistServiceDep

router = APIRouter()


@router.get("/watchlist", response_model=list[WatchlistEntryOut])
def list_watchlist(
    _: Annotated[None, Depends(api_read_rate_limit)],
    svc: WatchlistServiceDep,
    user: Any = Depends(require_analyst),
):
    """List active watchlist entries (analyst or admin)."""
    return svc.list_active(user=user)


@router.post("/watchlist", response_model=WatchlistEntryOut)
def add_watchlist_entry(
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: WatchlistCreate,
    svc: WatchlistServiceDep,
    current_user: Any = Depends(require_analyst),
):
    """Add or update a watchlisted MMSI (analyst or admin)."""
    return svc.add_or_update(body, user=current_user)


@router.delete("/watchlist/{mmsi}", status_code=204)
def remove_watchlist_entry(
    _: Annotated[None, Depends(api_write_rate_limit)],
    mmsi: str,
    svc: WatchlistServiceDep,
    user: Any = Depends(require_analyst),
):
    """Remove an MMSI from the watchlist (soft-deactivate; analyst or admin)."""
    svc.deactivate(mmsi, user=user)
