"""Expanded critical infrastructure database (GAP-08).

Pre-loaded infrastructure corridors beyond the original 4 Baltic cables.
Covers Mediterranean, Atlantic, Arctic, and Indo-Pacific routes.

Each zone follows the same schema as baltic_cables.py — seamless integration
with existing ITDAE geofence matching.
"""

from __future__ import annotations

from typing import Any

# ──────────────────────────────────────────────────────────────────────
# Mediterranean / Black Sea Infrastructure
# ──────────────────────────────────────────────────────────────────────
MEDITERRANEAN_ZONES: list[dict[str, Any]] = [
    {
        "id": "med-1-tanap-corridor",
        "name": "TANAP Pipeline Corridor",
        "description": "Trans-Anatolian gas pipeline crossing at Dardanelles",
        "risk_level": "critical",
        "polygon": [
            [26.3, 40.0], [26.6, 40.2], [26.9, 40.3], [27.2, 40.2],
            [27.2, 40.0], [26.9, 40.0], [26.6, 39.9], [26.3, 39.8], [26.3, 40.0],
        ],
    },
    {
        "id": "med-2-eastmed-corridor",
        "name": "EastMed Gas Pipeline Corridor",
        "description": "Planned Eastern Mediterranean gas pipeline (Israel-Cyprus-Greece)",
        "risk_level": "high",
        "polygon": [
            [34.0, 31.5], [33.5, 32.0], [33.0, 33.0], [32.0, 34.0],
            [30.0, 34.5], [26.0, 36.0], [26.0, 35.7], [30.0, 34.2],
            [32.0, 33.7], [33.0, 32.7], [33.5, 31.7], [34.0, 31.2], [34.0, 31.5],
        ],
    },
    {
        "id": "med-3-seamewe-corridor",
        "name": "SEA-ME-WE Submarine Cable Mediterranean Transit",
        "description": "SEA-ME-WE 3/4/5 submarine cable corridor, Mediterranean segment",
        "risk_level": "critical",
        "polygon": [
            [5.3, 43.2], [5.5, 43.3], [7.0, 42.5], [9.0, 41.0],
            [12.0, 38.5], [15.5, 36.5], [15.5, 36.2], [12.0, 38.2],
            [9.0, 40.7], [7.0, 42.2], [5.5, 43.0], [5.3, 42.9], [5.3, 43.2],
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────
# Atlantic Infrastructure
# ──────────────────────────────────────────────────────────────────────
ATLANTIC_ZONES: list[dict[str, Any]] = [
    {
        "id": "atl-1-tata-tgn-corridor",
        "name": "TGN-Atlantic Submarine Cable Corridor",
        "description": "Tata Global Network transatlantic cable (UK-US)",
        "risk_level": "critical",
        "polygon": [
            [-5.0, 50.3], [-5.3, 50.5], [-15.0, 50.0], [-30.0, 47.0],
            [-50.0, 42.0], [-70.0, 40.8], [-70.0, 40.5], [-50.0, 41.7],
            [-30.0, 46.7], [-15.0, 49.7], [-5.3, 50.2], [-5.0, 50.0], [-5.0, 50.3],
        ],
    },
    {
        "id": "atl-2-marea-corridor",
        "name": "MAREA Submarine Cable Corridor",
        "description": "Microsoft/Facebook MAREA cable (Virginia Beach-Bilbao)",
        "risk_level": "critical",
        "polygon": [
            [-75.9, 36.8], [-76.1, 37.0], [-50.0, 42.0], [-30.0, 43.5],
            [-3.0, 43.4], [-3.0, 43.1], [-30.0, 43.2], [-50.0, 41.7],
            [-76.1, 36.7], [-75.9, 36.5], [-75.9, 36.8],
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────
# Arctic / GIUK Gap Infrastructure
# ──────────────────────────────────────────────────────────────────────
ARCTIC_ZONES: list[dict[str, Any]] = [
    {
        "id": "arctic-1-giuk-gap",
        "name": "GIUK Gap Transit Zone",
        "description": "Greenland-Iceland-UK gap — strategic maritime chokepoint",
        "risk_level": "critical",
        "polygon": [
            [-44.0, 60.0], [-30.0, 64.0], [-20.0, 65.0], [-13.0, 63.5],
            [-6.0, 60.0], [-6.0, 59.5], [-13.0, 63.0], [-20.0, 64.5],
            [-30.0, 63.5], [-44.0, 59.5], [-44.0, 60.0],
        ],
    },
    {
        "id": "arctic-2-north-connect-corridor",
        "name": "North Sea Link / NorthConnect Corridor",
        "description": "HVDC interconnectors between Norway and UK/Scotland",
        "risk_level": "high",
        "polygon": [
            [1.5, 56.5], [1.8, 56.7], [3.0, 57.0], [4.5, 58.0],
            [5.3, 60.0], [5.3, 59.7], [4.5, 57.7], [3.0, 56.7],
            [1.8, 56.4], [1.5, 56.2], [1.5, 56.5],
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────
# Consolidated database
# ──────────────────────────────────────────────────────────────────────

def get_all_infrastructure_zones() -> list[dict[str, Any]]:
    """Return all pre-loaded infrastructure protection zones.

    This combines the original Baltic corridors with Mediterranean,
    Atlantic, Arctic/GIUK, and global submarine cable zones.
    """
    from app.modules.itdae.geofences.baltic_cables import BALTIC_CABLE_ZONES
    from app.modules.itdae.geofences.global_cables import get_global_cable_zones

    return (
        BALTIC_CABLE_ZONES
        + MEDITERRANEAN_ZONES
        + ATLANTIC_ZONES
        + ARCTIC_ZONES
        + get_global_cable_zones()
    )


def get_zones_by_risk_level(level: str) -> list[dict[str, Any]]:
    """Filter infrastructure zones by risk level."""
    return [z for z in get_all_infrastructure_zones() if z["risk_level"] == level]


def get_zone_ids() -> list[str]:
    """Return list of all zone IDs for quick lookup."""
    return [z["id"] for z in get_all_infrastructure_zones()]
