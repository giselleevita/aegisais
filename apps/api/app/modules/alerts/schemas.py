from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional

class AlertOut(BaseModel):
    id: int
    timestamp: datetime
    mmsi: str
    asset_id: Optional[int] = None
    source_device_id: Optional[int] = None
    type: str
    severity: int
    summary: str
    evidence: Any
    evidence_hash: Optional[str] = None  # BL-009: SHA-256 fingerprint of slim evidence
    status: str = "new"
    notes: Optional[str] = None

class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="Alert status: new, reviewed, resolved, false_positive")
    notes: Optional[str] = Field(None, description="Optional notes/comments")
