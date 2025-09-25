"""fix order_status enum in one go

Revision ID: cd8d3b4d6240
Revises: 94173e165ec5
Create Date: 2025-09-25 21:30:41.856652

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd8d3b4d6240'
down_revision = '94173e165ec5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Создать enum, если его нет
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
                CREATE TYPE order_status AS ENUM ('open', 'in_progress', 'done', 'cancelled');
            END IF;
        END$$;
    """)

    # 2. Снять дефолт с колонки status
    op.alter_column("orders", "status", server_default=None)

    # 3. Сменить тип колонки на enum
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE order_status USING status::text::order_status;")

    # 4. Установить корректный дефолт
    op.alter_column("orders", "status", server_default=sa.text("'open'::order_status"))


def downgrade() -> None:
    # Откат: смена обратно на VARCHAR(20)
    op.alter_column("orders", "status", server_default=None)
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(20) USING status::text;")
    op.alter_column("orders", "status", server_default="'open'")