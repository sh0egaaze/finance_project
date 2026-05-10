from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, condecimal, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import Transaction, Category, User
from app.routers.auth import get_current_user
from app.ml.model_loader import registry
import logging
from app.ml.categorizer import categorize
from app.ml.anomaly_detector import detect_anomaly
from sqlalchemy import func as sql_func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])

limiter = Limiter(key_func=get_remote_address)

class TransactionCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=500, description="Описание транзакции")
    amount: Decimal = Field(..., gt=0, description="Сумма > 0. Если указан флаг is_income")
    is_income: bool = Field(..., description="True = доход, False = расход")
    category_id: Optional[int] = Field(None, description="ID категории")
    transaction_date: Optional[str] = None

class TransactionUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    amount: Optional[Decimal] = Field(None, gt=0)
    is_income: Optional[bool] = None
    category_id: Optional[int] = None
    category_manual: Optional[bool] = None
    transaction_date: Optional[str] = None

class TransactionResponse(BaseModel):
    id: int
    description: str
    amount: Decimal
    is_income: bool
    category_id: Optional[int]
    transaction_date: Optional[datetime]
    created_at: datetime
    source: Optional[str] = None
    
    class Config:
        from_attributes = True

def get_own_transaction(
    tx_id: int,
    db: Session,
    user: User,
) -> Transaction:
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.user_id == user.id,   
    ).first()
    if not tx:
        raise HTTPException(
            status_code=404,
            detail="Транзакция не найдена или не принадлежит вам",
        )
    return tx

class SmartInputRequest(BaseModel):
    text: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="Текст для парсинга транзакции"
    )
    
    class Config:
        from_attributes = True

@router.put("/{tx_id}")
async def update_transaction(
    tx_id: int,
    data: TransactionUpdate,   
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.user_id == user.id
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Транзакция не найдена")

    update_data = data.model_dump(exclude_unset=True)
    
    new_amount = update_data.pop('amount', None)
    new_is_income = update_data.pop('is_income', None)
    
    if new_amount is not None:
        if new_is_income is not None:
            tx.amount = new_amount if new_is_income else -new_amount
        else:
            tx.amount = new_amount if tx.amount >= 0 else -new_amount
    elif new_is_income is not None and tx.amount is not None:
        tx.amount = abs(tx.amount) if new_is_income else -abs(tx.amount)
    
    new_date = update_data.pop('transaction_date', None)
    if new_date:
        try:
            from datetime import datetime
            tx.transaction_date = datetime.fromisoformat(new_date)
        except ValueError:
            pass
    
    for field, value in update_data.items():
        setattr(tx, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Недопустимые данные"
        )
    return {"status": "updated"}

@router.get("/{tx_id}")
async def get_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return get_own_transaction(tx_id, db, user)

@router.delete("/{tx_id}", status_code=204)
async def delete_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    tx = get_own_transaction(tx_id, db, user)
    try:
        db.delete(tx)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при удалении транзакции"
        )

