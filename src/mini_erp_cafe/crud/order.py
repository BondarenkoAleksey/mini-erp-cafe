from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select, func, cast, Date, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mini_erp_cafe.models import Order, OrderItem, MenuItem, User
from mini_erp_cafe.schemas.order import OrderCreate, OrderRead, OrderUpdate
from typing_extensions import Dict


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


async def get_top_menu_items(
    db: AsyncSession,
    limit: int = 5
) -> list[dict]:
    """
    Возвращает топ самых популярных блюд по количеству заказанных позиций.
    """
    stmt = (
        select(
            MenuItem.name.label("menu_item_name"),
            func.sum(OrderItem.quantity).label("total_sold"),
        )
        .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
        .group_by(MenuItem.name)
        .order_by(desc("total_sold"))
        .limit(limit)
    )

    result = await db.execute(stmt)
    return [
        {
            "menu_item_name": row.menu_item_name,
            "total_sold": int(row.total_sold or 0),
        }
        for row in result.all()
    ]


async def get_top_users_stats(
    db: AsyncSession,
    limit: int = 10,
    metric: str = "count",
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[dict]:
    """
    Возвращает топ пользователей по заказам или сумме за период.
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    # Базовый запрос с join
    stmt = (
        select(
            User.id.label("user_id"),
            User.name.label("user_name"),
            func.count(Order.id).label("count_orders"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
        )
        .join(Order, Order.user_id == User.id)
        .join(Order.items)
        .where(Order.created_at.between(date_from, date_to))
        .group_by(User.id, User.name)
    )

    # Сортировка по выбранной метрике
    if metric == "revenue":
        stmt = stmt.order_by(desc(func.sum(OrderItem.price * OrderItem.quantity)))
    else:
        stmt = stmt.order_by(desc(func.count(Order.id)))

    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    return [
        {
            "user_id": row.user_id,
            "user_name": row.user_name,
            "count_orders": int(row.count_orders or 0),
            "total_revenue": float(row.total_revenue or 0),
        }
        for row in result.all()
    ]


async def get_orders_summary_stats(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    """
    Возвращает сводную статистику по заказам с опциональной фильтрацией по дате.
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        # по умолчанию за последние 30 дней
        date_from = date_to - timedelta(days=30)

    stmt = (
        select(
            func.count(Order.id).label("count_orders"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
            func.count(func.distinct(Order.user_id)).label("unique_users"),
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(Order.created_at.between(date_from, date_to))
    )

    result = await db.execute(stmt)
    row = result.first()

    count_orders = row.count_orders or 0
    total_revenue = float(row.total_revenue or 0)
    unique_users = row.unique_users or 0
    avg_check = round(total_revenue / count_orders, 2) if count_orders else 0.0

    return {
        "date_from": date_from.date().isoformat(),
        "date_to": date_to.date().isoformat(),
        "count_orders": count_orders,
        "total_revenue": total_revenue,
        "avg_check": avg_check,
        "unique_users": unique_users,
    }


async def get_orders_stats_by_user(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[Dict]:
    """
    Возвращает статистику заказов по каждому пользователю.
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    stmt = (
        select(
            Order.user_id,
            func.count(Order.id).label("count_orders"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(Order.created_at.between(date_from, date_to))
        .group_by(Order.user_id)
        .order_by(func.sum(OrderItem.price * OrderItem.quantity).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    stats = []
    for row in rows:
        total_revenue = float(row.total_revenue or 0)
        count_orders = row.count_orders or 0
        avg_check = round(total_revenue / count_orders, 2) if count_orders else 0.0
        stats.append(
            {
                "user_id": row.user_id,
                "count_orders": count_orders,
                "total_revenue": total_revenue,
                "avg_check": avg_check,
            }
        )

    return stats


async def get_orders_stats_by_item(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[Dict]:
    """
    Возвращает статистику продаж по блюдам (позициям меню).
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    stmt = (
        select(
            OrderItem.menu_item_id,
            MenuItem.name.label("menu_item_name"),
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
            func.avg(OrderItem.price).label("avg_price"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
        .where(Order.created_at.between(date_from, date_to))
        .group_by(OrderItem.menu_item_id, MenuItem.name)
        .order_by(func.sum(OrderItem.price * OrderItem.quantity).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "menu_item_id": row.menu_item_id,
            "menu_item_name": row.menu_item_name,
            "total_quantity": int(row.total_quantity or 0),
            "total_revenue": float(row.total_revenue or 0),
            "avg_price": float(round(row.avg_price or 0, 2)),
        }
        for row in rows
    ]


async def get_orders_stats_by_day_and_user(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[Dict]:
    """
    Возвращает статистику заказов по дням и пользователям.
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=7)

    stmt = (
        select(
            cast(func.date_trunc("day", Order.created_at), Date).label("date"),
            Order.user_id,
            User.name.label("user_name"),
            func.count(Order.id).label("count_orders"),
        )
        .join(User, User.id == Order.user_id)
        .where(Order.created_at.between(date_from, date_to))
        .group_by("date", Order.user_id, User.name)
        .order_by("date", Order.user_id)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "date": row.date,
            "user_id": row.user_id,
            "user_name": row.user_name,
            "count_orders": int(row.count_orders or 0),
        }
        for row in rows
    ]


async def get_orders_weekly_stats(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[dict]:
    """
    Возвращает статистику заказов по неделям:
    количество заказов и общая сумма.
    По умолчанию за последние 8 недель.
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(weeks=8)

    stmt = (
        select(
            func.date_trunc("week", Order.created_at).label("week_start"),
            func.count(Order.id).label("count_orders"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
        )
        .join(Order.items)
        .where(Order.created_at.between(date_from, date_to))
        .group_by("week_start")
        .order_by("week_start")
    )

    result = await db.execute(stmt)
    return [
        {
            "week_start": row.week_start.date(),
            "count_orders": int(row.count_orders or 0),
            "total_revenue": float(row.total_revenue or 0),
        }
        for row in result.all()
    ]


async def get_orders_by_user_stats(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[dict]:
    """
    Возвращает статистику заказов по пользователям:
    количество, сумма и средний чек за период.
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    stmt = (
        select(
            User.id.label("user_id"),
            User.username.label("username"),
            func.count(Order.id).label("count_orders"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
            (func.sum(OrderItem.price * OrderItem.quantity) / func.count(Order.id)).label("avg_order_value"),
        )
        .join(Order, Order.user_id == User.id)
        .join(Order.items)
        .where(Order.created_at.between(date_from, date_to))
        .group_by(User.id, User.username)
        .order_by(desc("total_revenue"))
    )

    result = await db.execute(stmt)
    return [
        {
            "user_id": row.user_id,
            "username": row.username,
            "count_orders": int(row.count_orders or 0),
            "total_revenue": float(row.total_revenue or 0),
            "avg_order_value": float(row.avg_order_value or 0),
        }
        for row in result.all()
    ]


async def get_orders_by_item_stats(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 10,
) -> List[dict]:
    """
    Возвращает статистику заказов по блюдам (позициям меню):
    количество продаж, сумма и средняя цена.
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    stmt = (
        select(
            MenuItem.id.label("menu_item_id"),
            MenuItem.name.label("menu_item_name"),
            func.sum(OrderItem.quantity).label("count_sold"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
            func.avg(OrderItem.price).label("avg_price"),
        )
        .join(OrderItem.menu_item)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.created_at.between(date_from, date_to))
        .group_by(MenuItem.id, MenuItem.name)
        .order_by(desc("count_sold"))
        .limit(limit)
    )

    result = await db.execute(stmt)
    return [
        {
            "menu_item_id": row.menu_item_id,
            "menu_item_name": row.menu_item_name,
            "count_sold": int(row.count_sold or 0),
            "total_revenue": float(row.total_revenue or 0),
            "avg_price": float(row.avg_price or 0),
        }
        for row in result.all()
    ]


async def get_orders_by_hour_stats(
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[dict]:
    """
    Возвращает статистику заказов по часам суток.
    """
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=7)

    stmt = (
        select(
            func.extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count_orders"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
        )
        .join(Order.items)
        .where(Order.created_at.between(date_from, date_to))
        .group_by("hour")
        .order_by("hour")
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Формируем полный диапазон 0–23, чтобы в ответе были и "пустые" часы
    hours = {int(row.hour): row for row in rows}
    return [
        {
            "hour": h,
            "count_orders": int(hours[h].count_orders) if h in hours else 0,
            "total_revenue": float(hours[h].total_revenue or 0) if h in hours else 0.0,
        }
        for h in range(24)
    ]
