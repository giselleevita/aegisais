"""Input validation utilities for API endpoints."""
import re
from typing import Optional
from fastapi import HTTPException, status

# MMSI validation: 9 digits
MMSI_PATTERN = re.compile(r'^\d{9}$')

def validate_mmsi(mmsi: str) -> str:
    """
    Validate MMSI format.
    
    Args:
        mmsi: MMSI string to validate
    
    Returns:
        Validated MMSI
    
    Raises:
        HTTPException: If MMSI is invalid
    """
    if not mmsi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MMSI is required"
        )
    
    if not MMSI_PATTERN.match(mmsi):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MMSI format: {mmsi}. MMSI must be exactly 9 digits."
        )
    
    return mmsi

def validate_alert_type(alert_type: str) -> str:
    """
    Validate alert type.
    
    Args:
        alert_type: Alert type string to validate
    
    Returns:
        Validated alert type
    
    Raises:
        HTTPException: If alert type is invalid
    """
    valid_types = {
        "TELEPORT",
        "TELEPORT_T2",
        "TURN_RATE",
        "TURN_RATE_T2",
        "POSITION_INVALID",
        "ACCELERATION",
        "HEADING_COG_CONSISTENCY",
    }
    
    if alert_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid alert type: {alert_type}. Valid types: {', '.join(sorted(valid_types))}"
        )
    
    return alert_type

def validate_alert_status(status: str) -> str:
    """
    Validate alert status.
    
    Args:
        status: Status string to validate
    
    Returns:
        Validated status
    
    Raises:
        HTTPException: If status is invalid
    """
    valid_statuses = {"new", "reviewed", "resolved", "false_positive"}
    
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status}. Valid statuses: {', '.join(sorted(valid_statuses))}"
        )
    
    return status

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    
    Raises:
        HTTPException: If filename is invalid
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    # Remove path components
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")
    
    # Only allow alphanumeric, dots, dashes, underscores
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename. Only alphanumeric characters, dots, dashes, and underscores are allowed."
        )
    
    return filename
