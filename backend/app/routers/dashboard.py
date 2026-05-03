"""
Роутер для дашборда
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel

from app.database import get_db
from app.models import Transaction, Category, Reminder, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardResponse(BaseModel):
    total_balance: float
    total_income: float
    total_expense: float
    savings_rate: float
    transactions_count: int
    recent_transactions: List[dict]
    spending_by_category: List[dict]
    upcoming_reminders: List[dict]


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить данные дашборда"""
    now = datetime.now(timezone.utc)
    month_ago = now - timedelta(days=30)
    
    # Получаем транзакции за месяц
    transactions = db.query(Transaction)/options(
        joinedload(Transaction.category)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= month_ago
    ).all()
    
    # Считаем суммы
    total_income = sum(float(t.amount) for t in transactions if t.amount > 0)
    total_expense = abs(sum(float(t.amount) for t in transactions if t.amount < 0))
    total_balance = total_income - total_expense
    savings_rate = (total_income - total_expense) / total_income * 100 if total_income > 0 else 0
    
    # Последние транзакции
    recent = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.transaction_date.desc()).limit(5).all()
    
    recent_transactions = []
    for t in recent:
        recent_transactions.append({
            "id": t.id,
            "amount": float(t.amount),
            "description": t.description,
            "category_name": t.category.name if t.category else "Другое",
            "category_icon": t.category.icon if t.category else "📦",
            "transaction_date": t.transaction_date.isoformat(),
        })
    
    # Расходы по категориям
    spending_by_category = []
    categories = db.query(Category).filter(Category.is_expense == True, Category.is_active == True).all()
    
    for cat in categories:
        cat_sum = sum(
            abs(float(t.amount)) 
            for t in transactions 
            if t.category_id == cat.id and t.amount < 0
        )
        if cat_sum > 0:
            spending_by_category.append({
                "category_id": cat.id,
                "category_name": cat.name,
                "category_icon": cat.icon,
                "category_color": cat.color,
                "amount": cat_sum,
            })
    
    spending_by_category.sort(key=lambda x: x["amount"], reverse=True)
    
    # Ближайшие напоминания
    reminders = db.query(Reminder).filter(
        Reminder.user_id == current_user.id,
        Reminder.is_active == True,
        Reminder.is_completed == False,
        Reminder.next_reminder_date >= now
    ).order_by(Reminder.next_reminder_date).limit(5).all()
    
    upcoming_reminders = []
    for r in reminders:
        upcoming_reminders.append({
            "id": r.id,
            "title": r.title,
            "amount": float(r.amount) if r.amount else None,
            "next_reminder_date": r.next_reminder_date.isoformat(),
        })
    
    return {
        "total_balance": total_balance,
        "total_income": total_income,
        "total_expense": total_expense,
        "savings_rate": savings_rate,
        "transactions_count": len(transactions),
        "recent_transactions": recent_transactions,
        "spending_by_category": spending_by_category,
        "upcoming_reminders": upcoming_reminders,
    }


@router.get("/analytics")
async def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Аналитика расходов"""
    now = datetime.now(timezone.utc)
    month_ago = now - timedelta(days=30)
    
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= month_ago
    ).all()
    
    # По категориям
    by_category = {}
    for t in transactions:
        if t.amount < 0:
            cat_name = t.category.name if t.category else "Другое"
            by_category[cat_name] = by_category.get(cat_name, 0) + abs(float(t.amount))
    
    # По дням
    by_day = {}
    for t in transactions:
        if t.amount < 0:
            day = t.transaction_date.strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0) + abs(float(t.amount))
    
    return {
        "by_category": [{"name": k, "value": v} for k, v in by_category.items()],
        "by_day": [{"date": k, "amount": v} for k, v in sorted(by_day.items())],
        "total_expense": sum(abs(float(t.amount)) for t in transactions if t.amount < 0),
        "total_income": sum(float(t.amount) for t in transactions if t.amount > 0),
    }
