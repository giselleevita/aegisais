import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..settings import settings
from ..schemas import ReplayStartIn
from ..ingest.replay import start_replay_task, replay_state

router = APIRouter()

@router.post("/replay/start")
async def replay_start(
    path: str = Query(..., description="Server-side path to data file (.csv, .dat, or .zst compressed)"),
    speedup: float = Query(100.0, ge=0.1),
    use_streaming: bool = Query(True, description="Use streaming mode for large files (memory-efficient)"),
    batch_size: int = Query(100, ge=1, le=10000, description="Batch size for database commits"),
    db: Session = Depends(get_db),
):
    if not settings.allow_replay:
        raise HTTPException(status_code=403, detail="Replay disabled")

    if replay_state.running:
        raise HTTPException(status_code=409, detail="Replay already running")

    # Validate path exists before starting
    from pathlib import Path
    from ..ingest.replay import PROJECT_ROOT
    
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
            import logging
            from ..api.ws import broadcast
            log = logging.getLogger("aegisais.replay")
            error_msg = f"Replay task failed: {str(e)}"
            log.error(error_msg, exc_info=True)
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
                import logging
                log = logging.getLogger("aegisais.replay")
                log.error("Replay task raised exception: %s", task.exception(), exc_info=True)
        except:
            pass
    
    task.add_done_callback(log_task_result)
    return {"status": "started", "path": path, "speedup": speedup, "streaming": use_streaming, "batch_size": batch_size}

@router.post("/replay/stop")
async def replay_stop():
    replay_state.stop_requested = True
    return {"status": "stopping"}

@router.get("/replay/status")
async def replay_status():
    return {
        "running": replay_state.running,
        "processed": replay_state.processed,
        "last_timestamp": replay_state.last_timestamp,
        "stop_requested": replay_state.stop_requested,
    }
