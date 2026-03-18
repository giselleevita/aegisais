import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import json

log = logging.getLogger("aegisais.ws")

router = APIRouter()

_clients: Set[WebSocket] = set()

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
    """WebSocket endpoint for real-time updates (alerts, replay progress, etc.)."""
    await ws.accept()
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
