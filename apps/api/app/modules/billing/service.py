"""Usage ledger service — record billable events and enforce entitlements (BL-010).

Design decisions
----------------
- ``record_usage`` is a lightweight fire-and-forget write; callers should not
  block on it for the hot path.  Use the async variant when available.
- ``check_entitlement`` returns the entitlement state without side-effects;
  enforcement is always the caller's responsibility.
- Limits are currently read from a hard-coded tier table.  The intent is to
  replace this with a database-backed entitlement configuration in a future
  sprint once commercial pricing is finalised.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.billing.models import BILLABLE_EVENTS, UsageLedgerEntry
from app.modules.billing.schemas import EntitlementLimit, UsageLedgerEntryOut, UsageSummary

_log = logging.getLogger("aegisais.billing")

# ---------------------------------------------------------------------------
# Hard-coded soft-cap tier — replace with DB config when pricing is finalised.
# ---------------------------------------------------------------------------

# Default monthly limits by event type (applied when no org-specific cap exists).
_DEFAULT_MONTHLY_LIMITS: dict[str, Decimal] = {
    "alert.processed": Decimal("10000"),
    "vessel.active": Decimal("500"),
    "export.csv": Decimal("100"),
    "export.pdf": Decimal("50"),
    "data_retention.day": Decimal("365"),
}


class UsageLedgerService:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def record_usage(
        self,
        *,
        organisation_id: int,
        event_type: str,
        quantity: Decimal = Decimal("1"),
        reference_id: Optional[int] = None,
        reference_key: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> UsageLedgerEntry:
        """Append one immutable usage record to the ledger.

        Raises ``ValueError`` if ``event_type`` is not in the canonical set.
        """
        if event_type not in BILLABLE_EVENTS:
            raise ValueError(
                f"Unknown billable event type '{event_type}'. "
                f"Valid types: {sorted(BILLABLE_EVENTS)}"
            )
        entry = UsageLedgerEntry(
            organisation_id=organisation_id,
            event_type=event_type,
            quantity=quantity,
            reference_id=reference_id,
            reference_key=reference_key,
            occurred_at=occurred_at or datetime.now(tz=timezone.utc),
        )
        self._db.add(entry)
        self._db.flush()
        _log.debug(
            "usage_recorded",
            extra={
                "org_id": organisation_id,
                "event_type": event_type,
                "quantity": str(quantity),
            },
        )
        return entry

    # ------------------------------------------------------------------
    # Query path
    # ------------------------------------------------------------------

    def get_usage_summary(
        self,
        *,
        organisation_id: int,
        event_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> UsageSummary:
        """Return aggregated usage for one event type over a calendar period."""
        result = self._db.execute(
            select(
                func.sum(UsageLedgerEntry.quantity).label("total"),
                func.count(UsageLedgerEntry.id).label("count"),
            ).where(
                UsageLedgerEntry.organisation_id == organisation_id,
                UsageLedgerEntry.event_type == event_type,
                UsageLedgerEntry.occurred_at >= period_start,
                UsageLedgerEntry.occurred_at <= period_end,
            )
        ).first()

        total_value, count_value = result if result is not None else (None, 0)
        total = Decimal(str(total_value or 0))
        count = int(count_value or 0)
        return UsageSummary(
            organisation_id=organisation_id,
            event_type=event_type,
            period_start=period_start,
            period_end=period_end,
            total_quantity=total,
            event_count=count,
        )

    def check_entitlement(
        self,
        *,
        organisation_id: int,
        event_type: str,
        period_start: datetime,
        period_end: datetime,
        limit_override: Optional[Decimal] = None,
    ) -> EntitlementLimit:
        """Return entitlement state without raising or blocking the caller.

        The caller is responsible for enforcement (e.g. HTTP 402 / 403).
        """
        limit = limit_override or _DEFAULT_MONTHLY_LIMITS.get(event_type, Decimal("0"))
        summary = self.get_usage_summary(
            organisation_id=organisation_id,
            event_type=event_type,
            period_start=period_start,
            period_end=period_end,
        )
        remaining = max(limit - summary.total_quantity, Decimal("0"))
        return EntitlementLimit(
            event_type=event_type,
            limit_per_month=limit,
            current_usage=summary.total_quantity,
            remaining=remaining,
            exceeded=summary.total_quantity >= limit,
        )

    def list_entries(
        self,
        *,
        organisation_id: int,
        event_type: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[UsageLedgerEntryOut]:
        """Return raw ledger entries for an org, optionally filtered."""
        q = self._db.query(UsageLedgerEntry).filter(
            UsageLedgerEntry.organisation_id == organisation_id
        )
        if event_type:
            q = q.filter(UsageLedgerEntry.event_type == event_type)
        if period_start:
            q = q.filter(UsageLedgerEntry.occurred_at >= period_start)
        if period_end:
            q = q.filter(UsageLedgerEntry.occurred_at <= period_end)
        rows = q.order_by(UsageLedgerEntry.occurred_at.desc()).offset(offset).limit(limit).all()
        return [UsageLedgerEntryOut.model_validate(r, from_attributes=True) for r in rows]
