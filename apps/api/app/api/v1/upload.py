from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.infrastructure.ingest import upload_validation
from app.middleware.rate_limit import upload_file_rate_limit
from app.modules.audit.services import AuditService
from app.modules.auth.dependencies import require_admin, require_viewer_or_above

log = structlog.get_logger("aegisais.upload")

router = APIRouter()

BACKEND_DIR = Path(__file__).parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_MB = 5000
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

log.info("Upload directory configured: %s", DATA_RAW_DIR.absolute())
log.info("Directory exists: %s", DATA_RAW_DIR.exists())


def _delimiter_for_upload(filename: str) -> str:
    p = Path(filename.lower())
    if p.suffix == ".zst":
        inner = Path(p.stem).suffix
        return "\t" if inner == ".dat" else ","
    return "\t" if p.suffix == ".dat" else ","


@router.post("/upload")
async def upload_file(
    _: Annotated[None, Depends(upload_file_rate_limit)],
    file: UploadFile = File(...),
    admin: Any = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Upload a file to the data/raw directory.
    Supports .csv, .dat, .csv.zst, and .dat.zst files.

    Security:
    - Validates file extension
    - Enforces file size limits
    - Sanitizes filename to prevent path traversal
    - CSV/DAT header validation (first 4KB) and zstd decompressed size bound
    - Optional ClamAV malware scanning (SCAN_UPLOADS_FOR_MALWARE=true)
    """
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    if not safe_filename or safe_filename != filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename. Only alphanumeric characters, dots, dashes, and underscores are allowed.",
        )

    file_ext = Path(filename).suffix.lower()
    file_stem_ext = Path(filename).stem.lower()

    if file_ext == ".zst":
        base_ext = Path(file_stem_ext).suffix.lower()
        if base_ext not in {".csv", ".dat"}:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: .csv, .dat, .csv.zst, .dat.zst",
            )
    elif file_ext not in {".csv", ".dat"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: .csv, .dat, .csv.zst, .dat.zst",
            )

    if hasattr(file, "size") and file.size:
        if file.size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB} MB",
            )

    file_path = DATA_RAW_DIR / safe_filename

    try:
        resolved_path = file_path.resolve()
        if not str(resolved_path).startswith(str(DATA_RAW_DIR.resolve())):
            raise HTTPException(
                status_code=400,
                detail="Invalid file path - path traversal detected",
            )
    except Exception as e:
        log.error("path_resolution_error", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid file path")

    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    log.info("saving_file", path=str(file_path.absolute()))

    try:
        total_size = 0
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE_BYTES:
                    if file_path.exists():
                        file_path.unlink()
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB} MB",
                    )
                buffer.write(chunk)

        if not file_path.exists():
            raise Exception(f"File was not created at {file_path.absolute()}")

        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # --- AV scanning pipeline (Issue #2) ---
        if settings.scan_uploads_for_malware:
            from app.services.av_scanner import scan_file

            scan_result = scan_file(file_path)
            if scan_result.infected:
                if file_path.exists():
                    file_path.unlink()
                if settings.enable_audit_logging:
                    AuditService.log_event(
                        db,
                        action="upload.file.rejected.malware",
                        change_summary=f"Rejected infected upload: {safe_filename} (virus={scan_result.virus_name})",
                        organisation_id=admin.organisation_id,
                        user_id=admin.username,
                        resource_type="upload",
                        resource_id=safe_filename,
                        details={
                            "filename": safe_filename,
                            "virus": scan_result.virus_name,
                            "user": admin.username,
                        },
                    )
                    db.commit()
                raise HTTPException(
                    status_code=422,
                    detail=f"File rejected: malware detected ({scan_result.virus_name})",
                )
            log.info("av_scan_passed", filename=safe_filename)
        # --- end AV scanning ---

        max_dec = int(settings.max_decompressed_size_gb * (1024**3))
        name_lower = safe_filename.lower()
        is_zst = name_lower.endswith(".zst")
        delim = _delimiter_for_upload(safe_filename)

        try:
            if is_zst:
                upload_validation.validate_zst_decompressed_bound(file_path, max_dec)
                upload_validation.validate_zst_header_row(file_path, delimiter=delim)
            else:
                upload_validation.validate_uncompressed_upload(file_path, delimiter=delim)
        except ValueError as ve:
            msg = str(ve)
            if file_path.exists():
                file_path.unlink()
            code = 413 if "exceeds configured limit" in msg else 400
            raise HTTPException(status_code=code, detail=msg) from ve

        if settings.enable_audit_logging:
            AuditService.log_event(
                db,
                action="upload.file.success",
                change_summary=f"Uploaded {safe_filename} ({file_size} bytes)",
                organisation_id=admin.organisation_id,
                user_id=admin.username,
                resource_type="upload",
                resource_id=safe_filename,
                details={
                    "filename": safe_filename,
                    "size_bytes": file_size,
                    "user": admin.username,
                },
            )
            db.commit()

        log.info("upload_success", filename=safe_filename, size_mb=round(file_size_mb, 2))

        return JSONResponse(
            {
                "status": "success",
                "filename": safe_filename,
                "path": f"data/raw/{safe_filename}",
                "size_bytes": file_size,
                "size_mb": round(file_size_mb, 2),
                "absolute_path": str(file_path.absolute()),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error("upload_failed", filename=filename, error=str(e), exc_info=True)
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/upload/list")
async def list_uploaded_files(_viewer: Any = Depends(require_viewer_or_above)):
    """List all files in the data/raw directory."""
    try:
        files: list[dict[str, Any]] = []
        for file_path in DATA_RAW_DIR.iterdir():
            if file_path.is_file():
                file_size = file_path.stat().st_size
                files.append(
                    {
                        "filename": file_path.name,
                        "path": f"data/raw/{file_path.name}",
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                    }
                )
        files.sort(key=lambda x: str(x["filename"]))
        return {"files": files}
    except Exception as e:
        log.error("list_files_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")
