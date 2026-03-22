from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class GenerateReportRequest(BaseModel):
    start_time: datetime = Field(description="Inclusive lower bound on alert timestamp (ISO-8601)")
    end_time: datetime = Field(description="Inclusive upper bound on alert timestamp (ISO-8601)")
    mmsi: Optional[list[str]] = Field(
        default=None,
        description="Optional list of MMSIs to include (9-digit strings)",
    )
    zone_substring: Optional[str] = Field(
        default=None,
        description="Optional case-insensitive substring filter on alert summary / evidence JSON text",
    )

    @model_validator(mode="after")
    def end_after_start(self) -> "GenerateReportRequest":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be >= start_time")
        return self

    @field_validator("mmsi")
    @classmethod
    def mmsi_list_size(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None and len(v) > 100:
            raise ValueError("At most 100 MMSI values allowed")
        return v
