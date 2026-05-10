"""
Роутер для дашборда
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Transaction, Category, Reminder, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Дашборд"])


# ===== Pydantic схемы =====
class StatsResponse(BaseModel):
    """Статистика за текущий месяц"""
    total_balance: float = Field(..., description="Общий баланс за всё время", examples=[150000.0])
    total_income: float = Field(..., description="Доходы за текущий месяц", examples=[100000.0])
    total_expense: float = Field(..., description="Расходы за текущий месяц", examples=[65000.0])
    savings_rate: float = Field(..., description="Процент сбережений от дохода", examples=[35.0])
    transaction_count: int = Field(..., description="Количество транзакций за месяц", examples=[42])


class RecentTransactionItem(BaseModel):
    """Недавняя транзакция"""
    id: int = Field(..., description="ID транзакции", examples=[1])
    amount: float = Field(..., description="Сумма (отрицательная для расходов)", examples=[-1500.0])
    description: str = Field(..., description="Описание транзакции", examples=["Покупка в супермаркете"])
    category_name: str = Field(..., description="Название категории", examples=["Еда и продукты"])
    category_icon: str = Field(..., description="Иконка категории", examples=["🍔"])
    transaction_date: str = Field(..., description="Дата транзакции (ISO 8601)", examples=["2024-01-15T14:30:00+00:00"])


class SpendingCategoryItem(BaseModel):
    """Расходы по категории"""
    category_id: int = Field(..., description="ID категории", examples=[1])
    category: str = Field(..., description="Название категории", examples=["Еда и продукты"])
    name: str = Field(..., description="Название категории (алиас)", examples=["Еда и продукты"])
    amount: float = Field(..., description="Сумма расходов", examples=[25000.0])
    color: str = Field(..., description="HEX-цвет категории", examples=["#ef4444"])
    icon: str = Field(..., description="Иконка категории", examples=["🍔"])


class IncomeCategoryItem(BaseModel):
    """Доходы по категории"""
    category_id: int = Field(..., description="ID категории", examples=[20])
    category: str = Field(..., description="Название категории", examples=["Зарплата и доход"])
    name: str = Field(..., description="Название категории (алиас)", examples=["Зарплата и доход"])
    amount: float = Field(..., description="Сумма доходов", examples=[100000.0])
    color: str = Field(..., description="HEX-цвет категории", examples=["#16a34a"])
    icon: str = Field(..., description="Иконка категории", examples=["💰"])


class TrendItem(BaseModel):
    """Данные тренда за день"""
    date: str = Field(..., description="Дата (YYYY-MM-DD)", examples=["2024-01-15"])
    income: float = Field(..., description="Доходы за день", examples=[0.0])
    expense: float = Field(..., description="Расходы за день", examples=[3500.0])


class ReminderItem(BaseModel):
    """Напоминание"""
    id: int = Field(..., description="ID напоминания", examples=[1])
    title: str = Field(..., description="Заголовок напоминания", examples=["Оплата аренды"])
    amount: Optional[float] = Field(None, description="Сумма платежа", examples=[35000.0])
    next_reminder_date: str = Field(..., description="Дата следующего напоминания (ISO 8601)", examples=["2024-01-25T10:00:00+00:00"])


class SuspiciousTransactionItem(BaseModel):
    """Подозрительная транзакция"""
    id: int = Field(..., description="ID транзакции", examples=[5])
    amount: float = Field(..., description="Сумма транзакции", examples=[-50000.0])
    description: str = Field(..., description="Описание", examples=["Перевод на неизвестный счёт"])
    category_id: Optional[int] = Field(None, description="ID категории", examples=[21])
    category_name: str = Field(..., description="Название категории", examples=["Переводы"])
    transaction_date: str = Field(..., description="Дата транзакции (ISO 8601)", examples=["2024-01-14T03:45:00+00:00"])
    suspicious_reason: str = Field(..., description="Причина подозрительности", examples=["Необычно крупная сумма"])


class DashboardResponse(BaseModel):
    """Полный ответ дашборда"""
    stats: dict = Field(..., description="Статистика за текущий месяц")
    recent_transactions: List[dict] = Field(..., description="Последние 5 транзакций")
    spending_by_category: List[dict] = Field(..., description="Расходы по категориям")
    income_by_category: List[dict] = Field(..., description="Доходы по категориям")
    monthly_trend: List[dict] = Field(..., description="Тренд доходов/расходов по дням")
    upcoming_reminders: List[dict] = Field(..., description="Ближайшие напоминания")
    suspicious_transactions: List[dict] = Field(..., description="Подозрительные транзакции")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "stats": {
                        "total_balance": 150000.0,
                        "total_income": 100000.0,
                        "total_expense": 65000.0,
                        "savings_rate": 35.0,
                        "transaction_count": 42
                    },
                    "recent_transactions": [
                        {
                            "id": 1,
                            "amount": -1500.0,
                            "description": "Пятёрочка",
                            "category_name": "Еда и продукты",
                            "category_icon": "🍔",
                            "transaction_date": "2024-01-15T14:30:00+00:00"
                        }
                    ],
                    "spending_by_category": [
                        {"category_id": 1, "category": "Еда и продукты", "name": "Еда и продукты", "amount": 25000.0, "color": "#ef4444", "icon": "🍔"}
                    ],
                    "income_by_category": [
                        {"category_id": 20, "category": "Зарплата", "name": "Зарплата", "amount": 100000.0, "color": "#16a34a", "icon": "💰"}
                    ],
                    "monthly_trend": [
                        {"date": "2024-01-15", "income": 0.0, "expense": 3500.0}
                    ],
                    "upcoming_reminders": [
                        {"id": 1, "title": "Оплата аренды", "amount": 35000.0, "next_reminder_date": "2024-01-25T10:00:00+00:00"}
                    ],
                    "suspicious_transactions": []
                }
            ]
        }
    }


class AnalyticsResponse(BaseModel):
    """Ответ аналитики"""
    spending_by_category: List[dict] = Field(..., description="Расходы по категориям")
    income_by_category: List[dict] = Field(..., description="Доходы по категориям")
    spending_by_day: List[dict] = Field(..., description="Расходы по дням")
    spending_trend: List[dict] = Field(..., description="Тренд доходов/расходов")
    income_vs_expense: List[dict] = Field(..., description="Сравнение доходов и расходов")
    top_merchants: List[dict] = Field(..., description="Топ мерчантов (продавцов)")
    average_transaction: float = Field(..., description="Средняя сумма транзакции", examples=[1548.50])
    total_transactions: int = Field(..., description="Всего транзакций", examples=[42])
    total_expense: float = Field(..., description="Всего расходов", examples=[65000.0])
    total_income: float = Field(..., description="Всего доходов", examples=[100000.0])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "spending_by_category": [
                        {"category_id": 1, "category": "Еда", "name": "Еда", "amount": 25000.0, "color": "#ef4444"}
                    ],
                    "income_by_category": [
                        {"category_id": 20, "category": "Зарплата", "name": "Зарплата", "amount": 100000.0, "color": "#16a34a"}
                    ],
                    "spending_by_day": [
                        {"date": "2024-01-15", "amount": 3500.0}
                    ],
                    "spending_trend": [
                        {"date": "15.01", "income": 0.0, "expense": 3500.0}
                    ],
                    "income_vs_expense": [
                        {"name": "Доходы", "value": 100000.0},
                        {"name": "Расходы", "value": 65000.0}
                    ],
                    "top_merchants": [],
                    "average_transaction": 1548.50,
                    "total_transactions": 42,
                    "total_expense": 65000.0,
                    "total_income": 100000.0
                }
            ]
        }
    }


class CategoryPrediction(BaseModel):
    """Прогноз по категории"""
    category_id: int = Field(..., description="ID категории", examples=[1])
    name: str = Field(..., description="Название категории", examples=["Еда и продукты"])
    color: str = Field(..., description="HEX-цвет категории", examples=["#ef4444"])
    predicted_amount: float = Field(..., description="Прогнозируемая сумма", examples=[27500.0])
    trend: str = Field(..., description="Тренд: up, down, stable", examples=["up"])


class PredictionsResponse(BaseModel):
    """Ответ с прогнозами"""
    next_month_total: float = Field(..., description="Прогнозируемый баланс на следующий месяц", examples=[35000.0])
    next_month_expense: float = Field(..., description="Прогнозируемые расходы", examples=[65000.0])
    next_month_income: float = Field(..., description="Прогнозируемые доходы", examples=[100000.0])
    by_category: List[CategoryPrediction] = Field(..., description="Прогнозы по категориям")
    trends: List[dict] = Field(default=[], description="Тренды (зарезервировано)")
    recommendations: List[str] = Field(default=[], description="Рекомендации")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "next_month_total": 35000.0,
                    "next_month_expense": 65000.0,
                    "next_month_income": 100000.0,
                    "by_category": [
                        {"category_id": 1, "name": "Еда и продукты", "color": "#ef4444", "predicted_amount": 27500.0, "trend": "up"},
                        {"category_id": 3, "name": "Транспорт", "color": "#3b82f6", "predicted_amount": 12000.0, "trend": "stable"}
                    ],
                    "trends": [],
                    "recommendations": []
                }
            ]
        }
    }


class SavingTip(BaseModel):
    """Совет по экономии"""
    id: int = Field(..., description="ID совета", examples=[1])
    title: str = Field(..., description="Заголовок совета", examples=["🛍️ Высокие расходы на «Покупки»"])
    description: str = Field(..., description="Описание совета", examples=["Категория занимает 25% расходов. Попробуйте сократить на 30%."])
    potential_savings: Optional[float] = Field(None, description="Потенциальная экономия в рублях", examples=[5000.0])
    category: Optional[str] = Field(None, description="Код категории (если применимо)", examples=["SHOPPING"])
    priority: str = Field(..., description="Приоритет: high, medium, low", examples=["high"])


class TipsResponse(BaseModel):
    """Ответ с советами по экономии"""
    tips: List[SavingTip] = Field(..., description="Список советов по экономии")
    total_potential_savings: float = Field(..., description="Общая потенциальная экономия", examples=[15000.0])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tips": [
                        {
                            "id": 1,
                            "title": "🛍️ Высокие расходы на «Покупки»",
                            "description": "Категория занимает 25% расходов (15 000 ₽/мес). Попробуйте сократить на 30%.",
                            "potential_savings": 4500.0,
                            "category": "SHOPPING",
                            "priority": "high"
                        },
                        {
                            "id": 2,
                            "title": "💰 Откладывайте излишки",
                            "description": "У вас остаётся ~35 000 ₽/мес. Переводите их на накопительный счёт автоматически.",
                            "potential_savings": None,
                            "category": None,
                            "priority": "low"
                        }
                    ],
                    "total_potential_savings": 15000.0
                }
            ]
        }
    }


# ===== Эндпоинты =====
@router.get(
    "",
    response_model=DashboardResponse,
    summary="Получить данные дашборда",
    description="""
