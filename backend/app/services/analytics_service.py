"""
Сервис аналитики и прогнозирования
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from loguru import logger

from ..models import Transaction, Category


class AnalyticsService:
    """Сервис аналитики финансов"""
    
    @staticmethod
    def get_spending_by_category(
        db: Session,
        user_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict]:
        """Получить расходы по категориям"""
        if not date_from:
            date_from = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        if not date_to:
            date_to = datetime.utcnow()
        
        # Группировка по категориям
        results = db.query(
            Category.code,
            Category.name,
            Category.color,
            func.sum(func.abs(Transaction.amount)).label('total'),
            func.count(Transaction.id).label('count')
        ).join(
            Category, Transaction.category_id == Category.id
        ).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.amount < 0,  # Только расходы
                Transaction.transaction_date >= date_from,
                Transaction.transaction_date <= date_to
            )
        ).group_by(Category.code, Category.name, Category.color).all()
        
        # Общая сумма для расчёта процентов
        total_spending = sum(float(r.total) for r in results) if results else 0
        
        spending_list = []
        for result in results:
            amount = float(result.total)
            percentage = (amount / total_spending * 100) if total_spending > 0 else 0
            
            spending_list.append({
                "category": result.code,
                "category_name": result.name,
                "amount": amount,
                "percentage": round(percentage, 1),
                "transaction_count": result.count,
                "color": result.color or "#9ca3af"
            })
        
        # Сортировка по сумме
        spending_list.sort(key=lambda x: x["amount"], reverse=True)
        return spending_list
    
    @staticmethod
    def get_monthly_stats(
        db: Session,
        user_id: int,
        months: int = 6
    ) -> List[Dict]:
        """Получить статистику по месяцам"""
        stats = []
        now = datetime.utcnow()
        
        for i in range(months - 1, -1, -1):
            # Вычисляем начало и конец месяца
            month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1)
            
            # Доходы
            income = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.amount > 0,
                    Transaction.transaction_date >= month_start,
                    Transaction.transaction_date < month_end
                )
            ).scalar() or Decimal("0")
            
            # Расходы
            expense = db.query(func.sum(func.abs(Transaction.amount))).filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.amount < 0,
                    Transaction.transaction_date >= month_start,
                    Transaction.transaction_date < month_end
                )
            ).scalar() or Decimal("0")
            
            balance = float(income) - float(expense)
            savings_rate = (balance / float(income) * 100) if income > 0 else 0
            
            stats.append({
                "month": month_start.strftime("%Y-%m"),
                "income": float(income),
                "expense": float(expense),
                "balance": balance,
                "savings_rate": round(savings_rate, 1)
            })
        
        return stats
    
    @staticmethod
    def predict_next_month(
        db: Session,
        user_id: int
    ) -> Dict:
        """
        Прогноз расходов на следующий месяц.
        Использует простую модель на основе скользящего среднего.
        """
        # Получаем данные за последние 6 месяцев
        monthly_stats = AnalyticsService.get_monthly_stats(db, user_id, months=6)
        
        expenses = [s["expense"] for s in monthly_stats]
        incomes = [s["income"] for s in monthly_stats]
        
        if len(expenses) < 2:
            predicted_expense = expenses[-1] if expenses else 0
            predicted_income = incomes[-1] if incomes else 0
            confidence = 0.3
        else:
            # Скользящее среднее с учётом тренда
            weights = [0.1, 0.15, 0.15, 0.2, 0.2, 0.2][:len(expenses)]
            weights = [w / sum(weights) for w in weights]
            
            predicted_expense = sum(e * w for e, w in zip(expenses, weights))
            predicted_income = sum(i * w for i, w in zip(incomes, weights))
            
            # Добавляем тренд
            if len(expenses) >= 3:
                trend = (expenses[-1] - expenses[-3]) / 3
                predicted_expense += trend
            
            confidence = min(0.85, 0.5 + len(expenses) * 0.05)
        
        # Прогноз по категориям
        category_predictions = []
        current_spending = AnalyticsService.get_spending_by_category(db, user_id)
        
        for spending in current_spending[:5]:  # Топ-5 категорий
            predicted = spending["amount"] * 1.02  # Небольшой рост
            change = 2.0
            
            category_predictions.append({
                "category": spending["category"],
                "category_name": spending["category_name"],
                "current_month": spending["amount"],
                "predicted_next_month": predicted,
                "change_percent": change,
                "trend": "stable"
            })
        
        recommendations = []
        if predicted_expense > predicted_income * 0.9:
            recommendations.append("⚠️ Прогнозируемые расходы близки к доходам. Рекомендуем пересмотреть бюджет.")
        else:
            recommendations.append("✅ Ваши финансы выглядят стабильно!")
        
        return {
            "predicted_total_expense": max(0, predicted_expense),
            "predicted_total_income": max(0, predicted_income),
            "confidence": round(confidence, 2),
            "by_category": category_predictions,
            "recommendations": recommendations,
            "prediction_date": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_saving_tips(
        db: Session,
        user_id: int
    ) -> List[Dict]:
        """Получить персонализированные советы по экономии"""
        tips = []
        spending = AnalyticsService.get_spending_by_category(db, user_id)
        
        tip_id = 1
        for s in spending:
            if s["category"] == "subscriptions" and s["amount"] > 1000:
                tips.append({
                    "id": tip_id,
                    "title": "Проверьте подписки",
                    "description": f"Вы тратите {s['amount']:.0f}₽ на подписки. Возможно, некоторые из них не используются.",
                    "category": "subscriptions",
                    "potential_saving": s["amount"] * 0.3,
                    "priority": "medium",
                    "icon": "📱"
                })
                tip_id += 1
            
            if s["category"] == "food" and s["amount"] > 15000:
                tips.append({
                    "id": tip_id,
                    "title": "Оптимизируйте расходы на еду",
                    "description": "Попробуйте готовить дома чаще и планировать покупки заранее.",
                    "category": "food",
                    "potential_saving": s["amount"] * 0.2,
                    "priority": "high",
                    "icon": "🍽️"
                })
                tip_id += 1
            
            if s["category"] == "entertainment" and s["percentage"] > 15:
                tips.append({
                    "id": tip_id,
                    "title": "Развлечения занимают большую долю",
                    "description": f"На развлечения уходит {s['percentage']:.0f}% бюджета. Рассмотрите бесплатные альтернативы.",
                    "category": "entertainment",
                    "potential_saving": s["amount"] * 0.25,
                    "priority": "low",
                    "icon": "🎮"
                })
                tip_id += 1
        
        if not tips:
            tips.append({
                "id": 1,
                "title": "Отличная работа!",
                "description": "Ваши расходы выглядят сбалансированно. Продолжайте отслеживать траты.",
                "category": "general",
                "potential_saving": 0,
                "priority": "low",
                "icon": "✨"
            })
        
        return tips
    
    @staticmethod
    def get_dashboard_stats(
        db: Session,
        user_id: int
    ) -> Dict:
        """Получить статистику для дашборда"""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Доходы за месяц
        monthly_income = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.amount > 0,
                Transaction.transaction_date >= month_start
            )
        ).scalar() or Decimal("0")
        
        # Расходы за месяц
        monthly_expense = db.query(func.sum(func.abs(Transaction.amount))).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.amount < 0,
                Transaction.transaction_date >= month_start
            )
        ).scalar() or Decimal("0")
        
        # Общий баланс
        total_balance = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id
        ).scalar() or Decimal("0")
        
        savings = float(monthly_income) - float(monthly_expense)
        savings_rate = (savings / float(monthly_income) * 100) if monthly_income > 0 else 0
        
        # Подозрительные транзакции
        suspicious_count = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.is_suspicious == True
            )
        ).scalar() or 0
        
        return {
            "total_balance": float(total_balance),
            "monthly_income": float(monthly_income),
            "monthly_expense": float(monthly_expense),
            "savings_this_month": savings,
            "savings_rate": round(savings_rate, 1),
            "spending_by_category": AnalyticsService.get_spending_by_category(db, user_id),
            "monthly_trend": AnalyticsService.get_monthly_stats(db, user_id),
            "suspicious_count": suspicious_count,
            "upcoming_reminders_count": 0
        }
