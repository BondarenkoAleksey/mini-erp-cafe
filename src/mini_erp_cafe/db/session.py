from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from mini_erp_cafe.config import settings

# Base для моделей
Base = declarative_base()

# Асинхронный движок
engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Зависимость для FastAPI
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Использовать в Depends(get_async_session)
    Пример: async def endpoint(db: AsyncSession = Depends(get_async_session))
    """
    async with AsyncSessionLocal() as session:
        yield session
