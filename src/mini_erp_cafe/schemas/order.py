from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


class OrderItemRead(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    price: Decimal
    menu_item_name: Optional[str] = None  # удобство для фронта

    class Config:
        orm_mode = True


class OrderRead(BaseModel):
    id: int
    user_id: int
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None
    items: List[OrderItemRead] = []

    class Config:
        orm_mode = True
