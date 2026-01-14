"""Type definitions for detection rules."""
from typing import TypedDict, Optional
from datetime import datetime

class AlertResult(TypedDict, total=False):
    """Result structure returned by detection rules."""
    type: str
    severity: int
    summary: str
    evidence: dict
