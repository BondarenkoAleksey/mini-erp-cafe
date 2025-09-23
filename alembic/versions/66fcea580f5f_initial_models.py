"""initial models"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "initial_models"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_available", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("menu_item_id", sa.Integer, sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("menu_items")
    op.drop_table("users")
