"""Live AIS ingestion via aisstream.io WebSocket API (GAP-02).

Connects to aisstream.io's free-tier WebSocket feed, decodes AIS position
reports, and feeds them into the existing detection pipeline via
``enqueue_point()``.  Designed for sovereign deployment — the API key is
the only external dependency.

Environment variables:
    AISSTREAM_API_KEY   — aisstream.io API key (required for live feed)
    AISSTREAM_BBOX      — Bounding box filter as "lat_min,lon_min,lat_max,lon_max"
                          Default: Baltic Sea
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import settings
from app.infrastructure.ingest.loaders import AisPoint
from app.services.pipeline import enqueue_point, process_point

_log = logging.getLogger("aegisais.aisstream")

# Default bounding box: Baltic Sea
_DEFAULT_BBOX = [[54.0, 9.0], [66.0, 30.0]]


def _parse_bbox(raw: str) -> list[list[float]]:
    """Parse 'lat_min,lon_min,lat_max,lon_max' into [[lat_min,lon_min],[lat_max,lon_max]]."""
    parts = [float(x.strip()) for x in raw.split(",")]
    if len(parts) != 4:
        raise ValueError(f"AISSTREAM_BBOX must have 4 values, got {len(parts)}")
    return [[parts[0], parts[1]], [parts[2], parts[3]]]


def _build_subscribe_message(api_key: str, bbox: list[list[float]]) -> str:
    return json.dumps({
        "APIKey": api_key,
        "BoundingBoxes": [bbox],
        "FiltersShipMMSI": [],
        "FilterMessageTypes": ["PositionReport", "StandardClassBPositionReport"],
    })


def _ais_message_to_point(msg: dict[str, Any]) -> Optional[AisPoint]:
    """Convert an aisstream.io PositionReport to an AisPoint."""
    meta = msg.get("MetaData", {})
    position = msg.get("Message", {}).get("PositionReport") or msg.get("Message", {}).get("StandardClassBPositionReport")
    if not position:
        return None

    mmsi_raw = meta.get("MMSI") or position.get("UserID")
    if not mmsi_raw:
        return None

    try:
        lat = float(position.get("Latitude", 0))
        lon = float(position.get("Longitude", 0))
        if lat == 0 and lon == 0:
            return None
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None

        ts_str = meta.get("time_utc")
        if ts_str:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        else:
            ts = datetime.now(timezone.utc)

        sog = position.get("Sog")
        cog = position.get("Cog")
        heading = position.get("TrueHeading")
        if heading == 511:
            heading = None

        return AisPoint(
            mmsi=str(mmsi_raw),
            timestamp=ts,
            lat=lat,
            lon=lon,
            sog=float(sog) if sog is not None else None,
            cog=float(cog) if cog is not None else None,
            heading=float(heading) if heading is not None else None,
        )
    except (ValueError, TypeError, KeyError) as exc:
        _log.debug("Failed to parse AIS message: %s", exc)
        return None


class AISStreamClient:
    """WebSocket client for aisstream.io live AIS feed."""

    def __init__(self, api_key: str | None = None, bbox: str | None = None):
        self._api_key = api_key or getattr(settings, "AISSTREAM_API_KEY", "")
        raw_bbox = bbox or getattr(settings, "AISSTREAM_BBOX", "")
        self._bbox = _parse_bbox(raw_bbox) if raw_bbox else _DEFAULT_BBOX
        self._running = False
        self._ws = None
        self._stats = {"messages_received": 0, "points_processed": 0, "errors": 0}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    async def start(self) -> None:
        if not self._api_key:
            _log.warning("AISSTREAM_API_KEY not set — live AIS feed disabled")
            return
        if self._running:
            _log.info("AIS stream already running")
            return
        self._running = True
        _log.info("Starting aisstream.io live feed (bbox=%s)", self._bbox)
        asyncio.get_event_loop().create_task(self._connect_loop())

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        _log.info("AIS stream stopped. Stats: %s", self._stats)

    async def _connect_loop(self) -> None:
        """Reconnecting loop with exponential backoff."""
        try:
            import websockets  # type: ignore[import-untyped]
        except ImportError:
            _log.error("websockets package not installed — pip install websockets")
            self._running = False
            return

        backoff = 1
        while self._running:
            try:
                async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
                    self._ws = ws
                    backoff = 1
                    subscribe_msg = _build_subscribe_message(self._api_key, self._bbox)
                    await ws.send(subscribe_msg)
                    _log.info("Connected to aisstream.io WebSocket")

                    async for raw_msg in ws:
                        if not self._running:
                            break
                        try:
                            msg = json.loads(raw_msg)
                            self._stats["messages_received"] += 1
                            point = _ais_message_to_point(msg)
                            if point:
                                result = process_point(point)
                                self._stats["points_processed"] += 1
                                if result.get("alerts"):
                                    for alert in result["alerts"]:
                                        _log.info(
                                            "Live alert: %s MMSI=%s severity=%d",
                                            alert["type"], alert["mmsi"], alert["severity"],
                                        )
                        except json.JSONDecodeError:
                            self._stats["errors"] += 1
                        except Exception as exc:
                            self._stats["errors"] += 1
                            _log.warning("Error processing live AIS message: %s", exc)

            except Exception as exc:
                if not self._running:
                    break
                _log.warning("AIS stream connection error: %s (reconnecting in %ds)", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

        self._ws = None


# Module-level singleton
aisstream_client = AISStreamClient()
