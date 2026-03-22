"""Redis-backed rate limit path (fakeredis; no real Redis required)."""

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.middleware.rate_limit import reset_rate_limit_store


@pytest.fixture
def redis_rl_client(client: TestClient, monkeypatch):
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(settings, "rate_limit_use_redis", True)
    monkeypatch.setattr(
        "app.infrastructure.cache.redis_client.get_redis_client",
        lambda: fake,
    )
    reset_rate_limit_store()
    fake.flushall()
    yield client
    reset_rate_limit_store()
    fake.flushall()


def test_login_rate_limit_returns_429_with_redis_backend(redis_rl_client: TestClient):
    """Same limit as in-memory: 30 failed logins/min then 429."""
    for i in range(30):
        r = redis_rl_client.post(
            "/v1/auth/login",
            data={"username": "nouser", "password": "bad"},
        )
        assert r.status_code == 401, f"expected 401 on attempt {i + 1}, got {r.status_code}"

    r31 = redis_rl_client.post(
        "/v1/auth/login",
        data={"username": "nouser", "password": "bad"},
    )
    assert r31.status_code == 429
    assert "Rate limit" in (r31.json().get("detail") or "")
