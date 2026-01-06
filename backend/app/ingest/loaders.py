import logging
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
import pandas as pd
from pathlib import Path

try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

log = logging.getLogger("aegisais.loaders")

@dataclass(frozen=True)
class AisPoint:
    mmsi: str
    timestamp: datetime
    lat: float
    lon: float
    sog: float | None = None
    cog: float | None = None
    heading: float | None = None

def _parse_timestamp(value) -> datetime:
    """Parse timestamp from various formats: epoch seconds, ISO strings, or pandas datetime."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise ValueError("Missing timestamp")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    # string or pandas datetime
    dt = pd.to_datetime(value, utc=True)
    return dt.to_pydatetime()

def _safe_float(value, default=None):
    """Safely convert value to float, returning default if conversion fails."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to handle common variations.
    Maps common column name variations to standard names:
    - latitude -> lat
    - longitude -> lon
    - base_date_time, datetime, date_time -> timestamp
    """
    # Create a copy to avoid modifying the original
    df = df.copy()
    
    # Normalize: strip whitespace and lowercase
    df.columns = df.columns.str.strip().str.lower()
    
    # Map common variations (only if target doesn't already exist)
    column_mapping = {}
    
    # Map latitude variations (prefer 'lat' if it exists, otherwise map from variations)
    if 'lat' in df.columns:
        # Already have 'lat', no mapping needed
        pass
    else:
        for lat_col in ['latitude', 'y']:
            if lat_col in df.columns:
                column_mapping[lat_col] = 'lat'
                break
    
    # Map longitude variations
    if 'lon' in df.columns:
        # Already have 'lon', no mapping needed
        pass
    else:
        for lon_col in ['longitude', 'lng', 'long', 'x']:
            if lon_col in df.columns:
                column_mapping[lon_col] = 'lon'
                break
    
    # Map timestamp variations
    if 'timestamp' in df.columns:
        # Already have 'timestamp', no mapping needed
        pass
    else:
        for ts_col in ['base_date_time', 'datetime', 'date_time', 'time', 'date']:
            if ts_col in df.columns:
                column_mapping[ts_col] = 'timestamp'
                break
    
    # Apply mapping
    if column_mapping:
        df.rename(columns=column_mapping, inplace=True)
        log.info("Mapped columns: %s", column_mapping)
    
    return df

def _detect_file_format(path_obj: Path) -> tuple[str, str]:
    """
    Detect file format and delimiter.
    Returns (file_type, delimiter) where file_type is 'csv', 'dat', or 'unknown'
    """
    # Check if compressed
    if path_obj.suffix == ".zst":
        # Get the base file extension (e.g., .dat.zst -> .dat)
        base_name = path_obj.stem  # filename without .zst
        base_path = Path(base_name)
        if base_path.suffix == ".dat":
            return ("dat", "\t")  # Default .dat to tab-delimited
        elif base_path.suffix == ".csv" or base_path.suffix == "":
            return ("csv", ",")
    else:
        if path_obj.suffix == ".dat":
            return ("dat", "\t")  # Default .dat to tab-delimited
        elif path_obj.suffix == ".csv":
            return ("csv", ",")
    
    # Default to CSV if unknown
    return ("csv", ",")

def _read_dataframe(path: str, path_obj: Path, delimiter: str = ",") -> pd.DataFrame:
    """Read a dataframe from file, handling compression and format."""
    # Handle .zst compressed files
    if path_obj.suffix == ".zst":
        if not HAS_ZSTD:
            raise ImportError(
                "zstandard library is required to read .zst files. "
                "Install it with: pip install zstandard"
            )
        try:
            log.info("Decompressing .zst file: %s", path)
            with open(path, "rb") as f:
                dctx = zstd.ZstdDecompressor()
                with dctx.stream_reader(f) as reader:
                    decompressed = reader.read()
            # Try to detect delimiter from decompressed content
            if delimiter == "\t":
                # Try tab first, fall back to comma or space
                try:
                    df = pd.read_csv(io.BytesIO(decompressed), sep="\t", engine="python")
                except:
                    try:
                        df = pd.read_csv(io.BytesIO(decompressed), sep=",", engine="python")
                    except:
                        df = pd.read_csv(io.BytesIO(decompressed), sep=r"\s+", engine="python")
            else:
                df = pd.read_csv(io.BytesIO(decompressed), sep=delimiter, engine="python")
        except Exception as e:
            raise ValueError(f"Failed to decompress and read file {path}: {e}") from e
    else:
        # Regular file
        try:
            if delimiter == "\t":
                # Try tab first, fall back to comma or space
                try:
                    df = pd.read_csv(path, sep="\t", engine="python")
                except:
                    try:
                        df = pd.read_csv(path, sep=",", engine="python")
                    except:
                        df = pd.read_csv(path, sep=r"\s+", engine="python")
            else:
                df = pd.read_csv(path, sep=delimiter, engine="python")
        except Exception as e:
            raise ValueError(f"Failed to read file {path}: {e}") from e
    
    return df

def load_csv_points(path: str, chunk_size: int = 10000) -> list[AisPoint]:
    """
    Load AIS points from CSV or DAT file (supports .csv, .dat, and .zst compressed files).
    
    Supports:
    - .csv files (comma-delimited)
    - .dat files (tab or space-delimited)
    - .csv.zst or .dat.zst (compressed files)
    
    For large files, consider using load_csv_points_streaming() instead.
    
    Expected columns:
    - mmsi (required): Vessel MMSI identifier
    - timestamp (required): Timestamp (epoch seconds, ISO string, or datetime)
    - lat (required): Latitude
    - lon (required): Longitude
    - sog (optional): Speed over ground in knots
    - cog (optional): Course over ground in degrees
    - heading (optional): Vessel heading in degrees
    
    Returns sorted list of AisPoint objects (by timestamp).
    Raises ValueError if file is missing or has invalid format.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    
    # Detect file format
    file_type, delimiter = _detect_file_format(path_obj)
    log.info("Detected file type: %s, delimiter: %r", file_type, delimiter)
    
    # Read the dataframe
    df = _read_dataframe(path, path_obj, delimiter)
    
    if df.empty:
        log.warning("Data file %s is empty", path)
        return []

    # Normalize column names (handles variations like latitude->lat, longitude->lon, base_date_time->timestamp)
    df = _normalize_column_names(df)
    
    required = {"mmsi", "timestamp", "lat", "lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Data file missing required columns: {sorted(missing)}. Found columns: {sorted(df.columns)}")

    pts: list[AisPoint] = []
    errors = 0
    
    for idx, r in df.iterrows():
        try:
            # Validate and parse required fields
            mmsi = str(r["mmsi"]).strip()
            if not mmsi:
                log.warning("Row %d: empty MMSI, skipping", idx)
                errors += 1
                continue
            
            timestamp = _parse_timestamp(r["timestamp"])
            lat = _safe_float(r["lat"])
            lon = _safe_float(r["lon"])
            
            if lat is None or lon is None:
                log.warning("Row %d: invalid lat/lon, skipping", idx)
                errors += 1
                continue
            
            # Validate lat/lon ranges
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                log.warning("Row %d: lat/lon out of range (lat=%.4f, lon=%.4f), skipping", idx, lat, lon)
                errors += 1
                continue
            
            # Parse optional fields
            sog = _safe_float(r.get("sog"))
            cog = _safe_float(r.get("cog"))
            heading = _safe_float(r.get("heading"))
            
            # Validate optional fields if present
            if cog is not None and not (0 <= cog <= 360):
                log.warning("Row %d: COG out of range (%.2f), setting to None", idx, cog)
                cog = None
            if heading is not None and not (0 <= heading <= 360):
                log.warning("Row %d: heading out of range (%.2f), setting to None", idx, heading)
                heading = None
            
            pts.append(
                AisPoint(
                    mmsi=mmsi,
                    timestamp=timestamp,
                    lat=lat,
                    lon=lon,
                    sog=sog,
                    cog=cog,
                    heading=heading,
                )
            )
        except Exception as e:
            log.warning("Row %d: error parsing row: %s, skipping", idx, e)
            errors += 1
            continue

    if errors > 0:
        log.warning("Skipped %d invalid rows out of %d total rows", errors, len(df))
    
    if not pts:
        raise ValueError(f"No valid AIS points found in CSV file {path}")

    pts.sort(key=lambda p: p.timestamp)
    log.info("Loaded %d valid AIS points from %s (%s format)", len(pts), path, file_type.upper())
    return pts


