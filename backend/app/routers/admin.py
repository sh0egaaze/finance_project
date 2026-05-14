"""
Роутер админ-панели
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User, Transaction, Reminder, AuditLog, Category
from app.routers.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Админ-панель"])


# ===== Зависимость: только суперпользователь =====
def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Доступ только для суперпользователей"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён. Требуются права администратора."
        )
    return current_user


# ===== Pydantic схемы =====
class AdminUserResponse(BaseModel):
    """Пользователь для админки"""
    id: int = Field(..., description="ID пользователя")
    email: str = Field(..., description="Email")
    full_name: Optional[str] = Field(None, description="Полное имя")
    is_active: bool = Field(..., description="Активен")
    is_superuser: bool = Field(..., description="Администратор")
    email_verified: bool = Field(..., description="Email подтверждён")
    email_notifications: bool = Field(..., description="Уведомления")
    tbank_connected: bool = Field(False, description="Т-Банк подключён")
    transactions_count: int = Field(0, description="Количество транзакций")
    created_at: Optional[str] = Field(None, description="Дата регистрации")
    last_login: Optional[str] = Field(None, description="Последний вход")

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    """Список пользователей"""
    items: List[AdminUserResponse]
    total: int


class AdminStatsResponse(BaseModel):
    """Системная статистика"""
    total_users: int = Field(..., description="Всего пользователей")
    active_users: int = Field(..., description="Активных пользователей")
    verified_users: int = Field(..., description="Подтвердили email")
    total_transactions: int = Field(..., description="Всего транзакций")
    total_reminders: int = Field(..., description="Всего напоминаний")
    total_categories: int = Field(..., description="Всего категорий")
    users_today: int = Field(..., description="Зарегистрировались сегодня")
    users_this_week: int = Field(..., description="Зарегистрировались за неделю")
    users_this_month: int = Field(..., description="Зарегистрировались за месяц")
    active_today: int = Field(..., description="Активны сегодня")
    active_this_week: int = Field(..., description="Активны за неделю")
    transactions_today: int = Field(..., description="Транзакций сегодня")
    transactions_this_week: int = Field(..., description="Транзакций за неделю")
    transactions_this_month: int = Field(..., description="Транзакций за месяц")
    tbank_connected_count: int = Field(..., description="Подключили Т-Банк")


class AuditLogResponse(BaseModel):
    """Запись аудит-лога"""
    id: int
    user_id: Optional[int]
    user_email: Optional[str] = None
    action: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    description: Optional[str]
    status: Optional[str]
    error_message: Optional[str]
    created_at: Optional[str]

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Список аудит-логов"""
    items: List[AuditLogResponse]
    total: int


class UserActionRequest(BaseModel):
    """Запрос на действие с пользователем"""
    reason: Optional[str] = Field(None, description="Причина действия")


class MessageResponse(BaseModel):
    """Ответ с сообщением"""
    message: str


# ===== Эндпоинты =====

