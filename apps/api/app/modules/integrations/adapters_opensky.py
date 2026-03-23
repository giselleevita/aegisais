"""OpenSky adapter with quota management, TTL caching, and canonical mapping."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings

_log = logging.getLogger("aegisais.integrations.opensky")


@dataclass(frozen=True)
class CanonicalTrackPoint:
    """Provider-agnostic position point used across ingestion pipelines."""

    source: str
    provider: str
    track_id: str
    transponder_id: str | None
    latitude: float
    longitude: float
    altitude_m: float | None
    speed_mps: float | None
    heading_deg: float | None
    vertical_rate_mps: float | None
    observed_at_utc: str
    raw: dict[str, Any]


class OpenSkyQuotaManager:
    """Simple in-process quota limiter for OpenSky calls."""

    def __init__(
        self,
        *,
        minute_limit: int,
        day_limit: int,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        self.minute_limit = max(0, minute_limit)
        self.day_limit = max(0, day_limit)
        self._now_fn = now_fn or time.time
        self._minute_bucket_start = int(self._now_fn() // 60)
        self._day_bucket_start = int(self._now_fn() // 86400)
        self._minute_count = 0
        self._day_count = 0

    def allow(self) -> bool:
        now = self._now_fn()
        minute_bucket = int(now // 60)
        day_bucket = int(now // 86400)
        if minute_bucket != self._minute_bucket_start:
            self._minute_bucket_start = minute_bucket
            self._minute_count = 0
        if day_bucket != self._day_bucket_start:
            self._day_bucket_start = day_bucket
            self._day_count = 0

        if self.minute_limit and self._minute_count >= self.minute_limit:
            return False
        if self.day_limit and self._day_count >= self.day_limit:
            return False
        self._minute_count += 1
        self._day_count += 1
        return True

    def snapshot(self) -> dict[str, int]:
        return {
            "minute_count": self._minute_count,
            "minute_limit": self.minute_limit,
            "day_count": self._day_count,
            "day_limit": self.day_limit,
        }


class _TTLCache:
    def __init__(self, ttl_sec: int, now_fn: Callable[[], float] | None = None) -> None:
        self.ttl_sec = max(0, ttl_sec)
        self._now_fn = now_fn or time.time
        self._store: dict[str, tuple[float, list[CanonicalTrackPoint]]] = {}

    def get(self, key: str) -> list[CanonicalTrackPoint] | None:
        if self.ttl_sec <= 0:
            return None
        hit = self._store.get(key)
        if not hit:
            return None
        expires_at, payload = hit
        if self._now_fn() >= expires_at:
            self._store.pop(key, None)
            return None
        return payload

    def set(self, key: str, payload: list[CanonicalTrackPoint]) -> None:
        if self.ttl_sec <= 0:
            return
        self._store[key] = (self._now_fn() + self.ttl_sec, payload)


class OpenSkyAdapter:
    """Adapter for OpenSky state vectors endpoint."""

    def __init__(
        self,
        *,
        quota: OpenSkyQuotaManager | None = None,
        cache_ttl_sec: int | None = None,
        fetcher: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self._base_url = (settings.OPENSKY_API_BASE_URL or "https://opensky-network.org").rstrip("/")
        self._quota = quota or OpenSkyQuotaManager(
            minute_limit=settings.OPENSKY_RATE_LIMIT_PER_MINUTE,
            day_limit=settings.OPENSKY_RATE_LIMIT_PER_DAY,
        )
        self._cache = _TTLCache(cache_ttl_sec if cache_ttl_sec is not None else settings.OPENSKY_CACHE_TTL_SEC)
        self._fetcher = fetcher or self._default_fetcher

    def status(self) -> dict[str, Any]:
        has_user = bool(settings.OPENSKY_USERNAME)
        has_pass = bool(settings.OPENSKY_PASSWORD)
        return {
            "provider": "opensky",
            "configured": has_user and has_pass,
            "credentials_mode": "basic_auth" if has_user and has_pass else "anonymous",
            "quota": self._quota.snapshot(),
        }

    def fetch_states(self, *, bbox: tuple[float, float, float, float] | None = None) -> list[CanonicalTrackPoint]:
        cache_key = self._cache_key(bbox)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not self._quota.allow():
            _log.warning("OpenSky quota exceeded, returning cached/empty result")
            return []

        try:
            data = self._fetcher(self._states_url(bbox))
        except (HTTPError, URLError, TimeoutError) as exc:
            _log.warning("OpenSky request failed: %s", exc)
            return []
        except Exception as exc:  # defensive for provider outages
            _log.exception("Unexpected OpenSky adapter failure: %s", exc)
            return []

        states = data.get("states", []) if isinstance(data, dict) else []
        mapped = [self._map_state_vector(row, source_time=data.get("time")) for row in states if isinstance(row, list)]
        normalized = [row for row in mapped if row is not None]
        self._cache.set(cache_key, normalized)
        return normalized

    def _cache_key(self, bbox: tuple[float, float, float, float] | None) -> str:
        if not bbox:
            return "global"
        lamin, lomin, lamax, lomax = bbox
        return f"{lamin:.4f}:{lomin:.4f}:{lamax:.4f}:{lomax:.4f}"

    def _states_url(self, bbox: tuple[float, float, float, float] | None) -> str:
        if not bbox:
            return f"{self._base_url}/api/states/all"
        lamin, lomin, lamax, lomax = bbox
        q = urlencode(
            {
                "lamin": lamin,
                "lomin": lomin,
                "lamax": lamax,
                "lomax": lomax,
            }
        )
        return f"{self._base_url}/api/states/all?{q}"

    def _default_fetcher(self, url: str) -> dict[str, Any]:
        req = Request(url)
        # Deliberately no secrets in logs/exceptions.
        with urlopen(req, timeout=10) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload)

    def _map_state_vector(self, row: list[Any], *, source_time: Any) -> CanonicalTrackPoint | None:
        # OpenSky states schema (subset):
        # [0]icao24,[1]callsign,[2]origin_country,[3]time_position,[4]last_contact,
        # [5]lon,[6]lat,[7]baro_altitude,[8]on_ground,[9]velocity,[10]true_track,[11]vertical_rate,...
        lon = self._to_float(self._safe_get(row, 5))
        lat = self._to_float(self._safe_get(row, 6))
        if lat is None or lon is None:
            return None
        observed = self._safe_get(row, 4) or self._safe_get(row, 3) or source_time
        observed_iso = self._epoch_to_iso(observed)
        icao24 = self._safe_get(row, 0)
        callsign = self._safe_get(row, 1)
        return CanonicalTrackPoint(
            source="air_traffic",
            provider="opensky",
            track_id=str(icao24 or callsign or "unknown"),
            transponder_id=str(icao24) if icao24 is not None else None,
            latitude=lat,
            longitude=lon,
            altitude_m=self._to_float(self._safe_get(row, 7)),
            speed_mps=self._to_float(self._safe_get(row, 9)),
            heading_deg=self._to_float(self._safe_get(row, 10)),
            vertical_rate_mps=self._to_float(self._safe_get(row, 11)),
            observed_at_utc=observed_iso,
            raw={
                "callsign": callsign,
                "origin_country": self._safe_get(row, 2),
                "on_ground": self._safe_get(row, 8),
            },
        )

    @staticmethod
    def _safe_get(row: list[Any], idx: int) -> Any:
        return row[idx] if len(row) > idx else None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _epoch_to_iso(value: Any) -> str:
        if value is None:
            return datetime.now(timezone.utc).isoformat()
        try:
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
            return dt.isoformat()
        except (TypeError, ValueError, OSError):
            return datetime.now(timezone.utc).isoformat()

