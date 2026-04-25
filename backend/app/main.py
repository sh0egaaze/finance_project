"""
Главный файл FastAPI приложения
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.database import engine, Base
from app.models import (
    User, Category, CurrencyRate, Transaction, 
    Reminder, NotificationHistory, Prediction, AuditLog
)
from app.routers import (
    auth_router,
    transactions_router,
    categories_router,
    dashboard_router,
    reminders_router,
    currency_router,
    tbank_router,
)


from app.ml.model_loader import registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Запуск Finance App Backend...")
    
    # 1. Создание таблиц
    Base.metadata.create_all(bind=engine)
    
    # 2. Загрузка ML-моделей
    registry.load_all()
    
    logger.info("✅ Приложение инициализировано!")
    yield
    logger.info("Остановка Finance App Backend...")


app = FastAPI(
    title="Finance App API",
    description="API для управления личными финансами",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(auth_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(reminders_router, prefix="/api/v1")
app.include_router(currency_router, prefix="/api/v1")
app.include_router(tbank_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Finance App API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
