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
    """Синхронизировать транзакции с Т-Банком"""
    if not current_user.tbank_token_encrypted:
        raise HTTPException(
            status_code=400, 
            detail="Т-Банк не подключён. Сначала подключите аккаунт в настройках."
        )
    
    token = current_user.tbank_token_encrypted
    
    # Пытаемся получить операции из Sandbox API
    try:
        import requests
        
        # Получаем аккаунты
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        accounts_response = requests.post(
            "https://sandbox-invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts",
            headers=headers,
            json={},
            timeout=10
        )
        
        if accounts_response.status_code != 200:
            # Токен невалидный - добавляем демо-транзакции
            return await _add_demo_transactions(db, current_user)
        
        accounts_data = accounts_response.json()
        accounts = accounts_data.get("accounts", [])
        
        if not accounts:
            # Создаём аккаунт
            create_response = requests.post(
                "https://sandbox-invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.SandboxService/OpenSandboxAccount",
                headers=headers,
                json={},
                timeout=10
            )
            if create_response.status_code == 200:
                accounts_data = create_response.json()
                account_id = accounts_data.get("accountId")
            else:
                return await _add_demo_transactions(db, current_user)
        else:
            account_id = accounts[0].get("id")
        
        # Получаем операции
        from datetime import timedelta
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        
        operations_response = requests.post(
            "https://sandbox-invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.OperationsService/GetOperations",
            headers=headers,
            json={
                "accountId": account_id,
                "from": week_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            timeout=10
        )
        
        if operations_response.status_code != 200:
            return await _add_demo_transactions(db, current_user)
        
        operations = operations_response.json().get("operations", [])
        
        if not operations:
            # Нет операций - добавляем демо
            return await _add_demo_transactions(db, current_user)
        
        # Обрабатываем реальные операции
        added_count = 0
        other_category = db.query(Category).filter(Category.code == "other").first()
        
        for op in operations:
            external_id = op.get("id")
            
            # Проверяем что такой транзакции ещё нет
            existing = db.query(Transaction).filter(
                Transaction.external_id == external_id,
                Transaction.user_id == current_user.id
            ).first()
            
            if existing:
                continue
            
            # Извлекаем сумму
            payment = op.get("payment", {})
            units = int(payment.get("units", 0))
            nano = int(payment.get("nano", 0))
            amount = Decimal(str(units)) + Decimal(str(nano)) / Decimal("1000000000")
            
            if amount == 0:
                continue
            
            transaction = Transaction(
                user_id=current_user.id,
                amount=amount,
                currency=payment.get("currency", "RUB"),
                description=op.get("description") or op.get("type", "Операция Т-Банк"),
                category_id=other_category.id if other_category else None,
                source=TransactionSource.tbank_api,
                external_id=external_id,
                transaction_date=datetime.fromisoformat(op.get("date", now.isoformat()).replace("Z", "")),
            )
            db.add(transaction)
            added_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Синхронизировано {added_count} транзакций из Т-Банка",
            "transactions_added": added_count,
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Таймаут запроса к Т-Банк API")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="Не удалось подключиться к Т-Банк API")
    except HTTPException:
        raise  # Пробрасываем HTTPException без изменений
    except Exception as e:
        logger.error(f"Неожиданная ошибка при синхронизации Т-Банк: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка при синхронизации")

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
