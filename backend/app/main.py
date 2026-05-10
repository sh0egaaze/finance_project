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

# Описание тегов для Swagger документации
tags_metadata = [
    {
        "name": "Система",
        "description": "Системные эндпоинты: проверка здоровья, статус ML и информация о приложении",
    },
    {
        "name": "Авторизация",
        "description": "Регистрация, авторизация и управление сессиями пользователей",
    },
    {
        "name": "Транзакции",
        "description": "CRUD операции с транзакциями, импорт и категоризация",
    },
    {
        "name": "Категории",
        "description": "Управление категориями доходов и расходов",
    },
    {
        "name": "Дашборд",
        "description": "Аналитика, статистика и прогнозы по финансам",
    },
    {
        "name": "Напоминания",
        "description": "Управление напоминаниями о платежах и подписках",
    },
    {
        "name": "Валюты",
        "description": "Курсы валют и конвертация",
    },
    {
        "name": "Т-Банк",
        "description": "Интеграция с API Т-Банка: синхронизация счетов и транзакций",
    },
]


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
    description="""
## 💰 Finance App API

API для управления личными финансами, отслеживания расходов и доходов.

### Основные возможности:
- **Авторизация** — регистрация и вход с JWT токенами
- **Транзакции** — добавление, редактирование, удаление и категоризация
- **Категории** — пользовательские категории доходов/расходов
- **Аналитика** — статистика, графики, прогнозы на основе ML
- **Напоминания** — уведомления о предстоящих платежах
- **Валюты** — актуальные курсы и конвертация
- **Т-Банк** — автоматическая синхронизация транзакций

### Авторизация:
Для доступа к защищённым эндпоинтам используйте JWT токен в заголовке:
Authorization: Bearer <token>
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    openapi_tags=tags_metadata,
    contact={
        "name": "Finance App Support",
        "url": "https://github.com/sh0egaaze/finance_project",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
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
app.include_router(auth_router, prefix="/api/v1", tags=["Авторизация"])
app.include_router(transactions_router, prefix="/api/v1", tags=["Транзакции"])
app.include_router(categories_router, prefix="/api/v1", tags=["Категории"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["Дашборд"])
app.include_router(reminders_router, prefix="/api/v1", tags=["Напоминания"])
app.include_router(currency_router, prefix="/api/v1", tags=["Валюты"])
app.include_router(tbank_router, prefix="/api/v1", tags=["Т-Банк"])


@app.get(
    "/",
    tags=["Система"],
    summary="Корневой эндпоинт",
    description="Возвращает базовую информацию о приложении и его версии.",
    response_description="Информация о приложении",
    responses={
        200: {
            "description": "Успешный ответ",
            "content": {
                "application/json": {
                    "example": {"message": "Finance App API", "version": "1.0.0"}
                }
            },
        }
    },
)
async def root():
    """
    Корневой эндпоинт API.
    
    Возвращает название и версию приложения.
    Используется для проверки доступности API.
    """
    return {"message": "Finance App API", "version": "1.0.0"}


@app.get(
    "/health",
    tags=["Система"],
    summary="Проверка здоровья сервиса",
    description="Эндпоинт для проверки работоспособности сервиса. Используется для мониторинга и load balancer.",
    response_description="Статус работы сервиса",
    responses={
        200: {
            "description": "Сервис работает нормально",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            },
        },
        503: {
            "description": "Сервис недоступен",
            "content": {
                "application/json": {
                    "example": {"status": "unhealthy", "detail": "Database connection failed"}
                }
            },
        },
    },
)
async def health():
    """
    Проверка здоровья сервиса.
    
    Возвращает статус работы приложения.
    Используется для:
    - Health checks в Docker/Kubernetes
    - Мониторинга доступности
    - Load balancer проверок
    """
    return {"status": "ok"}


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"DB Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Ошибка базы данных. Попробуйте позже."}
    )


@app.get(
    "/ml-status",
    tags=["Система"],
    summary="Статус ML-моделей",
    description="""
Возвращает информацию о загруженных ML-моделях.

**Требуется авторизация.**

Показывает:
- Список всех моделей и их статус загрузки
- Общее количество моделей
- Количество успешно загруженных моделей
    """,
    response_description="Статус загрузки ML-моделей",
    responses={
        200: {
            "description": "Успешный ответ со статусом моделей",
            "content": {
                "application/json": {
                    "example": {
                        "models": {
                            "categorizer": {"loaded": True},
                            "predictor": {"loaded": True},
                            "anomaly_detector": {"loaded": False}
                        },
                        "total": 3,
                        "loaded_count": 2
                    }
                }
            },
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            },
        },
    },
)
async def ml_status(current_user: User = Depends(get_current_user)):
    """
    Статус ML-модулей (только для авторизованных пользователей).
    
    Возвращает информацию о всех зарегистрированных ML-моделях
    и их текущем состоянии загрузки.
    """
    return {
        "models": {
            name: {"loaded": loaded}
            for name, loaded in registry._loaded.items()
        },
        "total": len(registry._loaded),
        "loaded_count": sum(1 for v in registry._loaded.values() if v)
    }