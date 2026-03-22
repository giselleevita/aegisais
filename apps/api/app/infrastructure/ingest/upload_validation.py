"""Header validation for uploaded AIS CSV/DAT files (aligned with loaders.py column rules)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import zstandard as zstd

# Match loaders._normalize_column_names + required set in load_csv_points
_REQUIRED = frozenset({"mmsi", "timestamp", "lat", "lon"})


def _canonical_column_set(names: list[str]) -> set[str]:
    cols = {n.strip().lower() for n in names if n.strip()}
    if "lat" not in cols:
        for alt in ("latitude", "y"):
            if alt in cols:
                cols.add("lat")
                break
    if "lon" not in cols:
        for alt in ("longitude", "lng", "long", "x"):
            if alt in cols:
                cols.add("lon")
                break
    if "timestamp" not in cols:
        for alt in ("base_date_time", "datetime", "date_time", "time", "date"):
            if alt in cols:
                cols.add("timestamp")
                break
    return cols


def validate_header_row(names: list[str]) -> None:
    """Raise ValueError if required AIS columns are missing after alias mapping."""
    canon = _canonical_column_set(names)
    missing = sorted(_REQUIRED - canon)
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. Found (after mapping): {sorted(canon)}"
        )


def _first_csv_row(sample: bytes, delimiter: str) -> list[str]:
    text = sample.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        row = next(reader)
    except StopIteration as e:
        raise ValueError("Empty or unreadable file") from e
    return [c.strip() for c in row]


def validate_uncompressed_upload(path: Path, *, delimiter: str, peek_bytes: int = 4096) -> None:
    """Read the first chunk and validate the header row."""
    with open(path, "rb") as f:
        sample = f.read(peek_bytes)
    if not sample.strip():
        raise ValueError("Empty file")
    header = _first_csv_row(sample, delimiter)
    validate_header_row(header)


def validate_zst_decompressed_bound(path: Path, max_decompressed_bytes: int) -> None:
    """Reject .zst if declared decompressed size is unknown or exceeds max."""
    with open(path, "rb") as f:
        chunk = f.read(1024 * 1024)
    if len(chunk) < 4:
        raise ValueError("Compressed file too small to be a valid zstd frame")
    try:
        size = zstd.frame_content_size(chunk)
    except zstd.ZstdError as e:
        raise ValueError(f"Invalid zstd frame: {e}") from e
    if size in (zstd.CONTENTSIZE_UNKNOWN, zstd.CONTENTSIZE_ERROR):
        raise ValueError(
            "Cannot determine decompressed size for this zstd file; refuse upload for safety"
        )
    if size > max_decompressed_bytes:
        raise ValueError(
            f"Decompressed size ({size} bytes) exceeds configured limit ({max_decompressed_bytes} bytes)"
        )


def validate_zst_header_row(path: Path, *, delimiter: str) -> None:
    """Decompress enough of a .zst file to read the header row."""
    dctx = zstd.ZstdDecompressor()
    with open(path, "rb") as f, dctx.stream_reader(f) as reader:
        sample = reader.read(65536)
    if not sample.strip():
        raise ValueError("Empty decompressed content")
    header = _first_csv_row(sample, delimiter)
    validate_header_row(header)
