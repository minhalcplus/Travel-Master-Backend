"""add_super_admin_to_role_enum

Revision ID: 5323098e3d99
Revises: 2c849f287428
Create Date: 2025-12-15 14:37:31.456830

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5323098e3d99'
down_revision: Union[str, Sequence[str], None] = '2c849f287428'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE role ADD VALUE 'super_admin'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
