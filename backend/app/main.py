"""
Главный файл FastAPI приложения
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger

from app.database import engine, Base
from app.models import (
    User, Category, CurrencyRate, Transaction, 
    Reminder, NotificationHistory, Prediction, AuditLog
)
from app.config import get_settings
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

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Finance App API",
    description="API для управления личными финансами",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

settings = get_settings()

# CORS — разрешаем только домены из переменной окружения ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
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

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"DB Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Ошибка базы данных. Повторите позже."}
    )
