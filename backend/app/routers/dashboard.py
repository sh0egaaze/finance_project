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
    stats: dict
    recent_transactions: List[dict]
    spending_by_category: List[dict]
    monthly_trend: List[dict]
    upcoming_reminders: List[dict]
    suspicious_transactions: List[dict]


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить данные дашборда"""
    now = datetime.now(timezone.utc)
    month_ago = now - timedelta(days=30)
    
    # Получаем транзакции за месяц
    transactions = db.query(Transaction).options(
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
        "stats": {
            "total_balance": total_balance,
            "total_income": total_income,
            "total_expense": total_expense,
            "savings_rate": savings_rate,
            "transaction_count": len(transactions),
        },
        "recent_transactions": recent_transactions,
        "spending_by_category": [
            {
                "category_id": item["category_id"],
                "category": item.get("category_name", "Другое"),
                "name": item.get("category_name", "Другое"),
                "amount": item["amount"],
                "color": item.get("category_color", "#6B7280"),
                "icon": item.get("category_icon", "📦"),
            }
            for item in spending_by_category
        ],
        "monthly_trend": [],
        "upcoming_reminders": upcoming_reminders,
        "suspicious_transactions": [],
    }


@router.get("/analytics")
async def get_analytics(
    period: str = "month",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Аналитика расходов"""
    now = datetime.now(timezone.utc)
    
    # Определяем период
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "quarter":
        start_date = now - timedelta(days=90)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)
    
    transactions = db.query(Transaction).options(
        joinedload(Transaction.category)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= start_date
    ).all()
    
    # Расходы по категориям (для PieChart и BarChart)
    spending_by_category = []
    category_totals = {}
    
    for t in transactions:
        if t.amount < 0:  # Только расходы
            cat_id = t.category_id or 0
            cat_name = t.category.name if t.category else "Другое"
            cat_color = t.category.color if t.category else "#6B7280"
            
            if cat_id not in category_totals:
                category_totals[cat_id] = {
                    "category_id": cat_id,
                    "category": cat_name,
                    "name": cat_name,
                    "amount": 0,
                    "color": cat_color,
                }
            category_totals[cat_id]["amount"] += abs(float(t.amount))
    
    spending_by_category = list(category_totals.values())
    spending_by_category.sort(key=lambda x: x["amount"], reverse=True)
    
    # Тренд по дням (для LineChart)
    spending_trend = []
    trend_data = {}
    
    for t in transactions:
        day = t.transaction_date.strftime("%d.%m")
        if day not in trend_data:
            trend_data[day] = {"date": day, "income": 0, "expense": 0}
        
        if t.amount > 0:
            trend_data[day]["income"] += float(t.amount)
        else:
            trend_data[day]["expense"] += abs(float(t.amount))
    
    # Сортируем по дате
    spending_trend = list(trend_data.values())
    
    # Расходы по дням (для BarChart)
    spending_by_day = []
    by_day = {}
    for t in transactions:
        if t.amount < 0:
            day = t.transaction_date.strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0) + abs(float(t.amount))
    
    spending_by_day = [{"date": k, "amount": v} for k, v in sorted(by_day.items())]
    
    # Статистика
    total_expense = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
    total_income = sum(float(t.amount) for t in transactions if t.amount > 0)
    transaction_count = len([t for t in transactions if t.amount < 0])
    average_transaction = total_expense / transaction_count if transaction_count > 0 else 0
    
    return {
        "spending_by_category": spending_by_category,
        "spending_by_day": spending_by_day,
        "spending_trend": spending_trend,
        "income_vs_expense": [
            {"name": "Доходы", "value": total_income},
            {"name": "Расходы", "value": total_expense},
        ],
        "top_merchants": [],
        "average_transaction": average_transaction,
        "total_transactions": transaction_count,
        "total_expense": total_expense,
        "total_income": total_income,
    }

