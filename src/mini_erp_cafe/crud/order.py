from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from mini_erp_cafe.models import Order, OrderItem, MenuItem
from mini_erp_cafe.schemas.order import OrderCreate, OrderRead, OrderUpdate


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


async def create_order(db: AsyncSession, order_in: OrderCreate) -> OrderRead:
    """
    Создаём заказ и позиции, возвращаем с menu_item_name через Pydantic.
    """
    # создаём заказ
    order = Order(user_id=order_in.user_id)
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # создаём позиции заказа
    for item in order_in.items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(order_item)

    await db.commit()

    # загружаем заказ обратно с items -> menu_item
    stmt = (
        select(Order)
        .where(Order.id == order.id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item)
        )
    )
    result = await db.execute(stmt)
    order = result.scalars().unique().first()

    # возвращаем через Pydantic с menu_item_name
    return OrderRead.from_orm_with_name(order)


VALID_STATUSES = {"open", "in_progress", "done", "cancelled"}

async def update_order(db: AsyncSession, order_id: int, order_in: OrderUpdate) -> OrderRead:
    """
    Обновляет заказ.
    """
    order = await db.get(Order, order_id)
    if not order:
        raise ValueError(f"Order with id={order_id} not found")

    update_data = order_in.dict(exclude_unset=True)

    # Обновление menu_item_id
    if "menu_item_id" in update_data:
        menu_item_id = update_data["menu_item_id"]
        menu_item = await db.get(MenuItem, menu_item_id)
        if not menu_item:
            raise ValueError(f"Menu item with id={menu_item_id} not found")
        order.menu_item_id = menu_item.id

    # Обновление статуса
    if "status" in update_data:
        status = update_data["status"]
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        order.status = status

    # Остальные поля
    for key, value in update_data.items():
        if key in {"menu_item_id", "status"}:
            continue
        setattr(order, key, value)

    await db.commit()

    # Явная загрузка items + menu_item, чтобы не было lazy load
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item)
        )
        .where(Order.id == order.id)
    )
    order = result.scalar_one()

    return OrderRead.from_orm_with_name(order)


async def delete_order(session: AsyncSession, order_id: int) -> bool:
    """
    Удаляет заказ.
    """
    order = await session.get(Order, order_id)
    if not order:
        return False
    await session.delete(order)
    await session.commit()
    return True
