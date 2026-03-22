"""Rate limit dependency behaviour."""

import pytest
from fastapi.testclient import TestClient

from app.middleware.rate_limit import reset_rate_limit_store


@pytest.fixture(autouse=True)
def clear_limits():
    reset_rate_limit_store()
    yield
    reset_rate_limit_store()


def test_login_rate_limit_returns_429(client: TestClient):
    """auth_login_rate_limit allows 30 POSTs/min; the 31st returns 429."""
    for i in range(30):
        r = client.post(
            "/v1/auth/login",
            data={"username": "nouser", "password": "bad"},
        )
        assert r.status_code == 401, f"expected 401 on attempt {i + 1}, got {r.status_code}"

    r31 = client.post(
        "/v1/auth/login",
        data={"username": "nouser", "password": "bad"},
    )
    assert r31.status_code == 429
    assert "Rate limit" in (r31.json().get("detail") or "")
