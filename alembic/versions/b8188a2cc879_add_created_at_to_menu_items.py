"""add created_at to menu_items

Revision ID: b8188a2cc879
Revises: 7fdff78b25d1
Create Date: 2025-09-25 22:21:33.896500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8188a2cc879'
down_revision: Union[str, Sequence[str], None] = '7fdff78b25d1'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('menu_items', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

def downgrade():
    op.drop_column('menu_items', 'created_at')
