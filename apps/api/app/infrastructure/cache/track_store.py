import json
from typing import List
from datetime import datetime, timezone
from app.infrastructure.ingest.loaders import AisPoint
from app.infrastructure.cache.redis_client import get_redis_client
from app.core.config import settings

class RedisTrackStore:
    """
    Redis-backed track store using Sorted Sets (ZSETs).
    Keys: {prefix}:vessel:{mmsi}:track
    Score: Timestamp (epoch)
    Value: JSON serialized AisPoint
    """
    
    def __init__(self, window_size_min: int = 60):
        self.redis = get_redis_client()
        self.prefix = settings.redis_prefix
        self.window_size_sec = window_size_min * 60

    def _get_key(self, mmsi: str) -> str:
        return f"{self.prefix}:vessel:{mmsi}:track"

    def push(self, p: AisPoint):
        """Add a point to the track and trim the window."""
        key = self._get_key(p.mmsi)
        score = p.timestamp.replace(tzinfo=timezone.utc).timestamp()
        
        # Serialize point to JSON
        # Note: Datetime needs string conversion for JSON
        point_data = {
            "mmsi": p.mmsi,
            "timestamp": p.timestamp.isoformat(),
            "lat": p.lat,
            "lon": p.lon,
            "sog": p.sog,
            "cog": p.cog,
            "heading": p.heading
        }
        
        # Add to ZSET
        self.redis.zadd(key, {json.dumps(point_data): score})
        
        # Trim old points from the window
        min_score = score - self.window_size_sec
        self.redis.zremrangebyscore(key, "-inf", min_score)
        
        # Set expiration on the whole key to clean up abandoned vessels
        self.redis.expire(key, 86400)  # 24 hours

    def get_track(self, mmsi: str, limit: int = 5) -> List[AisPoint]:
        """Retrieve the last N points for a vessel, ordered by time."""
        key = self._get_key(mmsi)
        raw_points = self.redis.zrevrange(key, 0, limit - 1)
        
        points = []
        for raw in reversed(raw_points):
            data = json.loads(raw)
            # Deserialize back to AisPoint
            points.append(AisPoint(
                mmsi=data["mmsi"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                lat=data["lat"],
                lon=data["lon"],
                sog=data["sog"],
                cog=data["cog"],
                heading=data["heading"]
            ))
        return points