@router.get("/predictions")
async def get_predictions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Прогнозы расходов на следующий месяц с ML-рекомендациями"""
    from app.ml.model_loader import registry
    
    now = datetime.now(timezone.utc)
    
    # Берём данные за последние 90 дней для прогноза
    start_date = now - timedelta(days=90)
    
    transactions = db.query(Transaction).options(
        joinedload(Transaction.category)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= start_date
    ).all()
    
    if not transactions:
        return {
            "next_month_total": 0,
            "next_month_expense": 0,
            "next_month_income": 0,
            "by_category": [],
            "trends": [],
            "recommendations": [
                "Добавьте больше транзакций для точных прогнозов",
            ],
        }
    
    # Считаем средние за месяц
    dates = [t.transaction_date for t in transactions]
    first_date = min(dates)
    last_date = max(dates)
    
    # Если все транзакции за один день — считаем как 1 месяц
    days_range = (last_date - first_date).days
    if days_range < 30:
        months = 1  # Минимум 1 месяц для прогноза
    else:
        months = days_range / 30
    
    total_income = sum(float(t.amount) for t in transactions if t.amount > 0)
    total_expense = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
    
    avg_monthly_income = total_income / months if months > 0 else 0
    avg_monthly_expense = total_expense / months if months > 0 else 0
    
    # Прогноз по категориям
    category_spending = {}
    for t in transactions:
        if t.amount < 0:
            cat_id = t.category_id or 0
            cat_name = t.category.name if t.category else "Другое"
            cat_color = t.category.color if t.category else "#6B7280"
            
            if cat_id not in category_spending:
                category_spending[cat_id] = {
                    "category_id": cat_id,
                    "name": cat_name,
                    "color": cat_color,
                    "total": 0,
                }
            category_spending[cat_id]["total"] += abs(float(t.amount))
    
    by_category = []
    for cat_id, info in category_spending.items():
        predicted = info["total"] / months if months > 0 else 0
        
        # Определяем тренд
        last_month = now - timedelta(days=30)
        prev_month = now - timedelta(days=60)
        
        recent_sum = sum(
            abs(float(t.amount)) for t in transactions
            if t.amount < 0 and t.category_id == (cat_id or None) and t.transaction_date >= last_month
        )
        older_sum = sum(
            abs(float(t.amount)) for t in transactions
            if t.amount < 0 and t.category_id == (cat_id or None) 
            and t.transaction_date >= prev_month and t.transaction_date < last_month
        )
        
        if older_sum > 0:
            change = ((recent_sum - older_sum) / older_sum) * 100
            if change > 10:
                trend = "up"
            elif change < -10:
                trend = "down"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        by_category.append({
            "category_id": cat_id,
            "name": info["name"],
            "color": info["color"],
            "predicted_amount": round(predicted, 2),
            "trend": trend,
        })
    
    by_category.sort(key=lambda x: x["predicted_amount"], reverse=True)
    
    # ============ ML-рекомендации ============
    recommendations = []
    
    # Маппинг категорий БД → категории модели
    CATEGORY_MAP = {
        "food": "groceries",
        "restaurants": "restaurants",
        "transport": "transport",
        "shopping": "shopping",
        "utilities": "utilities",
        "health": "health",
        "entertainment": "entertainment",
        "education": "education",
        "subscriptions": "subscriptions",
    }
    
    # Преобразуем транзакции в формат для ML-модели
    ml_transactions = []
    for t in transactions:
        cat_code = t.category.code if t.category else "other"
        ml_category = CATEGORY_MAP.get(cat_code, "shopping")
        
        # Определяем выходной день
        is_weekend = 1 if t.transaction_date.weekday() >= 5 else 0
        
        ml_transactions.append({
            "type": "income" if t.amount > 0 else "expense",
            "amount": abs(float(t.amount)),
            "category": ml_category,
            "weekend": is_weekend,
            "merchant": t.merchant_name or "",
        })
    
    # Получаем рекомендации от ML-модели
    recommender = registry.get("recommender")
    if recommender and ml_transactions:
        try:
            ml_recs = recommender.predict(ml_transactions)
            for rec in ml_recs:
                if isinstance(rec, dict):
                    recommendations.append(rec.get("title", "") + " " + rec.get("description", ""))
                elif isinstance(rec, str):
                    recommendations.append(rec)
        except Exception as e:
            import logging
            logging.error(f"ML recommender error: {e}")
    
    # Добавляем базовые рекомендации если ML не дал
    if not recommendations:
        if avg_monthly_expense > avg_monthly_income * 0.9:
            recommendations.append("⚠️ Расходы близки к доходам. Рекомендуем сократить необязательные траты.")
        
        if avg_monthly_income > avg_monthly_expense:
            savings = avg_monthly_income - avg_monthly_expense
            recommendations.append(f"💰 Вы можете откладывать ~{round(savings):,} ₽ в месяц.".replace(",", " "))
        
        growing = [c for c in by_category if c["trend"] == "up"]
        if growing:
            top_growing = growing[0]
            recommendations.append(f"📈 Расходы на \"{top_growing['name']}\" растут. Обратите внимание.")
        
        if not recommendations:
            recommendations.append("✅ Финансы в норме! Продолжайте отслеживать расходы.")
    
    return {
        "next_month_total": round(avg_monthly_income - avg_monthly_expense, 2),
        "next_month_expense": round(avg_monthly_expense, 2),
        "next_month_income": round(avg_monthly_income, 2),
        "by_category": by_category,
        "trends": [],
        "recommendations": recommendations,
    }