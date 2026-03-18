from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional

class AlertOut(BaseModel):
    id: int
    timestamp: datetime
    mmsi: str
    type: str
    severity: int
    summary: str
    evidence: Any
    status: str = "new"
    notes: Optional[str] = None

class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="Alert status: new, reviewed, resolved, false_positive")
    notes: Optional[str] = Field(None, description="Optional notes/comments")
