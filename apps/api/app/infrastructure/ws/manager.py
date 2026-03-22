import asyncio
import logging
from contextlib import contextmanager
from typing import Generator, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.middleware.rate_limit import (
    WS_CONNECT_PER_MINUTE,
    WS_CONNECT_WINDOW_SEC,
    rate_limit_allow_ip,
)
from app.modules.auth.models import User
from app.modules.auth.service import decode_access_token

log = logging.getLogger("aegisais.ws")

_ws_auth_dev_warned: bool = False

router = APIRouter()

_clients: Set[WebSocket] = set()

# Set from FastAPI lifespan so sync code (e.g. threadpool routes) can schedule broadcasts.
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_event_loop(loop: asyncio.AbstractEventLoop | None) -> None:
    global _main_loop
    _main_loop = loop


def schedule_broadcast(payload: dict) -> None:
    """Fire-and-forget broadcast from sync code (e.g. AlertService in a threadpool worker)."""
    loop = _main_loop
    if loop is None:
        log.debug("schedule_broadcast skipped: main event loop not set")
        return

    def _done(fut) -> None:
        try:
            fut.result()
        except Exception as e:
            log.warning("broadcast task failed: %s", e)

    fut = asyncio.run_coroutine_threadsafe(broadcast(payload), loop)
    fut.add_done_callback(_done)


@contextmanager
def _scoped_db(ws: WebSocket) -> Generator[Session, None, None]:
    """Open a DB session for the scope only (respects FastAPI dependency_overrides in tests)."""
    app = ws.scope.get("app")
    factory = (
        app.dependency_overrides.get(get_db, get_db)
        if app is not None and hasattr(app, "dependency_overrides")
        else get_db
    )
    gen = factory()
    db = next(gen)
    try:
        yield db
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _ws_token_ok(token: str, db: Session) -> bool:
    """Return True if JWT decodes and maps to an active user."""
    payload = decode_access_token(token)
    if not payload:
        return False
    username = payload.get("sub")
    if not username:
        return False
    user = db.query(User).filter(User.username == username).first()
    return user is not None and bool(user.is_active)

async def broadcast(payload: dict):
    """Broadcast a message to all connected WebSocket clients."""
    if not _clients:
        return
    
    dead = []
    message = json.dumps(payload, default=str)
    
    for ws in list(_clients):
        try:
            await ws.send_text(message)
        except WebSocketDisconnect:
            dead.append(ws)
        except Exception as e:
            log.warning("Error sending to WebSocket client: %s", e)
            dead.append(ws)
    
    for ws in dead:
        _clients.discard(ws)
    
    if dead:
        log.debug("Removed %d dead WebSocket connections", len(dead))

@router.websocket("/stream")
async def stream(ws: WebSocket):
    """WebSocket endpoint for real-time updates (alerts, replay progress, etc.).

    Optional query: ?token=<JWT> — when present, token must be valid and user active.

    If settings.websocket_require_auth is True, a valid token is required.
    Otherwise token is optional (local dev); invalid tokens are still rejected when sent.

    DB is only used for the token check, then released (no session held for the whole connection).
    """
    global _ws_auth_dev_warned
    client = ws.scope.get("client")
    client_ip = client[0] if client else "unknown"
    if not rate_limit_allow_ip(
        "ws_connect",
        client_ip,
        WS_CONNECT_PER_MINUTE,
        WS_CONNECT_WINDOW_SEC,
    ):
        await ws.close(code=1008)
        return
    if not settings.websocket_require_auth and not _ws_auth_dev_warned:
        _ws_auth_dev_warned = True
        log.warning(
            "WEBSOCKET_REQUIRE_AUTH is disabled; anonymous WebSocket /v1/stream allowed (dev/test only)"
        )
    await ws.accept()
    token = ws.query_params.get("token") or None
    with _scoped_db(ws) as db:
        if settings.websocket_require_auth:
            if not token or not _ws_token_ok(token, db):
                await ws.close(code=1008)
                return
        elif token and not _ws_token_ok(token, db):
            await ws.close(code=1008)
            return

    _clients.add(ws)
    log.info("WebSocket client connected. Total clients: %d", len(_clients))
    
    try:
        while True:
            # Keep connection alive; client can send pings or any text
            try:
                await ws.receive_text()
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        log.debug("WebSocket client disconnected normally")
    except Exception as e:
        log.warning("WebSocket error: %s", e, exc_info=True)
    finally:
        _clients.discard(ws)
        log.info("WebSocket client disconnected. Total clients: %d", len(_clients))
