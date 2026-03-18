"""itdae schema

Revision ID: 003
Revises: 002_add_status_track
Create Date: 2026-03-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002_add_status_track'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE itdae_positions (
        id           SERIAL PRIMARY KEY,
        mmsi         VARCHAR(9) NOT NULL,
        timestamp    TIMESTAMPTZ NOT NULL,
        lat          DOUBLE PRECISION NOT NULL,
        lon          DOUBLE PRECISION NOT NULL,
        speed        DOUBLE PRECISION,
        course       DOUBLE PRECISION,
        heading      DOUBLE PRECISION,
        nav_status   SMALLINT,
        msg_type     SMALLINT,
        raw_json     JSONB,
        created_at   TIMESTAMPTZ DEFAULT NOW()
    );
    """)
    op.execute("""
    CREATE INDEX itdae_pos_mmsi_ts ON itdae_positions (mmsi, timestamp);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE itdae_positions CASCADE;")
