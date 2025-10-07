from pydantic import BaseModel, conint
from typing import List, Optional
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


class OrderItemRead(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    price: Decimal
    menu_item_name: str | None = None

    @classmethod
    def from_orm_with_name(cls, item):
        return cls(
            id=item.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            price=item.price,
            menu_item_name=item.menu_item.name if item.menu_item else None
        )

    class Config:
        from_attributes = True


class OrderRead(BaseModel):
    id: int
    user_id: int
    customer_name: Optional[str] = None
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None
    items: List[OrderItemRead] = []
    total_price: Decimal
    count_items: int

    @classmethod
    def from_orm_with_name(cls, order):
        total = sum(
            (item.price or Decimal("0")) * item.quantity for item in order.items
        )
        count = sum(item.quantity for item in order.items)

        customer_name = order.user.name if getattr(order, "user", None) else None

        return cls(
            id=order.id,
            user_id=order.user_id,
            customer_name=customer_name,
            status=order.status,
            created_at=order.created_at,
            closed_at=order.closed_at,
            items=[OrderItemRead.from_orm_with_name(i) for i in order.items],
            total_price=total.quantize(Decimal("0.01")),
            count_items=count,
        )

    class Config:
        from_attributes = True


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int
    price: Decimal


class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    menu_item_id: Optional[int] = None
    quantity: Optional[conint(ge=1)] = None
    status: Optional[str] = None  # убрали Enum → строка
    special_requests: Optional[str] = None
    scheduled_at: Optional[datetime] = None

    class Config:
        extra = "forbid"
