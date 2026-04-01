"""Multi-national collaboration and alert sharing (GAP-12).

Provides:
- Cross-org alert sharing with TLP marking
- Shared watchlists between allied organisations
- Federated data exchange metadata

All sharing is explicit opt-in with TLP markings controlling
information dissemination boundaries.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.modules.interop.classification import TLPMarking, apply_classification

_log = logging.getLogger("aegisais.sharing")


def create_shared_alert(
    alert_data: dict[str, Any],
    source_org_id: int,
    target_org_ids: list[int],
    tlp: TLPMarking = TLPMarking.GREEN,
    share_reason: str = "",
) -> dict[str, Any]:
    """Create a shareable alert record for cross-org dissemination.

    Wraps the alert with sharing metadata and TLP marking.
    """
    shared = {
        "shared_alert": {
            "type": alert_data.get("type"),
            "severity": alert_data.get("severity"),
            "mmsi": alert_data.get("mmsi"),
            "summary": alert_data.get("summary"),
            "timestamp": alert_data.get("timestamp"),
            # Evidence is EXCLUDED by default for shared alerts (need-to-know)
            # Include only summary-level data
        },
        "sharing_metadata": {
            "source_org_id": source_org_id,
            "target_org_ids": target_org_ids,
            "shared_at": datetime.now(timezone.utc).isoformat(),
            "share_reason": share_reason,
            "tlp": tlp.value,
        },
    }
    return apply_classification(shared, tlp=tlp)


def create_shared_watchlist_entry(
    mmsi: str,
    source_org_id: int,
    target_org_ids: list[int],
    reason: str,
    priority: str = "medium",
    tlp: TLPMarking = TLPMarking.GREEN,
) -> dict[str, Any]:
    """Create a shared watchlist entry visible to allied organisations."""
    return {
        "mmsi": mmsi,
        "source_org_id": source_org_id,
        "target_org_ids": target_org_ids,
        "reason": reason,
        "priority": priority,
        "shared_at": datetime.now(timezone.utc).isoformat(),
        "tlp": tlp.value,
    }


def generate_cop_feed(
    vessels: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    tlp: TLPMarking = TLPMarking.GREEN,
) -> dict[str, Any]:
    """Generate a Common Operational Picture (COP) feed snapshot.

    Suitable for display on shared tactical displays.
    Contains only data cleared at the specified TLP level.
    """
    now = datetime.now(timezone.utc)

    # Filter based on TLP — for AMBER+STRICT and RED, omit specific evidence
    include_evidence = tlp in (TLPMarking.WHITE, TLPMarking.GREEN)

    cop = {
        "feed_type": "COP",
        "generated_at": now.isoformat(),
        "generated_by": "AEGISAIS",
        "vessels": [
            {
                "mmsi": v.get("mmsi"),
                "lat": v.get("lat"),
                "lon": v.get("lon"),
                "sog": v.get("sog"),
                "cog": v.get("cog"),
                "last_seen": v.get("timestamp"),
            }
            for v in vessels
        ],
        "alerts": [
            {
                "type": a.get("type"),
                "severity": a.get("severity"),
                "mmsi": a.get("mmsi"),
                "summary": a.get("summary") if include_evidence else "[REDACTED]",
                "timestamp": a.get("timestamp"),
            }
            for a in alerts
            if a.get("severity", 0) >= 50  # Only share significant alerts
        ],
        "stats": {
            "total_vessels": len(vessels),
            "total_alerts": len(alerts),
            "critical_alerts": sum(1 for a in alerts if a.get("severity", 0) >= 80),
        },
    }

    return apply_classification(cop, tlp=tlp)
