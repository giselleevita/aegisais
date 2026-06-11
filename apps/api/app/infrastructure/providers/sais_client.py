"""S-AIS (Satellite AIS) provider client factory.

Supports multiple satellite data providers:
- MarineTraffic: Marine traffic data via MarineTraffic API
- Spire: Satellite AIS data via Spire API
- Orbcomm: Satellite AIS data via Orbcomm API
- ExactEarth: Satellite AIS data via ExactEarth API
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from app.core.config import settings

log = logging.getLogger("aegisais.providers.sais")


@dataclass
class SAISPosition:
    """Satellite AIS position record."""
    mmsi: int
    lat: float
    lon: float
    timestamp: datetime
    confidence: float = 1.0
    source: str = "sais"


class BaseSAISClient(ABC):
    """Base class for all S-AIS provider clients."""

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """Fetch all available positions from the provider."""
        pass

    @abstractmethod
    def get_positions_for_mmsis(self, mmsis: List[int]) -> List[Dict[str, Any]]:
        """Fetch positions for specific MMSIs."""
        pass


class MarineTrafficClient(BaseSAISClient):
    """MarineTraffic API client for satellite AIS data."""

    def __init__(self, api_key: str = "", base_url: str = ""):
        super().__init__(api_key, base_url or "https://api.marinetraffic.com/v5")

    def get_all_positions(self) -> List[Dict[str, Any]]:
        """Fetch all positions from MarineTraffic API."""
        if not self.api_key:
            log.warning("marinetraffic_api_key_missing")
            return []

        try:
            url = f"{self.base_url}/vessels/list"
            params: Dict[str, str] = {
                "api_key": self.api_key,
                "output": "json",
            }
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            positions: List[Dict[str, Any]] = []
            data = response.json()
            if isinstance(data, list):
                for vessel in data:
                    try:
                        pos: Dict[str, Any] = {
                            "mmsi": int(vessel.get("MMSI", 0)),
                            "lat": float(vessel.get("LAT", 0)),
                            "lon": float(vessel.get("LON", 0)),
                            "timestamp": datetime.now(timezone.utc),
                            "confidence": 0.95,
                        }
                        if pos["mmsi"] > 0:
                            positions.append(pos)
                    except (ValueError, KeyError) as e:
                        log.debug("marinetraffic_parse_error: %s", e)

            return positions

        except requests.RequestException as e:
            log.error("marinetraffic_fetch_failed: %s", e)
            return []

    def get_positions_for_mmsis(self, mmsis: List[int]) -> List[Dict[str, Any]]:
        """Fetch positions for specific MMSIs from MarineTraffic API."""
        if not self.api_key or not mmsis:
            return []

        try:
            positions: List[Dict[str, Any]] = []
            for mmsi in mmsis:
                url = f"{self.base_url}/vessel/get"
                params: Dict[str, str | int] = {
                    "api_key": self.api_key,
                    "mmsi": mmsi,
                    "output": "json",
                }
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()
                if data:
                    try:
                        pos: Dict[str, Any] = {
                            "mmsi": int(data.get("MMSI", mmsi)),
                            "lat": float(data.get("LAT", 0)),
                            "lon": float(data.get("LON", 0)),
                            "timestamp": datetime.now(timezone.utc),
                            "confidence": 0.95,
                        }
                        positions.append(pos)
                    except (ValueError, KeyError) as e:
                        log.debug("marinetraffic_parse_error mmsi=%s: %s", mmsi, e)

            return positions

        except requests.RequestException as e:
            log.error("marinetraffic_mmsi_fetch_failed: %s", e)
            return []


class NoOpSAISClient(BaseSAISClient):
    """No-op S-AIS client for when provider is disabled."""

    def get_all_positions(self) -> List[Dict[str, Any]]:
        return []

    def get_positions_for_mmsis(self, mmsis: List[int]) -> List[Dict[str, Any]]:
        return []


class SAISClientFactory:
    """Factory for creating S-AIS provider clients."""

    _clients: Dict[str, type[BaseSAISClient]] = {
        "marinetraffic": MarineTrafficClient,
        "spire": NoOpSAISClient,  # Placeholder for Spire
        "orbcomm": NoOpSAISClient,  # Placeholder for Orbcomm
        "exactearth": NoOpSAISClient,  # Placeholder for ExactEarth
        "none": NoOpSAISClient,
    }

    @classmethod
    def get_client(cls, provider: Optional[str] = None) -> Optional[BaseSAISClient]:
        """Get a client for the specified provider."""
        provider = (provider or settings.SAIS_PROVIDER or "none").lower().strip()

        if provider not in cls._clients:
            log.warning("unknown_sais_provider: %s", provider)
            return NoOpSAISClient()

        if provider == "marinetraffic":
            return MarineTrafficClient(
                api_key=settings.MARINETRAFFIC_API_KEY or "",
                base_url=settings.SAIS_API_BASE_URL or "https://api.marinetraffic.com/v5"
            )
        elif provider == "none":
            return NoOpSAISClient()
        else:
            log.warning("sais_provider_not_implemented: %s", provider)
            return NoOpSAISClient()

    @classmethod
    def register_client(cls, provider: str, client_class: type[BaseSAISClient]):
        """Register a custom S-AIS provider client."""
        cls._clients[provider.lower()] = client_class
