"""Watchlist CRUD for analyst-prioritised MMSIs."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.api.validators import validate_mmsi
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.org_scope import apply_org_filter
from app.modules.vessels.models import WatchlistEntry
from app.modules.vessels.schemas import WatchlistCreate, WatchlistEntryOut


class WatchlistService:
    def __init__(self, db: Session):
        self._db = db

    def list_active(self, *, user: User) -> list[WatchlistEntryOut]:
        prio = case(
            (WatchlistEntry.priority == "high", 0),
            (WatchlistEntry.priority == "medium", 1),
            (WatchlistEntry.priority == "low", 2),
            else_=3,
        )
        q = self._db.query(WatchlistEntry).filter(WatchlistEntry.is_active.is_(True))
        q = apply_org_filter(q, WatchlistEntry, user)
        rows = q.order_by(prio, WatchlistEntry.created_at.desc()).all()
        return [WatchlistEntryOut.model_validate(r) for r in rows]

    def add_or_update(self, body: WatchlistCreate, *, user: User) -> WatchlistEntryOut:
        mmsi = validate_mmsi(body.mmsi.strip())
        existing = (
            self._db.query(WatchlistEntry)
            .filter(
                WatchlistEntry.mmsi == mmsi,
                WatchlistEntry.organisation_id == user.organisation_id,
            )
            .first()
        )
        if existing:
            existing.label = body.label
            existing.priority = body.priority
            existing.added_by_id = user.id
            existing.is_active = True
            self._db.commit()
            self._db.refresh(existing)
            return WatchlistEntryOut.model_validate(existing)

        row = WatchlistEntry(
            organisation_id=user.organisation_id,
            mmsi=mmsi,
            label=body.label,
            priority=body.priority,
            added_by_id=user.id,
            is_active=True,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return WatchlistEntryOut.model_validate(row)

    def deactivate(self, mmsi: str, *, user: User) -> None:
        mmsi = validate_mmsi(mmsi.strip())
        row = (
            self._db.query(WatchlistEntry)
            .filter(
                WatchlistEntry.mmsi == mmsi,
                WatchlistEntry.organisation_id == user.organisation_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Watchlist entry not found")
        row.is_active = False
        self._db.commit()


def get_watchlist_service(db: Session = Depends(get_db)) -> WatchlistService:
    return WatchlistService(db)


WatchlistServiceDep = Annotated[WatchlistService, Depends(get_watchlist_service)]
