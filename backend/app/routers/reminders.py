"""
Роутер для напоминаний
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Reminder, User, ReminderFrequency
from app.routers.auth import get_current_user

router = APIRouter(prefix="/reminders", tags=["reminders"])


# ===== Pydantic схемы =====
class ReminderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "RUB"
    frequency: str = "once"
    interval_days: Optional[int] = None
    repeat_count: Optional[int] = None
    next_reminder_date: datetime
    send_email: bool = True


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    frequency: Optional[str] = None
    next_reminder_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class ReminderResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    amount: Optional[float]
    currency: str
    frequency: str
    interval_days: Optional[int]
    repeat_count: Optional[int]
    current_count: int
    next_reminder_date: datetime
    is_active: bool
    is_completed: bool
    send_email: bool

    class Config:
        from_attributes = True


# ===== Эндпоинты =====
@router.get("", response_model=List[ReminderResponse])
async def get_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить напоминания пользователя"""
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


@router.post("", response_model=ReminderResponse)
async def create_reminder(
    data: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать напоминание"""
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


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: int,
    data: ReminderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить напоминание"""
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


@router.delete("/{reminder_id}")
async def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить напоминание"""
    reminder = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id
    ).first()
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Напоминание не найдено")
    
    db.delete(reminder)
    db.commit()
    
    return {"message": "Напоминание удалено"}
