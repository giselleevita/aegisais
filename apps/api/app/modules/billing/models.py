"""Billing ORM models — append-only usage ledger (BL-010).

The ledger is intentionally append-only: rows are never updated or deleted.
Queries aggregate over the immutable log to derive period totals, making
the ledger suitable as an audit artifact and billing source of truth.

Billable event types
--------------------
- ``alert.processed``      — one row per alert persisted against an org.
- ``vessel.active``        — one row per unique (org, mmsi) tracked per day.
- ``export.csv``           — one row per CSV export triggered.
- ``export.pdf``           — one row per PDF report produced.
- ``data_retention.day``   — one row per org per day data is retained in hot storage.
"""
from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)

from app.core.database import Base

# ---------------------------------------------------------------------------
# Canonical billable event types
# ---------------------------------------------------------------------------

BILLABLE_EVENTS = frozenset(
    {
        "alert.processed",
        "vessel.active",
        "export.csv",
        "export.pdf",
        "data_retention.day",
    }
)


class UsageLedgerEntry(Base):
    """Immutable record of a billable event against an organisation.

    ``quantity`` is a decimal so that fractional units (e.g. 0.5 data-retention
    days, API call weights) can be recorded without schema changes.
    """

    __tablename__ = "usage_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)

    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ISO-8601 UTC timestamp of the billable event.
    occurred_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    # Canonical event type string, e.g. ``alert.processed``.
    event_type = Column(String(64), nullable=False, index=True)

    # Number of units consumed; defaults to 1.
    quantity = Column(Numeric(precision=18, scale=6), nullable=False, default=1)

    # Optional reference to the entity that caused the event (e.g. alert.id).
    reference_id = Column(Integer, nullable=True)

    # Optional extra detail (e.g. mmsi for vessel events, filename for exports).
    reference_key = Column(String(255), nullable=True)


# Composite indexes optimised for per-org period queries and deduplication.
Index(
    "ix_usage_ledger_org_type_occurred",
    UsageLedgerEntry.organisation_id,
    UsageLedgerEntry.event_type,
    UsageLedgerEntry.occurred_at,
)
