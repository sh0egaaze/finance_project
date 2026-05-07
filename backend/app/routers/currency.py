"""
Роутер для курсов валют с реальным API
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
import httpx
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.database import get_db
from app.models import CurrencyRate
from app.config import get_settings

router = APIRouter(prefix="/currency", tags=["currency"])
logger = logging.getLogger(__name__)

# Метаинформация о валютах
CURRENCY_INFO = {
    "USD": {"name": "Доллар США", "flag": "🇺🇸"},
    "EUR": {"name": "Евро", "flag": "🇪🇺"},
    "GBP": {"name": "Фунт стерлингов", "flag": "🇬🇧"},
    "CNY": {"name": "Китайский юань", "flag": "🇨🇳"},
    "JPY": {"name": "Японская иена", "flag": "🇯🇵"},
    "TRY": {"name": "Турецкая лира", "flag": "🇹🇷"},
    "KZT": {"name": "Казахстанский тенге", "flag": "🇰🇿"},
    "BYN": {"name": "Белорусский рубль", "flag": "🇧🇾"},
    "CHF": {"name": "Швейцарский франк", "flag": "🇨🇭"},
    "AED": {"name": "Дирхам ОАЭ", "flag": "🇦🇪"},
}

# Основные валюты для отображения
MAIN_CURRENCIES = ["USD", "EUR", "CNY", "GBP", "TRY", "KZT"]


async def fetch_rates_from_api() -> Optional[dict]:
    """Получить курсы из внешнего API"""
    settings = get_settings()
    
    # exchangerate-api.com (бесплатный тариф)
    # Формат: https://v6.exchangerate-api.com/v6/YOUR_API_KEY/latest/RUB
    # Или бесплатный без ключа: https://api.exchangerate-api.com/v4/latest/RUB
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Пробуем с ключом
            if settings.CURRENCY_API_KEY:
                url = f"https://v6.exchangerate-api.com/v6/{settings.CURRENCY_API_KEY}/latest/RUB"
            else:
                # Бесплатный вариант без ключа
                url = "https://api.exchangerate-api.com/v4/latest/RUB"
            
            response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Currency API error: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Currency API request failed: {e}")
        return None


def save_rates_to_db(db: Session, api_data: dict) -> None:
    """Сохранить курсы в БД"""
    now = datetime.now(timezone.utc)
    rates = api_data.get("rates") or api_data.get("conversion_rates", {})
    
    for currency in MAIN_CURRENCIES:
        if currency in rates:
            # API возвращает сколько единиц валюты за 1 RUB
            # Нам нужно: сколько RUB за 1 единицу валюты
            rate_from_api = rates[currency]
            if rate_from_api > 0:
                rate_value = 1 / rate_from_api
            else:
                continue
            
            # Проверяем, есть ли уже запись за сегодня
            existing = db.query(CurrencyRate).filter(
                CurrencyRate.base_currency == "RUB",
                CurrencyRate.target_currency == currency,
                CurrencyRate.rate_date >= now.replace(hour=0, minute=0, second=0, microsecond=0)
            ).first()
            
            if existing:
                existing.rate = Decimal(str(round(rate_value, 6)))
                existing.rate_date = now
            else:
                new_rate = CurrencyRate(
                    base_currency="RUB",
                    target_currency=currency,
                    rate=Decimal(str(round(rate_value, 6))),
                    rate_date=now,
                    source="exchangerate-api.com"
                )
                db.add(new_rate)
    
    db.commit()


def get_rate_change(db: Session, currency: str) -> float:
    """Получить изменение курса за день"""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    
    # Текущий курс
    current = db.query(CurrencyRate).filter(
        CurrencyRate.base_currency == "RUB",
        CurrencyRate.target_currency == currency
    ).order_by(desc(CurrencyRate.rate_date)).first()
    
    # Вчерашний курс
    old = db.query(CurrencyRate).filter(
        CurrencyRate.base_currency == "RUB",
        CurrencyRate.target_currency == currency,
        CurrencyRate.rate_date < now.replace(hour=0, minute=0, second=0)
    ).order_by(desc(CurrencyRate.rate_date)).first()
    
    if current and old and old.rate > 0:
        change = ((float(current.rate) - float(old.rate)) / float(old.rate)) * 100
        return round(change, 2)
    
    return 0.0


@router.get("/rates")
async def get_rates(db: Session = Depends(get_db)):
    """Получить актуальные курсы валют"""
    now = datetime.now(timezone.utc)
    
    # Проверяем, когда последний раз обновляли курсы
    latest = db.query(CurrencyRate).order_by(desc(CurrencyRate.rate_date)).first()
    
    # Если курсов нет или они старше 1 часа — обновляем из API
    need_update = (
        not latest or 
        (now - latest.rate_date.replace(tzinfo=timezone.utc)) > timedelta(hours=1)
    )
    
    if need_update:
        api_data = await fetch_rates_from_api()
        if api_data:
            save_rates_to_db(db, api_data)
    
    # Получаем курсы из БД
    rates_list = []
    for currency in MAIN_CURRENCIES:
        rate_record = db.query(CurrencyRate).filter(
            CurrencyRate.base_currency == "RUB",
            CurrencyRate.target_currency == currency
        ).order_by(desc(CurrencyRate.rate_date)).first()
        
        if rate_record:
            info = CURRENCY_INFO.get(currency, {"name": currency, "flag": "🏳️"})
            change = get_rate_change(db, currency)
            
            rates_list.append({
                "currency": currency,
                "rate": round(float(rate_record.rate), 2),
                "change": change,
                "name": info["name"],
                "flag": info["flag"],
            })
    
    # Если БД пустая — вернём fallback
    if not rates_list:
        rates_list = [
            {"currency": "USD", "rate": 92.50, "change": 0.0, "name": "Доллар США", "flag": "🇺🇸"},
            {"currency": "EUR", "rate": 100.20, "change": 0.0, "name": "Евро", "flag": "🇪🇺"},
            {"currency": "CNY", "rate": 12.80, "change": 0.0, "name": "Китайский юань", "flag": "🇨🇳"},
            {"currency": "GBP", "rate": 117.30, "change": 0.0, "name": "Фунт стерлингов", "flag": "🇬🇧"},
        ]
    
    return {
        "base": "RUB",
        "date": now.isoformat(),
        "rates": rates_list,
    }


class ConvertRequest(BaseModel):
    amount: float
    from_currency: str = "RUB"
    to_currency: str = "USD"


@router.post("/convert")
async def convert_currency(data: ConvertRequest, db: Session = Depends(get_db)):
    """Конвертировать валюту"""
    amount = data.amount
    from_currency = data.from_currency.upper()
    to_currency = data.to_currency.upper()

    def get_rub_rate(currency: str) -> float:
        """Получить курс к рублю (сколько рублей за 1 единицу)"""
        if currency == "RUB":
            return 1.0
        
        rate_record = db.query(CurrencyRate).filter(
            CurrencyRate.base_currency == "RUB",
            CurrencyRate.target_currency == currency
        ).order_by(desc(CurrencyRate.rate_date)).first()
        
        if rate_record:
            return float(rate_record.rate)
        
        # Fallback
        fallback = {"USD": 92.5, "EUR": 100.2, "CNY": 12.8, "GBP": 117.3}
        return fallback.get(currency, 1.0)

    from_rate = get_rub_rate(from_currency)
    to_rate = get_rub_rate(to_currency)

    # Конвертируем: сначала в рубли, потом в целевую валюту
    amount_in_rub = amount * from_rate
    converted = amount_in_rub / to_rate

    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "original_amount": amount,
        "converted_amount": round(converted, 2),
        "result": round(converted, 2),
        "rate": round(from_rate / to_rate, 6),
    }


@router.post("/refresh")
async def refresh_rates(db: Session = Depends(get_db)):
    """Принудительно обновить курсы из API"""
    api_data = await fetch_rates_from_api()
    
    if not api_data:
        raise HTTPException(status_code=503, detail="Не удалось получить курсы из API")
    
    save_rates_to_db(db, api_data)
    
    return {"message": "Курсы обновлены", "updated_at": datetime.now(timezone.utc).isoformat()}