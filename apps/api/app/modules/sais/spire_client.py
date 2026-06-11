"""Spire Maritime S-AIS client (GAP-02).

Implements the SatelliteAISClient interface using Spire's Vessels API.
Requires SAIS_API_KEY and SAIS_PROVIDER=spire in environment.
"""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urlencode

from app.core.config import settings
from app.modules.sais.client import SatelliteAISClient, VesselSatellitePosition

_log = logging.getLogger("aegisais.sais.spire")

_SPIRE_BASE_URL = "https://api.spire.com/v2"


class SpireSatelliteAISClient(SatelliteAISClient):
    """Real Spire Maritime S-AIS REST client."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or settings.SAIS_API_KEY
        self._base_url = (base_url or settings.SAIS_API_BASE_URL or _SPIRE_BASE_URL).rstrip("/")

    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        if not self._api_key:
            _log.warning("Spire API key not configured")
            return []

        try:
            import httpx
        except ImportError:
            _log.error("httpx not installed — pip install httpx")
            return []

        params = {
            "mmsi": mmsi,
            "position_updated_after": time_range[0].isoformat(),
            "position_updated_before": time_range[1].isoformat(),
        }
        url = f"{self._base_url}/vessels?{urlencode(params)}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            _log.error("Spire API request failed: %s", exc)
            return []

        positions: list[VesselSatellitePosition] = []
        for vessel in data.get("data", []):
            last_pos = vessel.get("lastPositionUpdate", {})
            if not last_pos:
                continue
            positions.append(VesselSatellitePosition(
                mmsi=str(vessel.get("staticData", {}).get("mmsi", mmsi)),
                latitude=float(last_pos.get("latitude", 0)),
                longitude=float(last_pos.get("longitude", 0)),
                timestamp_utc=last_pos.get("timestamp", ""),
                sog_knots=last_pos.get("speed"),
                cog_degrees=last_pos.get("course"),
            ))

        _log.info("Spire returned %d positions for MMSI %s", len(positions), mmsi)
        return positions


def create_sais_client() -> SatelliteAISClient:
    """Factory: returns Spire client if configured, else stub."""
    from app.modules.sais.client import StubSatelliteAISClient

    provider = settings.SAIS_PROVIDER.lower()
    if provider == "spire" and settings.SAIS_API_KEY:
        return SpireSatelliteAISClient()
    return StubSatelliteAISClient()
