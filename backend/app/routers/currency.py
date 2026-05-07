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
    # Основные мировые
    "USD": {"name": "Доллар США", "flag": "🇺🇸"},
    "EUR": {"name": "Евро", "flag": "🇪🇺"},
    "GBP": {"name": "Фунт стерлингов", "flag": "🇬🇧"},
    "CHF": {"name": "Швейцарский франк", "flag": "🇨🇭"},
    "JPY": {"name": "Японская иена", "flag": "🇯🇵"},
    
    # Азия
    "CNY": {"name": "Китайский юань", "flag": "🇨🇳"},
    "HKD": {"name": "Гонконгский доллар", "flag": "🇭🇰"},
    "SGD": {"name": "Сингапурский доллар", "flag": "🇸🇬"},
    "KRW": {"name": "Южнокорейская вона", "flag": "🇰🇷"},
    "INR": {"name": "Индийская рупия", "flag": "🇮🇳"},
    "THB": {"name": "Тайский бат", "flag": "🇹🇭"},
    "VND": {"name": "Вьетнамский донг", "flag": "🇻🇳"},
    "IDR": {"name": "Индонезийская рупия", "flag": "🇮🇩"},
    "MYR": {"name": "Малайзийский ринггит", "flag": "🇲🇾"},
    "PHP": {"name": "Филиппинское песо", "flag": "🇵🇭"},
    
    # СНГ и соседи
    "KZT": {"name": "Казахстанский тенге", "flag": "🇰🇿"},
    "BYN": {"name": "Белорусский рубль", "flag": "🇧🇾"},
    "UAH": {"name": "Украинская гривна", "flag": "🇺🇦"},
    "UZS": {"name": "Узбекский сум", "flag": "🇺🇿"},
    "GEL": {"name": "Грузинский лари", "flag": "🇬🇪"},
    "AMD": {"name": "Армянский драм", "flag": "🇦🇲"},
    "AZN": {"name": "Азербайджанский манат", "flag": "🇦🇿"},
    "MDL": {"name": "Молдавский лей", "flag": "🇲🇩"},
    "KGS": {"name": "Киргизский сом", "flag": "🇰🇬"},
    "TJS": {"name": "Таджикский сомони", "flag": "🇹🇯"},
    
    # Ближний Восток
    "TRY": {"name": "Турецкая лира", "flag": "🇹🇷"},
    "AED": {"name": "Дирхам ОАЭ", "flag": "🇦🇪"},
    "SAR": {"name": "Саудовский риял", "flag": "🇸🇦"},
    "ILS": {"name": "Израильский шекель", "flag": "🇮🇱"},
    "QAR": {"name": "Катарский риал", "flag": "🇶🇦"},
    "KWD": {"name": "Кувейтский динар", "flag": "🇰🇼"},
    "BHD": {"name": "Бахрейнский динар", "flag": "🇧🇭"},
    "OMR": {"name": "Оманский риал", "flag": "🇴🇲"},
    "EGP": {"name": "Египетский фунт", "flag": "🇪🇬"},
    
    # Америка
    "CAD": {"name": "Канадский доллар", "flag": "🇨🇦"},
    "MXN": {"name": "Мексиканское песо", "flag": "🇲🇽"},
    "BRL": {"name": "Бразильский реал", "flag": "🇧🇷"},
    "ARS": {"name": "Аргентинское песо", "flag": "🇦🇷"},
    "CLP": {"name": "Чилийское песо", "flag": "🇨🇱"},
    "COP": {"name": "Колумбийское песо", "flag": "🇨🇴"},
    "PEN": {"name": "Перуанский соль", "flag": "🇵🇪"},
    
    # Европа
    "PLN": {"name": "Польский злотый", "flag": "🇵🇱"},
    "CZK": {"name": "Чешская крона", "flag": "🇨🇿"},
    "HUF": {"name": "Венгерский форинт", "flag": "🇭🇺"},
    "RON": {"name": "Румынский лей", "flag": "🇷🇴"},
    "BGN": {"name": "Болгарский лев", "flag": "🇧🇬"},
    "HRK": {"name": "Хорватская куна", "flag": "🇭🇷"},
    "RSD": {"name": "Сербский динар", "flag": "🇷🇸"},
    "SEK": {"name": "Шведская крона", "flag": "🇸🇪"},
    "NOK": {"name": "Норвежская крона", "flag": "🇳🇴"},
    "DKK": {"name": "Датская крона", "flag": "🇩🇰"},
    "ISK": {"name": "Исландская крона", "flag": "🇮🇸"},
    
    # Океания и Африка
    "AUD": {"name": "Австралийский доллар", "flag": "🇦🇺"},
    "NZD": {"name": "Новозеландский доллар", "flag": "🇳🇿"},
    "ZAR": {"name": "Южноафриканский рэнд", "flag": "🇿🇦"},
    "NGN": {"name": "Нигерийская найра", "flag": "🇳🇬"},
    "MAD": {"name": "Марокканский дирхам", "flag": "🇲🇦"},
}

