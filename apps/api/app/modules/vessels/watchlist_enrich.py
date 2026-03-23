"""Attach watchlist_priority to alert evidence when the MMSI is watchlisted."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.orm import Session

from app.modules.vessels.models import WatchlistEntry


def enrich_evidence_dict(db: Session, mmsi: str, evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        evidence = {}
    else:
        evidence = dict(evidence)
    entry = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.mmsi == mmsi, WatchlistEntry.is_active.is_(True))
        .first()
    )
    if entry:
        evidence["watchlist_priority"] = entry.priority
    return evidence


def priority_map_for_mmsis(db: Session, mmsis: set[str]) -> dict[str, str]:
    if not mmsis:
        return {}
    rows = (
        db.query(WatchlistEntry)
        .filter(
            WatchlistEntry.mmsi.in_(mmsis),
            WatchlistEntry.is_active.is_(True),
        )
        .all()
    )
    return {
        cast(str, r.mmsi): cast(str, r.priority)
        for r in rows
    }
