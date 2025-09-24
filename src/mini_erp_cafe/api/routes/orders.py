from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from mini_erp_cafe.schemas.order import OrderRead
from mini_erp_cafe.crud.order import get_orders
from mini_erp_cafe.db.session import get_async_session


router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=List[OrderRead])
async def list_orders(db: AsyncSession = Depends(get_async_session)):
    """
    Возвращает список всех заказов с позициями.
    """
    orders = await get_orders(db)
    return orders
