import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import logging
import os

log = logging.getLogger("aegisais.upload")

router = APIRouter()

# Get the project root directory
# __file__ is at: backend/app/api/routes_upload.py
# So we go: app/api -> app -> backend -> project_root
BACKEND_DIR = Path(__file__).parent.parent.parent  # backend/app/api -> backend
PROJECT_ROOT = BACKEND_DIR.parent  # backend -> project root (aegisais)
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

# Log the absolute path for debugging
log.info("Upload directory configured: %s", DATA_RAW_DIR.absolute())
log.info("Directory exists: %s", DATA_RAW_DIR.exists())

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the data/raw directory.
    Supports .csv, .dat, .csv.zst, and .dat.zst files.
    """
    # Validate file extension
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check if file extension is supported
    allowed_extensions = {".csv", ".dat", ".zst", ".csv.zst", ".dat.zst"}
    file_ext = Path(filename).suffix.lower()
    file_stem_ext = Path(filename).stem.lower()
    
    # Check for .zst files
    if file_ext == ".zst":
        base_ext = Path(file_stem_ext).suffix.lower()
        if base_ext not in {".csv", ".dat"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: .csv, .dat, .csv.zst, .dat.zst"
            )
    elif file_ext not in {".csv", ".dat"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: .csv, .dat, .csv.zst, .dat.zst"
        )
    
    # Save file to data/raw directory
    file_path = DATA_RAW_DIR / filename
    
    # Ensure directory exists
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    log.info("Saving file to: %s", file_path.absolute())
    
    try:
        # Write file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Verify file was written
        if not file_path.exists():
            raise Exception(f"File was not created at {file_path.absolute()}")
        
        # Get file size
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        log.info("Successfully uploaded file: %s (%.2f MB) to %s", filename, file_size_mb, file_path.absolute())
        
        return JSONResponse({
            "status": "success",
            "filename": filename,
            "path": f"data/raw/{filename}",
            "size_bytes": file_size,
            "size_mb": round(file_size_mb, 2),
            "absolute_path": str(file_path.absolute()),
        })
    except Exception as e:
        log.error("Error uploading file %s to %s: %s", filename, file_path.absolute(), e, exc_info=True)
        # Clean up partial file if it exists
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@router.get("/upload/list")
async def list_uploaded_files():
    """List all files in the data/raw directory."""
    try:
        files = []
        for file_path in DATA_RAW_DIR.iterdir():
            if file_path.is_file():
                file_size = file_path.stat().st_size
                files.append({
                    "filename": file_path.name,
                    "path": f"data/raw/{file_path.name}",
                    "size_bytes": file_size,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                })
        
        # Sort by filename
        files.sort(key=lambda x: x["filename"])
        return {"files": files}
    except Exception as e:
        log.error("Error listing files: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

