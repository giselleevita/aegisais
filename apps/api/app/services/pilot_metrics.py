"""Pilot KPI calculation helpers for funding evidence generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Iterable


@dataclass(frozen=True)
class PilotKpiSummary:
    detection_lead_time_seconds: float | None
    false_alert_rate: float | None
    analyst_time_saved_seconds: float | None

    def to_dict(self) -> dict[str, float | None]:
        return asdict(self)


def calculate_detection_lead_time_seconds(records: Iterable[dict[str, float]]) -> float | None:
    values = [record["alert_created_at"] - record["ingested_at"] for record in records if record.get("alert_created_at") is not None and record.get("ingested_at") is not None]
    return float(median(values)) if values else None


def calculate_false_alert_rate(records: Iterable[dict[str, bool]]) -> float | None:
    reviewed = [record for record in records if record.get("reviewed")]
    if not reviewed:
        return None
    false_alerts = sum(1 for record in reviewed if record.get("is_false_alert"))
    return false_alerts / len(reviewed)


def calculate_analyst_time_saved_seconds(records: Iterable[dict[str, float]]) -> float | None:
    deltas = [record["baseline_seconds"] - record["pilot_seconds"] for record in records if record.get("baseline_seconds") is not None and record.get("pilot_seconds") is not None]
    return float(median(deltas)) if deltas else None


def build_pilot_kpi_summary(
    *,
    detection_records: Iterable[dict[str, float]],
    review_records: Iterable[dict[str, bool]],
    workflow_records: Iterable[dict[str, float]],
) -> PilotKpiSummary:
    return PilotKpiSummary(
        detection_lead_time_seconds=calculate_detection_lead_time_seconds(detection_records),
        false_alert_rate=calculate_false_alert_rate(review_records),
        analyst_time_saved_seconds=calculate_analyst_time_saved_seconds(workflow_records),
    )