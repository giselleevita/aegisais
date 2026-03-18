import asyncio
import structlog
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.logging import configure_logging
from app.modules.auth.dependencies import get_current_user, require_admin
from app.infrastructure.ingest.schemas import ReplayStartIn
from app.infrastructure.ingest.replay import start_replay_task, replay_state

log = structlog.get_logger("aegisais.replay")

router = APIRouter()

@router.post("/replay/start")
async def replay_start(
    path: str = Query(..., description="Server-side path to data file (.csv, .dat, or .zst compressed)"),
    speedup: float = Query(100.0, ge=0.1),
    use_streaming: bool = Query(True, description="Use streaming mode for large files (memory-efficient)"),
    batch_size: int = Query(100, ge=1, le=10000, description="Batch size for database commits"),
    db: Session = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    if not settings.allow_replay:
        raise HTTPException(status_code=403, detail="Replay disabled")

    if replay_state.running:
        raise HTTPException(status_code=409, detail="Replay already running")

    # Validate path exists before starting
    from pathlib import Path
    from app.infrastructure.ingest.replay import PROJECT_ROOT
    
    path_obj = Path(path)
    resolved_path = None
    
    if path_obj.is_absolute():
        resolved_path = path_obj
    else:
        resolved_path = PROJECT_ROOT / path
        if not resolved_path.exists():
            resolved_path = Path.cwd() / path
    
    if not resolved_path or not resolved_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"File not found: {path}. Tried: {PROJECT_ROOT / path if not path_obj.is_absolute() else path}"
        )

    # Start replay task with error handling
    async def run_replay_with_error_handling():
        try:
            await start_replay_task(path=path, speedup=speedup, use_streaming=use_streaming, batch_size=batch_size)
        except Exception as e:
            from app.infrastructure.ws.manager import broadcast
            error_msg = f"Replay task failed: {str(e)}"
            log.error("replay_task_failed", error=str(e), path=path, exc_info=True)
            try:
                await broadcast({"kind": "error", "message": error_msg, "path": path})
            except:
                pass
    
    # fire-and-forget asyncio task with proper error handling
    task = asyncio.create_task(run_replay_with_error_handling())
    
    # Add a callback to log if task fails (but don't await it)
    def log_task_result(task):
        try:
            if task.exception():
                log.error("replay_task_exception", exception=str(task.exception()), exc_info=True)
        except:
            pass
    
    task.add_done_callback(log_task_result)
    return {"status": "started", "path": path, "speedup": speedup, "streaming": use_streaming, "batch_size": batch_size}

@router.post("/replay/stop")
async def replay_stop(admin: Any = Depends(require_admin)):
    replay_state.stop_requested = True
    return {"status": "stopping"}

@router.get("/replay/status")
async def replay_status(current_user: Any = Depends(get_current_user)):
    return {
        "running": replay_state.running,
        "processed": replay_state.processed,
        "last_timestamp": replay_state.last_timestamp,
        "stop_requested": replay_state.stop_requested,
    }
