import json
from typing import Any, Dict
from app.infrastructure.cache.redis_client import get_redis_client
from app.core.config import settings

class RedisPublisher:
    """
    Publishes events to Redis Streams.
    """
    def __init__(self):
        self.redis = get_redis_client()
        self.prefix = settings.redis_prefix

    def _get_key(self, stream_name: str) -> str:
        return f"{self.prefix}:stream:{stream_name}"

    def publish(self, stream_name: str, data: Dict[str, Any]):
        """
        Append a message to a Redis Stream.
        Data is serialized to JSON to handle nested structures/types safely in a single field.
        """
        stream_key = self._get_key(stream_name)
        # We use a single field 'payload' to store the JSON blob
        # This keeps the stream message flat and easy to parse
        payload = json.dumps(data)
        self.redis.xadd(stream_key, {"payload": payload})

# Singleton instance
publisher = RedisPublisher()
