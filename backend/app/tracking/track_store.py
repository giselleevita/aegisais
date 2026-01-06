from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict
from ..ingest.loaders import AisPoint

@dataclass
class TrackWindow:
    points: Deque[AisPoint]

class TrackStore:
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self._tracks: Dict[str, TrackWindow] = {}

    def push(self, p: AisPoint) -> TrackWindow:
        tw = self._tracks.get(p.mmsi)
        if tw is None:
            tw = TrackWindow(points=deque(maxlen=self.window_size))
            self._tracks[p.mmsi] = tw
        tw.points.append(p)
        return tw
