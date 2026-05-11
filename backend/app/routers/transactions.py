"""
Роутер для транзакций
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Path, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, condecimal, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import Transaction, Category, User
from app.routers.auth import get_current_user
from app.ml.model_loader import registry
import logging
from app.ml.categorizer import categorize
from app.ml.anomaly_detector import detect_anomaly
from sqlalchemy import func as sql_func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["Транзакции"])

limiter = Limiter(key_func=get_remote_address)


# ===== Pydantic схемы =====
class TransactionCreate(BaseModel):
    """Схема для создания транзакции"""
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Описание транзакции",
        examples=["Покупка в Пятёрочке"]
    )
    amount: Decimal = Field(
        ...,
        gt=0,
        description="Сумма транзакции (всегда положительная, знак определяется is_income)",
        examples=[1500.50]
    )
    is_income: bool = Field(
        ...,
        description="True = доход, False = расход",
        examples=[False]
    )
    category_id: Optional[int] = Field(
        None,
        description="ID категории (опционально)",
        examples=[1]
    )
    transaction_date: Optional[str] = Field(
        None,
        description="Дата транзакции (ISO 8601). По умолчанию — текущая",
        examples=["2024-01-15T14:30:00+00:00"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Покупка в Пятёрочке",
                    "amount": 1500.50,
                    "is_income": False,
                    "category_id": 1,
                    "transaction_date": "2024-01-15T14:30:00+00:00"
                }
            ]
        }
    }


class TransactionUpdate(BaseModel):
    """Схема для обновления транзакции"""
    description: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="Новое описание",
        examples=["Обновлённое описание"]
    )
    amount: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Новая сумма (положительная)",
        examples=[2000.0]
    )
    is_income: Optional[bool] = Field(
        None,
        description="Изменить тип: True = доход, False = расход",
        examples=[False]
    )
    category_id: Optional[int] = Field(
        None,
        description="Новый ID категории",
        examples=[2]
    )
    category_manual: Optional[bool] = Field(
        None,
        description="Была ли категория выбрана вручную",
        examples=[True]
    )
    transaction_date: Optional[str] = Field(
        None,
        description="Новая дата транзакции (ISO 8601)",
        examples=["2024-01-16T10:00:00+00:00"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Обновлённое описание",
                    "amount": 2000.0,
                    "category_id": 2
                }
            ]
        }
    }


class TransactionResponse(BaseModel):
    """Схема ответа с данными транзакции"""
    id: int = Field(..., description="Уникальный идентификатор", examples=[1])
    description: str = Field(..., description="Описание транзакции", examples=["Покупка в магазине"])
    amount: Decimal = Field(..., description="Сумма (отрицательная для расходов)", examples=[-1500.50])
    is_income: bool = Field(..., description="Является ли доходом", examples=[False])
    category_id: Optional[int] = Field(None, description="ID категории", examples=[1])
    transaction_date: Optional[datetime] = Field(None, description="Дата транзакции", examples=["2024-01-15T14:30:00+00:00"])
    created_at: datetime = Field(..., description="Дата создания записи", examples=["2024-01-15T14:30:00+00:00"])
    source: Optional[str] = Field(None, description="Источник: MANUAL, TBANK и т.д.", examples=["MANUAL"])

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "description": "Покупка в Пятёрочке",
                    "amount": -1500.50,
                    "is_income": False,
                    "category_id": 1,
                    "transaction_date": "2024-01-15T14:30:00+00:00",
                    "created_at": "2024-01-15T14:30:00+00:00",
                    "source": "MANUAL"
                }
            ]
        }
    }


class TransactionListResponse(BaseModel):
    """Схема ответа со списком транзакций"""
    items: List[dict] = Field(..., description="Список транзакций")
    total: int = Field(..., description="Общее количество транзакций", examples=[142])
    page: int = Field(..., description="Текущая страница", examples=[1])
    per_page: int = Field(..., description="Записей на странице", examples=[20])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [
                        {
                            "id": 1,
                            "description": "Покупка в Пятёрочке",
                            "amount": -1500.50,
                            "is_income": False,
                            "category_id": 1,
                            "transaction_date": "2024-01-15T14:30:00+00:00",
                            "created_at": "2024-01-15T14:30:00+00:00",
                            "source": "MANUAL",
                            "is_suspicious": False,
                            "suspicious_reason": None
                        }
                    ],
                    "total": 142,
                    "page": 1,
                    "per_page": 20
                }
            ]
        }
    }


class TransactionCreateResponse(BaseModel):
    """Схема ответа при создании транзакции"""
    id: int = Field(..., description="ID созданной транзакции", examples=[1])
    description: str = Field(..., description="Описание", examples=["Покупка в магазине"])
    amount: float = Field(..., description="Сумма", examples=[-1500.50])
    is_income: bool = Field(..., description="Является ли доходом", examples=[False])
    category_id: Optional[int] = Field(None, description="ID категории", examples=[1])
    transaction_date: Optional[str] = Field(None, description="Дата транзакции", examples=["2024-01-15T14:30:00+00:00"])
    created_at: Optional[str] = Field(None, description="Дата создания", examples=["2024-01-15T14:30:00+00:00"])
    source: Optional[str] = Field(None, description="Источник", examples=["MANUAL"])


class SmartInputRequest(BaseModel):
    """Схема запроса умного ввода"""
    text: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="Текст для парсинга транзакции на естественном языке",
        examples=["кофе 350р", "зарплата 100000", "такси 500 рублей"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"text": "кофе в старбаксе 450р"},
                {"text": "зарплата 100000"},
                {"text": "такси до работы 500 рублей"}
            ]
        }
    }


class SmartInputResponse(BaseModel):
    """Схема ответа умного ввода (превью)"""
    amount: Optional[float] = Field(None, description="Распознанная сумма", examples=[450.0])
    description: Optional[str] = Field(None, description="Распознанное описание", examples=["кофе в старбаксе"])
    category_id: Optional[int] = Field(None, description="Предложенная категория", examples=[2])
    is_income: bool = Field(False, description="Определён ли как доход", examples=[False])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "amount": 450.0,
                    "description": "кофе в старбаксе",
                    "category_id": 2,
                    "is_income": False
                }
            ]
        }
    }


class UpdateResponse(BaseModel):
    """Схема ответа при обновлении"""
    status: str = Field(..., description="Статус операции", examples=["updated"])


# ===== Вспомогательные функции =====
def get_own_transaction(
    tx_id: int,
    db: Session,
    user: User,
) -> Transaction:
    """Получить транзакцию, принадлежащую пользователю"""
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.user_id == user.id,   
    ).first()
    if not tx:
        raise HTTPException(
            status_code=404,
            detail="Транзакция не найдена или не принадлежит вам",
        )
    return tx


# ===== Эндпоинты =====
@router.get(
    "",
    response_model=TransactionListResponse,
    summary="Получить список транзакций",
    description="""
