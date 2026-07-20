import json
from datetime import date, datetime
from typing import Any, Dict
from uuid import UUID
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
        payload = json.dumps(data, default=_json_default)
        self.redis.xadd(stream_key, {"payload": payload})


def _json_default(value: Any) -> str:
    """Serialize the timestamp/identifier types detection rules may emit."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

# Singleton instance
publisher = RedisPublisher()
