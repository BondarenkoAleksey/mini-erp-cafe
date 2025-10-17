from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mini_erp_cafe.models import Order, OrderItem, MenuItem
from mini_erp_cafe.schemas.order import OrderCreate, OrderRead, OrderUpdate


async def get_orders(
    db: AsyncSession,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Order]:
    """
    Возвращает список заказов с опциональной фильтрацией по статусу и дате.
    Подгружаем items, menu_item и user.
    Сортируем по created_at (новые первыми).
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.user),
        )
        .order_by(Order.created_at.desc())
    )

    if status:
        stmt = stmt.where(Order.status == status)
    if date_from:
        stmt = stmt.where(Order.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Order.created_at <= date_to)
    if limit:
        stmt = stmt.limit(limit)
    if offset:
        stmt = stmt.offset(offset)

    result = await db.execute(stmt)
    return result.scalars().unique().all()


async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[Order]:
    """
    Возвращает заказ по ID с подгруженными items, menu_item и user.
    Предотвращает MissingGreenlet при сериализации.
    """
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.user),
        )
    )
    result = await db.execute(stmt)
    order = result.scalars().unique().first()
    return order


async def get_orders_summary(
    db,
    group_by: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """
    Возвращает агрегированную статистику по заказам:
    - количество заказов
    - общую сумму (total_revenue)
    - средний чек (average_check)
    Поддерживает группировку (по статусу, пользователю или дате)
    и итоговую строку "total" для всех групп.
    """

    # Базовый запрос с join
    base_stmt = (
        select(
            func.count(Order.id).label("count_orders"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue")
        )
        .join(Order.items)
        .join(OrderItem.menu_item)
        .where(OrderItem.menu_item_id.isnot(None))
    )

    # Фильтрация по дате
    if date_from:
        base_stmt = base_stmt.where(Order.created_at >= date_from)
    if date_to:
        base_stmt = base_stmt.where(Order.created_at <= date_to)

    # Поддерживаемые поля для группировки
    group_map = {
        "status": Order.status,
        "user_id": Order.user_id,
        "menu_item_id": OrderItem.menu_item_id,
        "date": func.date(Order.created_at)
    }

    if group_by and group_by in group_map:
        base_stmt = base_stmt.add_columns(group_map[group_by].label("group"))
        base_stmt = base_stmt.group_by(group_map[group_by])
        result = await db.execute(base_stmt)
        rows = result.all()

        grouped = []
        total_orders = 0
        total_revenue_sum = Decimal(0)

        for row in rows:
            total_revenue = Decimal(row.total_revenue or 0)
            average_check = total_revenue / row.count_orders if row.count_orders > 0 else Decimal(0)
            grouped.append({
                "group": str(row.group),
                "count_orders": row.count_orders,
                "total_revenue": total_revenue,
                "average_check": round(average_check, 2)
            })

            total_orders += row.count_orders
            total_revenue_sum += total_revenue

        # Добавляем итоговую строку
        total_avg = total_revenue_sum / total_orders if total_orders > 0 else Decimal(0)
        total_row = {
            "group": "total",
            "count_orders": total_orders,
            "total_revenue": total_revenue_sum,
            "average_check": round(total_avg, 2)
        }

        return {"group_by": group_by, "results": grouped, "total": total_row}

    # Без группировки — просто общая статистика
    result = await db.execute(base_stmt)
    row = result.first()
    total_revenue = Decimal(row.total_revenue or 0)
    average_check = total_revenue / row.count_orders if row.count_orders > 0 else Decimal(0)

    return {
        "count_orders": row.count_orders,
        "total_revenue": total_revenue,
        "average_check": round(average_check, 2)
    }


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


async def get_orders_stats(
    db: AsyncSession,
    interval: str = "day",
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[dict]:
    """
    Возвращает агрегированную статистику заказов:
    - по дням, неделям или месяцам
    - добавлено поле avg_order_value (средний чек)
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=7)

    trunc_unit = {
        "day": "day",
        "week": "week",
        "month": "month"
    }[interval]

    stmt = (
        select(
            cast(func.date_trunc(trunc_unit, Order.created_at), Date).label("period"),
            func.count(Order.id).label("count_orders"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
            (
                func.sum(OrderItem.price * OrderItem.quantity) / func.nullif(func.count(Order.id), 0)
            ).label("avg_order_value"),
        )
        .join(Order.items)
        .where(Order.created_at.between(date_from, date_to))
        .group_by("period")
        .order_by("period")
    )

    result = await db.execute(stmt)
    return [
        {
            "period": row.period,
            "count_orders": row.count_orders,
            "total_revenue": float(row.total_revenue or 0),
            "avg_order_value": float(row.avg_order_value or 0),
        }
        for row in result.all()
    ]