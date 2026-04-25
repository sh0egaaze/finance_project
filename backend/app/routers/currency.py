"""
Роутер для курсов валют
"""
from datetime import datetime
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import CurrencyRate

router = APIRouter(prefix="/currency", tags=["currency"])


class CurrencyRateResponse(BaseModel):
    base_currency: str
    target_currency: str
    rate: float
    rate_date: datetime
    change: float = 0


@router.get("/rates", response_model=List[CurrencyRateResponse])
async def get_rates(db: Session = Depends(get_db)):
    """Получить актуальные курсы валют"""
    # Проверяем есть ли курсы в БД
    rates = db.query(CurrencyRate).filter(
        CurrencyRate.base_currency == "RUB"
    ).order_by(CurrencyRate.rate_date.desc()).limit(5).all()
    
    if not rates:
        # Возвращаем дефолтные курсы
        default_rates = [
            {"base_currency": "RUB", "target_currency": "USD", "rate": 0.011, "change": 0.2},
            {"base_currency": "RUB", "target_currency": "EUR", "rate": 0.010, "change": -0.1},
            {"base_currency": "RUB", "target_currency": "CNY", "rate": 0.079, "change": 0.3},
            {"base_currency": "RUB", "target_currency": "GBP", "rate": 0.009, "change": 0.1},
        ]
        now = datetime.utcnow()
        return [
            CurrencyRateResponse(
                base_currency=r["base_currency"],
                target_currency=r["target_currency"],
                rate=r["rate"],
                rate_date=now,
                change=r["change"]
            )
            for r in default_rates
        ]
    
    return [
        CurrencyRateResponse(
            base_currency=r.base_currency,
            target_currency=r.target_currency,
            rate=float(r.rate),
            rate_date=r.rate_date,
            change=0
        )
        for r in rates
    ]


@router.post("/convert")
async def convert_currency(
    amount: float,
    from_currency: str = "RUB",
    to_currency: str = "USD",
    db: Session = Depends(get_db)
):
    """Конвертировать валюту"""
    # Простая конвертация
    rates = {
        ("RUB", "USD"): 0.011,
        ("RUB", "EUR"): 0.010,
        ("RUB", "CNY"): 0.079,
        ("USD", "RUB"): 90.5,
        ("EUR", "RUB"): 98.2,
    }
    
    key = (from_currency, to_currency)
    if key in rates:
        converted = amount * rates[key]
    elif from_currency == to_currency:
        converted = amount
    else:
        converted = amount  # Не знаем курс
    
    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "original_amount": amount,
        "converted_amount": round(converted, 2),
    }
