"""
Сервис интеграции с Т-Банк Sandbox API (Invest API)
Документация: https://tinkoff.github.io/investAPI/
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import httpx
from loguru import logger

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
            date_from = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            date_to = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            
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
        from ..models import Transaction, Category
        from ..ml.categorizer import MLCategorizer
        
        # Получаем операции
        operations = await self.get_operations(days)
        
        if not operations:
            return 0
        
        categorizer = MLCategorizer()
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
            
            # Определяем категорию через ML
            cat_result = categorizer.predict(description)
            category_code = cat_result.get("category", "other")
            confidence = Decimal(str(cat_result.get("confidence", 0.5)))
            
            category = categories.get(category_code) or categories.get("other")
            
            # Парсим дату
            op_date = op.get("date", "")
            try:
                transaction_date = datetime.fromisoformat(op_date.replace("Z", "+00:00"))
            except:
                transaction_date = datetime.utcnow()
            
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
            db_session.add(transaction)
            new_count += 1
        
        if new_count > 0:
            db_session.commit()
            logger.info(f"Синхронизировано {new_count} транзакций из Т-Банк для пользователя {user_id}")
        
        return new_count
