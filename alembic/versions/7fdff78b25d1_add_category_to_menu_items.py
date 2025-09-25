"""add category to menu_items

Revision ID: 7fdff78b25d1
Revises: eaa97d66f228
Create Date: 2025-09-25 22:16:06.174262

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7fdff78b25d1'
down_revision: Union[str, Sequence[str], None] = 'eaa97d66f228'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('menu_items', sa.Column('category', sa.String(length=50), nullable=True))

def downgrade():
    op.drop_column('menu_items', 'category')