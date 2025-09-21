from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from ..config import settings

# Асинхронный движок
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

# async_sessionmaker (SQLAlchemy >=1.4/2.0)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # совет: избегаем автоматического "expiration" данных после commit
)
