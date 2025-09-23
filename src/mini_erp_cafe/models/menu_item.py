from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from ..db.base import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=True)  # кофе, еда, десерт и т.д.
    price = Column(Numeric(10, 2), nullable=False)  # цена
    is_available = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # связь с OrderItem
    order_items = relationship("OrderItem", back_populates="menu_item")
