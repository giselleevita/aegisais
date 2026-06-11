"""Open-Meteo marine weather service.

Provides real-time and forecast weather/sea state data to contextualise
AIS anomaly scoring.  Free API — no key required.

API: https://open-meteo.com/en/docs/marine-weather-api
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

_log = logging.getLogger("aegisais.weather")

_BASE_URL = "https://marine-api.open-meteo.com/v1/marine"

# Module-level client — reused across calls
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
    return _client


async def get_marine_weather(
    lat: float,
    lon: float,
) -> Optional[dict[str, Any]]:
    """Fetch current marine weather for a position.

    Returns wave height, period, direction, swell data, and wind-wave data.
    Returns None on failure (graceful degradation).
    """
    params: dict[str, str | float] = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "current": ",".join([
            "wave_height",
            "wave_direction",
            "wave_period",
            "wind_wave_height",
            "wind_wave_direction",
            "swell_wave_height",
            "swell_wave_direction",
        ]),
        "timezone": "UTC",
    }

    try:
        client = _get_client()
        resp = await client.get("", params=params)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        return {
            "lat": lat,
            "lon": lon,
            "timestamp": current.get("time"),
            "wave_height_m": current.get("wave_height"),
            "wave_direction_deg": current.get("wave_direction"),
            "wave_period_sec": current.get("wave_period"),
            "wind_wave_height_m": current.get("wind_wave_height"),
            "wind_wave_direction_deg": current.get("wind_wave_direction"),
            "swell_wave_height_m": current.get("swell_wave_height"),
            "swell_wave_direction_deg": current.get("swell_wave_direction"),
            "sea_state": _classify_sea_state(current.get("wave_height")),
        }
    except httpx.TimeoutException:
        _log.warning("Weather API timeout for (%.4f, %.4f)", lat, lon)
        return None
    except httpx.HTTPStatusError as e:
        _log.warning("Weather API error %d for (%.4f, %.4f)", e.response.status_code, lat, lon)
        return None
    except Exception as e:
        _log.warning("Weather fetch failed: %s", e)
        return None


def _classify_sea_state(wave_height: Optional[float]) -> str:
    """Classify sea state from wave height using Douglas Scale."""
    if wave_height is None:
        return "unknown"
    if wave_height < 0.1:
        return "calm_glassy"
    if wave_height < 0.5:
        return "calm_rippled"
    if wave_height < 1.25:
        return "smooth"
    if wave_height < 2.5:
        return "slight"
    if wave_height < 4.0:
        return "moderate"
    if wave_height < 6.0:
        return "rough"
    if wave_height < 9.0:
        return "very_rough"
    if wave_height < 14.0:
        return "high"
    return "phenomenal"


def is_weather_relevant_for_anomaly(
    weather: dict[str, Any],
    vessel_sog: Optional[float],
) -> Optional[dict[str, Any]]:
    """Check if weather conditions could explain anomalous vessel behaviour.

    High sea states can explain sudden speed/heading changes.
    Returns contextual assessment or None.
    """
    wave_height = weather.get("wave_height_m")
    if wave_height is None:
        return None

    sea_state = weather.get("sea_state", "unknown")

    # Sea state >= rough can explain anomalous heading/speed changes
    if wave_height >= 4.0:
        return {
            "weather_mitigating": True,
            "sea_state": sea_state,
            "wave_height_m": wave_height,
            "assessment": f"Sea state '{sea_state}' ({wave_height:.1f}m waves) may explain anomalous vessel behaviour",
        }

    # Very calm seas make any anomalous behaviour MORE suspicious
    if wave_height < 0.5 and vessel_sog is not None and vessel_sog < 2.0:
        return {
            "weather_mitigating": False,
            "sea_state": sea_state,
            "wave_height_m": wave_height,
            "assessment": "Calm sea conditions — anomalous behaviour unlikely caused by weather",
        }

    return None
