"""
Роутер для напоминаний
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Reminder, User, ReminderFrequency
from app.routers.auth import get_current_user

router = APIRouter(prefix="/reminders", tags=["Напоминания"])


# ===== Pydantic схемы =====
class ReminderCreate(BaseModel):
    """Схема для создания напоминания"""
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Заголовок напоминания",
        examples=["Оплата аренды"]
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Описание или заметка",
        examples=["Перевод на карту арендодателя"]
    )
    amount: Optional[float] = Field(
        None,
        gt=0,
        description="Сумма платежа (если применимо)",
        examples=[35000.0]
    )
    currency: str = Field(
        "RUB",
        max_length=3,
        description="Валюта (ISO 4217)",
        examples=["RUB"]
    )
    frequency: str = Field(
        "once",
        description="Частота повторения: once, daily, weekly, monthly, custom",
        examples=["monthly"]
    )
    interval_days: Optional[int] = Field(
        None,
        ge=1,
        description="Интервал в днях (для frequency='custom')",
        examples=[14]
    )
    repeat_count: Optional[int] = Field(
        None,
        ge=1,
        description="Количество повторений (None = бесконечно)",
        examples=[12]
    )
    next_reminder_date: datetime = Field(
        ...,
        description="Дата и время следующего напоминания (ISO 8601)",
        examples=["2024-01-25T10:00:00+00:00"]
    )
    send_email: bool = Field(
        True,
        description="Отправлять email-уведомление",
        examples=[True]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Оплата аренды",
                    "description": "Перевод на карту арендодателя",
                    "amount": 35000.0,
                    "currency": "RUB",
                    "frequency": "monthly",
                    "next_reminder_date": "2024-01-25T10:00:00+00:00",
                    "send_email": True
                }
            ]
        }
    }


class ReminderUpdate(BaseModel):
    """Схема для обновления напоминания"""
    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Заголовок напоминания",
        examples=["Оплата аренды"]
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Описание или заметка",
        examples=["Новое описание"]
    )
    amount: Optional[float] = Field(
        None,
        gt=0,
        description="Сумма платежа",
        examples=[40000.0]
    )
    frequency: Optional[str] = Field(
        None,
        description="Частота повторения",
        examples=["monthly"]
    )
    next_reminder_date: Optional[datetime] = Field(
        None,
        description="Новая дата напоминания (ISO 8601)",
        examples=["2024-02-25T10:00:00+00:00"]
    )
    is_active: Optional[bool] = Field(
        None,
        description="Активно ли напоминание",
        examples=[True]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Оплата аренды (обновлено)",
                    "amount": 40000.0,
                    "next_reminder_date": "2024-02-25T10:00:00+00:00"
                }
            ]
        }
    }


class ReminderResponse(BaseModel):
    """Схема ответа с данными напоминания"""
    id: int = Field(..., description="Уникальный идентификатор", examples=[1])
    user_id: int = Field(..., description="ID пользователя", examples=[1])
    title: str = Field(..., description="Заголовок", examples=["Оплата аренды"])
    description: Optional[str] = Field(None, description="Описание", examples=["Перевод на карту"])
    amount: Optional[float] = Field(None, description="Сумма платежа", examples=[35000.0])
    currency: str = Field(..., description="Валюта", examples=["RUB"])
    frequency: str = Field(..., description="Частота: once, daily, weekly, monthly, custom", examples=["monthly"])
    interval_days: Optional[int] = Field(None, description="Интервал в днях (для custom)", examples=[None])
    repeat_count: Optional[int] = Field(None, description="Лимит повторений", examples=[12])
    current_count: int = Field(..., description="Текущее число выполнений", examples=[3])
    next_reminder_date: datetime = Field(..., description="Дата следующего напоминания", examples=["2024-01-25T10:00:00+00:00"])
    is_active: bool = Field(..., description="Активно ли напоминание", examples=[True])
    is_completed: bool = Field(..., description="Завершено ли напоминание", examples=[False])
    send_email: bool = Field(..., description="Отправлять ли email", examples=[True])

    class Config:
        from_attributes = True

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "user_id": 1,
                    "title": "Оплата аренды",
                    "description": "Перевод на карту арендодателя",
                    "amount": 35000.0,
                    "currency": "RUB",
                    "frequency": "monthly",
                    "interval_days": None,
                    "repeat_count": 12,
                    "current_count": 3,
                    "next_reminder_date": "2024-01-25T10:00:00+00:00",
                    "is_active": True,
                    "is_completed": False,
                    "send_email": True
                }
            ]
        }
    }


class DeleteResponse(BaseModel):
    """Схема ответа при удалении"""
    message: str = Field(..., description="Сообщение об успехе", examples=["Напоминание удалено"])


# ===== Эндпоинты =====
@router.get(
    "",
    response_model=List[ReminderResponse],
    summary="Получить активные напоминания",
    description="""
Возвращает список активных (незавершённых) напоминаний пользователя.

**Требуется авторизация.**

Напоминания отсортированы по дате следующего напоминания (ближайшие первыми).

