"""Основный файл FastAPI приложения"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
from app.scheduler import scheduler, setup_scheduler
from starlette.middleware.cors import CORSMiddleware

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

from app.routers.auth import get_current_user

from app.ml.model_loader import registry

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск Finance App Backend...")
    Base.metadata.create_all(bind=engine)
    registry.load_all()
    setup_scheduler()
    logger.info("✅ Все инициализации завершены!")
    yield
    scheduler.shutdown(wait=False)
    logger.info("Приложение остановлено.")

def get_real_ip(request):
    fwd = request.headers.get("X-Forwarded-For")
    return fwd.split(",")[0].strip() if fwd else get_remote_address(request)
limiter = Limiter(key_func=get_real_ip)
app = FastAPI(
    title="Finance App API",
    description="API для управления личными финансами и расходов",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    if not settings.DEBUG:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
    return response

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

@app.exception_handler(SQLAlchemyAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyAlchemyError):
    logger.error(f"DB Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Ошибка базы данных. Попробуйте позже."}
    )

@app.get("/ml-status")
async def ml_status(current_user: User = Depends(get_current_user)):
    """Статус ML-модулей (только для авторизованных)"""
    return {
        "models": {
            name: {"loaded": loaded}
            for name, loaded in registry._loaded.items()
        },
        "total": len(registry._loaded),
        "loaded_count": sum(1 for v in registry._loaded.values() if v)
    }