Возвращает полную информацию для главной страницы дашборда.

**Требуется авторизация.**

**Включает:**
- **Статистика** — баланс, доходы/расходы за месяц, процент сбережений
- **Последние транзакции** — 5 последних операций
- **Расходы по категориям** — распределение расходов за текущий месяц
- **Доходы по категориям** — распределение доходов за текущий месяц  
- **Тренд за 30 дней** — динамика доходов/расходов по дням
- **Напоминания** — ближайшие 5 активных напоминаний
- **Подозрительные транзакции** — транзакции, помеченные как подозрительные

**Периоды:**
- Статистика расходов/доходов — с 1 числа текущего месяца
- Общий баланс — за всё время
- Тренд — последние 30 дней
    """,
    response_description="Данные дашборда",
    responses={
        200: {
            "description": "Успешный ответ с данными дашборда",
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
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить данные дашборда.
    
    Возвращает агрегированную информацию о финансах пользователя
    для отображения на главной странице приложения.
    """
    now = datetime.now(timezone.utc)
    
    # Текущий месяц: с 1 числа по сегодня
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Для динамики берём последние 30 дней
    month_ago = now - timedelta(days=30)
    
    # Транзакции за текущий месяц (для категорий и статистики)
    transactions = db.query(Transaction).options(
        joinedload(Transaction.category)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= current_month_start
    ).all()
    
    # Транзакции за 30 дней (для динамики)
    trend_transactions = db.query(Transaction).options(
        joinedload(Transaction.category)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= month_ago
    ).all()
    
    # Суммы за текущий месяц (для карточек доходы/расходы)
    month_income = sum(float(t.amount) for t in transactions if t.amount > 0)
    month_expense = abs(sum(float(t.amount) for t in transactions if t.amount < 0))
    
    # Баланс за ВСЁ ВРЕМЯ (не обнуляется каждый месяц)
    all_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    all_income = sum(float(t.amount) for t in all_transactions if t.amount > 0)
    all_expense = abs(sum(float(t.amount) for t in all_transactions if t.amount < 0))
    total_balance = all_income - all_expense
    
    # Накопления = % дохода сохранённый в этом месяце
    savings_rate = (month_income - month_expense) / month_income * 100 if month_income > 0 else 0
    
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
    
    # Расходы по категориям (включая "Без категории")
    spending_by_category = []
    expense_totals = {}
    
    for t in transactions:
        if t.amount < 0:
            cat_id = t.category_id or 0
            cat_name = t.category.name if t.category else "Без категории"
            cat_color = t.category.color if t.category else "#6B7280"
            cat_icon = t.category.icon if t.category else "•"
            
            if cat_id not in expense_totals:
                expense_totals[cat_id] = {
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "category_icon": cat_icon,
                    "category_color": cat_color,
                    "amount": 0,
                }
            expense_totals[cat_id]["amount"] += abs(float(t.amount))
    
    spending_by_category = list(expense_totals.values())
    spending_by_category.sort(key=lambda x: x["amount"], reverse=True)

    # Тренд по дням за последние 30 дней
    monthly_trend = []
    trend_by_day = {}
    for t in trend_transactions:
        day = t.transaction_date.strftime("%Y-%m-%d")
        if day not in trend_by_day:
            trend_by_day[day] = {"date": day, "income": 0, "expense": 0}
        if t.amount > 0:
            trend_by_day[day]["income"] += float(t.amount)
        else:
            trend_by_day[day]["expense"] += abs(float(t.amount))
    
    monthly_trend = [v for k, v in sorted(trend_by_day.items())]

    # Доходы по категориям
    income_by_category = []
    income_totals = {}
    
    for t in transactions:
        if t.amount > 0:
            cat_id = t.category_id or 0
            cat_name = t.category.name if t.category else "Другой доход"
            cat_color = t.category.color if t.category else "#22c55e"
            cat_icon = t.category.icon if t.category else "💰"
            
            if cat_id not in income_totals:
                income_totals[cat_id] = {
                    "category_id": cat_id,
                    "category": cat_name,
                    "name": cat_name,
                    "amount": 0,
                    "color": cat_color,
                    "icon": cat_icon,
                }
            income_totals[cat_id]["amount"] += float(t.amount)
    
    income_by_category = list(income_totals.values())
    income_by_category.sort(key=lambda x: x["amount"], reverse=True)
    
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
    
    # Подозрительные транзакции
    suspicious = db.query(Transaction).options(
        joinedload(Transaction.category)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.is_suspicious == True
    ).order_by(Transaction.transaction_date.desc()).limit(5).all()
    
    suspicious_transactions = []
    for t in suspicious:
        suspicious_transactions.append({
            "id": t.id,
            "amount": float(t.amount),
            "description": t.description,
            "category_id": t.category_id,
            "category_name": t.category.name if t.category else "Без категории",
            "transaction_date": t.transaction_date.isoformat(),
            "suspicious_reason": t.suspicious_reason or "Подозрительная активность",
        })
    
    return {
        "stats": {
            "total_balance": total_balance,
            "total_income": month_income,
            "total_expense": month_expense,
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
        "monthly_trend": monthly_trend,
        "upcoming_reminders": upcoming_reminders,
        "suspicious_transactions": suspicious_transactions,
        "income_by_category": income_by_category,
    }


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Получить аналитику расходов",
    description="""
Возвращает детальную аналитику по доходам и расходам за выбранный период.

**Требуется авторизация.**

**Параметры периода:**
- `period` — предустановленный период: `week`, `month`, `quarter`, `year`
- `date_from` / `date_to` — произвольный диапазон дат (ISO 8601)

Если указаны `date_from` и `date_to`, параметр `period` игнорируется.

**Включает:**
- Расходы по категориям (для PieChart)
- Доходы по категориям
- Расходы по дням (для BarChart)
- Тренд доходов/расходов (для LineChart)
- Сравнение доходов и расходов
- Средняя сумма транзакции
    """,
    response_description="Аналитические данные",
    responses={
        200: {
            "description": "Успешный ответ с аналитикой",
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
async def get_analytics(
    period: str = Query(
        "month",
        description="Период анализа",
        examples=["week", "month", "quarter", "year"],
        enum=["week", "month", "quarter", "year"]
    ),
    date_from: Optional[str] = Query(
        None,
        description="Начало периода (ISO 8601)",
        examples=["2024-01-01"]
    ),
    date_to: Optional[str] = Query(
        None,
        description="Конец периода (ISO 8601)",
        examples=["2024-01-31"]
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Аналитика расходов.
    
    Возвращает детальную статистику по транзакциям
    для построения графиков и диаграмм.
    """
    now = datetime.now(timezone.utc)
    
    # Определяем период
    if date_from and date_to:
        try:
            start_date = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
            end_date = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            start_date = now - timedelta(days=30)
            end_date = now
    else:
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
        end_date = now
    
    transactions = db.query(Transaction).options(
        joinedload(Transaction.category)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
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
        day_key = t.transaction_date.strftime("%Y-%m-%d")
        day_label = t.transaction_date.strftime("%d.%m")
        if day_key not in trend_data:
            trend_data[day_key] = {"date": day_label, "sort_key": day_key, "income": 0, "expense": 0}
        
        if t.amount > 0:
            trend_data[day_key]["income"] += float(t.amount)
        else:
            trend_data[day_key]["expense"] += abs(float(t.amount))
    
    # Сортируем по дате
    spending_trend = [
        {"date": v["date"], "income": v["income"], "expense": v["expense"]}
        for v in sorted(trend_data.values(), key=lambda x: x["sort_key"])
    ]
    
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
    
    # Доходы по категориям
    income_by_category = []
    income_totals = {}
    
    for t in transactions:
        if t.amount > 0:
            cat_id = t.category_id or 0
            cat_name = t.category.name if t.category else "Другой доход"
            cat_color = t.category.color if t.category else "#22c55e"
            cat_icon = t.category.icon if t.category else "💰"
            
            if cat_id not in income_totals:
                income_totals[cat_id] = {
                    "category_id": cat_id,
                    "category": cat_name,
                    "name": cat_name,
                    "amount": 0,
                    "color": cat_color,
                }
            income_totals[cat_id]["amount"] += float(t.amount)
    
    income_by_category = list(income_totals.values())
    income_by_category.sort(key=lambda x: x["amount"], reverse=True)

    return {
        "spending_by_category": spending_by_category,
        "income_by_category": income_by_category,
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


@router.get(
    "/predictions",
    response_model=PredictionsResponse,
    summary="Получить прогнозы на следующий месяц",
    description="""
Возвращает прогнозы доходов и расходов на следующий месяц.

**Требуется авторизация.**

**Алгоритм прогнозирования:**
- Анализируются транзакции за последние 90 дней
- Используется взвешенное среднее (последние месяцы важнее)
- Для каждой категории определяется тренд (рост/падение/стабильно)

**Веса по месяцам:**
- Последний месяц: 50%
- Предпоследний: 30%  
- Позапрошлый: 20%

**Тренды категорий:**
- `up` — рост более 15%
- `down` — падение более 15%
- `stable` — изменение в пределах ±15%
    """,
    response_description="Прогнозы на следующий месяц",
    responses={
        200: {
            "description": "Успешный ответ с прогнозами",
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
async def get_predictions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Прогнозы расходов на следующий месяц.
    
    Использует исторические данные за 90 дней
    для построения прогноза с учётом трендов.
    """
    now = datetime.now(timezone.utc)
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
            "recommendations": ["Добавьте транзакции для получения прогнозов"],
        }
    
    # ======== Разбивка по месяцам для точного прогноза ========
    # Группируем транзакции по месяцам
    monthly_data = {}
    for t in transactions:
        month_key = t.transaction_date.strftime("%Y-%m")
        if month_key not in monthly_data:
            monthly_data[month_key] = {"income": 0, "expense": 0, "categories": {}}
        
        if t.amount > 0:
            monthly_data[month_key]["income"] += float(t.amount)
        else:
            monthly_data[month_key]["expense"] += abs(float(t.amount))
            
            cat_id = t.category_id or 0
            cat_name = t.category.name if t.category else "Другое"
            cat_color = t.category.color if t.category else "#6B7280"
            
            if cat_id not in monthly_data[month_key]["categories"]:
                monthly_data[month_key]["categories"][cat_id] = {
                    "name": cat_name,
                    "color": cat_color,
                    "amount": 0,
                    "count": 0,
                }
            monthly_data[month_key]["categories"][cat_id]["amount"] += abs(float(t.amount))
            monthly_data[month_key]["categories"][cat_id]["count"] += 1
    
    sorted_months = sorted(monthly_data.keys())
    num_months = len(sorted_months)
    
    # ======== Прогноз с весами (свежие месяцы важнее) ========
    # Веса: последний месяц важнее предыдущих
    if num_months == 1:
        weights = [1.0]
    elif num_months == 2:
        weights = [0.35, 0.65]
    else:
        weights = [0.2, 0.3, 0.5]
        # Если месяцев больше 3, берём последние 3
        sorted_months = sorted_months[-3:]
        num_months = 3
    
    # Взвешенное среднее доходов и расходов
    predicted_income = 0
    predicted_expense = 0
    for i, month_key in enumerate(sorted_months):
        w = weights[i]
        predicted_income += monthly_data[month_key]["income"] * w
        predicted_expense += monthly_data[month_key]["expense"] * w
    
    # ======== Прогноз по категориям ========
    # Собираем все категории
    all_categories = {}
    for t in transactions:
        if t.amount < 0:
            cat_id = t.category_id or 0
            if cat_id not in all_categories:
                all_categories[cat_id] = {
                    "name": t.category.name if t.category else "Другое",
                    "color": t.category.color if t.category else "#6B7280",
                }
    
    by_category = []
    for cat_id, cat_info in all_categories.items():
        # Взвешенный прогноз по категории
        cat_predicted = 0
        for i, month_key in enumerate(sorted_months):
            w = weights[i]
            cat_data = monthly_data[month_key]["categories"].get(cat_id)
            if cat_data:
                cat_predicted += cat_data["amount"] * w
        
        # Тренд: сравниваем последний месяц с предпоследним
        if len(sorted_months) >= 2:
            last = monthly_data[sorted_months[-1]]["categories"].get(cat_id, {}).get("amount", 0)
            prev = monthly_data[sorted_months[-2]]["categories"].get(cat_id, {}).get("amount", 0)
            
            if prev > 0:
                change_pct = ((last - prev) / prev) * 100
                if change_pct > 15:
                    trend = "up"
                elif change_pct < -15:
                    trend = "down"
                else:
                    trend = "stable"
            else:
                trend = "up" if last > 0 else "stable"
        else:
            trend = "stable"
        
        if cat_predicted > 0:
            by_category.append({
                "category_id": cat_id,
                "name": cat_info["name"],
                "color": cat_info["color"],
                "predicted_amount": round(cat_predicted, 2),
                "trend": trend,
            })
    
    by_category.sort(key=lambda x: x["predicted_amount"], reverse=True)

    return {
        "next_month_total": round(predicted_income - predicted_expense, 2),
        "next_month_expense": round(predicted_expense, 2),
        "next_month_income": round(predicted_income, 2),
        "by_category": by_category,
        "trends": [],
        "recommendations": [],
    }


@router.get(
    "/tips",
    response_model=TipsResponse,
    summary="Получить советы по экономии",
    description="""
Возвращает персонализированные советы по экономии на основе анализа расходов.

**Требуется авторизация.**

**Источники рекомендаций:**
1. **ML-модель** (если загружена) — анализирует паттерны расходов
2. **Правила** — срабатывают при превышении порогов:
   - Расходы > 90% доходов → критический уровень
   - Расходы > 70% доходов → выше нормы
   - Развлечения/шоппинг > 20% → высокие траты
   - Еда > 35% → много на еду
   - Транспорт > 15% → оптимизация

**Приоритеты:**
- `high` — потенциальная экономия > 5000 ₽
- `medium` — экономия 1000-5000 ₽
- `low` — менее 1000 ₽ или общие советы
    """,
    response_description="Список советов по экономии",
    responses={
        200: {
            "description": "Успешный ответ с советами",
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
async def get_saving_tips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Советы по экономии на основе ML-модели.
    
    Анализирует расходы за 90 дней и генерирует
    персонализированные рекомендации по экономии.
    """
    from app.ml.model_loader import registry
    import logging
    logger = logging.getLogger(__name__)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=90)
    
    transactions = db.query(Transaction).options(
        joinedload(Transaction.category)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= start_date
    ).all()
    
    if not transactions:
        return {"tips": [], "total_potential_savings": 0}
    
    total_income = sum(float(t.amount) for t in transactions if t.amount > 0)
    total_expense = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
    days_range = (now - min(t.transaction_date for t in transactions)).days or 1
    months = max(days_range / 30, 1)
    monthly_income = total_income / months
    monthly_expense = total_expense / months
    
    cat_totals = {}
    for t in transactions:
        if t.amount < 0:
            cat_name = t.category.name if t.category else "Другое"
            cat_code = t.category.code if t.category else "other"
            cat_totals[cat_code] = {
                "name": cat_name,
                "total": cat_totals.get(cat_code, {}).get("total", 0) + abs(float(t.amount)),
            }
    
    tips = []
    total_potential_savings = 0
    tip_id = 1
    
    CATEGORY_MAP = {
        "food": "groceries",
        "restaurants": "restaurants",
        "transport": "transport",
        "housing": "utilities",
        "shopping": "shopping",
        "health": "health",
        "entertainment": "entertainment",
        "education": "education",
        "subscriptions": "subscriptions",
        "beauty": "shopping",
        "sports": "health",
        "telecom": "subscriptions",
        "insurance": "utilities",
        "taxes": "utilities",
        "travel": "entertainment",
        "pets": "shopping",
        "charity": "shopping",
        "cash": "shopping",
        "other": "shopping",
        "salary": "income",
        "transfers": "utilities",
    }
    
    recommender = registry.get("recommender")
    if recommender:
        ml_transactions = []
        for t in transactions:
            cat_code = t.category.code if t.category else "other"
            ml_category = CATEGORY_MAP.get(cat_code, "shopping")
            is_weekend = 1 if t.transaction_date.weekday() >= 5 else 0
            ml_transactions.append({
                "type": "income" if t.amount > 0 else "expense",
                "amount": abs(float(t.amount)),
                "category": ml_category,
                "weekend": is_weekend,
                "merchant": t.merchant_name or "",
            })
        
        try:
            ml_recs = recommender.predict(ml_transactions)
            for rec in ml_recs:
                if isinstance(rec, dict):
                    savings = rec.get("potential_savings", 0) or 0
                    total_potential_savings += savings
                    tips.append({
                        "id": tip_id,
                        "title": rec.get("title", "Совет"),
                        "description": rec.get("description", ""),
                        "potential_savings": savings if savings > 0 else None,
                        "category": None,
                        "priority": "high" if savings > 5000 else "medium" if savings > 1000 else "low",
                    })
                    tip_id += 1
                elif isinstance(rec, str):
                    tips.append({
                        "id": tip_id,
                        "title": rec,
                        "description": "",
                        "potential_savings": None,
                        "category": None,
                        "priority": "medium",
                    })
                    tip_id += 1
        except Exception as e:
            logger.error(f"ML recommender error: {e}")
    
    if not tips:
        if monthly_income > 0:
            expense_ratio = monthly_expense / monthly_income
            if expense_ratio > 0.9:
                potential = round(monthly_expense * 0.15)
                total_potential_savings += potential
                tips.append({
                    "id": tip_id, "title": "⚠️ Критический уровень расходов",
                    "description": f"Вы тратите {expense_ratio*100:.0f}% от доходов. Рекомендуем сократить расходы минимум на 15%.",
                    "potential_savings": potential, "category": None, "priority": "high",
                })
                tip_id += 1
            elif expense_ratio > 0.7:
                potential = round(monthly_expense * 0.1)
                total_potential_savings += potential
                tips.append({
                    "id": tip_id, "title": "📊 Расходы выше нормы",
                    "description": f"Вы тратите {expense_ratio*100:.0f}% от доходов. Оптимальный уровень — 60-70%.",
                    "potential_savings": potential, "category": None, "priority": "medium",
                })
                tip_id += 1
        
        for code, info in sorted(cat_totals.items(), key=lambda x: x[1]["total"], reverse=True):
            monthly_cat = info["total"] / months
            share = info["total"] / total_expense * 100 if total_expense > 0 else 0
            
            if code in ("entertainment", "shopping") and share > 20:
                potential = round(monthly_cat * 0.3)
                total_potential_savings += potential
                tips.append({
                    "id": tip_id, "title": f"🛍️ Высокие расходы на «{info['name']}»",
                    "description": f"Категория занимает {share:.0f}% расходов ({round(monthly_cat):,} ₽/мес). Попробуйте сократить на 30%.".replace(",", " "),
                    "potential_savings": potential, "category": code.upper(), "priority": "high",
                })
                tip_id += 1
            elif code == "food" and share > 35:
                potential = round(monthly_cat * 0.15)
                total_potential_savings += potential
                tips.append({
                    "id": tip_id, "title": "🍔 Много тратите на еду",
                    "description": f"Еда занимает {share:.0f}% бюджета. Составляйте список покупок заранее.",
                    "potential_savings": potential, "category": "FOOD", "priority": "medium",
                })
                tip_id += 1
            elif code == "transport" and share > 15:
                potential = round(monthly_cat * 0.2)
                total_potential_savings += potential
                tips.append({
                    "id": tip_id, "title": "🚗 Оптимизируйте транспорт",
                    "description": f"Транспорт — {share:.0f}% расходов. Рассмотрите общественный транспорт или каршеринг.",
                    "potential_savings": potential, "category": "TRANSPORT", "priority": "low",
                })
                tip_id += 1
        
        if monthly_income > monthly_expense:
            savings = round(monthly_income - monthly_expense)
            tips.append({
                "id": tip_id, "title": "💰 Откладывайте излишки",
                "description": f"У вас остаётся ~{savings:,} ₽/мес. Переводите их на накопительный счёт автоматически.".replace(",", " "),
                "potential_savings": None, "category": None, "priority": "low",
            })
            tip_id += 1
    
    return {
        "tips": tips,
        "total_potential_savings": round(total_potential_savings),
    }