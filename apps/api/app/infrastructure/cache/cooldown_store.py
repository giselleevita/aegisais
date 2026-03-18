from app.infrastructure.cache.redis_client import get_redis_client
from app.core.config import settings

class RedisCooldownStore:
    """
    Redis-backed alert cooldown using SETNX and TTL.
    Keys: {prefix}:cooldown:{mmsi}:{rule_type}
    Value: "1"
    """
    
    def __init__(self):
        self.redis = get_redis_client()
        self.prefix = settings.redis_prefix
        self.cooldown_sec = settings.alert_cooldown_sec

    def _get_key(self, mmsi: str, rule_type: str) -> str:
        return f"{self.prefix}:cooldown:{mmsi}:{rule_type}"

    def check_and_set(self, mmsi: str, rule_type: str) -> bool:
        """
        Check if an alert is in cooldown. 
        Returns True if NOT in cooldown (and sets the cooldown), 
        False if currently in cooldown.
        """
        key = self._get_key(mmsi, rule_type)
        # SET key value NX EX seconds
        # Returns True if set (novel alert), False if already exists
        return bool(self.redis.set(key, "1", nx=True, ex=self.cooldown_sec))
