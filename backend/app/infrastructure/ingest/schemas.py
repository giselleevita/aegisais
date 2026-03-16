from pydantic import BaseModel, Field

class ReplayStartIn(BaseModel):
    path: str = Field(..., description="Path to CSV file (server-side, supports .csv and .zst compressed)")
    speedup: float = Field(100.0, ge=0.1, description="Replay speed factor")
