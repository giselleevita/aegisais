"""WebSocket stream auth behavior."""

import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings


def _register_login(client: TestClient) -> str:
    u = f"u_{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/v1/auth/register",
        json={"username": u, "email": f"{u}@test.local", "password": "p" * 12},
    )
    assert r.status_code == 200, r.text
    login = client.post(
        "/v1/auth/login",
        data={"username": u, "password": "p" * 12},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_ws_anonymous_ok_when_auth_not_required(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "websocket_require_auth", False)
    with client.websocket_connect("/v1/stream") as ws:
        ws.send_text("ping")


def test_ws_rejects_missing_token_when_auth_required(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "websocket_require_auth", True)
    with client.websocket_connect("/v1/stream") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_accepts_query_token_when_auth_required(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "websocket_require_auth", True)
    token = _register_login(client)
    with client.websocket_connect(f"/v1/stream?token={token}") as ws:
        ws.send_text("ping")


def test_ws_rejects_bad_token_when_auth_required(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "websocket_require_auth", True)
    with client.websocket_connect("/v1/stream?token=not-a-jwt") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008