Возвращает список транзакций пользователя с пагинацией.

**Требуется авторизация.**

**Параметры:**
- `limit` — максимальное количество записей (1-100, по умолчанию 20)
- `offset` — смещение для пагинации (по умолчанию 0)
- `is_suspicious` — фильтр по подозрительным транзакциям

**Сортировка:** по дате транзакции (новые первыми).

**Структура ответа:**
- `items` — массив транзакций
- `total` — общее количество (для пагинации)
- `page` / `per_page` — информация о странице
    """,
    response_description="Список транзакций с пагинацией",
    responses={
        200: {
            "description": "Успешный ответ со списком транзакций",
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
async def get_transactions(
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Максимальное количество записей",
        examples=[20]
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Смещение для пагинации",
        examples=[0]
    ),
    is_suspicious: Optional[bool] = Query(
        None,
        description="Фильтр: только подозрительные (true) или обычные (false)",
        examples=[False]
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Получение списка транзакций с пагинацией.
    
    Возвращает транзакции пользователя, отсортированные по дате (новые первыми).
    Поддерживает фильтрацию по подозрительности.
    """
    query = db.query(Transaction).filter(
        Transaction.user_id == user.id
    )
    
    if is_suspicious is not None:
        if is_suspicious:
            query = query.filter(
                Transaction.is_suspicious == True,
                Transaction.suspicious_dismissed == False
            )
        else:
            query = query.filter(Transaction.is_suspicious == False)
    
    total = query.count()
    
    transactions = query.order_by(
        Transaction.transaction_date.desc()
    ).offset(offset).limit(limit).all()
    
    items = []
    for t in transactions:
        items.append({
            "id": t.id,
            "description": t.description,
            "amount": float(t.amount),
            "is_income": t.amount > 0,
            "category_id": t.category_id,
            "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "source": t.source,
            "is_suspicious": t.is_suspicious,
            "suspicious_reason": t.suspicious_reason,
        })
    
    return {"items": items, "total": total, "page": 1, "per_page": limit}


