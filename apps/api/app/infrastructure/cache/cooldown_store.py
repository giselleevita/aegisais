import threading
import time
from typing import Dict

from prometheus_client import Counter

from app.infrastructure.cache.redis_client import get_redis_client
from app.core.config import settings

# Incremented every time a cooldown check falls back to the in-process store
# because Redis is unavailable.  Wire to alert_rules.yml (BL-007).
COOLDOWN_REDIS_DEGRADED = Counter(
    "aegisais_cooldown_redis_degraded_total",
    "Cooldown checks served from in-memory fallback during Redis outage",
)

# Bound on in-memory fallback entries to prevent unbounded memory growth.
_FALLBACK_MAX_ENTRIES = 1024


class RedisCooldownStore:
    """
    Redis-backed alert cooldown using SETNX and TTL.
    Keys: {prefix}:cooldown:{mmsi}:{rule_type}
    Value: "1"

    Degraded-mode policy (BL-007)
    ─────────────────────────────
    When Redis is unavailable the store falls back to an in-process TTL dict
    bounded to _FALLBACK_MAX_ENTRIES entries.  This keeps cooldown *bounded*
    during short outages within a single worker process (not cluster-safe).

    If the fallback dict is also saturated, the call fails-open (allows the
    alert) to avoid silently suppressing real detections.  Every fallback
    invocation increments aegisais_cooldown_redis_degraded_total; alert on
    this metric to page when Redis is down.
    """

    def __init__(self):
        self.redis = get_redis_client()
        self.prefix = settings.redis_prefix
        self.cooldown_sec = settings.alert_cooldown_sec
        self._fallback_lock = threading.Lock()
        # key -> expiry_monotonic_float
        self._fallback: Dict[str, float] = {}

    def _get_key(self, mmsi: str, rule_type: str) -> str:
        return f"{self.prefix}:cooldown:{mmsi}:{rule_type}"

    def _check_and_set_fallback(self, key: str) -> bool:
        """Thread-safe in-memory TTL fallback.

        Returns True if NOT in cooldown (novel alert), False if in cooldown.
        Fails-open when the store is saturated to avoid suppressing detections.
        """
        now = time.monotonic()
        with self._fallback_lock:
            # Evict expired entries first to keep the dict tidy.
            expired = [k for k, exp in self._fallback.items() if exp <= now]
            for k in expired:
                del self._fallback[k]

            if key in self._fallback:
                return False  # still in cooldown

            if len(self._fallback) >= _FALLBACK_MAX_ENTRIES:
                # Saturated — fail-open rather than drop detections.
                return True

            self._fallback[key] = now + self.cooldown_sec
            return True

    def check_and_set(self, mmsi: str, rule_type: str) -> bool:
        """
        Check if an alert is in cooldown.
        Returns True if NOT in cooldown (and sets the cooldown),
        False if currently in cooldown.

        On Redis failure falls back to in-memory TTL store and increments
        aegisais_cooldown_redis_degraded_total (see BL-007).
        """
        key = self._get_key(mmsi, rule_type)
        try:
            # SET key value NX EX seconds
            # Returns True if set (novel alert), False if already exists
            return bool(self.redis.set(key, "1", nx=True, ex=self.cooldown_sec))
        except Exception:
            COOLDOWN_REDIS_DEGRADED.inc()
            return self._check_and_set_fallback(key)
