import enum
from sqlalchemy import Column, Integer, String, DateTime, func, Enum
from sqlalchemy.orm import relationship
from ..db.base import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    waiter = "waiter"
    barista = "barista"
    manager = "manager"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    role = Column(Enum(RoleEnum, name="user_role"), nullable=False, default=RoleEnum.waiter)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # связь с заказами
    orders = relationship("Order", back_populates="user")
