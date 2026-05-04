"""
Роутер для интеграции с Т-Банком (Production версия без демо-данных)
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator, Field
from typing import Optional
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

router = APIRouter(prefix="/tbank", tags=["tbank"])

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


class TBankConnectRequest(BaseModel):
    token: str = Field(
        ..., 
        min_length=3, 
        max_length=200,
        description="Т-Банк API токен"
    )
    
    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("t."):
            raise ValueError("Токен должен начинаться с 't.'")
        if not re.match(r'^t\.[a-zA-Z0-9_-]+$', v):
            raise ValueError("Токен содержит недопустимые символы")
        return v


class TBankStatusResponse(BaseModel):
    connected: bool
    account_id: Optional[str] = None
    balance: Optional[float] = None
    message: str


# ========================================================
# GET /status — проверка статуса подключения
# ========================================================
@router.get("/status", response_model=TBankStatusResponse)
async def get_tbank_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Проверка текущего подключения Т-Банка"""
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
                f"{_s.TBANK_API_URL}/rest/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts",
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
                    account_id = accounts[0].get("accountId")
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
@router.post("/connect", response_model=TBankStatusResponse)
@limiter.limit("3/minute")
async def connect_tbank(
    request: Request,
    data: TBankConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Подключение Т-Банка"""
    if not data.token or not data.token.startswith("t."):
        raise HTTPException(
            status_code=400, 
            detail="Некорректный формат токена. Токен должен начинаться с 't.'"
        )
    
    _s = get_settings()
    
    # Проверяем токен через T-Bank API
    try:
        headers = {
            "Authorization": f"Bearer {data.token}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_s.TBANK_API_URL}/rest/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts",
                headers=headers,
                json={},
                timeout=10
            )
            if resp.status_code != 200:
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
@router.post("/disconnect")
async def disconnect_tbank(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отключение Т-Банка"""
    current_user.tbank_token_encrypted = None
    current_user.tbank_token_salt = None
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Т-Банк отключён"}


# ========================================================
# POST /sync — синхронизация транзакций
# ========================================================
@router.post("/sync")
@limiter.limit("5/minute")
async def sync_tbank(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Синхронизация транзакций с Т-Банком (через Sandbox API)"""
    if not current_user.tbank_token_encrypted:
        raise HTTPException(
            status_code=400, 
            detail="Т-Банк не подключён. Сначала подключитесь в настройках."
        )
    
    # Расшифровка токена
    _s = get_settings()
    try:
        token = _decrypt_token(
            current_user.tbank_token_encrypted,
            current_user.tbank_token_salt,
            _s.TBANK_ENCRYPTION_KEY
        )
    except InvalidToken:
        logger.error("Не удалось расшифровать токен — возможно, изменён ключ шифрования")
        raise HTTPException(
            status_code=500, 
            detail="Токен повреждён. Пожалуйста, переподключите Т-Банк."
        )
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Ошибка при расшифровке токена"
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Запрашиваем операции по API
    try:
        async with httpx.AsyncClient() as client:
            # Проверяем наличие аккаунтов
            accounts_response = await client.post(
                f"{_s.TBANK_API_URL}/rest/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts",
                headers=headers,
                json={},
                timeout=10
            )
            
            if accounts_response.status_code != 200:
                logger.warning(f"T-Bank API rejected token: {accounts_response.status_code}")
                raise HTTPException(
                    status_code=503,
                    detail="T-Bank API временно недоступен. Попробуйте позже."
                )
            
            accounts_data = accounts_response.json()
            accounts = accounts_data.get("accounts", [])
            
            # Если аккаунтов нет, создаём
            if not accounts:
                create_response = await client.post(
                    f"{_s.TBANK_API_URL}/rest/tinkoff.public.invest.api.contract.v1.SandboxService/OpenSandboxAccount",
                    headers=headers,
                    json={},
                    timeout=10
                )
                if create_response.status_code == 200:
                    account_id = create_response.json().get("accountId")
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="T-Bank API временно недоступен. Попробуйте позже."
                    )
            else:
                account_id = accounts[0].get("accountId")
            
            # Получаем операции за последние 30 дней
            now = datetime.now(timezone.utc)
            from_date = now - timedelta(days=30)
            operations_response = await client.post(
                f"{_s.TBANK_API_URL}/rest/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxOperations",
                headers=headers,
                json={
                    "accountId": account_id,
                    "from": from_date.isoformat(),
                    "to": now.isoformat(),
                },
                timeout=10
            )
            
            if operations_response.status_code != 200:
                raise HTTPException(
                    status_code=503,
                    detail="T-Bank API временно недоступен. Попробуйте позже."
                )
            
            operations = operations_response.json().get("operations", [])
            
            # Сохраняем транзакции в базу данных
            added_count = 0
            for op in operations:
                ext_id = op.get("id", "")
                
                # Проверяем, не существует ли уже такая транзакция
                existing = db.query(Transaction).filter(
                    Transaction.external_id == ext_id,
                    Transaction.user_id == current_user.id
                ).first()
                if existing:
                    continue
                
                # Определяем категорию по MCC-коду
                mcc = str(op.get("mcc", ""))
                cat = _find_category_by_mcc(db, mcc, current_user.id)
                
                amount = float(op.get("payment", {}).get("amount", 0))
                
                tx = Transaction(
                    user_id=current_user.id,
                    category_id=cat.id if cat else None,
                    amount=amount,
                    currency=op.get("payment", {}).get("currency", "RUB"),
                    description=op.get("description", ""),
                    source=TransactionSource.tbank_api,
                    external_id=ext_id,
                    merchant_name=op.get("merchant", {}).get("name", ""),
                    merchant_category_code=mcc,
                    transaction_date=datetime.fromisoformat(op.get("date", now.isoformat()).replace("Z", "+00:00")),
                )
                db.add(tx)
                added_count += 1
            
            db.commit()
            return {
                "message": f"Синхронизация завершена. Добавлено транзакций: {added_count}",
                "added": added_count
            }
            
    except httpx.TimeoutException:
        logger.error("T-Bank API timeout")
        raise HTTPException(
            status_code=503,
            detail="T-Bank API временно недоступен. Попробуйте позже."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"T-Bank sync error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ошибка синхронизации с T-Bank API"
        )


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