@router.post(
    "",
    response_model=TransactionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать транзакцию",
    description="""
Создаёт новую транзакцию (доход или расход).

**Требуется авторизация.**

**Обязательные поля:**
- `description` — описание транзакции
- `amount` — сумма (положительное число)
- `is_income` — тип: `true` = доход, `false` = расход

**Опциональные поля:**
- `category_id` — ID категории
- `transaction_date` — дата (по умолчанию текущая)

**Проверка на подозрительность:**

Каждая транзакция проверяется ML-моделью и эвристиками:
- Сумма значительно выше средней для категории
- Крупная транзакция в ночное время (02:00-05:00)
- Сумма превышает 30 000 ₽

Подозрительные транзакции помечаются флагом `is_suspicious`.
    """,
    response_description="Созданная транзакция",
    responses={
        201: {
            "description": "Транзакция успешно создана",
        },
        400: {
            "description": "Ошибка валидации или категория не принадлежит пользователю",
            "content": {
                "application/json": {
                    "example": {"detail": "Ошибка при создании: категория не принадлежит вам"}
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
            "description": "Ошибка валидации данных",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {"loc": ["body", "amount"], "msg": "Input should be greater than 0", "type": "greater_than"}
                        ]
                    }
                }
            }
        }
    }
)
async def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Создание новой транзакции.
    
    Создаёт транзакцию с проверкой на подозрительность
    через ML-модель и эвристические правила.
    """
    from app.ml.anomaly_detector import detect_anomaly
    from sqlalchemy import func as sql_func
    
    tx_date = datetime.now(timezone.utc)
    if data.transaction_date:
        try:
            tx_date = datetime.fromisoformat(data.transaction_date)
        except ValueError:
            pass
    
    amount = data.amount if data.is_income else -data.amount
    
    tx = Transaction(
        user_id=user.id,
        description=data.description,
        amount=amount,
        category_id=data.category_id,
        transaction_date=tx_date,
    )
    
    # === Проверка на подозрительность ===
    abs_amount = abs(float(amount))
    hour = tx_date.hour
    day_of_week = tx_date.weekday()
    
    # Средняя сумма пользователя за 3 месяца
    three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
    user_avg = db.query(sql_func.avg(sql_func.abs(Transaction.amount))).filter(
        Transaction.user_id == user.id,
        Transaction.transaction_date >= three_months_ago
    ).scalar() or abs_amount
    
    # Код категории
    category_code = "other"
    if data.category_id:
        cat = db.query(Category).filter(Category.id == data.category_id).first()
        if cat:
            category_code = cat.code
    
    # ML проверка
    try:
        result = detect_anomaly({
            "amount": abs_amount,
            "hour": hour,
            "day_of_week": day_of_week,
            "category": category_code,
            "user_avg_amount": float(user_avg),
            "is_weekend": 1 if day_of_week >= 5 else 0,
        })
        if result.get("is_suspicious"):
            tx.is_suspicious = True
            tx.suspicious_reason = result.get("reason") or "Нетипичная транзакция"
            logger.info(f"Подозрительно: {abs_amount}₽ — {tx.suspicious_reason}")
    except Exception as e:
        logger.warning(f"ML недоступен: {e}")
    
    # Эвристики (fallback)
    if not tx.is_suspicious and not data.is_income:
        # Средняя по категории
        if data.category_id:
            cat_avg = db.query(sql_func.avg(sql_func.abs(Transaction.amount))).filter(
                Transaction.user_id == user.id,
                Transaction.category_id == data.category_id,
                Transaction.transaction_date >= three_months_ago
            ).scalar()
            if cat_avg and float(cat_avg) > 0 and abs_amount > float(cat_avg) * 3:
                tx.is_suspicious = True
                tx.suspicious_reason = f"Сумма в {abs_amount/float(cat_avg):.1f} раз выше средней для этой категории"
        
        # Ночное время
        if not tx.is_suspicious and 2 <= hour <= 5 and abs_amount > 3000:
            tx.is_suspicious = True
            tx.suspicious_reason = "Крупная транзакция в ночное время"
        
        # Крупная сумма
        if not tx.is_suspicious and abs_amount > 30000:
            tx.is_suspicious = True
            tx.suspicious_reason = f"Крупная сумма: {abs_amount:,.0f}₽".replace(",", " ")
    
    try:
        db.add(tx)
        db.commit()
        db.refresh(tx)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ошибка при создании: категория не принадлежит вам"
        )
    return {
        "id": tx.id,
        "description": tx.description,
        "amount": float(tx.amount),
        "is_income": float(tx.amount) > 0,
        "category_id": tx.category_id,
        "transaction_date": tx.transaction_date.isoformat() if tx.transaction_date else None,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "source": tx.source,
    }


@router.get(
    "/{tx_id}",
    response_model=TransactionResponse,
    summary="Получить транзакцию по ID",
    description="""
