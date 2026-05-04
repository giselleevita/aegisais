from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.iot.schemas import EdgeBatchReplayOut
from app.modules.iot.service import replay_edge_batch


def replay_queued_edge_batch(db: Session, batch_id: int, *, actor: User) -> EdgeBatchReplayOut:
    return replay_edge_batch(db, batch_id, actor=actor)