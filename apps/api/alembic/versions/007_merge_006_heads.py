"""merge parallel 006 branches (refresh_tokens, watchlist, itdae geofence meta)

Revision ID: 007_merge_006_heads
Revises: 006_refresh_tokens, 006_watchlist, 006_itdae_geofence_meta
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "007_merge_006_heads"
down_revision: Union[str, tuple[str, ...], None] = (
    "006_refresh_tokens",
    "006_watchlist",
    "006_itdae_geofence_meta",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
