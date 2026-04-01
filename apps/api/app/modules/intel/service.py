"""Intelligence product generation (GAP-11).

Generates NATO-standard intelligence products:
- INTSUM (Intelligence Summary): Daily/weekly anomaly digest
- Vessel Dossier: Complete vessel profile with risk assessment
- Area Situation Report: Geographic threat summary

All products include TLP marking and STANAG 4774 classification.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.modules.interop.classification import (
    TLPMarking,
    classify_intelligence_product,
)
from app.services.llm import (
    generate_intsum_narrative as llm_intsum_narrative,
    generate_dossier_assessment as llm_dossier_assessment,
    is_llm_enabled,
)

_log = logging.getLogger("aegisais.intel")


async def generate_intsum(
    alerts: list[dict[str, Any]],
    period_start: datetime,
    period_end: datetime,
    area_name: str = "Baltic Sea",
    org_id: Optional[int] = None,
) -> dict[str, Any]:
    """Generate an Intelligence Summary (INTSUM).

    Summarises alert activity over a given period with threat breakdown,
    top vessels of interest, and trend analysis.
    """
    now = datetime.now(timezone.utc)

    # Categorize alerts by type
    type_counts: dict[str, int] = {}
    severity_sum: dict[str, int] = {}
    top_vessels: dict[str, int] = {}

    for alert in alerts:
        atype = alert.get("type", "UNKNOWN")
        type_counts[atype] = type_counts.get(atype, 0) + 1
        severity_sum[atype] = severity_sum.get(atype, 0) + alert.get("severity", 0)

        mmsi = alert.get("mmsi", "unknown")
        top_vessels[mmsi] = top_vessels.get(mmsi, 0) + 1

    # Sort vessels by alert count
    sorted_vessels = sorted(top_vessels.items(), key=lambda x: x[1], reverse=True)[:10]

    # Threat assessment
    total_alerts = len(alerts)
    critical_count = sum(1 for a in alerts if a.get("severity", 0) >= 80)
    high_count = sum(1 for a in alerts if 60 <= a.get("severity", 0) < 80)

    if critical_count > 5:
        threat_level = "HIGH"
    elif critical_count > 0 or high_count > 10:
        threat_level = "ELEVATED"
    else:
        threat_level = "NORMAL"

    intsum = {
        "product_type": "INTSUM",
        "serial": f"INTSUM-{now.strftime('%Y%m%d-%H%M')}",
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "area": area_name,
        "generated_at": now.isoformat(),
        "generated_by": "AEGISAIS",
        "threat_assessment": {
            "level": threat_level,
            "total_alerts": total_alerts,
            "critical_alerts": critical_count,
            "high_alerts": high_count,
        },
        "alert_breakdown": [
            {
                "type": atype,
                "count": count,
                "avg_severity": round(severity_sum[atype] / count, 1) if count > 0 else 0,
            }
            for atype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        ],
        "vessels_of_interest": [
            {"mmsi": mmsi, "alert_count": count}
            for mmsi, count in sorted_vessels
        ],
        "narrative": await _generate_intsum_narrative(
            total_alerts, critical_count, high_count, threat_level, area_name, type_counts,
            sorted_vessels, period_start.isoformat(), period_end.isoformat(),
        ),
    }

    return classify_intelligence_product(intsum, "INTSUM")


async def generate_vessel_dossier(
    mmsi: str,
    vessel_data: Optional[dict[str, Any]] = None,
    alerts: Optional[list[dict[str, Any]]] = None,
    track_summary: Optional[dict[str, Any]] = None,
    sanctions_result: Optional[dict[str, Any]] = None,
    dark_events: Optional[list[dict[str, Any]]] = None,
    ml_score: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Generate a complete vessel dossier (briefing aid).

    Combines all available intelligence on a single vessel.
    """
    now = datetime.now(timezone.utc)
    alerts = alerts or []
    dark_events = dark_events or []

    # Risk categorization
    max_severity = max((a.get("severity", 0) for a in alerts), default=0)
    alert_count = len(alerts)

    if sanctions_result:
        risk_level = "CRITICAL"
    elif max_severity >= 80 or alert_count > 20:
        risk_level = "HIGH"
    elif max_severity >= 50 or alert_count > 5:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    dossier = {
        "product_type": "VESSEL_DOSSIER",
        "serial": f"DOSSIER-{mmsi}-{now.strftime('%Y%m%d')}",
        "generated_at": now.isoformat(),
        "generated_by": "AEGISAIS",
        "vessel": {
            "mmsi": mmsi,
            **(vessel_data or {}),
        },
        "risk_assessment": {
            "level": risk_level,
            "max_alert_severity": max_severity,
            "total_alerts": alert_count,
            "sanctions_flagged": sanctions_result is not None,
            "dark_event_count": len(dark_events),
        },
        "alert_history": [
            {
                "type": a.get("type"),
                "severity": a.get("severity"),
                "timestamp": a.get("timestamp"),
                "summary": a.get("summary"),
            }
            for a in sorted(alerts, key=lambda x: x.get("severity", 0), reverse=True)[:20]
        ],
        "sanctions": sanctions_result,
        "dark_vessel_events": dark_events[:10],
        "ml_analysis": ml_score,
        "track_summary": track_summary,
        "analyst_assessment": await _generate_dossier_narrative(
            mmsi, risk_level, alert_count, max_severity,
            sanctions_result is not None, len(dark_events),
            list({a.get("type", "UNKNOWN") for a in alerts}),
            ml_score,
        ),
    }

    return classify_intelligence_product(dossier, "VESSEL_DOSSIER")


