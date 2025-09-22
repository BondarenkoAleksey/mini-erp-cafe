# src/mini_erp_cafe/db/session.py

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
# src/mini_erp_cafe/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from mini_erp_cafe.config import settings

# База для моделей
Base = declarative_base()

# Асинхронный движок
engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True)

# Создание сессии
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # данные не будут "исчезать" после commit
)


# async_session = AsyncSessionLocal
