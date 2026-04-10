"""WebSocket stream auth behavior."""

import asyncio
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.infrastructure.ws import manager as ws_manager


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


class _FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send_text(self, message: str) -> None:
        self.messages.append(message)


def test_broadcast_filters_org_scoped_payloads(monkeypatch):
    ws_org_1 = _FakeWebSocket()
    ws_org_2 = _FakeWebSocket()
    ws_global = _FakeWebSocket()

    monkeypatch.setattr(ws_manager, "_clients", {ws_org_1, ws_org_2, ws_global})
    monkeypatch.setattr(ws_manager, "_client_org_ids", {ws_org_1: 1, ws_org_2: 2, ws_global: None})

    asyncio.run(
        ws_manager.broadcast({"type": "alert_status_updated", "organisation_id": 1, "status": "reviewed"})
    )

    assert [json.loads(message) for message in ws_org_1.messages] == [
        {"type": "alert_status_updated", "organisation_id": 1, "status": "reviewed"}
    ]
    assert ws_org_2.messages == []
    assert ws_global.messages == []


def test_broadcast_keeps_global_messages_global(monkeypatch):
    ws_org_1 = _FakeWebSocket()
    ws_org_2 = _FakeWebSocket()

    monkeypatch.setattr(ws_manager, "_clients", {ws_org_1, ws_org_2})
    monkeypatch.setattr(ws_manager, "_client_org_ids", {ws_org_1: 1, ws_org_2: 2})

    asyncio.run(ws_manager.broadcast({"kind": "tick", "processed": 7}))

    expected = {"kind": "tick", "processed": 7}
    assert [json.loads(message) for message in ws_org_1.messages] == [expected]
    assert [json.loads(message) for message in ws_org_2.messages] == [expected]
