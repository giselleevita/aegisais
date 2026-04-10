from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.iot.schemas import EdgeBatchCreate, EdgeBatchOut
from app.modules.iot.service import create_edge_batch


def queue_edge_batch(db: Session, device_id: int, batch: EdgeBatchCreate, *, actor: User) -> EdgeBatchOut:
    return create_edge_batch(db, device_id, batch, actor=actor)