@router.get("")
async def get_transactions(
    limit: int = Query(20, ge=1, le=100, description="Макс. кол-во записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
    is_suspicious: Optional[bool] = Query(None, description="Фильтр по подозрительности"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получение списка транзакций с пагинацией"""
    query = db.query(Transaction).filter(
        Transaction.user_id == user.id
    )
    
    if is_suspicious is not None:
        query = query.filter(Transaction.is_suspicious == is_suspicious)
    
    total = query.count()
    
    transactions = query.order_by(
        Transaction.transaction_date.desc()
    ).offset(offset).limit(limit).all()
    
    items = []
    for t in transactions:
        items.append({
            "id": t.id,
            "description": t.description,
            "amount": float(t.amount),
            "is_income": t.amount > 0,
            "category_id": t.category_id,
            "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "source": t.source,
            "is_suspicious": t.is_suspicious,
            "suspicious_reason": t.suspicious_reason,
        })
    
    return {"items": items, "total": total, "page": 1, "per_page": limit}


@router.post("", status_code=201)
async def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Создание новой транзакции"""
    from app.ml.anomaly_detector import detect_anomaly
    from sqlalchemy import func as sql_func
    
    tx_date = datetime.now(timezone.utc)
    if data.transaction_date:
        try:
            tx_date = datetime.fromisoformat(data.transaction_date)
        except ValueError:
            pass
    
    amount = data.amount if data.is_income else -data.amount
    
    tx = Transaction(
        user_id=user.id,
        description=data.description,
        amount=amount,
        category_id=data.category_id,
        transaction_date=tx_date,
    )
    
    # === Проверка на подозрительность ===
    abs_amount = abs(float(amount))
    hour = tx_date.hour
    day_of_week = tx_date.weekday()
    
    # Средняя сумма пользователя за 3 месяца
    three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
    user_avg = db.query(sql_func.avg(sql_func.abs(Transaction.amount))).filter(
        Transaction.user_id == user.id,
        Transaction.transaction_date >= three_months_ago
    ).scalar() or abs_amount
    
    # Код категории
    category_code = "other"
    if data.category_id:
        cat = db.query(Category).filter(Category.id == data.category_id).first()
        if cat:
            category_code = cat.code
    
    # ML проверка
    try:
        result = detect_anomaly({
            "amount": abs_amount,
            "hour": hour,
            "day_of_week": day_of_week,
            "category": category_code,
            "user_avg_amount": float(user_avg),
            "is_weekend": 1 if day_of_week >= 5 else 0,
        })
        if result.get("is_suspicious"):
            tx.is_suspicious = True
            tx.suspicious_reason = result.get("reason") or "Нетипичная транзакция"
            logger.info(f"Подозрительно: {abs_amount}₽ — {tx.suspicious_reason}")
    except Exception as e:
        logger.warning(f"ML недоступен: {e}")
    
    # Эвристики (fallback)
    if not tx.is_suspicious and not data.is_income:
        # Средняя по категории
        if data.category_id:
            cat_avg = db.query(sql_func.avg(sql_func.abs(Transaction.amount))).filter(
                Transaction.user_id == user.id,
                Transaction.category_id == data.category_id,
                Transaction.transaction_date >= three_months_ago
            ).scalar()
            if cat_avg and float(cat_avg) > 0 and abs_amount > float(cat_avg) * 3:
                tx.is_suspicious = True
                tx.suspicious_reason = f"Сумма в {abs_amount/float(cat_avg):.1f} раз выше средней для этой категории"
        
        # Ночное время
        if not tx.is_suspicious and 2 <= hour <= 5 and abs_amount > 3000:
            tx.is_suspicious = True
            tx.suspicious_reason = "Крупная транзакция в ночное время"
        
        # Крупная сумма
        if not tx.is_suspicious and abs_amount > 30000:
            tx.is_suspicious = True
            tx.suspicious_reason = f"Крупная сумма: {abs_amount:,.0f}₽".replace(",", " ")
    
    try:
        db.add(tx)
        db.commit()
        db.refresh(tx)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ошибка при создании: категория не принадлежит вам"
        )
    return {
        "id": tx.id,
        "description": tx.description,
        "amount": float(tx.amount),
        "is_income": float(tx.amount) > 0,
        "category_id": tx.category_id,
        "transaction_date": tx.transaction_date.isoformat() if tx.transaction_date else None,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "source": tx.source,
    }

@router.post("/smart-input")
@limiter.limit("30/minute")
async def smart_input(
    request: Request,
    data: SmartInputRequest,
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    # Подключаем ML-модуль через .get() с проверкой на None
    nlp_parser = registry.get("nlp_parser")
    categorizer = registry.get("categorizer")
    
    if not nlp_parser:
        raise HTTPException(status_code=503, detail="NLP-парсер не загружен")
    
    # 1. Парсинг текста
    parsed = nlp_parser.parse(data.text)   
    
    # 2. Категоризация (умная модель загружена)
    category_id = None
    if categorizer and parsed.get("description"): 
        cat_pred = categorize(parsed["description"])
        if cat_pred.category_code in ("salary", "cash"):
            parsed["is_income"] = True
        db_cat = db.query(Category).filter(
            Category.code == cat_pred.category_code,
            Category.user_id == user.id
        ).first()
        category_id = db_cat.id if db_cat else None
        if not category_id:
            logger.warning(f"Category code {cat_pred.category_code} not found in DB")
    
    return {
        "amount": parsed["amount"],
        "description": parsed["description"],
        "category_id": category_id,
        "is_income": parsed["is_income"]
    }

@router.post("/smart-input/confirm", response_model=TransactionResponse, status_code=201)
@limiter.limit("30/minute")
async def smart_input_confirm(
    request: Request,
    data: SmartInputRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Подтверждение быстрого ввода — парсит текст и создаёт транзакцию"""
    nlp_parser = registry.get("nlp_parser")
    categorizer = registry.get("categorizer")

    if not nlp_parser:
        raise HTTPException(status_code=503, detail="NLP-парсер не загружен")

    # 1. Парсинг текста
    parsed = nlp_parser.parse(data.text)

    amount = parsed.get("amount")
    description = parsed.get("description", data.text)
    is_income = parsed.get("is_income", False)

    if not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Не удалось определить сумму из текста")

    # 2. Категоризация
    category_id = None
    cat_pred = None
    if categorizer and description:
        cat_pred = categorize(description)
        db_cat = db.query(Category).filter(
            Category.code == cat_pred.category_code,
            Category.user_id == user.id,
        ).first()
        category_id = db_cat.id if db_cat else None

    if cat_pred and cat_pred.category_code in ("salary", "cash"):
        is_income = True

    # 3. Создание транзакции
    tx = Transaction(
        user_id=user.id,
        description=description,
        amount=amount if is_income else -amount,
        category_id=category_id,
        transaction_date=datetime.now(timezone.utc),
    )

    try:
        abs_amount = abs(float(tx.amount))
        hour = tx.transaction_date.hour
        day_of_week = tx.transaction_date.weekday()
        
        three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
        user_avg = db.query(sql_func.avg(sql_func.abs(Transaction.amount))).filter(
            Transaction.user_id == user.id,
            Transaction.transaction_date >= three_months_ago
        ).scalar() or abs_amount
        
        category_code = "other"
        if tx.category_id:
            cat_obj = db.query(Category).filter(Category.id == tx.category_id).first()
            if cat_obj:
                category_code = cat_obj.code
        
        try:
            result = detect_anomaly({
                "amount": abs_amount,
                "hour": hour,
                "day_of_week": day_of_week,
                "category": category_code,
                "user_avg_amount": float(user_avg),
                "is_weekend": 1 if day_of_week >= 5 else 0,
            })
            if result.get("is_suspicious"):
                tx.is_suspicious = True
                tx.suspicious_reason = result.get("reason") or "Нетипичная транзакция"
        except Exception as e:
            logger.warning(f"ML anomaly check failed: {e}")
        
        if not tx.is_suspicious and abs_amount > 0:
            if tx.category_id:
                cat_avg = db.query(sql_func.avg(sql_func.abs(Transaction.amount))).filter(
                    Transaction.user_id == user.id,
                    Transaction.category_id == tx.category_id,
                    Transaction.transaction_date >= three_months_ago
                ).scalar()
                if cat_avg and float(cat_avg) > 0 and abs_amount > float(cat_avg) * 3:
                    tx.is_suspicious = True
                    tx.suspicious_reason = f"Сумма в {abs_amount/float(cat_avg):.1f} раз выше средней для этой категории"
            
            if not tx.is_suspicious and 2 <= hour <= 5 and abs_amount > 3000:
                tx.is_suspicious = True
                tx.suspicious_reason = "Крупная транзакция в ночное время"
            
            if not tx.is_suspicious and abs_amount > 30000:
                tx.is_suspicious = True
                tx.suspicious_reason = f"Крупная сумма: {abs_amount:,.0f}₽".replace(",", " ")
        
        db.add(tx)
        db.commit()
        db.refresh(tx)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка при создании транзакции")

    return tx