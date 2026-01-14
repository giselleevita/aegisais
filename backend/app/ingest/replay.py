from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from ..db import SessionLocal
from .loaders import load_csv_points, load_csv_points_streaming
from ..services.pipeline import process_point
from ..api.ws import broadcast

log = logging.getLogger("aegisais.replay")

# Get the project root directory (same logic as upload route)
# __file__ is at: backend/app/ingest/replay.py
# So we go: app/ingest -> app -> backend -> project_root
BACKEND_DIR = Path(__file__).parent.parent.parent  # backend/app/ingest -> backend
PROJECT_ROOT = BACKEND_DIR.parent  # backend -> project root (aegisais)

@dataclass
class ReplayState:
    running: bool = False
    processed: int = 0
    last_timestamp: str | None = None
    stop_requested: bool = False

replay_state = ReplayState()

async def start_replay_task(path: str, speedup: float = 100.0, use_streaming: bool = True, batch_size: int = 100):
    """
    Start replaying AIS data from a file.
    
    Args:
        path: Path to CSV or .zst file
        speedup: Replay speed multiplier (1.0 = real-time, 100.0 = 100x faster)
        use_streaming: If True, use streaming for large files (memory-efficient)
        batch_size: Number of points to process before committing to database
    """
    # Validate file exists BEFORE setting state to running
    try:
        path_obj = Path(path)
        resolved_path = None
        
        # Strategy 1: If absolute, use as-is
        if path_obj.is_absolute():
            if path_obj.exists():
                resolved_path = path_obj
            else:
                raise FileNotFoundError(f"Absolute path does not exist: {path}")
        else:
            # Strategy 2: Try relative to project root
            resolved_path = PROJECT_ROOT / path
            if not resolved_path.exists():
                # Strategy 3: Try relative to current working directory
                resolved_path = Path.cwd() / path
                if not resolved_path.exists():
                    # Strategy 4: Try resolving the path (follows symlinks)
                    try:
                        resolved_path = path_obj.resolve()
                        if not resolved_path.exists():
                            raise FileNotFoundError(f"File not found: {path} (tried: {PROJECT_ROOT / path}, {Path.cwd() / path}, {resolved_path})")
                    except Exception:
                        raise FileNotFoundError(f"File not found: {path} (tried: {PROJECT_ROOT / path}, {Path.cwd() / path})")
        
        path = str(resolved_path)
    except Exception as e:
        error_msg = f"Fatal error validating file path: {str(e)}"
        log.error(error_msg, exc_info=True)
        try:
            await broadcast({"kind": "error", "message": error_msg})
        except:
            pass
        return
    
    # Only set state to running after validation
    replay_state.running = True
    replay_state.stop_requested = False
    replay_state.processed = 0
    replay_state.last_timestamp = None

    try:
        # Estimate file size to decide on streaming
        resolved_path = Path(path)
        file_size_mb = resolved_path.stat().st_size / (1024 * 1024)
        log.info("Resolved replay path: %s (%.2f MB)", path, file_size_mb)
        log.info("PROJECT_ROOT: %s, CWD: %s", PROJECT_ROOT, Path.cwd())
        
        if use_streaming and file_size_mb > 50:  # Use streaming for files > 50MB
            log.info("Large file detected (%.1f MB), using streaming mode", file_size_mb)
            await _replay_streaming(path, speedup, batch_size)
        else:
            log.info("Using standard loading mode")
            await _replay_standard(path, speedup, batch_size)
    except Exception as e:
        error_msg = f"Fatal error in replay task: {str(e)}"
        log.error(error_msg, exc_info=True)
        # Broadcast error to frontend
        try:
            await broadcast({"kind": "error", "message": error_msg})
        except:
            pass
        replay_state.running = False
    finally:
        replay_state.running = False
        replay_state.stop_requested = False

