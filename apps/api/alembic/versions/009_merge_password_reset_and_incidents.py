"""merge password_reset_tokens branch with incidents branch

Revision ID: 009_merge_008_pw_incidents
Revises: 008_password_reset_tokens, e7a1c9d2f301
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op

revision: str = "009_merge_008_pw_incidents"
down_revision: Union[str, tuple[str, ...], None] = (
    "008_password_reset_tokens",
    "e7a1c9d2f301",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
