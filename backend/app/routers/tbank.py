"""
Роутер для интеграции с Т-Банком (Production версия без демо-данных)
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, status, Path
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator, Field
from typing import Optional, List
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64
import httpx
import os
import logging
import re

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models import User, Transaction, Category, TransactionSource
from app.routers.auth import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/tbank", tags=["Т-Банк"])

limiter = Limiter(key_func=get_remote_address)


def derive_fernet_key(secret_key: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Деривация ключа через PBKDF2 с salt"""
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return key, salt


def _decrypt_token(encrypted: str, salt_b64: str | None, secret_key: str) -> str:
    """Расшифровка токена Т-Банка"""
    if not salt_b64:
        raise InvalidToken("Salt не сохранён. Переподключите Т-Банк.")
    salt = base64.urlsafe_b64decode(salt_b64.encode())
    key, _ = derive_fernet_key(secret_key, salt)
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()


# ===== Pydantic схемы =====
class TBankConnectRequest(BaseModel):
    """Схема запроса на подключение Т-Банка"""
    token: str = Field(
        ..., 
        min_length=3, 
        max_length=500,
        description="API токен Т-Банка (начинается с 't.')",
        examples=["t.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"]
    )
    
    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("t."):
            raise ValueError("Токен должен начинаться с 't.'")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "t.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                }
            ]
        }
    }


class TBankStatusResponse(BaseModel):
    """Схема ответа о статусе подключения Т-Банка"""
    connected: bool = Field(..., description="Подключён ли Т-Банк", examples=[True])
    account_id: Optional[str] = Field(None, description="ID аккаунта в Т-Банке", examples=["2000000000"])
    balance: Optional[float] = Field(None, description="Баланс счёта (если доступен)", examples=[150000.50])
    message: str = Field(..., description="Сообщение о статусе", examples=["Т-Банк подключён"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "connected": True,
                    "account_id": "2000000000",
                    "balance": 150000.50,
                    "message": "Т-Банк подключён"
                }
            ]
        }
    }


class TBankDisconnectResponse(BaseModel):
    """Схема ответа при отключении Т-Банка"""
    message: str = Field(..., description="Сообщение об успехе", examples=["Т-Банк отключён"])


class TBankSyncResponse(BaseModel):
    """Схема ответа синхронизации"""
    message: str = Field(..., description="Сообщение о результате", examples=["Синхронизация завершена. Добавлено транзакций: 15"])
    added: int = Field(..., description="Количество добавленных транзакций", examples=[15])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Синхронизация завершена. Добавлено транзакций: 15",
                    "added": 15
                }
            ]
        }
    }


