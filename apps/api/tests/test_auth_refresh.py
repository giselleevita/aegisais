"""Refresh tokens, cookies, and access-token jti revocation (fakeredis)."""

import fakeredis
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def redis_auth(monkeypatch):
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.modules.auth.service.get_redis_client", lambda: fake)
    fake.flushall()
    yield fake
    fake.flushall()


def _register(client: TestClient, username: str = "rt_user", password: str = "p" * 12) -> None:
    r = client.post(
        "/v1/auth/register",
        json={"username": username, "email": f"{username}@t.local", "password": password},
    )
    assert r.status_code == 200, r.text


def test_login_returns_access_and_refresh_and_sets_cookie(
    client: TestClient, redis_auth: fakeredis.FakeRedis
):
    _register(client)
    login = client.post("/v1/auth/login", data={"username": "rt_user", "password": "p" * 12})
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body and "refresh_token" in body
    assert body["refresh_token"]
    jar = login.cookies.get("refresh_token")
    assert jar is not None and jar == body["refresh_token"]


def test_refresh_with_json_body(client: TestClient, redis_auth: fakeredis.FakeRedis):
    _register(client, username="u1")
    login = client.post("/v1/auth/login", data={"username": "u1", "password": "p" * 12})
    rt = login.json()["refresh_token"]
    r = client.post("/v1/auth/refresh", json={"refresh_token": rt})
    assert r.status_code == 200
    assert r.json()["access_token"] != login.json()["access_token"]


def test_refresh_with_cookie_only(client: TestClient, redis_auth: fakeredis.FakeRedis):
    _register(client, username="u2")
    login = client.post("/v1/auth/login", data={"username": "u2", "password": "p" * 12})
    assert login.cookies.get("refresh_token")
    r = client.post("/v1/auth/refresh", json={})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_logout_revokes_access_token(client: TestClient, redis_auth: fakeredis.FakeRedis):
    from app.modules.auth.service import decode_access_token

    _register(client, username="u3")
    login = client.post("/v1/auth/login", data={"username": "u3", "password": "p" * 12})
    access = login.json()["access_token"]
    assert decode_access_token(access) is not None

    out = client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert out.status_code == 200
    assert decode_access_token(access) is None


def test_refresh_requires_token(client: TestClient, redis_auth: fakeredis.FakeRedis):
    r = client.post("/v1/auth/refresh", json={})
    assert r.status_code == 401
