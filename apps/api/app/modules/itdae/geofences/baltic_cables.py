"""
Baltic Sea critical infrastructure cable corridors.

Each zone is a dict with:
  - id: unique identifier
  - name: human-readable name
  - description: what the cable/corridor is
  - polygon: list of [lon, lat] coordinate pairs forming a closed ring
  - risk_level: 'critical' | 'high' | 'medium'

These are approximate 5 nm buffer corridors around known Baltic subsea cable routes.
"""

BALTIC_CABLE_ZONES = [
    {
        "id": "baltic-1-nordstream-corridor",
        "name": "Nord Stream Pipeline Corridor",
        "description": "Nord Stream 1 & 2 pipeline routes across Baltic Sea",
        "risk_level": "critical",
        "polygon": [
            [10.9, 54.6],
            [11.2, 54.8],
            [13.5, 55.1],
            [16.0, 56.0],
            [18.0, 56.8],
            [20.0, 57.5],
            [22.0, 57.8],
            [23.5, 57.9],
            [23.5, 57.6],
            [22.0, 57.5],
            [20.0, 57.2],
            [18.0, 56.5],
            [16.0, 55.7],
            [13.5, 54.8],
            [11.2, 54.5],
            [10.9, 54.3],
            [10.9, 54.6],
        ]
    },
    {
        "id": "baltic-2-estlink-corridor",
        "name": "EstLink Power Cable Corridor",
        "description": "EstLink 1 & 2 submarine power cables between Finland and Estonia",
        "risk_level": "critical",
        "polygon": [
            [24.3, 59.5],
            [24.6, 59.6],
            [25.2, 59.7],
            [25.5, 59.8],
            [25.5, 59.6],
            [25.2, 59.5],
            [24.6, 59.4],
            [24.3, 59.3],
            [24.3, 59.5],
        ]
    },
    {
        "id": "baltic-3-nordbalt-corridor",
        "name": "NordBalt Interconnector Corridor",
        "description": "NordBalt HVDC cable between Sweden and Lithuania",
        "risk_level": "high",
        "polygon": [
            [17.5, 56.5],
            [17.8, 56.7],
            [18.5, 57.0],
            [19.5, 57.2],
            [20.5, 57.0],
            [21.0, 56.5],
            [21.0, 56.2],
            [20.5, 56.7],
            [19.5, 56.9],
            [18.5, 56.7],
            [17.8, 56.4],
            [17.5, 56.2],
            [17.5, 56.5],
        ]
    },
    {
        "id": "baltic-4-finestlink-corridor",
        "name": "FinEst Link Planned Corridor",
        "description": "Planned Helsinki-Tallinn tunnel and cable corridor",
        "risk_level": "medium",
        "polygon": [
            [24.7, 59.5],
            [25.0, 59.6],
            [25.4, 59.65],
            [25.4, 59.45],
            [25.0, 59.4],
            [24.7, 59.3],
            [24.7, 59.5],
        ]
    },
]
