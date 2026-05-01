"""
Планировщик фоновых задач
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from dateutil.relativedelta import relativedelta
from loguru import logger
from datetime import datetime

from .database import SessionLocal
from .models import User, Reminder, NotificationHistory, AuditLog
from .services.email_service import get_email_service

scheduler = AsyncIOScheduler()

async def process_reminders():
    """Обработка и отправка напоминаний"""
    try:
        db: Session = SessionLocal()
    except Exception as e:
        logger.error(f"Не удалось подключиться к БД: {e}")
        return
    email_service = get_email_service()
    now = datetime.utcnow()
    
    try:
        # Находим активные напоминания, время которых пришло
        due_reminders = db.query(Reminder).filter(
            Reminder.is_active == True,
            Reminder.is_completed == False,
            Reminder.next_reminder_date <= now
        ).all()
        
        for rem in due_reminders:
            try:
                user = db.query(User).get(rem.user_id)
                if not user: continue
                
                target_email = user.notification_email or user.email
                success = False
                error_msg = None
                
                if rem.send_email:
                    try:
                        await email_service.send_reminder_notification(target_email, rem)
                        success = True
                    except Exception as e:
                        error_msg = str(e)
                
                # Записываем в историю
                history = NotificationHistory(
                    reminder_id=rem.id,
                    status="sent" if success else "error",
                    error_message=error_msg
                )
                db.add(history)
                
                # Логируем событие
                audit = AuditLog(
                    user_id=user.id,
                    action="reminder_sent",
                    entity_type="reminder",
                    entity_id=rem.id,
                    status="success" if success else "failure"
                )
                db.add(audit)
                
                # Обновляем напоминание
                rem.current_count += 1
                rem.last_sent_date = now
                
                # Вычисляем следующую дату на основе частоты
                if rem.frequency == "daily":
                    rem.next_reminder_date = now + relativedelta(days=1)
                elif rem.frequency == "weekly":
                    rem.next_reminder_date = now + relativedelta(weeks=1)
                elif rem.frequency == "monthly":
                    rem.next_reminder_date = now + relativedelta(months=1)
                elif rem.frequency == "once":
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
    scheduler.add_job(process_reminders, trigger=IntervalTrigger(minutes=5), id="reminders")
    scheduler.start()
    logger.info("Планировщик запущен")
