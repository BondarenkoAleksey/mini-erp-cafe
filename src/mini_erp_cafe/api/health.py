from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health", summary="Health check")
async def health_check():
    """
    Простейший health-check эндпоинт.
    """
    return {
        "status": "ok",
        "timestamp": datetime. now()
    }