"""Rate limiting: in-memory (default) or Redis sliding window (multi-worker)."""
import logging
import time
from collections import defaultdict
from typing import Callable, cast

from fastapi import HTTPException, Request, status

from app.core.config import settings

log = logging.getLogger("aegisais.rate_limit")

_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def _sliding_window_allow_memory(mem_key: str, max_requests: int, window_seconds: int) -> bool:
    current_time = time.time()
    _rate_limit_store[mem_key] = [
        ts for ts in _rate_limit_store[mem_key] if current_time - ts < window_seconds
    ]
    if len(_rate_limit_store[mem_key]) >= max_requests:
        return False
    _rate_limit_store[mem_key].append(current_time)
    return True


def _sliding_window_allow_redis(
    redis_key: str,
    mem_key: str,
    max_requests: int,
    window_seconds: int,
) -> bool:
    """
    Fixed-window counter in Redis (INCR + EXPIRE). Atomic and works with fakeredis;
    close to "N per window_seconds" for multi-worker deployments.
    """
    try:
        from app.infrastructure.cache.redis_client import get_redis_client

        r = get_redis_client()
        now = time.time()
        bucket = int(now // window_seconds)
        key = f"{redis_key}:w{bucket}"
        n = cast(int, r.incr(key))
        if n == 1:
            r.expire(key, window_seconds)
        if n > max_requests:
            return False
        return True
    except Exception as e:
        log.warning(
            "rate_limit_redis_failed_using_memory_fallback: %s",
            e,
            exc_info=False,
        )
        return _sliding_window_allow_memory(mem_key, max_requests, window_seconds)


def rate_limit_allow_ip(
    name: str,
    client_ip: str,
    max_requests: int,
    window_seconds: int,
) -> bool:
    """Shared check for HTTP dependencies and WebSocket pre-accept limits."""
    mem_key = f"{client_ip}:{name}"
    redis_key = f"{settings.redis_prefix}:rl:{name}:{client_ip}"
    if settings.rate_limit_use_redis:
        return _sliding_window_allow_redis(
            redis_key, mem_key, max_requests, window_seconds
        )
    return _sliding_window_allow_memory(mem_key, max_requests, window_seconds)


def reset_rate_limit_store() -> None:
    """Clear in-memory counters; when Redis mode is on, drop rate-limit keys only."""
    _rate_limit_store.clear()
    if not settings.rate_limit_use_redis:
        return
    try:
        from app.infrastructure.cache.redis_client import get_redis_client

        r = get_redis_client()
        prefix = f"{settings.redis_prefix}:rl:"
        for k in r.scan_iter(f"{prefix}*"):
            r.delete(k)
    except Exception:
        pass


def rate_limit_dependency(
    max_requests: int = 100,
    window_seconds: int = 60,
    *,
    name: str = "default",
) -> Callable:
    """
    FastAPI dependency: call as ``Depends(auth_login_limit)`` with a shared instance per route.

    Example::

        auth_login_limit = rate_limit_dependency(30, 60, name="auth_login")

        @router.post("/login")
        async def login(
            _: None = Depends(auth_login_limit),
            form_data: OAuth2PasswordRequestForm = Depends(),
            ...
        ):
    """

    async def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limit_allow_ip(name, client_ip, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds",
            )

    return dependency


# Shared instances (stable object identity for Depends)
auth_login_rate_limit = rate_limit_dependency(30, 60, name="auth_login")
auth_register_rate_limit = rate_limit_dependency(10, 60, name="auth_register")
auth_forgot_password_rate_limit = rate_limit_dependency(10, 60, name="auth_forgot_password")
upload_file_rate_limit = rate_limit_dependency(30, 60, name="upload_file")
api_read_rate_limit = rate_limit_dependency(100, 60, name="api_read")
api_write_rate_limit = rate_limit_dependency(30, 60, name="api_write")
reports_generate_rate_limit = rate_limit_dependency(30, 60, name="reports_generate")
# WebSocket: checked in manager before accept (same name / limits)
WS_CONNECT_PER_MINUTE = 5
WS_CONNECT_WINDOW_SEC = 60


def rate_limit(max_requests: int = 100, window_seconds: int = 60) -> Callable:
    """
    Rate limiting decorator (legacy; prefer rate_limit_dependency + Depends).

    Uses the same in-memory sliding window as the dependency when Redis mode is off;
    when Redis mode is on, uses a per-endpoint name derived from the wrapped function.
    """

    def decorator(func: Callable) -> Callable:
        dep_name = f"decorator:{func.__name__}"

        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            mem_key = f"{client_ip}:{dep_name}"
            redis_key = f"{settings.redis_prefix}:rl:{dep_name}:{client_ip}"

            if settings.rate_limit_use_redis:
                allowed = _sliding_window_allow_redis(
                    redis_key, mem_key, max_requests, window_seconds
                )
            else:
                allowed = _sliding_window_allow_memory(mem_key, max_requests, window_seconds)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds",
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
