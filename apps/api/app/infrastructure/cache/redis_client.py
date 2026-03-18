import redis
from app.core.config import settings

# Global Redis connection pool
_redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=settings.redis_max_connections,
    decode_responses=True
)

def get_redis_client() -> redis.Redis:
    """Returns a Redis client from the global pool."""
    return redis.Redis(connection_pool=_redis_pool)
