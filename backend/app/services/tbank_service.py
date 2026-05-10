"""
Сервис интеграции с Т-Банк Sandbox API (Invest API)
Документация: https://tbank.github.io/investAPI/
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import httpx
from loguru import logger
from ..ml.anomaly_detector import detect_anomaly
from sqlalchemy import func as sql_func
from ..models import Transaction, Category
from ..ml.categorizer import categorize

from ..config import get_settings

settings = get_settings()


class TBankService:
    """
    Сервис для работы с Т-Банк Sandbox Invest API.
    Получает информацию о счетах и портфеле из песочницы.
    """
    
    SANDBOX_URL = "https://sandbox-invest-public-api.tinkoff.ru/rest"
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Проверить подключение и получить информацию об аккаунтах"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.SANDBOX_URL}/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts",
                    headers=self.headers,
                    json={}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    accounts = data.get("accounts", [])
                    return {
                        "connected": True,
                        "accounts_count": len(accounts),
                        "accounts": accounts
                    }
                else:
                    logger.error(f"Т-Банк API ответил: {response.status_code} - {response.text}")
                    return {"connected": False, "error": response.text}
                    
        except Exception as e:
            logger.error(f"Ошибка подключения к Т-Банк API: {e}")
            return {"connected": False, "error": str(e)}
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Получить информацию о первом аккаунте песочницы"""
        try:
            # Получаем список аккаунтов
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.SANDBOX_URL}/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts",
                    headers=self.headers,
                    json={}
                )
                
                if response.status_code != 200:
                    return None
                
                accounts = response.json().get("accounts", [])
                if not accounts:
                    # Создаём аккаунт если нет
                    create_resp = await client.post(
                        f"{self.SANDBOX_URL}/tinkoff.public.invest.api.contract.v1.SandboxService/OpenSandboxAccount",
                        headers=self.headers,
                        json={}
                    )
                    if create_resp.status_code == 200:
                        account_id = create_resp.json().get("accountId")
                        accounts = [{"id": account_id, "type": "ACCOUNT_TYPE_TINKOFF", "status": "ACCOUNT_STATUS_OPEN"}]
                
                if not accounts:
                    return None
                
                account = accounts[0]
                account_id = account.get("id") or account.get("accountId")
                
                # Получаем портфель (баланс)
                portfolio_resp = await client.post(
                    f"{self.SANDBOX_URL}/tinkoff.public.invest.api.contract.v1.OperationsService/GetPortfolio",
                    headers=self.headers,
                    json={"accountId": account_id}
                )
                
                balance = Decimal("0")
                if portfolio_resp.status_code == 200:
                    portfolio = portfolio_resp.json()
                    # Получаем total_amount_currencies (рублёвый баланс)
                    total = portfolio.get("totalAmountCurrencies", {})
                    units = int(total.get("units", 0))
                    nano = int(total.get("nano", 0))
                    balance = Decimal(str(units)) + Decimal(str(nano)) / Decimal("1000000000")
                
                return {
                    "account_id": account_id,
                    "type": account.get("type", "SANDBOX"),
                    "status": account.get("status", "OPEN"),
                    "balance": balance,
                    "currency": "RUB"
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения информации об аккаунте: {e}")
            return None
    
    async def get_operations(self, days: int = 30) -> List[Dict[str, Any]]:
        """Получить операции из песочницы"""
        try:
            # Сначала получаем аккаунт
            account_info = await self.get_account_info()
            if not account_info:
                return []
            
            account_id = account_info["account_id"]
            
            # Получаем операции
            date_from = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            date_to = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.SANDBOX_URL}/tinkoff.public.invest.api.contract.v1.OperationsService/GetOperations",
                    headers=self.headers,
                    json={
                        "accountId": account_id,
                        "from": date_from,
                        "to": date_to
                    }
                )
                
                if response.status_code == 200:
                    return response.json().get("operations", [])
                    
        except Exception as e:
            logger.error(f"Ошибка получения операций: {e}")
        
        return []
    
    async def sync_transactions(self, db_session, user_id: int, days: int = 30) -> int:
        """
        Синхронизировать операции из Т-Банк API в транзакции приложения.
        Возвращает количество добавленных транзакций.
        """

        # Получаем операции
        operations = await self.get_operations(days)
        
        if not operations:
            return 0
        
        new_count = 0
        
        # Получаем категории для маппинга
        categories = {c.code: c for c in db_session.query(Category).all()}
        
        for op in operations:
            external_id = op.get("id", "")
            
            if not external_id:
                continue
            
            # Проверяем, есть ли уже такая транзакция
            existing = db_session.query(Transaction).filter(
                Transaction.external_id == external_id,
                Transaction.user_id == user_id
            ).first()
            
            if existing:
                continue
            
            # Парсим сумму
            payment = op.get("payment", {})
            units = int(payment.get("units", 0))
            nano = int(payment.get("nano", 0))
            amount = Decimal(str(units)) + Decimal(str(nano)) / Decimal("1000000000")
            
            if amount == 0:
                continue
            
            description = op.get("description", "") or op.get("name", "") or "Операция Т-Банк"
            
            # Определяем тип операции Т-Банк
            op_type = op.get("operationType", "")
            op_state = op.get("state", "")
            
            # Для инвестиционных операций — категория "Другое" или "Переводы"
            if op_type in ("OPERATION_TYPE_BUY", "OPERATION_TYPE_SELL", 
                           "OPERATION_TYPE_BROKER_FEE", "OPERATION_TYPE_INPUT",
                           "OPERATION_TYPE_OUTPUT"):
                if op_type == "OPERATION_TYPE_BUY":
                    description = f"Покупка: {op.get('name', '') or op.get('description', 'ценные бумаги')}"
                    category_code = "shopping"
                elif op_type == "OPERATION_TYPE_SELL":
                    description = f"Продажа: {op.get('name', '') or op.get('description', 'ценные бумаги')}"
                    category_code = "salary"
                elif op_type == "OPERATION_TYPE_BROKER_FEE":
                    description = f"Комиссия брокера"
                    category_code = "other"
                elif op_type == "OPERATION_TYPE_INPUT":
                    description = f"Пополнение брокерского счёта"
                    category_code = "transfers"
                elif op_type == "OPERATION_TYPE_OUTPUT":
                    description = f"Вывод с брокерского счёта"
                    category_code = "transfers"
                confidence = Decimal("0.95")
            else:
                # Для остальных — пробуем ML
                cat_result = categorize(description)
                category_code = cat_result.category_code
                confidence = Decimal(str(cat_result.confidence))
            
            category = categories.get(category_code) or categories.get("other")
            
            # Парсим дату
            op_date = op.get("date", "")
            try:
                transaction_date = datetime.fromisoformat(op_date.replace("Z", "+00:00"))
            except:
                transaction_date = datetime.now(timezone.utc)
            
            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                currency=payment.get("currency", "RUB").upper(),
                description=description,
                category_id=category.id if category else None,
                category_confidence=confidence,
                category_manual=False,
                source="tbank_api",
                external_id=external_id,
                transaction_date=transaction_date
            )
            
            # Проверка на подозрительность
            try:
                abs_amount = abs(float(amount))
                hour = transaction_date.hour
                day_of_week = transaction_date.weekday()
                
                three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
                user_avg = db_session.query(sql_func.avg(sql_func.abs(Transaction.amount))).filter(
                    Transaction.user_id == user_id,
                    Transaction.transaction_date >= three_months_ago
                ).scalar() or abs_amount
                
                cat_code = category.code if category else "other"
                
                result = detect_anomaly({
                    "amount": abs_amount,
                    "hour": hour,
                    "day_of_week": day_of_week,
                    "category": cat_code,
                    "user_avg_amount": float(user_avg),
                    "is_weekend": 1 if day_of_week >= 5 else 0,
                })
                if result.get("is_suspicious"):
                    transaction.is_suspicious = True
                    transaction.suspicious_reason = result.get("reason") or "Нетипичная транзакция"
            except Exception as e:
                logger.warning(f"ML check failed for tbank tx: {e}")
                # Fallback эвристики
                abs_amount = abs(float(amount))
                if abs_amount > 30000:
                    transaction.is_suspicious = True
                    transaction.suspicious_reason = f"Крупная сумма: {abs_amount:,.0f}₽".replace(",", " ")
            
            db_session.add(transaction)
            new_count += 1
        
        if new_count > 0:
            db_session.commit()
            logger.info(f"Синхронизировано {new_count} транзакций из Т-Банк для пользователя {user_id}")
        
        return new_count
