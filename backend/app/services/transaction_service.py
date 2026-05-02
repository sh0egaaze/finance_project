"""
Сервис для работы с транзакциями
"""
from typing import List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from loguru import logger

from ..models import Transaction, Category
from ..schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionFilters, TransactionStats
)
from ..ml.categorizer import MLCategorizer


class TransactionService:
    """Сервис для работы с транзакциями"""
    
    @staticmethod
    def create_transaction(
        db: Session,
        user_id: int,
        data: TransactionCreate
    ) -> Transaction:
        """
        Создать новую транзакцию.
        Автоматически категоризирует, если категория не указана.
        """
        categorizer = MLCategorizer()
        
        # Определяем категорию автоматически, если не указана
        if data.category_id is None:
            cat_result = categorizer.predict(data.description or "")
            category_code = cat_result.get("category", "other")
            confidence = Decimal(str(cat_result.get("confidence", 0.5)))
            category_manual = False
            
            # Получаем category_id по коду
            category = db.query(Category).filter(Category.code == category_code).first()
            category_id = category.id if category else None
        else:
            category_id = data.category_id
            confidence = Decimal("1.0")
            category_manual = True
        
        # Определяем знак суммы (доходы положительные, расходы отрицательные)
        amount = data.amount
        if category_id:
            category = db.query(Category).filter(Category.id == category_id).first()
            if category and category.is_income:
                amount = abs(amount)
            elif category and category.is_expense:
                amount = -abs(amount)
        
        # Создаём транзакцию
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            currency=data.currency or "RUB",
            description=data.description,
            category_id=category_id,
            category_confidence=confidence,
            category_manual=category_manual,
            source=data.source or "manual",
            transaction_date=data.transaction_date or datetime.now(timezone.utc)
        )
        
        # Проверяем на подозрительность
        TransactionService._check_suspicious(db, user_id, transaction)
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        logger.info(f"Создана транзакция {transaction.id} для пользователя {user_id}")
        return transaction
    
    @staticmethod
    def get_transactions(
        db: Session,
        user_id: int,
        filters: Optional[TransactionFilters] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Transaction], int]:
        """
        Получить список транзакций с фильтрацией и пагинацией.
        
        Returns:
            Tuple[список транзакций, общее количество]
        """
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        
        # Применяем фильтры
        if filters:
            if filters.category_id:
                query = query.filter(Transaction.category_id == filters.category_id)
            if filters.source:
                query = query.filter(Transaction.source == filters.source)
            if filters.date_from:
                query = query.filter(Transaction.transaction_date >= filters.date_from)
            if filters.date_to:
                query = query.filter(Transaction.transaction_date <= filters.date_to)
            if filters.min_amount is not None:
                query = query.filter(func.abs(Transaction.amount) >= filters.min_amount)
            if filters.max_amount is not None:
                query = query.filter(func.abs(Transaction.amount) <= filters.max_amount)
            if filters.search:
                query = query.filter(
                    Transaction.description.ilike(f"%{filters.search}%")
                )
            if filters.is_suspicious is not None:
                query = query.filter(Transaction.is_suspicious == filters.is_suspicious)
        
        # Общее количество
        total = query.count()
        
        # Сортировка и пагинация
        transactions = query.order_by(Transaction.transaction_date.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()
        
        return transactions, total
    
    @staticmethod
    def get_transaction_by_id(
        db: Session,
        user_id: int,
        transaction_id: int
    ) -> Optional[Transaction]:
        """Получить транзакцию по ID"""
        return db.query(Transaction).filter(
            and_(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id
            )
        ).first()
    
    @staticmethod
    def update_transaction(
        db: Session,
        user_id: int,
        transaction_id: int,
        data: TransactionUpdate
    ) -> Optional[Transaction]:
        """Обновить транзакцию"""
        transaction = TransactionService.get_transaction_by_id(db, user_id, transaction_id)
        if not transaction:
            return None
        
        if data.description is not None:
            transaction.description = data.description
        if data.amount is not None:
            transaction.amount = data.amount
        if data.category_id is not None:
            transaction.category_id = data.category_id
            transaction.category_manual = True
            transaction.category_confidence = Decimal("1.0")
        if data.transaction_date is not None:
            transaction.transaction_date = data.transaction_date
        if data.is_suspicious is not None:
            transaction.is_suspicious = data.is_suspicious
        
        transaction.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(transaction)
        return transaction
    
    @staticmethod
    def delete_transaction(
        db: Session,
        user_id: int,
        transaction_id: int
    ) -> bool:
        """Удалить транзакцию"""
        transaction = TransactionService.get_transaction_by_id(db, user_id, transaction_id)
        if not transaction:
            return False
        
        db.delete(transaction)
        db.commit()
        return True
    
    @staticmethod
    def get_stats(
        db: Session,
        user_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> TransactionStats:
        """Получить статистику по транзакциям"""
        if not date_from:
            date_from = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0)
        if not date_to:
            date_to = datetime.now(timezone.utc)
        
        query = db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= date_from,
                Transaction.transaction_date <= date_to
            )
        )
        
        # Доходы (положительные суммы)
        total_income = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= date_from,
                Transaction.transaction_date <= date_to,
                Transaction.amount > 0
            )
        ).scalar() or Decimal("0")
        
        # Расходы (отрицательные суммы)
        total_expense = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= date_from,
                Transaction.transaction_date <= date_to,
                Transaction.amount < 0
            )
        ).scalar() or Decimal("0")
        
        transaction_count = query.count()
        
        return TransactionStats(
            total_income=float(total_income),
            total_expense=float(abs(total_expense)),
            balance=float(total_income + total_expense),
            transaction_count=transaction_count,
            period_start=date_from,
            period_end=date_to
        )
    
    @staticmethod
    def _check_suspicious(
        db: Session,
        user_id: int,
        transaction: Transaction
    ):
        """
        Проверить транзакцию на подозрительность.
        Критерии:
        - Сумма значительно выше средней в категории
        - Необычное время (ночь)
        - Очень крупная сумма
        """
        amount = abs(float(transaction.amount))
        
        # Получаем среднюю сумму в категории за последние 3 месяца
        three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
        
        if transaction.category_id:
            avg_amount = db.query(func.avg(func.abs(Transaction.amount))).filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.category_id == transaction.category_id,
                    Transaction.transaction_date >= three_months_ago
                )
            ).scalar()
            
            # Если сумма в 5 раз больше средней - подозрительно
            if avg_amount and amount > float(avg_amount) * 5:
                transaction.is_suspicious = True
                transaction.suspicious_reason = f"Сумма в {amount/float(avg_amount):.1f} раз выше средней"
                return
        
        # Проверяем время (2:00 - 5:00 - подозрительное время)
        hour = transaction.transaction_date.hour
        if 2 <= hour <= 5 and amount > 5000:
            transaction.is_suspicious = True
            transaction.suspicious_reason = "Крупная транзакция в ночное время"
            return
        
        # Очень крупная сумма
        if amount > 50000:
            transaction.is_suspicious = True
            transaction.suspicious_reason = "Крупная сумма транзакции"
    
    @staticmethod
    def get_suspicious_transactions(
        db: Session,
        user_id: int,
        limit: int = 10
    ) -> List[Transaction]:
        """Получить подозрительные транзакции"""
        return db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.is_suspicious == True
            )
        ).order_by(Transaction.transaction_date.desc()).limit(limit).all()
    
    @staticmethod
    def confirm_transaction(
        db: Session,
        user_id: int,
        transaction_id: int,
        is_legitimate: bool
    ) -> Optional[Transaction]:
        """Подтвердить или оспорить подозрительную транзакцию"""
        transaction = TransactionService.get_transaction_by_id(db, user_id, transaction_id)
        if not transaction:
            return None
        
        if is_legitimate:
            transaction.is_suspicious = False
            transaction.suspicious_reason = None
        
        db.commit()
        db.refresh(transaction)
        return transaction
