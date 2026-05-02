"""
Сервис для работы с курсами валют
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import httpx
from loguru import logger

from ..models.currency_rate import CurrencyRate
from ..schemas.currency import CurrencyRateResponse, CurrencyConvertResponse
from ..config import get_settings

settings = get_settings()


class CurrencyService:
    """Сервис для получения и конвертации валют"""
    
    # Основные валюты для отслеживания
    TRACKED_CURRENCIES = ["USD", "EUR", "CNY", "GBP", "JPY", "TRY", "KZT", "BYN"]
    BASE_CURRENCY = "RUB"
    
    @staticmethod
    async def fetch_rates_from_api() -> Dict[str, float]:
        """
        Получить актуальные курсы из внешнего API.
        Возвращает словарь {валюта: курс к RUB}
        """
        try:
            async with httpx.AsyncClient() as client:
                # Используем exchangerate-api.com (бесплатный)
                response = await client.get(
                    f"{settings.CURRENCY_API_URL}/RUB",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                rates = {}
                for currency in CurrencyService.TRACKED_CURRENCIES:
                    if currency in data.get("rates", {}):
                        # API возвращает сколько валюты за 1 RUB
                        # Нам нужно сколько RUB за 1 единицу валюты
                        rates[currency] = 1 / data["rates"][currency]
                
                return rates
        except Exception as e:
            logger.error(f"Ошибка получения курсов валют: {e}")
            return {}
    
    @staticmethod
    async def update_rates(db: Session) -> List[CurrencyRate]:
        """Обновить курсы валют в базе данных"""
        rates_data = await CurrencyService.fetch_rates_from_api()
        
        if not rates_data:
            logger.warning("Не удалось получить курсы валют")
            return []
        
        created_rates = []
        now = datetime.now(timezone.utc)
        
        for currency, rate in rates_data.items():
            currency_rate = CurrencyRate(
                base_currency=currency,
                target_currency=CurrencyService.BASE_CURRENCY,
                rate=rate,
                rate_date=now,
                source="exchangerate-api.com"
            )
            db.add(currency_rate)
            created_rates.append(currency_rate)
        
        db.commit()
        logger.info(f"Обновлено {len(created_rates)} курсов валют")
        return created_rates
    
    @staticmethod
    def get_latest_rates(db: Session) -> List[CurrencyRateResponse]:
        """Получить последние курсы валют"""
        rates = []
        
        for currency in CurrencyService.TRACKED_CURRENCIES:
            # Получаем последний курс
            latest = db.query(CurrencyRate).filter(
                and_(
                    CurrencyRate.base_currency == currency,
                    CurrencyRate.target_currency == CurrencyService.BASE_CURRENCY
                )
            ).order_by(desc(CurrencyRate.rate_date)).first()
            
            if latest:
                # Получаем вчерашний курс для расчёта изменения
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                previous = db.query(CurrencyRate).filter(
                    and_(
                        CurrencyRate.base_currency == currency,
                        CurrencyRate.target_currency == CurrencyService.BASE_CURRENCY,
                        CurrencyRate.rate_date < yesterday
                    )
                ).order_by(desc(CurrencyRate.rate_date)).first()
                
                change_percent = None
                if previous:
                    change_percent = ((latest.rate - previous.rate) / previous.rate) * 100
                
                rates.append(CurrencyRateResponse(
                    base_currency=latest.base_currency,
                    target_currency=latest.target_currency,
                    rate=latest.rate,
                    rate_date=latest.rate_date,
                    change_percent=change_percent,
                    source=latest.source
                ))
        
        return rates
    
    @staticmethod
    def get_rate(
        db: Session,
        from_currency: str,
        to_currency: str
    ) -> Optional[float]:
        """Получить курс между двумя валютами"""
        # Если валюты одинаковые
        if from_currency == to_currency:
            return 1.0
        
        # Если конвертируем в RUB
        if to_currency == CurrencyService.BASE_CURRENCY:
            rate = db.query(CurrencyRate).filter(
                and_(
                    CurrencyRate.base_currency == from_currency,
                    CurrencyRate.target_currency == to_currency
                )
            ).order_by(desc(CurrencyRate.rate_date)).first()
            return rate.rate if rate else None
        
        # Если конвертируем из RUB
        if from_currency == CurrencyService.BASE_CURRENCY:
            rate = db.query(CurrencyRate).filter(
                and_(
                    CurrencyRate.base_currency == to_currency,
                    CurrencyRate.target_currency == from_currency
                )
            ).order_by(desc(CurrencyRate.rate_date)).first()
            return 1 / rate.rate if rate else None
        
        # Кросс-курс через RUB
        rate_from = CurrencyService.get_rate(db, from_currency, CurrencyService.BASE_CURRENCY)
        rate_to = CurrencyService.get_rate(db, to_currency, CurrencyService.BASE_CURRENCY)
        
        if rate_from and rate_to:
            return rate_from / rate_to
        
        return None
    
    @staticmethod
    def convert(
        db: Session,
        amount: float,
        from_currency: str,
        to_currency: str
    ) -> Optional[CurrencyConvertResponse]:
        """Конвертировать сумму из одной валюты в другую"""
        rate = CurrencyService.get_rate(db, from_currency, to_currency)
        
        if rate is None:
            return None
        
        converted = amount * rate
        
        return CurrencyConvertResponse(
            original_amount=amount,
            converted_amount=round(converted, 2),
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            rate_date=datetime.now(timezone.utc)
        )
    
    @staticmethod
    def get_historical_rates(
        db: Session,
        currency: str,
        days: int = 30
    ) -> List[CurrencyRate]:
        """Получить историю курса валюты"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        return db.query(CurrencyRate).filter(
            and_(
                CurrencyRate.base_currency == currency,
                CurrencyRate.target_currency == CurrencyService.BASE_CURRENCY,
                CurrencyRate.rate_date >= start_date
            )
        ).order_by(CurrencyRate.rate_date.asc()).all()
