"""Pydantic schemas for the billing / entitlement module (BL-010)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class UsageLedgerEntryOut(BaseModel):
    id: int
    organisation_id: int
    occurred_at: datetime
    event_type: str
    quantity: Decimal
    reference_id: Optional[int] = None
    reference_key: Optional[str] = None

    model_config = {"from_attributes": True}


class UsageSummary(BaseModel):
    """Aggregated usage for one event type over a period."""

    organisation_id: int
    event_type: str
    period_start: datetime
    period_end: datetime
    total_quantity: Decimal = Field(description="Sum of all quantity values in the period.")
    event_count: int = Field(description="Number of individual ledger entries.")


class EntitlementLimit(BaseModel):
    """Per-event-type soft cap for an organisation."""

    event_type: str
    limit_per_month: Decimal
    current_usage: Decimal
    remaining: Decimal
    exceeded: bool
