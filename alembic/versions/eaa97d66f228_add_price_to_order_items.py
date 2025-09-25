"""add price to order_items

Revision ID: eaa97d66f228
Revises: cd8d3b4d6240
Create Date: 2025-09-25 22:07:10.984979

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eaa97d66f228'
down_revision = 'cd8d3b4d6240'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # добавляем колонку price
    op.add_column(
        'order_items',
        sa.Column('price', sa.Numeric(10, 2), nullable=False, server_default='0')
    )

def downgrade() -> None:
    # откат - удаляем колонку
    op.drop_column('order_items', 'price')
