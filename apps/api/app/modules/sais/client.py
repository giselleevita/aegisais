"""Satellite AIS client abstraction and stub implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypedDict
import os

_log = logging.getLogger("aegisais.sais.client")


class VesselSatellitePosition(TypedDict, total=False):
    """One satellite-reported vessel position sample (provider-agnostic shape)."""

    mmsi: str
    latitude: float
    longitude: float
    timestamp_utc: str
    sog_knots: float | None
    cog_degrees: float | None


class SatelliteAISClient(ABC):
    """Abstract client for commercial S-AIS REST/streaming providers."""

    @abstractmethod
    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        """Return vessel positions for ``mmsi`` within ``time_range`` (inclusive semantics TBD per provider)."""
        ...


class StubSatelliteAISClient(SatelliteAISClient):
    """No HTTP; returns an empty list until real provider keys are configured."""

    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        _log.info(
            "StubSatelliteAISClient: no outbound S-AIS request (provider not configured or stub mode); mmsi=%s range=%s to %s",
            mmsi,
            time_range[0].isoformat(),
            time_range[1].isoformat(),
        )
        return []


class SpireMaritimeAISClient(SatelliteAISClient):
    """Spire Maritime REST API adapter.

    Env vars:
        SPIRE_API_KEY   — Spire API token (required)
        SPIRE_BASE_URL  — override base URL (default: https://api.spire.com)
    """

    _DEFAULT_BASE = "https://api.spire.com"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self._api_key = api_key or os.getenv("SPIRE_API_KEY", "")
        self._base_url = (base_url or os.getenv("SPIRE_BASE_URL", self._DEFAULT_BASE)).rstrip("/")
        if not self._api_key:
            raise EnvironmentError("SPIRE_API_KEY is not set")

    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        import urllib.request
        import json

        start = time_range[0].strftime("%Y-%m-%dT%H:%M:%SZ")
        end = time_range[1].strftime("%Y-%m-%dT%H:%M:%SZ")
        url = (
            f"{self._base_url}/v2/messages?mmsi={mmsi}"
            f"&time_start={start}&time_end={end}&msg_type=1,2,3,18"
        )
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                data = json.loads(resp.read())
        except Exception as exc:
            _log.error("SpireMaritimeAISClient request failed: %s", exc)
            return []

        results: list[VesselSatellitePosition] = []
        for msg in data.get("data", []):
            try:
                results.append(
                    VesselSatellitePosition(
                        mmsi=str(msg.get("mmsi", mmsi)),
                        latitude=float(msg["latitude"]),
                        longitude=float(msg["longitude"]),
                        timestamp_utc=msg.get("timestamp", ""),
                        sog_knots=float(msg["sog"]) if msg.get("sog") is not None else None,
                        cog_degrees=float(msg["cog"]) if msg.get("cog") is not None else None,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        _log.info("SpireMaritimeAISClient: mmsi=%s returned %d positions", mmsi, len(results))
        return results


class MarineTrafficAISClient(SatelliteAISClient):
    """MarineTraffic Expected Arrivals / Vessel Track API adapter.

    Env vars:
        MARINETRAFFIC_API_KEY  — API key (required)
        MARINETRAFFIC_BASE_URL — override base URL (default: https://services.marinetraffic.com/api)
    """

    _DEFAULT_BASE = "https://services.marinetraffic.com/api"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self._api_key = api_key or os.getenv("MARINETRAFFIC_API_KEY", "")
        self._base_url = (base_url or os.getenv("MARINETRAFFIC_BASE_URL", self._DEFAULT_BASE)).rstrip("/")
        if not self._api_key:
            raise EnvironmentError("MARINETRAFFIC_API_KEY is not set")

    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        import urllib.request
        import urllib.parse
        import json

        from_datetime = time_range[0].strftime("%Y-%m-%dT%H:%M:%S")
        to_datetime = time_range[1].strftime("%Y-%m-%dT%H:%M:%S")
        params = urllib.parse.urlencode({
            "v": "8",
            "mmsi": mmsi,
            "fromdate": from_datetime,
            "todate": to_datetime,
            "protocol": "json",
        })
        url = f"{self._base_url}/gettrack/{self._api_key}/{params}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                raw = json.loads(resp.read())
        except Exception as exc:
            _log.error("MarineTrafficAISClient request failed: %s", exc)
            return []

        # MarineTraffic returns {"data": [{"MMSI":..,"LAT":..,"LON":..,"SPEED":..,"COURSE":..,"TIMESTAMP":..}]}
        results: list[VesselSatellitePosition] = []
        for row in raw.get("data", []):
            try:
                results.append(
                    VesselSatellitePosition(
                        mmsi=str(row.get("MMSI", mmsi)),
                        latitude=float(row["LAT"]),
                        longitude=float(row["LON"]),
                        timestamp_utc=row.get("TIMESTAMP", ""),
                        sog_knots=float(row["SPEED"]) if row.get("SPEED") is not None else None,
                        cog_degrees=float(row["COURSE"]) if row.get("COURSE") is not None else None,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        _log.info("MarineTrafficAISClient: mmsi=%s returned %d positions", mmsi, len(results))
        return results


def get_sais_client(provider: str | None = None) -> SatelliteAISClient:
    """Factory: return the right S-AIS client based on *provider* or SAIS_PROVIDER env var."""
    chosen = (provider or os.getenv("SAIS_PROVIDER", "none")).lower()
    if chosen == "spire":
        return SpireMaritimeAISClient()
    if chosen in ("marinetraffic", "exactearth"):
        return MarineTrafficAISClient()
    return StubSatelliteAISClient()
