"""itdae schema

Revision ID: 003
Revises: 002_add_status_track
Create Date: 2026-03-14 12:00:00.000000

Portable DDL: works on SQLite (local dev) and PostgreSQL.
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
    op.create_table(
        'itdae_positions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mmsi', sa.String(9), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lon', sa.Float(), nullable=False),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('course', sa.Float(), nullable=True),
        sa.Column('heading', sa.Float(), nullable=True),
        sa.Column('nav_status', sa.SmallInteger(), nullable=True),
        sa.Column('msg_type', sa.SmallInteger(), nullable=True),
        sa.Column('raw_json', sa.JSON(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('itdae_pos_mmsi_ts', 'itdae_positions', ['mmsi', 'timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index('itdae_pos_mmsi_ts', table_name='itdae_positions')
    op.drop_table('itdae_positions')