# ========================================================
# GET /status — проверка статуса подключения
# ========================================================
@router.get(
    "/status",
    response_model=TBankStatusResponse,
    summary="Проверить статус подключения Т-Банка",
    description="""
Проверяет текущий статус подключения к API Т-Банка.

**Требуется авторизация.**

**Возвращает:**
- `connected` — подключён ли аккаунт
- `account_id` — ID аккаунта (если подключён)
- `balance` — баланс счёта (если доступен)
- `message` — текстовое описание статуса

**Возможные статусы:**
- Т-Банк подключён
- Т-Банк не подключён
- Токен истёк / повреждён
- API временно недоступен
    """,
    response_description="Статус подключения Т-Банка",
    responses={
        200: {
            "description": "Успешный ответ со статусом",
            "content": {
                "application/json": {
                    "examples": {
                        "connected": {
                            "summary": "Подключён",
                            "value": {
                                "connected": True,
                                "account_id": "2000000000",
                                "balance": 150000.50,
                                "message": "Т-Банк подключён"
                            }
                        },
                        "not_connected": {
                            "summary": "Не подключён",
                            "value": {
                                "connected": False,
                                "account_id": None,
                                "balance": None,
                                "message": "Т-Банк не подключён"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Недействительный токен"}
                }
            }
        }
    }
)
async def get_tbank_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Проверка текущего подключения Т-Банка.
    
    Проверяет наличие сохранённого токена и его валидность
    через запрос к API Т-Банка.
    """
    if not current_user.tbank_token_encrypted:
        return {
            "connected": False,
            "account_id": None,
            "balance": None,
            "message": "Т-Банк не подключён"
        }
    
    _s = get_settings()
    
    # Расшифровка токена
    try:
        token = _decrypt_token(
            current_user.tbank_token_encrypted,
            current_user.tbank_token_salt,
            _s.TBANK_ENCRYPTION_KEY
        )
    except InvalidToken:
        logger.error("Не удалось расшифровать токен — возможно, изменён ключ шифрования")
        return {
            "connected": False,
            "account_id": None,
            "balance": None,
            "message": "Токен повреждён. Пожалуйста, переподключите Т-Банк."
        }
    except Exception as e:
        logger.error(f"Ошибка расшифровки: {e}")
        return {
            "connected": False,
            "account_id": None,
            "balance": None,
            "message": "Внутренняя ошибка. Обратитесь в поддержку."
        }
    
    # Проверка подключения через API
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_s.TBANK_API_URL}/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts",
                headers=headers,
                json={},
                timeout=10
            )
            if resp.status_code == 401:
                return {
                    "connected": False,
                    "account_id": None,
                    "balance": None,
                    "message": "Токен Т-Банка истёк. Переподключите."
                }
            if resp.status_code == 200:
                data = resp.json()
                accounts = data.get("accounts", [])
                if accounts:
                    balance = accounts[0].get("balance", {}).get("value")
                    account_id = accounts[0].get("id") or accounts[0].get("accountId")
                    return {
                        "connected": True,
                        "account_id": account_id,
                        "balance": balance,
                        "message": "Т-Банк подключён"
                    }
    except httpx.TimeoutException:
        logger.warning("T-Bank API timeout в /status")
        return {
            "connected": False,
            "account_id": None,
            "balance": None,
            "message": "T-Bank API временно недоступен"
        }
    except httpx.HTTPError as e:
        logger.error(f"HTTP ошибка: {e}")
        return {
            "connected": False,
            "account_id": None,
            "balance": None,
            "message": "Ошибка связи с T-Bank"
        }
    
    return {
        "connected": False,
        "account_id": None, 
        "balance": None,
        "message": "Ошибка проверки подключения"
    }


# ========================================================
# POST /connect — подключение Т-Банка
# ========================================================
@router.post(
    "/connect",
    response_model=TBankStatusResponse,
    summary="Подключить Т-Банк",
    description="""
Подключает аккаунт Т-Банка для автоматической синхронизации транзакций.

**Требуется авторизация.**

**Как получить токен:**
1. Зайдите в [T-Bank API](https://www.tbank.ru/invest/settings/api/)
2. Создайте новый токен с правами на чтение операций
3. Скопируйте токен (начинается с `t.`)

**Безопасность:**
- Токен шифруется с использованием PBKDF2 + Fernet
- Сервер не хранит токен в открытом виде
- Используется отдельный salt для каждого пользователя

**Лимит:** 3 запроса в минуту на IP.
    """,
    response_description="Результат подключения",
    responses={
        200: {
            "description": "Т-Банк успешно подключён",
            "content": {
                "application/json": {
                    "example": {
                        "connected": True,
                        "account_id": "sandbox-account",
                        "balance": None,
                        "message": "Т-Банк успешно подключён"
                    }
                }
            }
        },
        400: {
            "description": "Невалидный токен",
            "content": {
                "application/json": {
                    "example": {"detail": "Токен невалиден. T-Bank API вернул статус 401"}
                }
            }
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Недействительный токен"}
                }
            }
        },
        422: {
            "description": "Ошибка валидации (неверный формат токена)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {"loc": ["body", "token"], "msg": "Токен должен начинаться с 't.'"}
                        ]
                    }
                }
            }
        },
        429: {
            "description": "Превышен лимит запросов",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded: 3 per 1 minute"}
                }
            }
        },
        504: {
            "description": "Т-Банк API недоступен",
            "content": {
                "application/json": {
                    "example": {"detail": "T-Bank API недоступен. Попробуйте позже."}
                }
            }
        }
    }
)
@limiter.limit("3/minute")
async def connect_tbank(
    request: Request,
    data: TBankConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Подключение Т-Банка.
    
    Проверяет валидность токена через API Т-Банка,
    шифрует и сохраняет его в базе данных.
    """
    _s = get_settings()
    
    # Проверяем токен через T-Bank API
    try:
        headers = {
            "Authorization": f"Bearer {data.token}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_s.TBANK_API_URL}/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts",
                headers=headers,
                json={},
                timeout=10
            )
            if resp.status_code != 200:
                logger.error(f"T-Bank API rejected: status={resp.status_code}, body={resp.text[:500]}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Токен невалиден. T-Bank API вернул статус {resp.status_code}"
                )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="T-Bank API недоступен. Попробуйте позже."
        )
    
    # Шифруем и сохраняем токен
    key, salt = derive_fernet_key(_s.TBANK_ENCRYPTION_KEY)
    f = Fernet(key)
    encrypted = f.encrypt(data.token.encode()).decode()
    salt_str = base64.urlsafe_b64encode(salt).decode()

    current_user.tbank_token_encrypted = encrypted
    current_user.tbank_token_salt = salt_str
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {
        "connected": True,
        "account_id": "sandbox-account",
        "balance": None,
        "message": "Т-Банк успешно подключён"
    }


# ========================================================
# POST /disconnect — отключение Т-Банка
# ========================================================
@router.post(
    "/disconnect",
    response_model=TBankDisconnectResponse,
    summary="Отключить Т-Банк",
    description="""
Отключает интеграцию с Т-Банком.

**Требуется авторизация.**

**Что происходит:**
- Удаляется сохранённый токен
- Автоматическая синхронизация прекращается
- Ранее синхронизированные транзакции остаются в системе

Для повторного подключения потребуется новый токен.
    """,
    response_description="Подтверждение отключения",
    responses={
        200: {
            "description": "Т-Банк успешно отключён",
            "content": {
                "application/json": {
                    "example": {"message": "Т-Банк отключён"}
                }
            }
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Недействительный токен"}
                }
            }
        }
    }
)
async def disconnect_tbank(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отключение Т-Банка.
    
    Удаляет сохранённый токен из базы данных.
    Синхронизированные ранее транзакции не удаляются.
    """
    current_user.tbank_token_encrypted = None
    current_user.tbank_token_salt = None
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Т-Банк отключён"}


# ========================================================
# POST /sync — синхронизация транзакций
# ========================================================
@router.post(
    "/sync",
    response_model=TBankSyncResponse,
    summary="Синхронизировать транзакции",
    description="""
Синхронизирует транзакции из Т-Банка за последние 30 дней.

**Требуется авторизация и подключённый Т-Банк.**

**Процесс синхронизации:**
1. Загружаются операции за последние 30 дней
2. Дубликаты автоматически пропускаются (по ID операции)
3. Категории определяются автоматически по MCC-коду
4. Транзакции помечаются источником `TBANK`

**Автоматическая категоризация:**
Транзакции категоризируются по MCC-кодам:
- 5411-5462 → Еда и продукты
- 5812-5814 → Рестораны
- 4111-4784 → Транспорт
- и т.д.

**Лимит:** 5 запросов в минуту на IP.
    """,
    response_description="Результат синхронизации",
    responses={
        200: {
            "description": "Синхронизация завершена",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Синхронизация завершена. Добавлено транзакций: 15",
                        "added": 15
                    }
                }
            }
        },
        400: {
            "description": "Т-Банк не подключён",
            "content": {
                "application/json": {
                    "example": {"detail": "Т-Банк не подключён. Сначала подключитесь в настройках."}
                }
            }
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Недействительный токен"}
                }
            }
        },
        429: {
            "description": "Превышен лимит запросов",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded: 5 per 1 minute"}
                }
            }
        },
        500: {
            "description": "Ошибка синхронизации",
            "content": {
                "application/json": {
                    "examples": {
                        "token_error": {
                            "summary": "Ошибка токена",
                            "value": {"detail": "Токен повреждён. Переподключите Т-Банк."}
                        },
                        "api_error": {
                            "summary": "Ошибка API",
                            "value": {"detail": "Ошибка синхронизации с T-Bank API"}
                        }
                    }
                }
            }
        }
    }
)
@limiter.limit("5/minute")
async def sync_tbank(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Синхронизация транзакций с Т-Банком.
    
    Загружает операции за последние 30 дней и добавляет
    новые транзакции в базу данных с автоматической категоризацией.
    """
    if not current_user.tbank_token_encrypted:
        raise HTTPException(
            status_code=400, 
            detail="Т-Банк не подключён. Сначала подключитесь в настройках."
        )
    
    _s = get_settings()
    try:
        token = _decrypt_token(
            current_user.tbank_token_encrypted,
            current_user.tbank_token_salt,
            _s.TBANK_ENCRYPTION_KEY
        )
    except InvalidToken:
        raise HTTPException(status_code=500, detail="Токен повреждён. Переподключите Т-Банк.")
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при расшифровке токена")

    from app.services.tbank_service import TBankService
    
    service = TBankService(token)
    
    try:
        new_count = await service.sync_transactions(db, current_user.id, days=30)
        return {
            "message": f"Синхронизация завершена. Добавлено транзакций: {new_count}",
            "added": new_count
        }
    except Exception as e:
        logger.error(f"T-Bank sync error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка синхронизации с T-Bank API")


# ========================================================
# Вспомогательные функции
# ========================================================

MCC_CATEGORY_MAP = {
    "5411": "food", "5422": "food", "5441": "food",
    "5451": "food", "5462": "food",
    "5812": "restaurants", "5813": "restaurants", "5814": "restaurants",
    "4111": "transport", "4121": "transport", "4131": "transport",
    "4784": "transport", "5542": "transport",
    "6011": "housing", "6051": "housing",
    "5912": "health", "5921": "health", "5970": "health",
    "5200": "shopping", "5300": "shopping", "5600": "shopping",
    "5651": "shopping", "5691": "shopping", "5712": "shopping",
    "5815": "entertainment", "5816": "entertainment", "5977": "entertainment",
    "7032": "entertainment", "7033": "entertainment",
    "8211": "education", "8241": "education", "8299": "education",
}


def _find_category_by_mcc(db: Session, mcc: str, user_id: int):
    """Поиск категории по MCC-коду"""
    category_code = MCC_CATEGORY_MAP.get(mcc)
    if not category_code:
        return None
    return db.query(Category).filter(
        Category.code == category_code,
        Category.user_id == user_id
    ).first()