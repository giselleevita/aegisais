"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create vessels_latest table
    op.create_table(
        'vessels_latest',
        sa.Column('mmsi', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lon', sa.Float(), nullable=False),
        sa.Column('sog', sa.Float(), nullable=True),
        sa.Column('cog', sa.Float(), nullable=True),
        sa.Column('heading', sa.Float(), nullable=True),
        sa.Column('last_alert_severity', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('mmsi')
    )
    op.create_index('idx_vessels_timestamp', 'vessels_latest', ['timestamp'], unique=False)
    op.create_index('idx_vessels_severity', 'vessels_latest', ['last_alert_severity'], unique=False)

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('mmsi', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('severity', sa.Integer(), nullable=False),
        sa.Column('summary', sa.String(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Single column indexes (created automatically by SQLAlchemy from model definitions)
    op.create_index(op.f('ix_alerts_mmsi'), 'alerts', ['mmsi'], unique=False)
    op.create_index(op.f('ix_alerts_type'), 'alerts', ['type'], unique=False)
    op.create_index(op.f('ix_alerts_severity'), 'alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_alerts_timestamp'), 'alerts', ['timestamp'], unique=False)
    
    # Composite indexes for common query patterns
    op.create_index('idx_alerts_mmsi_time', 'alerts', ['mmsi', 'timestamp'], unique=False)
    op.create_index('idx_alerts_type_time', 'alerts', ['type', 'timestamp'], unique=False)
    op.create_index('idx_alerts_severity_time', 'alerts', ['severity', 'timestamp'], unique=False)

    # Create alert_cooldowns table
    op.create_table(
        'alert_cooldowns',
        sa.Column('mmsi', sa.String(), nullable=False),
        sa.Column('rule_type', sa.String(), nullable=False),
        sa.Column('last_alert_timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('mmsi', 'rule_type')
    )
    op.create_index('idx_cooldown_mmsi_type', 'alert_cooldowns', ['mmsi', 'rule_type'], unique=False)
    op.create_index('idx_cooldown_timestamp', 'alert_cooldowns', ['last_alert_timestamp'], unique=False)
    op.create_index(op.f('ix_alert_cooldowns_last_alert_timestamp'), 'alert_cooldowns', ['last_alert_timestamp'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_alert_cooldowns_last_alert_timestamp'), table_name='alert_cooldowns')
    op.drop_index('idx_cooldown_timestamp', table_name='alert_cooldowns')
    op.drop_index('idx_cooldown_mmsi_type', table_name='alert_cooldowns')
    
    op.drop_index('idx_alerts_severity_time', table_name='alerts')
    op.drop_index('idx_alerts_type_time', table_name='alerts')
    op.drop_index('idx_alerts_mmsi_time', table_name='alerts')
    op.drop_index(op.f('ix_alerts_timestamp'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_severity'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_type'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_mmsi'), table_name='alerts')
    
    op.drop_index('idx_vessels_severity', table_name='vessels_latest')
    op.drop_index('idx_vessels_timestamp', table_name='vessels_latest')

    # Drop tables
    op.drop_table('alert_cooldowns')
    op.drop_table('alerts')
    op.drop_table('vessels_latest')