**Частота напоминаний (frequency):**
- `once` — однократное
- `daily` — ежедневно
- `weekly` — еженедельно  
- `monthly` — ежемесячно
- `custom` — произвольный интервал (см. `interval_days`)
    """,
    response_description="Список активных напоминаний",
    responses={
        200: {
            "description": "Успешный ответ со списком напоминаний",
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
async def get_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить напоминания пользователя.
    
    Возвращает только активные (незавершённые) напоминания,
    отсортированные по дате ближайшего срабатывания.
    """
    reminders = db.query(Reminder).filter(
        Reminder.user_id == current_user.id,
        Reminder.is_completed == False
    ).order_by(Reminder.next_reminder_date).all()
    
    result = []
    for r in reminders:
        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "title": r.title,
            "description": r.description,
            "amount": float(r.amount) if r.amount else None,
            "currency": r.currency or "RUB",
            "frequency": r.frequency.value if r.frequency else "once",
            "interval_days": r.interval_days,
            "repeat_count": r.repeat_count,
            "current_count": r.current_count or 0,
            "next_reminder_date": r.next_reminder_date,
            "is_active": r.is_active,
            "is_completed": r.is_completed,
            "send_email": r.send_email,
        })
    return result


@router.get(
    "/archive",
    response_model=List[ReminderResponse],
    summary="Получить архивные напоминания",
    description="""
Возвращает список завершённых (архивных) напоминаний.

**Требуется авторизация.**

Напоминания отсортированы по дате в обратном порядке (последние первыми).

Напоминание попадает в архив после:
- Ручной отметки как выполненное
- Достижения лимита повторений (`repeat_count`)
    """,
    response_description="Список архивных напоминаний",
    responses={
        200: {
            "description": "Успешный ответ со списком архивных напоминаний",
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
async def get_archived_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить архивные (завершённые) напоминания.
    
    Возвращает напоминания, которые были отмечены как выполненные
    или достигли лимита повторений.
    """
    reminders = db.query(Reminder).filter(
        Reminder.user_id == current_user.id,
        Reminder.is_completed == True
    ).order_by(Reminder.next_reminder_date.desc()).all()
    
    result = []
    for r in reminders:
        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "title": r.title,
            "description": r.description,
            "amount": float(r.amount) if r.amount else None,
            "currency": r.currency or "RUB",
            "frequency": r.frequency.value if r.frequency else "once",
            "interval_days": r.interval_days,
            "repeat_count": r.repeat_count,
            "current_count": r.current_count or 0,
            "next_reminder_date": r.next_reminder_date,
            "is_active": r.is_active,
            "is_completed": r.is_completed,
            "send_email": r.send_email,
        })
    return result


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать напоминание",
    description="""
Создаёт новое напоминание о платеже или событии.

**Требуется авторизация.**

**Обязательные поля:**
- `title` — заголовок напоминания
- `next_reminder_date` — дата и время первого напоминания

**Типы частоты:**
- `once` — сработает один раз и будет завершено
- `daily` — каждый день в указанное время
- `weekly` — каждую неделю
- `monthly` — каждый месяц
- `custom` — произвольный интервал (укажите `interval_days`)

**Ограничение повторений:**
Укажите `repeat_count` для ограничения числа срабатываний.
После достижения лимита напоминание автоматически завершится.
    """,
    response_description="Созданное напоминание",
    responses={
        201: {
            "description": "Напоминание успешно создано",
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
                            {"loc": ["body", "title"], "msg": "Field required", "type": "missing"}
                        ]
                    }
                }
            }
        }
    }
)
async def create_reminder(
    data: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать напоминание.
    
    Создаёт новое напоминание с указанными параметрами.
    При включении `send_email` пользователь получит email-уведомление.
    """
    freq_map = {
        "once": ReminderFrequency.once,
        "daily": ReminderFrequency.daily,
        "weekly": ReminderFrequency.weekly,
        "monthly": ReminderFrequency.monthly,
        "custom": ReminderFrequency.custom,
    }
    
    reminder = Reminder(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        amount=Decimal(str(data.amount)) if data.amount else None,
        currency=data.currency,
        frequency=freq_map.get(data.frequency, ReminderFrequency.once),
        interval_days=data.interval_days,
        repeat_count=data.repeat_count,
        current_count=0,
        next_reminder_date=data.next_reminder_date,
        is_active=True,
        is_completed=False,
        send_email=data.send_email,
    )
    
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    
    return {
        "id": reminder.id,
        "user_id": reminder.user_id,
        "title": reminder.title,
        "description": reminder.description,
        "amount": float(reminder.amount) if reminder.amount else None,
        "currency": reminder.currency or "RUB",
        "frequency": reminder.frequency.value if reminder.frequency else "once",
        "interval_days": reminder.interval_days,
        "repeat_count": reminder.repeat_count,
        "current_count": reminder.current_count or 0,
        "next_reminder_date": reminder.next_reminder_date,
        "is_active": reminder.is_active,
        "is_completed": reminder.is_completed,
        "send_email": reminder.send_email,
    }


@router.put(
    "/{reminder_id}",
    response_model=ReminderResponse,
    summary="Обновить напоминание",
    description="""
Обновляет существующее напоминание.

**Требуется авторизация.**

Можно изменить:
- `title` — заголовок
- `description` — описание
- `amount` — сумму платежа
- `next_reminder_date` — дату следующего напоминания
- `is_active` — активность (для временной приостановки)

Передавайте только те поля, которые нужно изменить.
    """,
    response_description="Обновлённое напоминание",
    responses={
        200: {
            "description": "Напоминание успешно обновлено",
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
            "description": "Напоминание не найдено",
            "content": {
                "application/json": {
                    "example": {"detail": "Напоминание не найдено"}
                }
            }
        },
        422: {
            "description": "Ошибка валидации данных",
        }
    }
)
async def update_reminder(
    reminder_id: int = Path(..., description="ID напоминания", examples=[1]),
    data: ReminderUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновить напоминание.
    
    Изменяет параметры существующего напоминания.
    Можно изменить только свои напоминания.
    """
    reminder = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id
    ).first()
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Напоминание не найдено")
    
    if data.title is not None:
        reminder.title = data.title
    if data.description is not None:
        reminder.description = data.description
    if data.amount is not None:
        reminder.amount = Decimal(str(data.amount))
    if data.next_reminder_date is not None:
        reminder.next_reminder_date = data.next_reminder_date
    if data.is_active is not None:
        reminder.is_active = data.is_active
    
    reminder.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(reminder)
    
    return {
        "id": reminder.id,
        "user_id": reminder.user_id,
        "title": reminder.title,
        "description": reminder.description,
        "amount": float(reminder.amount) if reminder.amount else None,
        "currency": reminder.currency or "RUB",
        "frequency": reminder.frequency.value if reminder.frequency else "once",
        "interval_days": reminder.interval_days,
        "repeat_count": reminder.repeat_count,
        "current_count": reminder.current_count or 0,
        "next_reminder_date": reminder.next_reminder_date,
        "is_active": reminder.is_active,
        "is_completed": reminder.is_completed,
        "send_email": reminder.send_email,
    }


@router.delete(
    "/{reminder_id}",
    response_model=DeleteResponse,
    summary="Удалить напоминание",
    description="""
Полностью удаляет напоминание из системы.

**Требуется авторизация.**

⚠️ Действие необратимо! Для временного отключения используйте 
обновление с `is_active: false`.
    """,
    response_description="Подтверждение удаления",
    responses={
        200: {
            "description": "Напоминание успешно удалено",
            "content": {
                "application/json": {
                    "example": {"message": "Напоминание удалено"}
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
            "description": "Напоминание не найдено",
            "content": {
                "application/json": {
                    "example": {"detail": "Напоминание не найдено"}
                }
            }
        }
    }
)
async def delete_reminder(
    reminder_id: int = Path(..., description="ID напоминания", examples=[1]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удалить напоминание.
    
    Полностью удаляет напоминание из базы данных.
    Можно удалить только свои напоминания.
    """
    reminder = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id
    ).first()
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Напоминание не найдено")
    
    db.delete(reminder)
    db.commit()
    
    return {"message": "Напоминание удалено"}


@router.post(
    "/{reminder_id}/complete",
    response_model=ReminderResponse,
    summary="Отметить напоминание выполненным",
    description="""
Отмечает напоминание как выполненное.

**Требуется авторизация.**

**Поведение:**
- Увеличивается счётчик `current_count`
- Устанавливается `is_completed = true`
- Фиксируется дата выполнения

Для повторяющихся напоминаний это действие завершает напоминание полностью.
Если нужно только пропустить текущее срабатывание — обновите `next_reminder_date`.
    """,
    response_description="Обновлённое напоминание",
    responses={
        200: {
            "description": "Напоминание отмечено как выполненное",
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
            "description": "Напоминание не найдено",
            "content": {
                "application/json": {
                    "example": {"detail": "Напоминание не найдено"}
                }
            }
        }
    }
)
async def complete_reminder(
    reminder_id: int = Path(..., description="ID напоминания", examples=[1]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Отметить напоминание как выполненное.
    
    Завершает напоминание и фиксирует дату выполнения.
    После выполнения напоминание перемещается в архив.
    """
    reminder = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id
    ).first()
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Напоминание не найдено")
    
    reminder.is_completed = True
    reminder.current_count = (reminder.current_count or 0) + 1
    reminder.last_sent_date = datetime.now(timezone.utc)
    reminder.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(reminder)
    
    return {
        "id": reminder.id,
        "user_id": reminder.user_id,
        "title": reminder.title,
        "description": reminder.description,
        "amount": float(reminder.amount) if reminder.amount else None,
        "currency": reminder.currency or "RUB",
        "frequency": reminder.frequency.value if reminder.frequency else "once",
        "interval_days": reminder.interval_days,
        "repeat_count": reminder.repeat_count,
        "current_count": reminder.current_count or 0,
        "next_reminder_date": reminder.next_reminder_date,
        "is_active": reminder.is_active,
        "is_completed": reminder.is_completed,
        "send_email": reminder.send_email,
    }