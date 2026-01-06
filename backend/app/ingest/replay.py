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
    replay_state.running = True
    replay_state.stop_requested = False
    replay_state.processed = 0
    replay_state.last_timestamp = None

    try:
        # Resolve path - try multiple strategies
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
        
        # Estimate file size to decide on streaming
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
    
    await _process_points(pts, speedup, batch_size)

async def _replay_streaming(path: str, speedup: float, batch_size: int):
    """Replay using streaming (processes file in chunks, memory-efficient)."""
    log.info("Starting streaming replay: speedup=%.1fx, batch_size=%d", speedup, batch_size)
    
    all_pts: list = []
    chunk_count = 0
    
    try:
        for chunk in load_csv_points_streaming(path, chunk_size=10000):
            if replay_state.stop_requested:
                log.info("Replay stopped by user request")
                break
            
            all_pts.extend(chunk)
            chunk_count += 1
            
            # Process accumulated points in batches
            if len(all_pts) >= batch_size * 10:  # Process when we have enough points
                await _process_points(all_pts, speedup, batch_size)
                all_pts = []  # Clear processed points
                log.info("Processed %d chunks, continuing...", chunk_count)
        
        # Process remaining points
        if all_pts:
            await _process_points(all_pts, speedup, batch_size)
        
        log.info("Streaming replay complete: processed %d chunks", chunk_count)
    except Exception as e:
        log.error("Error in streaming replay: %s", e, exc_info=True)
        raise

async def _process_points(pts: list, speedup: float, batch_size: int):
    """Process a list of points with batching and pacing."""
    if not pts:
        return
    
    with SessionLocal() as db:
        prev_ts: datetime | None = None
        errors = 0
        batch: list = []
        
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

            try:
                alerts = process_point(db, p)
                batch.append((p, alerts))
                
                # Log if alerts were generated
                if alerts:
                    log.info("Generated %d alert(s) for point %d (MMSI %s)", len(alerts), idx, p.mmsi)
                
                # Commit in batches for better performance
                if len(batch) >= batch_size:
                    db.commit()
                    log.debug("Committed batch of %d points", len(batch))
                    
                    # Broadcast updates
                    total_alerts_in_batch = 0
                    for _, alerts_list in batch:
                        if alerts_list:
                            total_alerts_in_batch += len(alerts_list)
                            for a in alerts_list:
                                await broadcast({"kind": "alert", "data": a})
                    
                    if total_alerts_in_batch > 0:
                        log.info("Broadcast %d alert(s) from batch", total_alerts_in_batch)
                    
                    replay_state.processed += len(batch)
                    if batch:
                        replay_state.last_timestamp = batch[-1][0].timestamp.isoformat()
                    
                    # Broadcast progress update
                    await broadcast({"kind": "tick", "processed": replay_state.processed})
                    
                    batch = []  # Clear batch
                    
            except Exception as e:
                log.error("Error processing point %d (MMSI %s): %s", idx, p.mmsi, e, exc_info=True)
                db.rollback()
                errors += 1
                continue

        # Commit remaining batch
        if batch:
            try:
                db.commit()
                log.debug("Committed final batch of %d points", len(batch))
                
                # Broadcast remaining updates
                total_alerts_in_batch = 0
                for _, alerts_list in batch:
                    if alerts_list:
                        total_alerts_in_batch += len(alerts_list)
                        for a in alerts_list:
                            await broadcast({"kind": "alert", "data": a})
                
                if total_alerts_in_batch > 0:
                    log.info("Broadcast %d alert(s) from final batch", total_alerts_in_batch)
                
                replay_state.processed += len(batch)
                if batch:
                    replay_state.last_timestamp = batch[-1][0].timestamp.isoformat()
                
                await broadcast({"kind": "tick", "processed": replay_state.processed})
            except Exception as e:
                log.error("Error committing final batch: %s", e, exc_info=True)
                db.rollback()

        if errors > 0:
            log.warning("Replay completed with %d errors out of %d points", errors, len(pts))
        
        log.info("Processed batch: %d points, %d errors", len(pts), errors)
