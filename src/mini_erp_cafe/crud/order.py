from typing import List, Optional
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


async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[Order]:
    """
    Простая рабочая реализация: выбираем заказ по id и eagerly load items -> menu_item
    Это предотвращает lazy-load при сериализации (и ошибку MissingGreenlet).
    """
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item)
        )
    )
    result = await db.execute(stmt)
    order = result.scalars().unique().first()
    return order
