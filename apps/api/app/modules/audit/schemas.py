from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_id: int
    timestamp: datetime
    user_id: Optional[str] = None
    action: str
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    change_summary: str
    details: Optional[dict[str, Any]] = None
    correlation_id: Optional[str] = None
