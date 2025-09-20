from fastapi import FastAPI
from .api import health

app = FastAPI(title="Mini ERP Cafe")

# Подключаем роуты
app.include_router(health.router)

@app.on_event("startup")
async def on_startup():
    print("🚀 Application started")

@app.on_event("shutdown")
async def on_shutdown():
    print("🛑 Application stopped")