def load_csv_points_streaming(path: str, chunk_size: int = 10000) -> Iterator[list[AisPoint]]:
    """
    Stream AIS points from CSV or DAT file in chunks (memory-efficient for large files).
    
    Supports:
    - .csv files (comma-delimited)
    - .dat files (tab or space-delimited)
    - .csv.zst or .dat.zst (compressed files)
    
    This function yields batches of AisPoint objects, allowing processing of
    very large files without loading everything into memory at once.
    
    Args:
        path: Path to CSV, DAT, or .zst file
        chunk_size: Number of rows to process per chunk
        
    Yields:
        Lists of AisPoint objects (batches)
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    
    # Detect file format
    file_type, delimiter = _detect_file_format(path_obj)
    log.info("Streaming file type: %s, delimiter: %r", file_type, delimiter)
    
    # Handle .zst compressed files - need to decompress first
    if path_obj.suffix == ".zst":
        if not HAS_ZSTD:
            raise ImportError(
                "zstandard library is required to read .zst files. "
                "Install it with: pip install zstandard"
            )
        log.info("Decompressing .zst file: %s (this may take a moment for large files)", path)
        # For .zst, we need to decompress first, then stream
        with open(path, "rb") as f:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(f) as reader:
                decompressed = reader.read()
        file_handle = io.BytesIO(decompressed)
    else:
        file_handle = open(path, "rb")
    
    try:
        # Read file in chunks with appropriate delimiter
        if delimiter == "\t":
            # Try tab first, fall back to comma or space
            try:
                chunk_iterator = pd.read_csv(
                    file_handle,
                    chunksize=chunk_size,
                    iterator=True,
                    sep="\t",
                    engine="python"
                )
            except:
                try:
                    file_handle.seek(0)
                    chunk_iterator = pd.read_csv(
                        file_handle,
                        chunksize=chunk_size,
                        iterator=True,
                        sep=",",
                        engine="python"
                    )
                except:
                    file_handle.seek(0)
                    chunk_iterator = pd.read_csv(
                        file_handle,
                        chunksize=chunk_size,
                        iterator=True,
                        sep=r"\s+",
                        engine="python"
                    )
        else:
            chunk_iterator = pd.read_csv(
                file_handle,
                chunksize=chunk_size,
                iterator=True,
                sep=delimiter,
                engine="python"
            )
        
        total_processed = 0
        total_errors = 0
        
        for chunk_idx, df_chunk in enumerate(chunk_iterator):
            if df_chunk.empty:
                continue
            
            # Normalize column names (handles variations like latitude->lat, longitude->lon, base_date_time->timestamp)
            df_chunk = _normalize_column_names(df_chunk)
            
            # Validate required columns on first chunk
            if chunk_idx == 0:
                required = {"mmsi", "timestamp", "lat", "lon"}
                missing = required - set(df_chunk.columns)
                if missing:
                    raise ValueError(f"Data file missing required columns: {sorted(missing)}. Found columns: {sorted(df_chunk.columns)}")
            
            pts: list[AisPoint] = []
            errors = 0
            
            for idx, r in df_chunk.iterrows():
                try:
                    mmsi = str(r["mmsi"]).strip()
                    if not mmsi:
                        errors += 1
                        continue
                    
                    timestamp = _parse_timestamp(r["timestamp"])
                    lat = _safe_float(r["lat"])
                    lon = _safe_float(r["lon"])
                    
                    if lat is None or lon is None:
                        errors += 1
                        continue
                    
                    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                        errors += 1
                        continue
                    
                    sog = _safe_float(r.get("sog"))
                    cog = _safe_float(r.get("cog"))
                    heading = _safe_float(r.get("heading"))
                    
                    if cog is not None and not (0 <= cog <= 360):
                        cog = None
                    if heading is not None and not (0 <= heading <= 360):
                        heading = None
                    
                    pts.append(
                        AisPoint(
                            mmsi=mmsi,
                            timestamp=timestamp,
                            lat=lat,
                            lon=lon,
                            sog=sog,
                            cog=cog,
                            heading=heading,
                        )
                    )
                except Exception:
                    errors += 1
                    continue
            
            total_processed += len(pts)
            total_errors += errors
            
            if pts:
                # Sort chunk by timestamp
                pts.sort(key=lambda p: p.timestamp)
                yield pts
            
            if (chunk_idx + 1) % 10 == 0:
                log.info("Processed %d chunks, %d valid points, %d errors", 
                        chunk_idx + 1, total_processed, total_errors)
        
        log.info("Finished streaming: %d total valid points, %d errors", 
                total_processed, total_errors)
    
    finally:
        if path_obj.suffix != ".zst":
            file_handle.close()
