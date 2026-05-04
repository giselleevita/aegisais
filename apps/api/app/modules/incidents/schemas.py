from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class IncidentOut(BaseModel):
    id: int
    organisation_id: int
    alert_id: int
    asset_id: Optional[int] = None
    created_at: datetime
    status: str
    title: str
    evidence_bundle: dict[str, Any]


class IncidentUpdate(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="Incident status: open, triaged, investigating, resolved, dismissed",
    )
    title: Optional[str] = Field(default=None, description="Incident title")