async def generate_area_sitrep(
    area_name: str,
    alerts: list[dict[str, Any]],
    vessel_count: int,
    period_hours: int = 24,
) -> dict[str, Any]:
    """Generate an Area Situation Report."""
    now = datetime.now(timezone.utc)

    critical_alerts = [a for a in alerts if a.get("severity", 0) >= 80]

    sitrep = {
        "product_type": "AREA_SITREP",
        "serial": f"SITREP-{area_name.replace(' ', '_').upper()}-{now.strftime('%Y%m%d-%H%M')}",
        "generated_at": now.isoformat(),
        "generated_by": "AEGISAIS",
        "area": area_name,
        "period_hours": period_hours,
        "summary": {
            "total_vessels_tracked": vessel_count,
            "total_alerts": len(alerts),
            "critical_alerts": len(critical_alerts),
        },
        "critical_events": [
            {
                "type": a.get("type"),
                "mmsi": a.get("mmsi"),
                "severity": a.get("severity"),
                "summary": a.get("summary"),
            }
            for a in critical_alerts[:10]
        ],
    }

    return classify_intelligence_product(sitrep, "AREA_SITREP")


async def _generate_intsum_narrative(
    total: int,
    critical: int,
    high: int,
    threat_level: str,
    area: str,
    type_counts: dict[str, int],
    top_vessels: list[tuple[str, int]] | None = None,
    period_start: str = "",
    period_end: str = "",
) -> str:
    """Generate human-readable INTSUM narrative, LLM-enhanced when available."""
    # Try LLM first
    if is_llm_enabled():
        vessels_data = [{"mmsi": v[0], "alert_count": v[1]} for v in (top_vessels or [])]
        llm_text = await llm_intsum_narrative(
            total, critical, high, threat_level, area,
            type_counts, vessels_data, period_start, period_end,
        )
        if llm_text:
            return llm_text

    # Fallback to template
    parts = [
        f"During the reporting period, {total} anomalous events were detected in the {area} area.",
        f"Threat assessment: {threat_level}.",
    ]
    if critical > 0:
        parts.append(f"{critical} critical-severity events require immediate analyst review.")
    if high > 0:
        parts.append(f"{high} high-severity events flagged for follow-up.")

    if type_counts:
        top_type = max(type_counts, key=type_counts.get)  # type: ignore[arg-type]
        parts.append(f"Most frequent anomaly type: {top_type} ({type_counts[top_type]} occurrences).")

    return " ".join(parts)


async def _generate_dossier_narrative(
    mmsi: str,
    risk_level: str,
    alert_count: int,
    max_severity: int,
    sanctions_flagged: bool,
    dark_event_count: int,
    alert_types: list[str],
    ml_score: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Generate LLM-powered dossier assessment, or None if unavailable."""
    if not is_llm_enabled():
        return None
    return await llm_dossier_assessment(
        mmsi, risk_level, alert_count, max_severity,
        sanctions_flagged, dark_event_count, alert_types, ml_score,
    )
