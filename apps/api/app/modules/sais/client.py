"""Satellite AIS client abstraction and stub implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypedDict

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