async def _replay_standard(path: str, speedup: float, batch_size: int):
    """Replay using standard loading (loads entire file into memory)."""
    try:
        pts = load_csv_points(path)
    except Exception as e:
        log.error("Failed to load CSV file %s: %s", path, e, exc_info=True)
        replay_state.running = False
        return

    if not pts:
        log.warning("No points to replay from %s", path)
        replay_state.running = False
        return

    log.info("Starting replay: %d points, speedup=%.1fx, batch_size=%d", len(pts), speedup, batch_size)
    
    session_id = f"replay_{id(path)}"  # Unique session ID for track store isolation
    await _process_points(pts, speedup, batch_size, session_id)

async def _replay_streaming(path: str, speedup: float, batch_size: int):
    """Replay using streaming (processes file in chunks, memory-efficient)."""
    log.info("Starting streaming replay: speedup=%.1fx, batch_size=%d", speedup, batch_size)
    
    chunk_count = 0
    session_id = f"replay_{id(path)}"  # Unique session ID for track store isolation
    
    try:
        for chunk in load_csv_points_streaming(path, chunk_size=10000):
            if replay_state.stop_requested:
                log.info("Replay stopped by user request")
                break
            
            chunk_count += 1
            
            # Process chunk immediately - don't accumulate!
            await _process_points(chunk, speedup, batch_size, session_id)
            log.debug("Processed chunk %d (%d points), continuing...", chunk_count, len(chunk))
        
        log.info("Streaming replay complete: processed %d chunks", chunk_count)
    except Exception as e:
        log.error("Error in streaming replay: %s", e, exc_info=True)
        raise

async def _process_points(pts: list, speedup: float, batch_size: int, session_id: str = "default"):
    """Process a list of points with batching and pacing.
    
    Uses per-point transactions with error isolation to prevent one bad point
    from rolling back an entire batch.
    """
    if not pts:
        return
    
    prev_ts: datetime | None = None
    errors = 0
    alerts_to_broadcast: list[dict] = []
    processed_count = 0
    
    for idx, p in enumerate(pts):
        if replay_state.stop_requested:
            log.info("Replay stopped by user request")
            break

        # Pacing (optional)
        if prev_ts is not None:
            dt = (p.timestamp - prev_ts).total_seconds()
            if dt > 0:
                await asyncio.sleep(dt / max(speedup, 0.1))
        prev_ts = p.timestamp

        # Use per-point transaction for error isolation
        with SessionLocal() as db:
            try:
                alerts = process_point(db, p, session_id)
                
                # Commit immediately for this point (prevents rollback of entire batch)
                db.commit()
                
                # Log if alerts were generated
                if alerts:
                    log.info("Generated %d alert(s) for point %d (MMSI %s)", len(alerts), idx, p.mmsi)
                    alerts_to_broadcast.extend(alerts)
                
                processed_count += 1
                replay_state.processed = processed_count
                replay_state.last_timestamp = p.timestamp.isoformat()
                
                # Broadcast progress periodically (every batch_size points)
                if processed_count % batch_size == 0:
                    # Broadcast alerts accumulated so far
                    for a in alerts_to_broadcast:
                        await broadcast({"kind": "alert", "data": a})
                    alerts_to_broadcast = []  # Clear after broadcasting
                    
                    # Broadcast progress update
                    await broadcast({"kind": "tick", "processed": replay_state.processed})
                    log.debug("Processed %d points", processed_count)
                    
            except Exception as e:
                log.error("Error processing point %d (MMSI %s): %s", idx, p.mmsi, e, exc_info=True)
                db.rollback()  # Rollback only this point's transaction
                errors += 1
                continue  # Continue processing next point

    # Broadcast remaining alerts
    if alerts_to_broadcast:
        for a in alerts_to_broadcast:
            await broadcast({"kind": "alert", "data": a})
        log.info("Broadcast %d remaining alert(s)", len(alerts_to_broadcast))
    
    # Final progress update
    await broadcast({"kind": "tick", "processed": replay_state.processed})
    
    if errors > 0:
        log.warning("Replay completed with %d errors out of %d points", errors, len(pts))
    
    log.info("Processed batch: %d points, %d errors", len(pts), errors)
