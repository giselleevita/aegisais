"""Single provider registry for satellite AIS integrations.

Unsupported or incomplete providers are explicit ``unavailable`` clients.  A
configured provider must never silently masquerade as a healthy empty feed.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TypedDict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings

_log = logging.getLogger("aegisais.sais.client")


class VesselSatellitePosition(TypedDict, total=False):
    mmsi: str
    latitude: float
    longitude: float
    timestamp_utc: str
    sog_knots: float | None
    cog_degrees: float | None
    confidence: float
    source: str


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    state: str
    reason: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


class SatelliteAISClient(ABC):
    provider_id = "unknown"

    @property
    @abstractmethod
    def status(self) -> ProviderStatus:
        raise NotImplementedError

    @abstractmethod
    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        raise NotImplementedError


class UnavailableSatelliteAISClient(SatelliteAISClient):
    def __init__(self, provider: str = "none", reason: str = "provider_disabled"):
        self.provider_id = provider
        self._reason = reason

    @property
    def status(self) -> ProviderStatus:
        return ProviderStatus(self.provider_id, "unavailable", self._reason)

    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        _log.warning("sais_provider_unavailable provider=%s reason=%s", self.provider_id, self._reason)
        return []


class StubSatelliteAISClient(UnavailableSatelliteAISClient):
    """Backwards-compatible disabled client with an explicit health state."""

    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        _log.info("StubSatelliteAISClient: provider unavailable for mmsi=%s", mmsi)
        return []


class SpireMaritimeAISClient(SatelliteAISClient):
    provider_id = "spire"

    def __init__(self, api_key: str, base_url: str = "https://api.spire.com/v2"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    @property
    def status(self) -> ProviderStatus:
        return ProviderStatus(self.provider_id, "ready" if self._api_key else "unavailable", None if self._api_key else "missing_api_key")

    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        if not self._api_key:
            return []
        params = urlencode({
            "mmsi": mmsi,
            "position_updated_after": time_range[0].isoformat(),
            "position_updated_before": time_range[1].isoformat(),
        })
        request = Request(
            f"{self._base_url}/vessels?{params}",
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - configured provider URL
                payload = json.loads(response.read())
        except Exception as exc:
            _log.error("spire_request_failed error=%s", type(exc).__name__)
            return []
        positions: list[VesselSatellitePosition] = []
        for vessel in payload.get("data", []):
            last = vessel.get("lastPositionUpdate") or {}
            try:
                positions.append(VesselSatellitePosition(
                    mmsi=str(vessel.get("staticData", {}).get("mmsi", mmsi)),
                    latitude=float(last["latitude"]),
                    longitude=float(last["longitude"]),
                    timestamp_utc=str(last["timestamp"]),
                    sog_knots=_optional_float(last.get("speed")),
                    cog_degrees=_optional_float(last.get("course")),
                    confidence=0.95,
                    source="spire",
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return positions


class MarineTrafficAISClient(SatelliteAISClient):
    provider_id = "marinetraffic"

    def __init__(self, api_key: str, base_url: str = "https://services.marinetraffic.com/api"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    @property
    def status(self) -> ProviderStatus:
        return ProviderStatus(self.provider_id, "ready" if self._api_key else "unavailable", None if self._api_key else "missing_api_key")

    def fetch_vessel_positions(
        self,
        mmsi: str,
        time_range: tuple[datetime, datetime],
    ) -> list[VesselSatellitePosition]:
        if not self._api_key:
            return []
        params = urlencode({
            "v": "8",
            "mmsi": mmsi,
            "fromdate": time_range[0].strftime("%Y-%m-%dT%H:%M:%S"),
            "todate": time_range[1].strftime("%Y-%m-%dT%H:%M:%S"),
            "protocol": "json",
        })
        request = Request(f"{self._base_url}/gettrack/{self._api_key}/?{params}")
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - configured provider URL
                payload = json.loads(response.read())
        except Exception as exc:
            _log.error("marinetraffic_request_failed error=%s", type(exc).__name__)
            return []
        positions: list[VesselSatellitePosition] = []
        for row in payload.get("data", payload if isinstance(payload, list) else []):
            try:
                positions.append(VesselSatellitePosition(
                    mmsi=str(row.get("MMSI", mmsi)),
                    latitude=float(row["LAT"]),
                    longitude=float(row["LON"]),
                    timestamp_utc=str(row.get("TIMESTAMP") or time_range[1].isoformat()),
                    sog_knots=_optional_float(row.get("SPEED")),
                    cog_degrees=_optional_float(row.get("COURSE")),
                    confidence=0.95,
                    source="marinetraffic",
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return positions


def get_sais_client(provider: str | None = None) -> SatelliteAISClient:
    chosen = (provider or settings.SAIS_PROVIDER or "none").strip().lower()
    if chosen == "spire":
        return SpireMaritimeAISClient(
            settings.SAIS_API_KEY,
            settings.SAIS_API_BASE_URL or "https://api.spire.com/v2",
        )
    if chosen == "marinetraffic":
        return MarineTrafficAISClient(
            settings.MARINETRAFFIC_API_KEY or settings.SAIS_API_KEY,
            settings.SAIS_API_BASE_URL or "https://services.marinetraffic.com/api",
        )
    if chosen == "none":
        return UnavailableSatelliteAISClient("none", "provider_disabled")
    return UnavailableSatelliteAISClient(chosen, "provider_not_implemented")


def _optional_float(value):
    return None if value in (None, "") else float(value)
