"""itdae geofence zones table

Revision ID: 004
Revises: 003
Create Date: 2026-03-14 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'itdae_geofence_zones',
        sa.Column('id', sa.String(64), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('risk_level', sa.String(16), nullable=False),   # critical | high | medium
        sa.Column('polygon_geojson', sa.JSON, nullable=False),    # GeoJSON polygon coords
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_itdae_geofence_risk', 'itdae_geofence_zones', ['risk_level'])


def downgrade() -> None:
    op.drop_index('idx_itdae_geofence_risk', table_name='itdae_geofence_zones')
    op.drop_table('itdae_geofence_zones')
