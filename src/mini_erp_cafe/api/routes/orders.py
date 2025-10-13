from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mini_erp_cafe.crud.order import create_order, get_orders, get_order_by_id
from mini_erp_cafe.crud.order import get_orders_summary, update_order, delete_order
from mini_erp_cafe.db.session import get_async_session
from mini_erp_cafe.models.menu_item import MenuItem
from mini_erp_cafe.models.order import Order
from mini_erp_cafe.models.order_item import OrderItem
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
async def get_orders_summary(
    status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    group_by: Optional[str] = Query(None, description="status | user_id | day"),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Возвращает сводную статистику по заказам.
    Можно фильтровать и группировать по статусу, пользователю или дате.
    """
    summary = await get_orders_summary(db, status, user_id, date_from, date_to, group_by)
    return summary
