"""
ITDAE per-vessel track window store.
Mirrors app.tracking.track_store but typed for ItdaePoint.
"""
from collections import deque
from dataclasses import dataclass
from typing import Optional, Deque, Dict

from app.modules.itdae.tracking.features_itdae import ItdaePoint


@dataclass
class ItdaeTrackWindow:
    """Sliding window of recent ItdaePoints for one vessel."""
    points: Deque[ItdaePoint]


class ItdaeTrackStore:
    """
    In-memory store of per-vessel track windows for the ITDAE pipeline.
    Mirrors TrackStore but operates on ItdaePoint objects.

    Args:
        window_size: Max points to retain per vessel
    """
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._tracks: Dict[str, ItdaeTrackWindow] = {}

    def push(self, p: ItdaePoint) -> ItdaeTrackWindow:
        """Add a new point to the vessel's track window and return the updated window."""
        tw = self._tracks.get(p.mmsi)
        if tw is None:
            tw = ItdaeTrackWindow(points=deque(maxlen=self.window_size))
            self._tracks[p.mmsi] = tw
        tw.points.append(p)
        return tw

    def get(self, mmsi: str) ->Optional[ ItdaeTrackWindow]:
        """Return current track window for an MMSI, or None if not tracked."""
        return self._tracks.get(mmsi)

    def clear(self, mmsi: str) -> None:
        """Remove track for a vessel (e.g. after long gap)."""
        self._tracks.pop(mmsi, None)

    @property
    def tracked_vessels(self) -> list[str]:
        """List of all currently tracked MMSIs."""
        return list(self._tracks.keys())
