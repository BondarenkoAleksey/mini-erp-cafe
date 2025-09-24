"""add order status and closed_at

Revision ID: 94173e165ec5
Revises: initial_models
Create Date: 2025-09-24 21:19:01.139586
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94173e165ec5'
down_revision: Union[str, Sequence[str], None] = 'initial_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add status and closed_at to orders."""
    op.add_column('orders', sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('orders', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema: remove status and closed_at from orders."""
    op.drop_column('orders', 'closed_at')
    op.drop_column('orders', 'status')
