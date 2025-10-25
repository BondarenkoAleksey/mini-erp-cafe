from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mini_erp_cafe.crud.order import create_order, get_orders, get_order_by_id, get_orders_daily_stats
from mini_erp_cafe.crud.order import get_orders_summary, update_order, delete_order
from mini_erp_cafe.crud.order import get_top_menu_items, get_orders_stats, get_top_users_stats
from mini_erp_cafe.crud.order import get_orders_stats_by_user, get_orders_summary_stats
from mini_erp_cafe.crud.order import get_orders_stats_by_item, get_orders_stats_by_day_and_user
from mini_erp_cafe.db.session import get_async_session
from mini_erp_cafe.models.menu_item import MenuItem
from mini_erp_cafe.models.order import Order, OrderItem
from mini_erp_cafe.schemas.order import OrderCreate, OrderRead, OrderUpdate


router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/", response_model=List[OrderRead])
async def list_orders(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    date_from: Optional[datetime] = Query(None, description="Начальная дата"),
    date_to: Optional[datetime] = Query(None, description="Конечная дата"),
    limit: Optional[int] = Query(None, description="Количество записей для вывода"),
    offset: Optional[int] = Query(None, description="Смещение для пагинации"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Возвращает список заказов.
    Поддерживает фильтрацию по статусу и диапазону дат, фильтрацию и пагинацию.
    """
    orders = await get_orders(
        db, status=status, date_from=date_from, date_to=date_to, limit=limit, offset=offset
    )
    return [OrderRead.from_orm_with_name(o) for o in orders]


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int = Path(..., description="ID заказа"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Возвращает детализацию заказа по id.
    """
    order = await get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Добавляем menu_item_name (Pydantic будет его брать)
    for item in order.items:
        if getattr(item, "menu_item", None):
            setattr(item, "menu_item_name", item.menu_item.name)

    return order


@router.post("/", response_model=OrderRead)
async def create_order_endpoint(order_in: OrderCreate, db: AsyncSession = Depends(get_async_session)):
    """
    Возвращает созданный заказ.
    """
    order = await create_order(db, order_in)
    return order


@router.patch("/{order_id}", response_model=OrderRead)
async def patch_order_endpoint(
    order_id: int,
    order_in: OrderUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Частичное обновление заказа.
    Поддерживаемые поля: menu_item_id, quantity, status, special_requests, scheduled_at.
    """
    try:
        order = await update_order(db, order_id, order_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@router.delete("/{order_id}", status_code=204)
async def remove_order(order_id: int, session: AsyncSession = Depends(get_async_session)):
    """
    Удаляет заказ.
    """
    deleted = await delete_order(session, order_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Order not found")


@router.get("/summary")
async def get_orders_summary_endpoint(
    group_by: Optional[str] = Query(None, description="Группировка: status, user_id, menu_item_id, date"),
    date_from: Optional[str] = Query(None, description="Начальная дата (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Возвращает агрегированную статистику по заказам:
    - count_orders (кол-во заказов)
    - total_revenue (сумма)
    - average_check (средний чек)
    Поддерживает группировку по status, user_id, menu_item_id, date.
    Добавляет итоговую строку 'total' при использовании группировки.
    """
    summary = await get_orders_summary(
        db=db,
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
    )
    return summary


@router.get("/stats")
async def get_orders_stats_endpoint(
    db: AsyncSession = Depends(get_async_session),
    interval: str = Query("day", enum=["day", "week", "month"], description="Интервал группировки"),
    date_from: Optional[datetime] = Query(None, description="Начальная дата"),
    date_to: Optional[datetime] = Query(None, description="Конечная дата"),
):
    """
    Возвращает агрегированную статистику заказов:
    - interval: 'day' | 'week' | 'month'
    - по умолчанию последние 7 дней
    """
    return await get_orders_stats(db, interval=interval, date_from=date_from, date_to=date_to)


@router.get("/stats/daily")
async def get_orders_stats_daily_endpoint(
    db: AsyncSession = Depends(get_async_session),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    """
    Алиас для /stats с interval='day' (совместимость со старой ручкой)
    """
    return await get_orders_stats(db, interval="day", date_from=date_from, date_to=date_to)


@router.get("/stats/top")
async def get_top_items(
    limit: int = 5,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Топ самых популярных блюд (по количеству заказанных порций).
    """
    items = await get_top_menu_items(db, limit)
    return {"top_items": items}


@router.get("/stats/users")
async def get_top_users(
    limit: int = 5,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Топ пользователей по количеству заказов и общей сумме.
    """
    users = await get_top_users_stats(db, limit)
    return {"top_users": users}


@router.get("/stats/users")
async def get_top_users(
    limit: int = 5,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Топ пользователей по количеству заказов и общей сумме.
    """
    users = await get_top_users_stats(db, limit)
    return {"top_users": users}

@router.get("/stats/summary")
async def get_orders_summary(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Общая статистика по заказам:
    - количество заказов
    - общая выручка
    - средний чек
    - уникальные клиенты
    """
    summary = await get_orders_summary_stats(db)
    return summary


@router.get("/stats/by-user")
async def get_orders_stats_by_user_endpoint(
    db: AsyncSession = Depends(get_async_session),
    date_from: Optional[datetime] = Query(None, description="Начальная дата (ISO)"),
    date_to: Optional[datetime] = Query(None, description="Конечная дата (ISO)"),
):
    """
    Возвращает статистику заказов по пользователям:
    - количество заказов
    - общая выручка
    - средний чек
    - сортировка по сумме (по убыванию)
    """
    return await get_orders_stats_by_user(db, date_from, date_to)


@router.get("/stats/by-item")
async def get_orders_stats_by_item_endpoint(
    db: AsyncSession = Depends(get_async_session),
    date_from: Optional[datetime] = Query(None, description="Начальная дата (ISO)"),
    date_to: Optional[datetime] = Query(None, description="Конечная дата (ISO)"),
):
    """
    Возвращает статистику продаж по блюдам:
    - количество проданных единиц
    - общая выручка
    - средняя цена
    - сортировка по выручке
    """
    return await get_orders_stats_by_item(db, date_from, date_to)


@router.get("/stats/by-day-and-user")
async def get_orders_stats_by_day_and_user_endpoint(
    db: AsyncSession = Depends(get_async_session),
    date_from: Optional[datetime] = Query(None, description="Начальная дата (ISO)"),
    date_to: Optional[datetime] = Query(None, description="Конечная дата (ISO)"),
):
    """
    Возвращает статистику заказов по дням и пользователям.
    Удобно для анализа активности.
    """
    return await get_orders_stats_by_day_and_user(db, date_from, date_to)
