"""
Планировщик фоновых и периодических задач
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from loguru import logger

from .database import SessionLocal
from .models import User, Reminder, NotificationHistory, AuditLog
from .services.email_service import get_email_service

scheduler = AsyncIOScheduler()


async def process_reminders():
    """Обработка и отправка.pending напоминаний"""
    try:
        db: Session = SessionLocal()
    except Exception as e:
        logger.error(f"Не удалось подключиться к БД: {e}")
        return
    email_service = get_email_service()
    now = datetime.now(timezone.utc)
    
    try:
        # Находим активные периодические уведомления, в том числе корректные настройки
        due_reminders = db.query(Reminder).filter(
            Reminder.is_active == True,
            Reminder.is_completed == False,
            Reminder.next_reminder_date <= now
        ).all()

        logger.info(f"Проверка напоминаний: найдено {len(due_reminders)} шт.")
        
        for rem in due_reminders:
            try:
                user = db.get(User, rem.user_id)
                if not user:
                    continue
                
                if rem.last_sent_date:
                    time_since_last = now - rem.last_sent_date
                    if time_since_last < timedelta(hours=23):
                        continue
                   
                target_email = user.notification_email or user.email
                success = False
                error_msg = None
                
                if rem.send_email:
                    try:
                        await email_service.send_reminder_notification(target_email, rem)
                        success = True
                    except Exception as e:
                        error_msg = str(e)
                
                # Сохраняем в историю
                history = NotificationHistory(
                    reminder_id=rem.id,
                    status="sent" if success else "error",
                    error_message=error_msg
                )
                db.add(history)
                
                # Сохраняем в аудит-лог
                audit = AuditLog(
                    user_id=user.id,
                    action="reminder_sent",
                    entity_type="reminder",
                    entity_id=rem.id,
                    status="success" if success else "failure"
                )
                db.add(audit)
                
                # Обновляем периодические уведомления
                rem.current_count += 1
                rem.last_sent_date = now
                
                # Рассчитываем следующую дату и время
                if rem.frequency.value == "daily":
                    rem.next_reminder_date = now + timedelta(days=1)
                elif rem.frequency.value == "weekly":
                    rem.next_reminder_date = now + timedelta(weeks=1)
                elif rem.frequency.value == "monthly":
                    rem.next_reminder_date = now + relativedelta(months=1)
                elif rem.frequency.value == "once":
                    rem.is_completed = True
                
                # Проверяем лимит повторений
                if rem.repeat_count and rem.current_count >= rem.repeat_count:
                    rem.is_completed = True
                
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error processing reminder {rem.id}: {e}")
                continue
    except Exception as e:
        logger.error(f"Ошибка в планировщике уведомлений: {e}")
    finally:
        db.close()


def setup_scheduler():
    scheduler.add_job(process_reminders, trigger=IntervalTrigger(minutes=1), id="reminders")
    scheduler.start()
    logger.info("Планировщик инициализирован")
