from fastapi import FastAPI
from .api import health, users
from mini_erp_cafe.api.routes.orders import router as orders_router

app = FastAPI(title="Mini ERP Cafe")

# Подключаем роуты
app.include_router(health.router)
app.include_router(users.router)

@app.on_event("startup")
async def on_startup():
    print("🚀 Application started")

@app.on_event("shutdown")
async def on_shutdown():
    print("🛑 Application stopped")

app.include_router(orders_router)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("🚀 Application started")
#     yield
#     print("🛑 Application stopped")
#
# app = FastAPI(title="Mini ERP Cafe",
#               lifespan=lifespan)
#
# app.include_router(health.router)
# app.include_router(users.router)
