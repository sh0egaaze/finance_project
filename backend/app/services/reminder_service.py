"""
Сервис для работы с напоминаниями
"""
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from loguru import logger

from ..models.reminder import Reminder, ReminderFrequency
from ..schemas.reminder import ReminderCreate, ReminderUpdate


class ReminderService:
    """Сервис для работы с напоминаниями об оплате"""
    
    @staticmethod
    def create_reminder(
        db: Session,
        user_id: int,
        data: ReminderCreate
    ) -> Reminder:
        """Создать напоминание"""
        reminder = Reminder(
            user_id=user_id,
            title=data.title,
            description=data.description,
            amount=data.amount,
            currency=data.currency,
            frequency=data.frequency,
            interval_days=data.interval_days or ReminderService._get_default_interval(data.frequency),
            repeat_count=data.repeat_count,
            next_reminder_date=data.next_reminder_date,
            send_email=data.send_email
        )
        
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        
        logger.info(f"Создано напоминание {reminder.id} для пользователя {user_id}")
        return reminder
    
    @staticmethod
    def _get_default_interval(frequency: ReminderFrequency) -> int:
        """Получить интервал по умолчанию для периодичности"""
        intervals = {
            ReminderFrequency.ONCE: 0,
            ReminderFrequency.DAILY: 1,
            ReminderFrequency.WEEKLY: 7,
            ReminderFrequency.MONTHLY: 30,
            ReminderFrequency.YEARLY: 365
        }
        return intervals.get(frequency, 0)
    
    @staticmethod
    def get_reminders(
        db: Session,
        user_id: int,
        include_completed: bool = False
    ) -> List[Reminder]:
        """Получить все напоминания пользователя"""
        query = db.query(Reminder).filter(Reminder.user_id == user_id)
        
        if not include_completed:
            query = query.filter(Reminder.is_completed == False)
        
        return query.order_by(Reminder.next_reminder_date.asc()).all()
    
    @staticmethod
    def get_upcoming_reminders(
        db: Session,
        user_id: int,
        days_ahead: int = 7
    ) -> List[Reminder]:
        """Получить предстоящие напоминания"""
        future_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        
        return db.query(Reminder).filter(
            and_(
                Reminder.user_id == user_id,
                Reminder.is_active == True,
                Reminder.is_completed == False,
                Reminder.next_reminder_date <= future_date
            )
        ).order_by(Reminder.next_reminder_date.asc()).all()
    
    @staticmethod
    def get_due_reminders(db: Session) -> List[Reminder]:
        """Получить напоминания, которые нужно отправить сейчас"""
        now = datetime.now(timezone.utc)
        
        return db.query(Reminder).filter(
            and_(
                Reminder.is_active == True,
                Reminder.is_completed == False,
                Reminder.next_reminder_date <= now
            )
        ).all()
    
    @staticmethod
    def get_reminder_by_id(
        db: Session,
        user_id: int,
        reminder_id: int
    ) -> Optional[Reminder]:
        """Получить напоминание по ID"""
        return db.query(Reminder).filter(
            and_(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id
            )
        ).first()
    
    @staticmethod
    def update_reminder(
        db: Session,
        user_id: int,
        reminder_id: int,
        data: ReminderUpdate
    ) -> Optional[Reminder]:
        """Обновить напоминание"""
        reminder = ReminderService.get_reminder_by_id(db, user_id, reminder_id)
        if not reminder:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(reminder, field, value)
        
        db.commit()
        db.refresh(reminder)
        return reminder
    
    @staticmethod
    def delete_reminder(
        db: Session,
        user_id: int,
        reminder_id: int
    ) -> bool:
        """Удалить напоминание"""
        reminder = ReminderService.get_reminder_by_id(db, user_id, reminder_id)
        if not reminder:
            return False
        
        db.delete(reminder)
        db.commit()
        return True
    
    @staticmethod
    def mark_as_sent(db: Session, reminder: Reminder):
        """
        Отметить напоминание как отправленное.
        Обновляет даты и счётчики.
        """
        reminder.last_sent_date = datetime.now(timezone.utc)
        reminder.current_count += 1
        
        # Если это одноразовое напоминание или достигнут лимит повторений
        if reminder.frequency == ReminderFrequency.ONCE:
            reminder.is_completed = True
        elif reminder.repeat_count and reminder.current_count >= reminder.repeat_count:
            reminder.is_completed = True
        else:
            # Вычисляем следующую дату
            reminder.next_reminder_date = ReminderService._calculate_next_date(reminder)
        
        db.commit()
        db.refresh(reminder)
        logger.info(f"Напоминание {reminder.id} отправлено")
    
    @staticmethod
    def _calculate_next_date(reminder: Reminder) -> datetime:
        """Вычислить следующую дату напоминания"""
        current = reminder.next_reminder_date
        
        if reminder.interval_days > 0:
            return current + timedelta(days=reminder.interval_days)
        
        # Fallback на стандартные интервалы
        intervals = {
            ReminderFrequency.DAILY: timedelta(days=1),
            ReminderFrequency.WEEKLY: timedelta(days=7),
            ReminderFrequency.MONTHLY: timedelta(days=30),
            ReminderFrequency.YEARLY: timedelta(days=365)
        }
        
        delta = intervals.get(reminder.frequency, timedelta(days=30))
        return current + delta
