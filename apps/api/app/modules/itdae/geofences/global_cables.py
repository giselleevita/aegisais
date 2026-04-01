"""Global submarine cable network database.

Extends the existing infrastructure_db.py with comprehensive submarine cable
corridors from publicly available data (TeleGeography / ICPC).

Each zone follows the same schema as baltic_cables.py for seamless integration.
"""

from __future__ import annotations

from typing import Any

# ──────────────────────────────────────────────────────────────────────
# North Sea & English Channel
# ──────────────────────────────────────────────────────────────────────
NORTH_SEA_CABLES: list[dict[str, Any]] = [
    {
        "id": "ns-1-eurogrid-corridor",
        "name": "EuroGrid Interconnector Corridor",
        "description": "NorNed, BritNed, COBRAcable — North Sea HVDC interconnectors",
        "risk_level": "high",
        "polygon": [
            [2.0, 51.5], [2.5, 52.0], [3.5, 52.5], [4.5, 53.0],
            [5.0, 55.0], [5.5, 57.0], [5.5, 56.7], [5.0, 54.7],
            [4.5, 52.7], [3.5, 52.2], [2.5, 51.7], [2.0, 51.2], [2.0, 51.5],
        ],
    },
    {
        "id": "ns-2-channel-islands",
        "name": "English Channel Cable Corridor",
        "description": "Cross-Channel power and telecom cables (IFA, ElecLink, FAB Link)",
        "risk_level": "critical",
        "polygon": [
            [-2.0, 49.5], [-1.5, 49.8], [0.0, 50.5], [1.5, 51.0],
            [1.8, 51.1], [1.8, 50.8], [1.5, 50.7], [0.0, 50.2],
            [-1.5, 49.5], [-2.0, 49.2], [-2.0, 49.5],
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────
# Pacific Cables
# ──────────────────────────────────────────────────────────────────────
PACIFIC_CABLES: list[dict[str, Any]] = [
    {
        "id": "pac-1-japan-us-corridor",
        "name": "Trans-Pacific Cable Corridor (Japan–US)",
        "description": "FASTER, UNITY, PC-1, Japan-US — major transpacific cables",
        "risk_level": "critical",
        "polygon": [
            [139.5, 34.5], [140.0, 35.0], [170.0, 40.0], [-170.0, 42.0],
            [-140.0, 40.0], [-124.0, 38.0], [-124.0, 37.7], [-140.0, 39.7],
            [-170.0, 41.7], [170.0, 39.7], [140.0, 34.7], [139.5, 34.2], [139.5, 34.5],
        ],
    },
    {
        "id": "pac-2-sea-asia-corridor",
        "name": "South-East Asia Cable Corridor",
        "description": "AAG, APG, SJC — SE Asia submarine cable network",
        "risk_level": "high",
        "polygon": [
            [103.5, 1.0], [104.0, 1.3], [106.0, 6.0], [108.0, 10.0],
            [114.0, 14.0], [117.0, 18.0], [120.0, 22.0],
            [120.3, 21.7], [117.3, 17.7], [114.3, 13.7], [108.3, 9.7],
            [106.3, 5.7], [104.3, 1.0], [103.8, 0.7], [103.5, 1.0],
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────
# Indian Ocean / Red Sea
# ──────────────────────────────────────────────────────────────────────
INDIAN_OCEAN_CABLES: list[dict[str, Any]] = [
    {
        "id": "io-1-red-sea-corridor",
        "name": "Red Sea Cable Corridor",
        "description": "AAE-1, FALCON, IMEWE, EIG — critical Red Sea transit",
        "risk_level": "critical",
        "polygon": [
            [32.5, 27.5], [33.0, 28.0], [36.0, 25.0], [40.0, 20.0],
            [43.0, 14.0], [43.5, 12.0], [43.5, 11.7], [43.0, 13.7],
            [40.0, 19.7], [36.0, 24.7], [33.0, 27.7], [32.5, 27.2], [32.5, 27.5],
        ],
    },
    {
        "id": "io-2-suez-med-transit",
        "name": "Suez-Mediterranean Cable Transit",
        "description": "Submarine cables transiting Suez Canal to Mediterranean",
        "risk_level": "critical",
        "polygon": [
            [32.2, 31.0], [32.5, 31.3], [32.8, 30.8], [33.0, 30.0],
            [33.2, 29.5], [33.2, 29.2], [33.0, 29.7], [32.8, 30.5],
            [32.5, 31.0], [32.2, 30.7], [32.2, 31.0],
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────
# Africa West Coast
# ──────────────────────────────────────────────────────────────────────
AFRICA_CABLES: list[dict[str, Any]] = [
    {
        "id": "af-1-wacs-corridor",
        "name": "WACS / SAT-3 Cable Corridor",
        "description": "West Africa Cable System — London to Cape Town",
        "risk_level": "high",
        "polygon": [
            [-5.5, 36.0], [-5.2, 36.3], [-9.0, 32.0], [-13.0, 25.0],
            [-17.0, 15.0], [-17.5, 5.0], [-12.0, -5.0], [5.0, -15.0],
            [12.0, -25.0], [18.0, -34.0], [18.3, -34.3],
            [18.3, -34.0], [12.3, -24.7], [5.3, -14.7], [-11.7, -4.7],
            [-17.2, 5.0], [-16.7, 15.0], [-12.7, 25.0], [-8.7, 32.0],
            [-5.2, 36.0], [-5.5, 35.7], [-5.5, 36.0],
        ],
    },
]


def get_global_cable_zones() -> list[dict[str, Any]]:
    """Return all global submarine cable protection zones.

    Does NOT include Baltic/Mediterranean/Atlantic/Arctic zones — those
    are already in infrastructure_db.py. This module provides the rest
    of the global network.
    """
    return (
        NORTH_SEA_CABLES
        + PACIFIC_CABLES
        + INDIAN_OCEAN_CABLES
        + AFRICA_CABLES
    )