@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Системная статистика",
    description="Возвращает общую статистику по системе. Только для администраторов.",
    responses={
        200: {"description": "Статистика"},
        403: {"description": "Нет прав администратора"},
    }
)
async def get_system_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_superuser)
):
    """Системная статистика для админ-панели."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    verified_users = db.query(func.count(User.id)).filter(User.email_verified == True).scalar() or 0

    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    total_reminders = db.query(func.count(Reminder.id)).scalar() or 0
    total_categories = db.query(func.count(Category.id)).scalar() or 0

    users_today = db.query(func.count(User.id)).filter(User.created_at >= today_start).scalar() or 0
    users_this_week = db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar() or 0
    users_this_month = db.query(func.count(User.id)).filter(User.created_at >= month_ago).scalar() or 0

    active_today = db.query(func.count(User.id)).filter(User.last_login >= today_start).scalar() or 0
    active_this_week = db.query(func.count(User.id)).filter(User.last_login >= week_ago).scalar() or 0

    transactions_today = db.query(func.count(Transaction.id)).filter(Transaction.created_at >= today_start).scalar() or 0
    transactions_this_week = db.query(func.count(Transaction.id)).filter(Transaction.created_at >= week_ago).scalar() or 0
    transactions_this_month = db.query(func.count(Transaction.id)).filter(Transaction.created_at >= month_ago).scalar() or 0

    tbank_connected = db.query(func.count(User.id)).filter(User.tbank_token_encrypted.isnot(None)).scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        verified_users=verified_users,
        total_transactions=total_transactions,
        total_reminders=total_reminders,
        total_categories=total_categories,
        users_today=users_today,
        users_this_week=users_this_week,
        users_this_month=users_this_month,
        active_today=active_today,
        active_this_week=active_this_week,
        transactions_today=transactions_today,
        transactions_this_week=transactions_this_week,
        transactions_this_month=transactions_this_month,
        tbank_connected_count=tbank_connected,
    )


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="Список пользователей",
    description="Возвращает список всех пользователей с пагинацией и поиском.",
    responses={
        200: {"description": "Список пользователей"},
        403: {"description": "Нет прав администратора"},
    }
)
async def get_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Поиск по email или имени"),
    is_active: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_superuser)
):
    """Список пользователей с фильтрацией."""
    query = db.query(User)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_filter)) |
            (User.full_name.ilike(search_filter))
        )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if is_verified is not None:
        query = query.filter(User.email_verified == is_verified)

    total = query.count()
    users = query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()

    items = []
    for u in users:
        tx_count = db.query(func.count(Transaction.id)).filter(Transaction.user_id == u.id).scalar() or 0
        items.append(AdminUserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            is_superuser=u.is_superuser,
            email_verified=u.email_verified or False,
            email_notifications=u.email_notifications,
            tbank_connected=bool(u.tbank_token_encrypted),
            transactions_count=tx_count,
            created_at=u.created_at.isoformat() if u.created_at else None,
            last_login=u.last_login.isoformat() if u.last_login else None,
        ))

    return AdminUserListResponse(items=items, total=total)


@router.post(
    "/users/{user_id}/block",
    response_model=MessageResponse,
    summary="Заблокировать пользователя",
    responses={
        200: {"description": "Пользователь заблокирован"},
        403: {"description": "Нет прав или попытка заблокировать себя"},
        404: {"description": "Пользователь не найден"},
    }
)
async def block_user(
    user_id: int,
    data: UserActionRequest = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_superuser)
):
    """Заблокировать пользователя."""
    if user_id == admin.id:
        raise HTTPException(status_code=403, detail="Нельзя заблокировать самого себя")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_active = False
    user.updated_at = datetime.now(timezone.utc)

    # Аудит-лог
    log = AuditLog(
        user_id=admin.id,
        action="block_user",
        entity_type="user",
        entity_id=user_id,
        description=f"Заблокирован пользователь {user.email}. Причина: {data.reason if data and data.reason else 'не указана'}",
        status="success",
    )
    db.add(log)
    db.commit()

    return {"message": f"Пользователь {user.email} заблокирован"}


@router.post(
    "/users/{user_id}/unblock",
    response_model=MessageResponse,
    summary="Разблокировать пользователя",
    responses={
        200: {"description": "Пользователь разблокирован"},
        404: {"description": "Пользователь не найден"},
    }
)
async def unblock_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_superuser)
):
    """Разблокировать пользователя."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_active = True
    user.updated_at = datetime.now(timezone.utc)

    log = AuditLog(
        user_id=admin.id,
        action="unblock_user",
        entity_type="user",
        entity_id=user_id,
        description=f"Разблокирован пользователь {user.email}",
        status="success",
    )
    db.add(log)
    db.commit()

    return {"message": f"Пользователь {user.email} разблокирован"}


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Удалить пользователя",
    responses={
        200: {"description": "Пользователь удалён"},
        403: {"description": "Нельзя удалить себя"},
        404: {"description": "Пользователь не найден"},
    }
)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_superuser)
):
    """Удалить пользователя и все его данные."""
    if user_id == admin.id:
        raise HTTPException(status_code=403, detail="Нельзя удалить самого себя")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    email = user.email

    # Удаляем связанные данные вручную (категории не имеют CASCADE)
    db.query(Category).filter(Category.user_id == user_id).delete()
    
    # Логируем
    log = AuditLog(
        user_id=admin.id,
        action="delete_user",
        entity_type="user",
        entity_id=user_id,
        description=f"Удалён пользователь {email}",
        status="success",
    )
    db.add(log)

    # Удаляем пользователя
    db.delete(user)
    db.commit()

    return {"message": f"Пользователь {email} удалён"}


@router.post(
    "/users/{user_id}/verify-email",
    response_model=MessageResponse,
    summary="Вручную подтвердить email пользователя",
    responses={
        200: {"description": "Email подтверждён"},
        404: {"description": "Пользователь не найден"},
    }
)
async def admin_verify_email(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_superuser)
):
    """Подтвердить email пользователя вручную (админом)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.email_verified = True
    user.email_verification_token = None
    user.updated_at = datetime.now(timezone.utc)

    log = AuditLog(
        user_id=admin.id,
        action="admin_verify_email",
        entity_type="user",
        entity_id=user_id,
        description=f"Email {user.email} подтверждён администратором",
        status="success",
    )
    db.add(log)
    db.commit()

    return {"message": f"Email {user.email} подтверждён"}


@router.post(
    "/users/{user_id}/toggle-superuser",
    response_model=MessageResponse,
    summary="Переключить статус администратора",
    responses={
        200: {"description": "Статус изменён"},
        403: {"description": "Нельзя изменить свой статус"},
        404: {"description": "Пользователь не найден"},
    }
)
async def toggle_superuser(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_superuser)
):
    """Назначить/снять права администратора."""
    if user_id == admin.id:
        raise HTTPException(status_code=403, detail="Нельзя изменить свой статус администратора")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_superuser = not user.is_superuser
    user.updated_at = datetime.now(timezone.utc)
    action = "назначен администратором" if user.is_superuser else "снят с администратора"

    log = AuditLog(
        user_id=admin.id,
        action="toggle_superuser",
        entity_type="user",
        entity_id=user_id,
        description=f"Пользователь {user.email} {action}",
        status="success",
    )
    db.add(log)
    db.commit()

    return {"message": f"Пользователь {user.email} {action}"}


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    summary="Аудит-логи",
    description="Возвращает аудит-логи системы с пагинацией и фильтрацией.",
    responses={
        200: {"description": "Список логов"},
        403: {"description": "Нет прав администратора"},
    }
)
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None, description="Фильтр по действию"),
    user_id: Optional[int] = Query(None, description="Фильтр по пользователю"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_superuser)
):
    """Аудит-логи системы."""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()

    items = []
    for log in logs:
        user_email = None
        if log.user_id:
            u = db.query(User.email).filter(User.id == log.user_id).first()
            user_email = u[0] if u else None

        items.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=user_email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            description=log.description,
            status=log.status,
            error_message=log.error_message,
            created_at=log.created_at.isoformat() if log.created_at else None,
        ))

    return AuditLogListResponse(items=items, total=total)