from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from mini_erp_cafe.models import Order, OrderItem, MenuItem


async def get_orders(db: AsyncSession) -> List[Order]:
    """
    Возвращает все заказы, подгружая items и связанные menu_item (чтобы избежать N+1).
    Сортируем по времени создания (сначала новые).
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item)
        )
        .order_by(Order.created_at.desc())
    )
    result = await db.execute(stmt)
    orders = result.scalars().unique().all()
    return orders