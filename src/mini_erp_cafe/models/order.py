import enum
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import relationship
from ..db.base import Base


class OrderStatusEnum(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SAEnum(OrderStatusEnum, name="order_status"), nullable=False, default=OrderStatusEnum.open)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # связи
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
