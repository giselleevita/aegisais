"""BL-010: Usage ledger and entitlement tests.

Verifies:
  1. record_usage appends an immutable ledger entry.
  2. Unknown event type raises ValueError.
  3. get_usage_summary aggregates correctly over a period.
  4. check_entitlement returns correct exceeded flag.
  5. list_entries supports filtering by type and period.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.modules.billing.models import BILLABLE_EVENTS, UsageLedgerEntry
from app.modules.billing.service import UsageLedgerService
from tests.conftest import TestingSessionLocal


def _utc(year=2026, month=3, day=1, hour=0):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def test_record_usage_creates_entry(client):
    with TestingSessionLocal() as db:
        svc = UsageLedgerService(db)
        entry = svc.record_usage(
            organisation_id=1,
            event_type="alert.processed",
            reference_id=42,
        )
        db.commit()
        assert entry.id is not None
        assert entry.event_type == "alert.processed"
        assert entry.quantity == Decimal("1")
        assert entry.reference_id == 42


def test_record_usage_unknown_event_type_raises(client):
    with TestingSessionLocal() as db:
        svc = UsageLedgerService(db)
        with pytest.raises(ValueError, match="Unknown billable event type"):
            svc.record_usage(organisation_id=1, event_type="not.a.real.event")


def test_record_usage_all_canonical_types(client):
    """All BILLABLE_EVENTS must be accepted without error."""
    with TestingSessionLocal() as db:
        svc = UsageLedgerService(db)
        for event_type in BILLABLE_EVENTS:
            entry = svc.record_usage(organisation_id=1, event_type=event_type)
            assert entry.event_type == event_type
        db.commit()


def test_get_usage_summary_aggregates(client):
    with TestingSessionLocal() as db:
        svc = UsageLedgerService(db)
        ts = _utc()
        svc.record_usage(organisation_id=1, event_type="export.csv", quantity=Decimal("1"), occurred_at=ts)
        svc.record_usage(organisation_id=1, event_type="export.csv", quantity=Decimal("2"), occurred_at=ts)
        db.commit()

        summary = svc.get_usage_summary(
            organisation_id=1,
            event_type="export.csv",
            period_start=ts - timedelta(hours=1),
            period_end=ts + timedelta(hours=1),
        )
    assert summary.total_quantity == Decimal("3")
    assert summary.event_count == 2


def test_get_usage_summary_excludes_other_event_types(client):
    """Summary for one event_type must not count rows of other event_types."""
    with TestingSessionLocal() as db:
        svc = UsageLedgerService(db)
        ts = _utc(day=2)
        svc.record_usage(organisation_id=1, event_type="vessel.active", occurred_at=ts)
        svc.record_usage(organisation_id=1, event_type="alert.processed", occurred_at=ts)
        db.commit()

        summary = svc.get_usage_summary(
            organisation_id=1,
            event_type="vessel.active",
            period_start=ts - timedelta(hours=1),
            period_end=ts + timedelta(hours=1),
        )
    assert summary.event_count == 1


def test_check_entitlement_not_exceeded(client):
    with TestingSessionLocal() as db:
        svc = UsageLedgerService(db)
        ts = _utc(day=3)
        svc.record_usage(organisation_id=1, event_type="export.pdf", quantity=Decimal("5"), occurred_at=ts)
        db.commit()

        ent = svc.check_entitlement(
            organisation_id=1,
            event_type="export.pdf",
            period_start=ts - timedelta(hours=1),
            period_end=ts + timedelta(hours=1),
            limit_override=Decimal("50"),
        )
    assert ent.exceeded is False
    assert ent.remaining == Decimal("45")


def test_check_entitlement_exceeded(client):
    with TestingSessionLocal() as db:
        svc = UsageLedgerService(db)
        ts = _utc(day=4)
        svc.record_usage(organisation_id=1, event_type="export.pdf", quantity=Decimal("60"), occurred_at=ts)
        db.commit()

        ent = svc.check_entitlement(
            organisation_id=1,
            event_type="export.pdf",
            period_start=ts - timedelta(hours=1),
            period_end=ts + timedelta(hours=1),
            limit_override=Decimal("50"),
        )
    assert ent.exceeded is True
    assert ent.remaining == Decimal("0")


def test_list_entries_filters_by_event_type(client):
    with TestingSessionLocal() as db:
        svc = UsageLedgerService(db)
        ts = _utc(day=5)
        svc.record_usage(organisation_id=1, event_type="alert.processed", occurred_at=ts)
        svc.record_usage(organisation_id=1, event_type="export.csv", occurred_at=ts)
        db.commit()

        entries = svc.list_entries(organisation_id=1, event_type="alert.processed")
    assert all(e.event_type == "alert.processed" for e in entries)
