"""Merge parallel migration branches (015_subsea_assets_and_iot_core and 015_vessel_org_scoping)

Revision ID: 017_merge_iot_vessel_org_heads
Revises: 015_subsea_assets_and_iot_core, 015_vessel_org_scoping
Create Date: 2026-05-03

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "017_merge_iot_vessel_org_heads"
down_revision: Union[str, Sequence[str], None] = ("015_subsea_assets_and_iot_core", "015_vessel_org_scoping")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
