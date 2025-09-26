from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from mini_erp_cafe.models.order import Order
from mini_erp_cafe.schemas.order import OrderRead
from mini_erp_cafe.crud.order import get_orders
from mini_erp_cafe.crud.order import get_order_by_id
from mini_erp_cafe.db.session import get_async_session
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from mini_erp_cafe.models.order import Order
from mini_erp_cafe.models.order_item import OrderItem
from mini_erp_cafe.models.menu_item import MenuItem


router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=List[OrderRead])
async def list_orders(db: AsyncSession = Depends(get_async_session)):
    """
    Возвращает список всех заказов с позициями.
    """
    orders = await get_orders(db)

    # Дополняем menu_item_name для фронта (это поле есть в схеме)
    for order in orders:
        for item in order.items:
            if getattr(item, "menu_item", None):
                setattr(item, "menu_item_name", item.menu_item.name)

    return orders


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int = Path(..., description="ID заказа"),
    db: AsyncSession = Depends(get_async_session),
):
    order = await get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Добавляем menu_item_name (Pydantic будет его брать)
    for item in order.items:
        if getattr(item, "menu_item", None):
            setattr(item, "menu_item_name", item.menu_item.name)

    return order