# Валюты для отображения (можно регулировать)
MAIN_CURRENCIES = [
    # Топ мировые
    "USD", "EUR", "GBP", "CHF", "JPY",
    # Азия
    "CNY", "HKD", "SGD", "KRW", "INR", "THB",
    # СНГ
    "KZT", "BYN", "UAH", "UZS", "GEL", "AMD", "AZN",
    # Ближний Восток
    "TRY", "AED", "SAR", "ILS",
    # Америка
    "CAD", "MXN", "BRL",
    # Европа
    "PLN", "CZK", "SEK", "NOK", "DKK",
    # Океания
    "AUD", "NZD",
]


async def fetch_rates_from_api() -> Optional[dict]:
    """Получить курсы из внешнего API"""
    settings = get_settings()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if settings.CURRENCY_API_KEY:
                url = f"https://v6.exchangerate-api.com/v6/{settings.CURRENCY_API_KEY}/latest/RUB"
            else:
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
    """Сохранить курсы в БД (добавляем новые записи, не перезаписываем)"""
    now = datetime.now(timezone.utc)
    rates = api_data.get("rates") or api_data.get("conversion_rates", {})
    
    for currency in MAIN_CURRENCIES:
        if currency in rates:
            rate_from_api = rates[currency]
            if rate_from_api > 0:
                rate_value = 1 / rate_from_api
            else:
                continue
            
            new_rate = CurrencyRate(
                base_currency="RUB",
                target_currency=currency,
                rate=Decimal(str(round(rate_value, 6))),
                rate_date=now,
                source="exchangerate-api.com"
            )
            db.add(new_rate)
    
    db.commit()
    
    # Удаляем старые записи (оставляем только за последние 7 дней)
    week_ago = now - timedelta(days=7)
    db.query(CurrencyRate).filter(CurrencyRate.rate_date < week_ago).delete()
    db.commit()


def get_rate_change(db: Session, currency: str, current_rate: float) -> float:
    """Получить изменение курса по сравнению с предыдущей записью"""
    records = db.query(CurrencyRate).filter(
        CurrencyRate.base_currency == "RUB",
        CurrencyRate.target_currency == currency
    ).order_by(desc(CurrencyRate.rate_date)).limit(2).all()
    
    if len(records) >= 2:
        previous_rate = float(records[1].rate)
        if previous_rate > 0:
            change = ((current_rate - previous_rate) / previous_rate) * 100
            return round(change, 2)
    
    return 0.0


@router.get("/rates")
async def get_rates(db: Session = Depends(get_db)):
    """Получить актуальные курсы валют"""
    now = datetime.now(timezone.utc)
    
    latest = db.query(CurrencyRate).order_by(desc(CurrencyRate.rate_date)).first()
    
    need_update = False
    if not latest:
        need_update = True
    else:
        latest_date = latest.rate_date
        if latest_date.tzinfo is None:
            latest_date = latest_date.replace(tzinfo=timezone.utc)
        if (now - latest_date) > timedelta(hours=1):
            need_update = True
    
    if need_update:
        api_data = await fetch_rates_from_api()
        if api_data:
            save_rates_to_db(db, api_data)
    
    rates_list = []
    for currency in MAIN_CURRENCIES:
        rate_record = db.query(CurrencyRate).filter(
            CurrencyRate.base_currency == "RUB",
            CurrencyRate.target_currency == currency
        ).order_by(desc(CurrencyRate.rate_date)).first()
        
        if rate_record:
            info = CURRENCY_INFO.get(currency, {"name": currency, "flag": "🏳️"})
            current_rate = round(float(rate_record.rate), 2)
            change = get_rate_change(db, currency, current_rate)
            
            rates_list.append({
                "currency": currency,
                "rate": current_rate,
                "change": change,
                "name": info["name"],
                "flag": info["flag"],
            })
    
    if not rates_list:
        rates_list = [
            {"currency": "USD", "rate": 92.50, "change": 0.0, "name": "Доллар США", "flag": "🇺🇸"},
            {"currency": "EUR", "rate": 100.20, "change": 0.0, "name": "Евро", "flag": "🇪🇺"},
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
        if currency == "RUB":
            return 1.0
        
        rate_record = db.query(CurrencyRate).filter(
            CurrencyRate.base_currency == "RUB",
            CurrencyRate.target_currency == currency
        ).order_by(desc(CurrencyRate.rate_date)).first()
        
        if rate_record:
            return float(rate_record.rate)
        
        return 1.0

    from_rate = get_rub_rate(from_currency)
    to_rate = get_rub_rate(to_currency)

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