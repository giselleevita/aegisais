"""Add alert status and vessel track history

Revision ID: 002_add_status_track
Revises: 001_initial
Create Date: 2025-01-27 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_status_track'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status and notes to alerts table
    op.add_column('alerts', sa.Column('status', sa.String(), nullable=False, server_default='new'))
    op.add_column('alerts', sa.Column('notes', sa.String(), nullable=True))
    op.create_index('ix_alerts_status', 'alerts', ['status'], unique=False)
    
    # Create vessel_positions table for track history
    op.create_table(
        'vessel_positions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mmsi', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lon', sa.Float(), nullable=False),
        sa.Column('sog', sa.Float(), nullable=True),
        sa.Column('cog', sa.Float(), nullable=True),
        sa.Column('heading', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vessel_positions_mmsi_time', 'vessel_positions', ['mmsi', 'timestamp'], unique=False)
    op.create_index('idx_vessel_positions_timestamp', 'vessel_positions', ['timestamp'], unique=False)
    op.create_index(op.f('ix_vessel_positions_mmsi'), 'vessel_positions', ['mmsi'], unique=False)
    op.create_index(op.f('ix_vessel_positions_timestamp'), 'vessel_positions', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop vessel_positions table
    op.drop_index(op.f('ix_vessel_positions_timestamp'), table_name='vessel_positions')
    op.drop_index(op.f('ix_vessel_positions_mmsi'), table_name='vessel_positions')
    op.drop_index('idx_vessel_positions_timestamp', table_name='vessel_positions')
    op.drop_index('idx_vessel_positions_mmsi_time', table_name='vessel_positions')
    op.drop_table('vessel_positions')
    
    # Remove status and notes from alerts
    op.drop_index('ix_alerts_status', table_name='alerts')
    op.drop_column('alerts', 'notes')
    op.drop_column('alerts', 'status')