Возвращает детальную информацию о конкретной транзакции.

**Требуется авторизация.**

Можно получить только свои транзакции.
    """,
    response_description="Данные транзакции",
    responses={
        200: {
            "description": "Транзакция найдена",
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Недействительный токен"}
                }
            }
        },
        404: {
            "description": "Транзакция не найдена",
            "content": {
                "application/json": {
                    "example": {"detail": "Транзакция не найдена или не принадлежит вам"}
                }
            }
        }
    }
)
async def get_transaction(
    tx_id: int = Path(..., description="ID транзакции", examples=[1]),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Получить транзакцию по ID.
    
    Возвращает полную информацию о транзакции,
    включая категорию, дату и статус подозрительности.
    """
    return get_own_transaction(tx_id, db, user)


@router.put(
    "/{tx_id}",
    response_model=UpdateResponse,
    summary="Обновить транзакцию",
    description="""
Обновляет существующую транзакцию.

**Требуется авторизация.**

Можно изменить:
- `description` — описание
- `amount` — сумму (положительное число)
- `is_income` — тип (доход/расход)
- `category_id` — категорию
- `transaction_date` — дату

Передавайте только те поля, которые нужно изменить.

**Логика изменения суммы:**
- Если указаны `amount` и `is_income` — устанавливается новая сумма с новым знаком
- Если указан только `amount` — знак сохраняется от текущего значения
- Если указан только `is_income` — меняется знак существующей суммы
    """,
    response_description="Статус обновления",
    responses={
        200: {
            "description": "Транзакция успешно обновлена",
            "content": {
                "application/json": {
                    "example": {"status": "updated"}
                }
            }
        },
        400: {
            "description": "Недопустимые данные",
            "content": {
                "application/json": {
                    "example": {"detail": "Недопустимые данные"}
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
        404: {
            "description": "Транзакция не найдена",
            "content": {
                "application/json": {
                    "example": {"detail": "Транзакция не найдена"}
                }
            }
        }
    }
)
async def update_transaction(
    tx_id: int = Path(..., description="ID транзакции", examples=[1]),
    data: TransactionUpdate = ...,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Обновить транзакцию.
    
    Изменяет указанные поля транзакции.
    Можно обновить только свои транзакции.
    """
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.user_id == user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")

    update_data = data.model_dump(exclude_unset=True)
    
    new_amount = update_data.pop('amount', None)
    new_is_income = update_data.pop('is_income', None)
    
    if new_amount is not None:
        if new_is_income is not None:
            tx.amount = new_amount if new_is_income else -new_amount
        else:
            tx.amount = new_amount if tx.amount >= 0 else -new_amount
    elif new_is_income is not None and tx.amount is not None:
        tx.amount = abs(tx.amount) if new_is_income else -abs(tx.amount)
    
    new_date = update_data.pop('transaction_date', None)
    if new_date:
        try:
            tx.transaction_date = datetime.fromisoformat(new_date)
        except ValueError:
            pass
    
    for field, value in update_data.items():
        setattr(tx, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Недопустимые данные"
        )
    return {"status": "updated"}


@router.delete(
    "/{tx_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить транзакцию",
    description="""
Полностью удаляет транзакцию из системы.

**Требуется авторизация.**

⚠️ Действие необратимо! Удалённую транзакцию нельзя восстановить.

Можно удалить только свои транзакции.
    """,
    responses={
        204: {
            "description": "Транзакция успешно удалена",
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Недействительный токен"}
                }
            }
        },
        404: {
            "description": "Транзакция не найдена",
            "content": {
                "application/json": {
                    "example": {"detail": "Транзакция не найдена или не принадлежит вам"}
                }
            }
        },
        500: {
            "description": "Ошибка при удалении",
            "content": {
                "application/json": {
                    "example": {"detail": "Ошибка при удалении транзакции"}
                }
            }
        }
    }
)
async def delete_transaction(
    tx_id: int = Path(..., description="ID транзакции", examples=[1]),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Удалить транзакцию.
    
    Полностью удаляет транзакцию из базы данных.
    Можно удалить только свои транзакции.
    """
    tx = get_own_transaction(tx_id, db, user)
    try:
        db.delete(tx)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при удалении транзакции"
        )
@router.post(
    "/{tx_id}/dismiss-suspicious",
    response_model=UpdateResponse,
    summary="Подтвердить что транзакция легитимна",
    description="""
Помечает подозрительную транзакцию как проверенную пользователем.

После подтверждения транзакция больше не будет появляться в списке подозрительных,
даже если формально подходит под критерии.

**Требуется авторизация.**
    """,
    responses={
        200: {"description": "Транзакция подтверждена"},
        404: {"description": "Транзакция не найдена"},
    }
)
async def dismiss_suspicious(
    tx_id: int = Path(..., description="ID транзакции"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Подтвердить что транзакция легитимна (убрать из подозрительных навсегда)."""
    tx = get_own_transaction(tx_id, db, user)
    tx.suspicious_dismissed = True
    tx.is_suspicious = False
    tx.suspicious_reason = None
    db.commit()
    return {"status": "dismissed"}

@router.post(
    "/smart-input",
    response_model=SmartInputResponse,
    summary="Умный ввод (превью)",
    description="""
Парсит текст на естественном языке и извлекает данные транзакции.

**Требуется авторизация.**

**Примеры входного текста:**
- `кофе 350р` → расход 350₽, категория "Рестораны"
- `зарплата 100000` → доход 100 000₽, категория "Зарплата"
- `такси до работы 500 рублей` → расход 500₽, категория "Транспорт"
- `перевод маме 5000` → расход 5000₽

**Как работает:**
1. NLP-парсер извлекает сумму и описание
2. ML-категоризатор определяет категорию
3. Анализируются ключевые слова для определения дохода/расхода

**Лимит:** 30 запросов в минуту.

Этот эндпоинт только возвращает распознанные данные для предпросмотра.
Для создания транзакции используйте `/smart-input/confirm`.
    """,
    response_description="Распознанные данные транзакции",
    responses={
        200: {
            "description": "Текст успешно распознан",
            "content": {
                "application/json": {
                    "example": {
                        "amount": 450.0,
                        "description": "кофе в старбаксе",
                        "category_id": 2,
                        "is_income": False
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
        },
        429: {
            "description": "Превышен лимит запросов",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded: 30 per 1 minute"}
                }
            }
        },
        503: {
            "description": "NLP-парсер не загружен",
            "content": {
                "application/json": {
                    "example": {"detail": "NLP-парсер не загружен"}
                }
            }
        }
    }
)
@limiter.limit("30/minute")
async def smart_input(
    request: Request,
    data: SmartInputRequest,
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    """
    Умный ввод транзакции (превью).
    
    Парсит текст на естественном языке и возвращает
    распознанные данные для предварительного просмотра.
    """
    nlp_parser = registry.get("nlp_parser")
    categorizer = registry.get("categorizer")
    
    if not nlp_parser:
        raise HTTPException(status_code=503, detail="NLP-парсер не загружен")
    
    parsed = nlp_parser.parse(data.text)   
    
    category_id = None
    if categorizer and parsed.get("description"): 
        cat_pred = categorize(parsed["description"])
        if cat_pred.category_code in ("salary", "cash"):
            parsed["is_income"] = True
        db_cat = db.query(Category).filter(
            Category.code == cat_pred.category_code,
            Category.user_id == user.id
        ).first()
        category_id = db_cat.id if db_cat else None
        if not category_id:
            logger.warning(f"Category code {cat_pred.category_code} not found in DB")
    
    return {
        "amount": parsed["amount"],
        "description": parsed["description"],
        "category_id": category_id,
        "is_income": parsed["is_income"]
    }


@router.post(
    "/smart-input/confirm",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Умный ввод (создание)",
    description="""
Парсит текст и сразу создаёт транзакцию.

**Требуется авторизация.**

Объединяет функционал `/smart-input` и `POST /transactions`:
1. Парсит текст через NLP
2. Определяет категорию через ML
3. Проверяет на подозрительность
4. Создаёт транзакцию

**Лимит:** 30 запросов в минуту.

**Примеры:**
- `обед 500р` → создаст расход 500₽ в категории "Рестораны"
- `зп 150000` → создаст доход 150 000₽ в категории "Зарплата"
    """,
    response_description="Созданная транзакция",
    responses={
        201: {
            "description": "Транзакция успешно создана",
        },
        400: {
            "description": "Не удалось распознать сумму или ошибка создания",
            "content": {
                "application/json": {
                    "examples": {
                        "no_amount": {
                            "summary": "Сумма не распознана",
                            "value": {"detail": "Не удалось определить сумму из текста"}
                        },
                        "create_error": {
                            "summary": "Ошибка создания",
                            "value": {"detail": "Ошибка при создании транзакции"}
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
        },
        429: {
            "description": "Превышен лимит запросов",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded: 30 per 1 minute"}
                }
            }
        },
        503: {
            "description": "NLP-парсер не загружен",
            "content": {
                "application/json": {
                    "example": {"detail": "NLP-парсер не загружен"}
                }
            }
        }
    }
)
@limiter.limit("30/minute")
async def smart_input_confirm(
    request: Request,
    data: SmartInputRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Подтверждение быстрого ввода.
    
    Парсит текст и создаёт транзакцию с автоматической
    категоризацией и проверкой на подозрительность.
    """
    nlp_parser = registry.get("nlp_parser")
    categorizer = registry.get("categorizer")

    if not nlp_parser:
        raise HTTPException(status_code=503, detail="NLP-парсер не загружен")

    parsed = nlp_parser.parse(data.text)

    amount = parsed.get("amount")
    description = parsed.get("description", data.text)
    is_income = parsed.get("is_income", False)

    if not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Не удалось определить сумму из текста")

    category_id = None
    cat_pred = None
    if categorizer and description:
        cat_pred = categorize(description)
        db_cat = db.query(Category).filter(
            Category.code == cat_pred.category_code,
            Category.user_id == user.id,
        ).first()
        category_id = db_cat.id if db_cat else None

    if cat_pred and cat_pred.category_code in ("salary", "cash"):
        is_income = True

    tx = Transaction(
        user_id=user.id,
        description=description,
        amount=amount if is_income else -amount,
        category_id=category_id,
        transaction_date=datetime.now(timezone.utc),
    )

    try:
        abs_amount = abs(float(tx.amount))
        hour = tx.transaction_date.hour
        day_of_week = tx.transaction_date.weekday()
        
        three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
        user_avg = db.query(sql_func.avg(sql_func.abs(Transaction.amount))).filter(
            Transaction.user_id == user.id,
            Transaction.transaction_date >= three_months_ago
        ).scalar() or abs_amount
        
        category_code = "other"
        if tx.category_id:
            cat_obj = db.query(Category).filter(Category.id == tx.category_id).first()
            if cat_obj:
                category_code = cat_obj.code
        
        try:
            result = detect_anomaly({
                "amount": abs_amount,
                "hour": hour,
                "day_of_week": day_of_week,
                "category": category_code,
                "user_avg_amount": float(user_avg),
                "is_weekend": 1 if day_of_week >= 5 else 0,
            })
            if result.get("is_suspicious"):
                tx.is_suspicious = True
                tx.suspicious_reason = result.get("reason") or "Нетипичная транзакция"
        except Exception as e:
            logger.warning(f"ML anomaly check failed: {e}")
        
        if not tx.is_suspicious and abs_amount > 0:
            if tx.category_id:
                cat_avg = db.query(sql_func.avg(sql_func.abs(Transaction.amount))).filter(
                    Transaction.user_id == user.id,
                    Transaction.category_id == tx.category_id,
                    Transaction.transaction_date >= three_months_ago
                ).scalar()
                if cat_avg and float(cat_avg) > 0 and abs_amount > float(cat_avg) * 3:
                    tx.is_suspicious = True
                    tx.suspicious_reason = f"Сумма в {abs_amount/float(cat_avg):.1f} раз выше средней для этой категории"
            
            if not tx.is_suspicious and 2 <= hour <= 5 and abs_amount > 3000:
                tx.is_suspicious = True
                tx.suspicious_reason = "Крупная транзакция в ночное время"
            
            if not tx.is_suspicious and abs_amount > 30000:
                tx.is_suspicious = True
                tx.suspicious_reason = f"Крупная сумма: {abs_amount:,.0f}₽".replace(",", " ")
        
        db.add(tx)
        db.commit()
        db.refresh(tx)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка при создании транзакции")

    return tx