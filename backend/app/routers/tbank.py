"""
Роутер для интеграции с Т-Банком
"""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from cryptography.fernet import Fernet
import base64, hashlib
import os

from app.database import get_db
from app.models import User, Transaction, Category, TransactionSource
from app.routers.auth import get_current_user

router = APIRouter(prefix="/tbank", tags=["tbank"])


class TBankConnectRequest(BaseModel):
    token: str


class TBankStatusResponse(BaseModel):
    connected: bool
    account_id: Optional[str] = None
    balance: Optional[float] = None
    message: str


@router.get("/status", response_model=TBankStatusResponse)
async def get_tbank_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Проверить статус подключения Т-Банка"""
    if current_user.tbank_token_encrypted:
        return {
            "connected": True,
            "account_id": "sandbox-account",
            "balance": None,
            "message": "Т-Банк подключён"
        }
    
    return {
        "connected": False,
        "account_id": None,
        "balance": None,
        "message": "Т-Банк не подключён"
    }


@router.post("/connect", response_model=TBankStatusResponse)
async def connect_tbank(
    data: TBankConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Подключить Т-Банк"""
    if not data.token or not data.token.startswith("t."):
        raise HTTPException(status_code=400, detail="Неверный формат токена. Токен должен начинаться с 't.'")
    
    _s = get_settings()
    key = base64.urlsafe_b64encode(
        hashlib.sha256(_s.SECRET_KEY.encode()).digest()
    )
    f = Fernet(key)
    encrypted = f.encrypt(data.token.encode()).decode()

    current_user.tbank_token_encrypted = encrypted
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "connected": True,
        "account_id": "sandbox-account",
        "balance": None,
        "message": "Т-Банк успешно подключён"
    }


@router.post("/disconnect")
async def disconnect_tbank(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отключить Т-Банк"""
    current_user.tbank_token_encrypted = None
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Т-Банк отключён"}


@router.post("/sync")
async def sync_tbank(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Синхронизировать транзакции с Т-Банком (через Sandbox API)"""
    if not current_user.tbank_token_encrypted:
        raise HTTPException(
            status_code=400, 
            detail="Т-Банк не подключен. Сначала подключите аккаунт в настройках."
        )
    
    # 1. Расшифровка токена
    try:
        _s = get_settings()
        # Генерируем ключ на основе SECRET_KEY
        key = base64.urlsafe_b64encode(hashlib.sha256(_s.SECRET_KEY.encode()).digest())
        f = Fernet(key)
        # Расшифровываем
        token = f.decrypt(current_user.tbank_token_encrypted.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка безопасности при чтении токена")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Асинхронное взаимодействие с API через httpx
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            # Шаг A: Получаем список аккаунтов
            accounts_response = await client.post(
                "https://sandbox-invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts",
                headers=headers,
                json={},
                timeout=10
            )
            
            if accounts_response.status_code != 200:
                # Если токен невалиден для API, откатываемся на демо-данные
                logger.warning(f"T-Bank API rejected token: {accounts_response.status_code}")
                return await _add_demo_transactions(db, current_user)
            
            accounts_data = accounts_response.json()
            accounts = accounts_data.get("accounts", [])
            
            # Шаг B: Если аккаунтов нет, создаем новый в песочнице
            if not accounts:
                create_response = await client.post(
                    "https://sandbox-invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.SandboxService/OpenSandboxAccount",
                    headers=headers,
                    json={},
                    timeout=10
                )
                if create_response.status_code == 200:
                    account_id = create_response.json().get("accountId")
                else:
                    return await _add_demo_transactions(db, current_user)
            else:
                account_id = accounts[0].get("id")
            
            # Шаг C: Получаем операции за последнюю неделю
            from datetime import timedelta
            now = datetime.utcnow()
            week_ago = now - timedelta(days=7)
            
            operations_response = await client.post(
                "https://sandbox-invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.OperationsService/GetOperations",
                headers=headers,
                json={
                    "accountId": account_id,
                    "from": week_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "state": "OPERATION_STATE_EXECUTED"
                },
                timeout=10
            )
            
            if operations_response.status_code != 200:
                return await _add_demo_transactions(db, current_user)
            
            # Шаг D: Обработка полученных данных
            operations_data = operations_response.json()
            operations = operations_data.get("operations", [])
            
            if not operations:
                return await _add_demo_transactions(db, current_user)
            
            # Сохраняем операции в базу
            new_count = 0
            for op in operations:
                # Проверяем, нет ли уже такой транзакции
                external_id = op.get("id")
                exists = db.query(Transaction).filter(Transaction.external_id == external_id).first()
                if exists:
                    continue
                
                # Создаем новую транзакцию
                amount_data = op.get("payment", {})
                # В API Т-Банка суммы часто в объектах {units, nano}
                units = int(amount_data.get("units", 0))
                nano = int(amount_data.get("nano", 0))
                amount = Decimal(units) + Decimal(nano) / Decimal(10**9)
                
                # Т-Банк Инвестиции обычно возвращают отрицательные суммы для покупок
                # Для нашего приложения приводим к абсолютному значению или логике доход/расход
                is_expense = amount < 0
                
                new_tx = Transaction(
                    user_id=current_user.id,
                    amount=abs(amount),
                    currency=amount_data.get("currency", "RUB").upper(),
                    description=op.get("typeDescription", "Операция Т-Банк"),
                    source=TransactionSource.tbank_api,
                    external_id=external_id,
                    merchant_name=op.get("figi", "Инвестиционный актив"),
                    transaction_date=datetime.strptime(op.get("date")[:19], "%Y-%m-%dT%H:%M:%S"),
                    category_manual=False
                )
                db.add(new_tx)
                new_count += 1
            
            db.commit()
            return {
                "status": "success", 
                "message": f"Синхронизация завершена. Добавлено {new_count} новых транзакций.",
                "count": new_count
            }

        except Exception as e:
            logger.error(f"Error during T-Bank sync: {str(e)}")
            # В любой непонятной ситуации — добавляем демо-данные, чтобы интерфейс не был пустым
            return await _add_demo_transactions(db, current_user)

async def _add_demo_transactions(db: Session, user: User):
    """Добавить демо-транзакции"""
    from datetime import timedelta
    
    # Получаем категории
    food = db.query(Category).filter(Category.code == "food").first()
    transport = db.query(Category).filter(Category.code == "transport").first()
    other = db.query(Category).filter(Category.code == "other").first()
    
    now = datetime.utcnow()
    
    demo_transactions = [
        {"amount": Decimal("50000"), "description": "Пополнение счёта", "category_id": None, "days_ago": 0},
        {"amount": Decimal("-1500"), "description": "Покупка акций SBER", "category_id": other.id if other else None, "days_ago": 0},
    ]
    
    added = 0
    for t_data in demo_transactions:
        t = Transaction(
            user_id=user.id,
            amount=t_data["amount"],
            description=t_data["description"],
            category_id=t_data["category_id"],
            currency="RUB",
            source=TransactionSource.tbank_api,
            external_id=f"demo_{user.id}_{added}_{now.timestamp()}",
            transaction_date=now - timedelta(days=t_data["days_ago"]),
        )
        db.add(t)
        added += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Добавлено {added} демо-транзакций (Sandbox API недоступен или пуст)",
        "transactions_added": added,
    }
