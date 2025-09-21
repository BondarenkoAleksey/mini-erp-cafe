from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..db.deps import get_async_session
from ..schemas.user import UserOut
from ..models.user import User

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=List[UserOut])
async def list_users(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return users
